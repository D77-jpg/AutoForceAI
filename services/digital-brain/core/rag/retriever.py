"""
core/rag/retriever.py — 混合检索（向量 + 词法）

- Postgres：pgvector 余弦距离 `<=>` + HNSW 索引
- SQLite：Python 端点积（embedder 已 L2 归一化，点积 = 余弦）
- 无嵌入模型 / 向量为空时自动降级为词法检索（关键词重叠打分）
- 返回结构与 brain_router 约定一致：content / doc_name / score / kb_id / doc_id
"""
from __future__ import annotations

import logging
import math
import re
from typing import Any, Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.orm import Session, joinedload

from core.rag.embedder import EmbeddingClient, EmbeddingUnavailable
from database.shared_models import KnowledgeChunk, KnowledgeDoc

logger = logging.getLogger(__name__)

_TOKEN_RE = re.compile(r"[A-Za-z0-9\u4e00-\u9fff]{2,}")


def _tokenize(q: str) -> List[str]:
    return [t.lower() for t in _TOKEN_RE.findall(q or "")]


def _lexical_score(chunk_text: str, tokens: List[str]) -> float:
    if not tokens or not chunk_text:
        return 0.0
    hay = chunk_text.lower()
    hits = sum(1 for t in tokens if t in hay)
    return hits / max(len(tokens), 1)


class KnowledgeRetriever:
    def __init__(self, db: Optional[Session] = None):
        self.db = db
        self.embedder = EmbeddingClient(db)

    def _is_postgres(self) -> bool:
        try:
            return self.db.bind.dialect.name == "postgresql"  # type: ignore[union-attr]
        except Exception:
            return False

    def search_multi_kb(
        self,
        kb_ids: List[int],
        query: str,
        top_k: int = 5,
        score_threshold: float = 0.35,
    ) -> List[Dict[str, Any]]:
        if not kb_ids or not query or not query.strip():
            return []
        if self.db is None:
            logger.warning("[RAG] KnowledgeRetriever 未绑定数据库会话")
            return []

        top_k = max(1, min(int(top_k or 5), 20))
        threshold = float(score_threshold if score_threshold is not None else 0.35)

        lexical = self._lexical_search(kb_ids, query, top_k * 3)
        vector: List[Dict[str, Any]] = []
        if self.embedder.available:
            try:
                vector = self._vector_search(kb_ids, query, top_k * 3)
            except EmbeddingUnavailable as exc:
                logger.info("[RAG] 向量检索不可用，降级词法：%s", exc)
            except Exception as exc:
                logger.warning("[RAG] 向量检索失败，降级词法：%s", exc)

        merged = self._merge(vector, lexical, top_k, threshold)
        logger.info(
            "[RAG] query=%r kb=%s vector=%d lexical=%d merged=%d (embedder=%s)",
            query[:60], kb_ids, len(vector), len(lexical), len(merged),
            self.embedder.describe,
        )
        return merged

    # ---------- 向量 ----------

    def _vector_search(self, kb_ids: List[int], query: str, limit: int) -> List[Dict[str, Any]]:
        qvec = self.embedder.embed_query(query)
        if self._is_postgres():
            return self._pgvector_search(kb_ids, qvec, limit)
        return self._sqlite_vector_search(kb_ids, qvec, limit)

    def _pgvector_search(self, kb_ids: List[int], qvec: List[float], limit: int) -> List[Dict[str, Any]]:
        sql = text(
            """
            SELECT c.id, c.doc_id, c.chunk_text, c.chunk_index,
                   d.filename AS doc_name, d.kb_id,
                   1 - (c.embedding <=> :qvec) AS score
            FROM knowledge_chunks c
            JOIN knowledge_docs d ON d.id = c.doc_id
            WHERE d.kb_id = ANY(:kb_ids)
              AND d.status IN ('embedded', 'indexed')
              AND c.embedding IS NOT NULL
            ORDER BY c.embedding <=> :qvec
            LIMIT :lim
            """
        )
        rows = self.db.execute(sql, {"qvec": str(qvec), "kb_ids": kb_ids, "lim": limit}).mappings().all()
        return [self._row_to_hit(r, float(r["score"] or 0)) for r in rows]

    def _sqlite_vector_search(self, kb_ids: List[int], qvec: List[float], limit: int) -> List[Dict[str, Any]]:
        chunks = (
            self.db.query(KnowledgeChunk)
            .join(KnowledgeDoc)
            .options(joinedload(KnowledgeChunk.document))
            .filter(
                KnowledgeDoc.kb_id.in_(kb_ids),
                KnowledgeDoc.status.in_(["embedded", "indexed"]),
                KnowledgeChunk.embedding.isnot(None),
            )
            .all()
        )
        scored = []
        for c in chunks:
            vec = c.embedding
            if not vec or not isinstance(vec, (list, tuple)):
                continue
            n = min(len(vec), len(qvec))
            if n == 0:
                continue
            score = sum(float(vec[i]) * float(qvec[i]) for i in range(n))
            scored.append((score, c))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [self._chunk_to_hit(c, score) for score, c in scored[:limit]]

    # ---------- 词法 ----------

    def _lexical_search(self, kb_ids: List[int], query: str, limit: int) -> List[Dict[str, Any]]:
        tokens = _tokenize(query)
        if not tokens:
            return []
        chunks = (
            self.db.query(KnowledgeChunk)
            .join(KnowledgeDoc)
            .options(joinedload(KnowledgeChunk.document))
            .filter(
                KnowledgeDoc.kb_id.in_(kb_ids),
                KnowledgeDoc.status.in_(["embedded", "indexed", "parsing"]),
            )
            .all()
        )
        scored = []
        for c in chunks:
            s = _lexical_score(c.chunk_text or "", tokens)
            if s > 0:
                scored.append((s, c))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [self._chunk_to_hit(c, score) for score, c in scored[:limit]]

    # ---------- 合并 ----------

    def _merge(
        self,
        vector: List[Dict[str, Any]],
        lexical: List[Dict[str, Any]],
        top_k: int,
        threshold: float,
    ) -> List[Dict[str, Any]]:
        by_id: Dict[Any, Dict[str, Any]] = {}
        for src, weight in ((vector, 1.0), (lexical, 0.65)):
            for hit in src:
                key = (hit.get("doc_id"), hit.get("content", "")[:80])
                score = float(hit.get("score") or 0) * weight
                existing = by_id.get(key)
                if existing is None or score > existing["score"]:
                    merged = dict(hit)
                    merged["score"] = score
                    by_id[key] = merged
        ranked = sorted(by_id.values(), key=lambda h: h["score"], reverse=True)
        return [h for h in ranked if h["score"] >= threshold][:top_k]

    def _chunk_to_hit(self, chunk: KnowledgeChunk, score: float) -> Dict[str, Any]:
        doc = chunk.document
        return {
            "content": chunk.chunk_text or "",
            "doc_name": doc.filename if doc else "Unknown",
            "score": float(score),
            "kb_id": doc.kb_id if doc else 0,
            "doc_id": chunk.doc_id,
            "chunk_id": chunk.id,
            "chunk_index": chunk.chunk_index,
        }

    def _row_to_hit(self, row, score: float) -> Dict[str, Any]:
        return {
            "content": row["chunk_text"] or "",
            "doc_name": row["doc_name"] or "Unknown",
            "score": float(score),
            "kb_id": row["kb_id"],
            "doc_id": row["doc_id"],
            "chunk_id": row["id"],
            "chunk_index": row["chunk_index"],
        }

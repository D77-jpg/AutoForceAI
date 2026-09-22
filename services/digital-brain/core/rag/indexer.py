"""
core/rag/indexer.py — 文档解析 → 分块 → 向量化 → 入库

失败时保留已切块文本（status=embedded 若有向量，否则 indexed 表示仅词法可用）。
"""
from __future__ import annotations

import logging
import os
from typing import Optional

from sqlalchemy.orm import Session

from core.rag.embedder import EmbeddingUnavailable
from core.rag.parser import chunk_text, extract_text_from_path
from database.shared_models import KnowledgeChunk, KnowledgeDoc, RAGConfig

logger = logging.getLogger(__name__)


def index_document(db: Session, doc: KnowledgeDoc, organization_id: Optional[int] = None) -> KnowledgeDoc:
    doc.status = "parsing"
    doc.error_msg = None
    db.commit()

    try:
        if not doc.file_path or not os.path.exists(doc.file_path):
            raise FileNotFoundError(f"文件不存在: {doc.file_path}")

        text = extract_text_from_path(doc.file_path)
        if not text:
            raise ValueError("未能从文件中抽取到文本（可能是扫描件 PDF）")

        rag = None
        if organization_id is not None:
            rag = db.query(RAGConfig).filter(RAGConfig.organization_id == organization_id).first()
        if rag is None:
            rag = db.query(RAGConfig).filter(RAGConfig.organization_id == None).first()  # noqa: E711

        chunks = chunk_text(
            text,
            chunk_size=rag.chunk_size if rag else 1000,
            chunk_overlap=rag.chunk_overlap if rag else 200,
        )
        if not chunks:
            raise ValueError("切块结果为空")

        db.query(KnowledgeChunk).filter(KnowledgeChunk.doc_id == doc.id).delete()

        vectors = None
        try:
            from core.rag.embedder import EmbeddingClient
            client = EmbeddingClient(db)
            if client.available:
                vectors = client.embed_documents(chunks)
        except EmbeddingUnavailable as exc:
            logger.info("[Indexer] 无嵌入模型，仅保存文本块：%s", exc)
        except Exception as exc:
            logger.warning("[Indexer] 向量化失败，仅保存文本块：%s", exc)

        for i, chunk in enumerate(chunks):
            embedding = vectors[i] if vectors and i < len(vectors) else None
            db.add(KnowledgeChunk(
                doc_id=doc.id,
                chunk_text=chunk,
                chunk_index=i,
                embedding=embedding,
                meta_info={"source": doc.filename},
            ))

        doc.chunk_count = len(chunks)
        doc.status = "embedded" if vectors else "indexed"
        doc.error_msg = None if vectors else "未配置嵌入模型，已启用词法检索"
        db.commit()
        db.refresh(doc)
        return doc
    except Exception as exc:
        doc.status = "failed"
        doc.error_msg = str(exc)[:500]
        db.commit()
        logger.exception("[Indexer] 文档 %s 解析失败", doc.id)
        return doc

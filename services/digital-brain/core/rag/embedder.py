"""
core/rag/embedder.py — 嵌入向量客户端

职责
----
从数据库解析「嵌入模型」配置，调用服务商 Embeddings API，产出 **固定 1024 维** 的向量，
与 `knowledge_chunks.embedding` 的 Vector(1024) 列严格保持一致。

设计要点
--------
1. **全链路固定 1024 维**
   - ZhipuAI `embedding-3`：原生支持 1024
   - OpenAI `text-embedding-3-*`：通过 `dimensions` 参数降维（MRL 模型，截断后重新归一化在数学上等价）
   - DashScope `text-embedding-v3`：通过 `dimensions` 参数降维
2. **统一走 OpenAI 兼容协议**：ZhipuAI v4 / DashScope compatible-mode / OpenAI 均兼容
   `/embeddings`，因此只维护一套 HTTP 调用，避免多套 SDK 的版本差异。
3. **优雅降级**：无可用模型或密钥时 `available` 为 False，由 retriever 自动降级到词法检索，
   保证系统不会因为「没配密钥」而完全不可用。
4. **写入前 L2 归一化**：使余弦相似度等价于点积，简化 SQLite 下的 Python 计算路径。

模型解析优先级
--------------
`LLMModel`（type='Embedding' 且 is_active）中：
  1. `is_kb_search_default == True` 的模型
  2. 任一活跃的 Embedding 模型
  3. 环境变量推断的兜底模型（ZhipuAI embedding-3 / OpenAI text-embedding-3-small）
"""
from __future__ import annotations

import logging
import math
import os
import time
from typing import Any, Dict, List, Optional

import requests

logger = logging.getLogger(__name__)

# 与 knowledge_chunks.embedding = Vector(1024) 必须一致，不要随意改动
EMBEDDING_DIM = 1024

# 单次请求的最大文本条数（各服务商上限不同，取保守值）
_BATCH_SIZE = 16
_MAX_RETRIES = 3
_RETRY_BACKOFF = 1.5
_TIMEOUT = 60


class EmbeddingUnavailable(Exception):
    """无可用嵌入模型/密钥，调用方应降级到词法检索。"""


def _guess_provider_family(model_name: str, provider_name: str) -> str:
    """根据模型名/供应商名推断服务商族，用于决定 base_url 与环境变量。"""
    haystack = f"{provider_name or ''} {model_name or ''}".lower()
    if "zhipu" in haystack or "glm" in haystack or "embedding-3" in haystack:
        return "zhipu"
    if "dashscope" in haystack or "qwen" in haystack or "text-embedding-v" in haystack:
        return "dashscope"
    if "deepseek" in haystack:
        return "deepseek"
    if "openai" in haystack or "text-embedding" in haystack:
        return "openai"
    return "openai"


_DEFAULT_BASE_URLS = {
    "zhipu": "https://open.bigmodel.cn/api/paas/v4",
    "dashscope": "https://dashscope.aliyuncs.com/compatible-mode/v1",
    "deepseek": "https://api.deepseek.com/v1",
    "openai": "https://api.openai.com/v1",
}

_ENV_KEYS = {
    "zhipu": "ZHIPUAI_API_KEY",
    "dashscope": "DASHSCOPE_API_KEY",
    "deepseek": "DEEPSEEK_API_KEY",
    "openai": "OPENAI_API_KEY",
}

# 无数据库配置时的兜底模型（与 1024 维兼容）
_FALLBACK_MODELS = {
    "zhipu": "embedding-3",
    "dashscope": "text-embedding-v3",
    "openai": "text-embedding-3-small",
}

# 支持 Matryoshka 表示学习、可安全截断降维的模型族
_MRL_HINTS = ("text-embedding-3", "embedding-3")


def _l2_normalize(vec: List[float]) -> List[float]:
    norm = math.sqrt(sum(v * v for v in vec))
    if norm <= 0:
        return vec
    return [v / norm for v in vec]


def _fit_dim(vec: List[float], model_name: str) -> List[float]:
    """
    将向量调整到 EMBEDDING_DIM 维。

    - 维度相同：直接归一化返回
    - 维度更大且为 MRL 模型：截断后重新归一化（对 MRL 模型数学等价）
    - 其他情况：抛出明确错误，避免静默写入错误维度的向量
    """
    if len(vec) == EMBEDDING_DIM:
        return _l2_normalize(vec)
    if len(vec) > EMBEDDING_DIM and any(h in (model_name or "").lower() for h in _MRL_HINTS):
        logger.warning(
            "[Embedder] 模型 %s 返回 %d 维，按 MRL 特性截断到 %d 维并重新归一化",
            model_name, len(vec), EMBEDDING_DIM,
        )
        return _l2_normalize(vec[:EMBEDDING_DIM])
    raise EmbeddingUnavailable(
        f"嵌入模型 {model_name!r} 返回 {len(vec)} 维，但知识库列固定为 {EMBEDDING_DIM} 维。"
        f"请在模型纳管中改用支持 {EMBEDDING_DIM} 维的嵌入模型（如 embedding-3 / text-embedding-3-small）。"
    )


class EmbeddingClient:
    """按数据库配置调用嵌入 API 的客户端。线程内可复用，不做跨请求缓存。"""

    def __init__(self, db=None):
        self.db = db
        self.model_name: Optional[str] = None
        self.base_url: Optional[str] = None
        self.api_key: Optional[str] = None
        self.provider_family: str = "openai"
        self.source: str = "none"          # 记录配置来源，便于排查
        self._send_dimensions: bool = True  # 某些服务商不接受 dimensions 参数，失败后自动关闭
        self._resolve()

    # ---------- 配置解析 ----------

    def _resolve(self) -> None:
        """依次尝试：KB 默认嵌入模型 → 任一活跃嵌入模型 → 环境变量兜底。"""
        row = self._pick_model_row()
        if row is not None:
            self.model_name = row.name
            self.base_url = (row.base_url or "").strip() or None
            self.api_key = (row.api_key or "").strip() or None
            provider_name = ""
            try:
                # provider 关系是可选加载的，避免 DetachedInstanceError 时整体失败
                if getattr(row, "provider", None) is not None:
                    provider_name = row.provider.name or ""
                    if not self.base_url:
                        self.base_url = (row.provider.base_url or "").strip() or None
                    if not self.api_key:
                        self.api_key = (row.provider.api_key or "").strip() or None
            except Exception:  # pragma: no cover - 关系加载失败不应阻断
                provider_name = ""
            self.provider_family = _guess_provider_family(self.model_name, provider_name)
            self.source = "database"
        else:
            # 环境变量兜底：挑第一个有密钥的族
            for family, env_key in _ENV_KEYS.items():
                key = os.getenv(env_key)
                if key and family in _FALLBACK_MODELS:
                    self.provider_family = family
                    self.model_name = _FALLBACK_MODELS[family]
                    self.api_key = key
                    self.source = f"env:{env_key}"
                    break

        if not self.base_url:
            self.base_url = _DEFAULT_BASE_URLS.get(self.provider_family)

        # 数据库配置但缺密钥时，尝试同族环境变量补齐
        if self.model_name and not self.api_key:
            env_key = _ENV_KEYS.get(self.provider_family)
            if env_key:
                self.api_key = os.getenv(env_key) or None
                if self.api_key:
                    self.source = f"{self.source}+env:{env_key}"

        if not self.model_name or not self.api_key:
            logger.info(
                "[Embedder] 未配置可用的嵌入模型（source=%s, model=%s），检索将降级为词法模式",
                self.source, self.model_name,
            )

    def _pick_model_row(self):
        """从数据库挑选嵌入模型行。任何异常都视为「无配置」，交由降级路径处理。"""
        if self.db is None:
            return None
        try:
            from database.shared_models import LLMModel

            base = self.db.query(LLMModel).filter(
                LLMModel.type == "Embedding",
                LLMModel.is_active == True,  # noqa: E712 - SQLAlchemy 需要 == 比较
            )
            row = base.filter(LLMModel.is_kb_search_default == True).first()  # noqa: E712
            if row is None:
                row = base.first()
            return row
        except Exception as exc:  # pragma: no cover
            logger.warning("[Embedder] 读取嵌入模型配置失败：%s", exc)
            return None

    # ---------- 对外接口 ----------

    @property
    def available(self) -> bool:
        return bool(self.model_name and self.api_key and self.base_url)

    @property
    def describe(self) -> Dict[str, Any]:
        return {
            "available": self.available,
            "model": self.model_name,
            "dim": EMBEDDING_DIM,
            "source": self.source,
            "base_url": self.base_url,
        }

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """批量向量化文档切片。文本为空时返回空列表对应项（零向量）。"""
        if not self.available:
            raise EmbeddingUnavailable("未配置可用的嵌入模型")
        if not texts:
            return []

        vectors: List[List[float]] = []
        for start in range(0, len(texts), _BATCH_SIZE):
            batch = texts[start:start + _BATCH_SIZE]
            # 空串或纯空白会让部分服务商报错，替换为占位符
            cleaned = [t if (t and t.strip()) else "(empty)" for t in batch]
            vectors.extend(self._call_api(cleaned))
        return vectors

    def embed_query(self, text: str) -> List[float]:
        """向量化单条查询。"""
        if not self.available:
            raise EmbeddingUnavailable("未配置可用的嵌入模型")
        return self._call_api([text if (text and text.strip()) else "(empty)"])[0]

    # ---------- HTTP 调用 ----------

    def _call_api(self, batch: List[str]) -> List[List[float]]:
        url = self.base_url.rstrip("/") + "/embeddings"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        last_error: Optional[Exception] = None
        for attempt in range(_MAX_RETRIES):
            payload: Dict[str, Any] = {"model": self.model_name, "input": batch}
            if self._send_dimensions:
                payload["dimensions"] = EMBEDDING_DIM

            try:
                resp = requests.post(url, headers=headers, json=payload, timeout=_TIMEOUT)

                # 部分服务商不认 dimensions 参数：去掉后重试一次
                if resp.status_code >= 400 and self._send_dimensions:
                    body_lower = (resp.text or "").lower()
                    if "dimension" in body_lower or "unknown" in body_lower or "extra" in body_lower:
                        logger.info("[Embedder] 服务商不接受 dimensions 参数，改用原生维度")
                        self._send_dimensions = False
                        continue

                if resp.status_code >= 500:
                    raise RuntimeError(f"HTTP {resp.status_code}: {resp.text[:200]}")
                resp.raise_for_status()

                data = resp.json()
                items = data.get("data") or []
                if len(items) != len(batch):
                    raise RuntimeError(
                        f"嵌入返回条数不匹配：期望 {len(batch)}，实际 {len(items)}"
                    )
                # 按 index 排序，避免服务商乱序返回
                items = sorted(items, key=lambda d: d.get("index", 0))
                return [_fit_dim(list(item["embedding"]), self.model_name or "") for item in items]

            except Exception as exc:
                last_error = exc
                if attempt < _MAX_RETRIES - 1:
                    sleep_for = _RETRY_BACKOFF ** attempt
                    logger.warning(
                        "[Embedder] 调用失败（第 %d 次）：%s，%.1fs 后重试",
                        attempt + 1, exc, sleep_for,
                    )
                    time.sleep(sleep_for)

        raise EmbeddingUnavailable(f"嵌入调用失败：{last_error}")


def get_embedding_client(db=None) -> EmbeddingClient:
    """便捷工厂。每次新建实例，避免跨请求共享过期配置。"""
    return EmbeddingClient(db)

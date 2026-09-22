# core/rag — 企业知识库 RAG 管道
#
# 文档解析 → 分块 → 向量化（1024 维）→ 混合检索（向量 + 词法）
# 无嵌入密钥时自动降级为词法检索，保证系统可用。

from core.rag.retriever import KnowledgeRetriever
from core.rag.embedder import EmbeddingClient, EmbeddingUnavailable
from core.rag.parser import chunk_text, extract_text_from_path

__all__ = [
    "KnowledgeRetriever",
    "EmbeddingClient",
    "EmbeddingUnavailable",
    "chunk_text",
    "extract_text_from_path",
]

"""
core/rag/parser.py — 文档抽取与分块

复用已有 FileParser 抽取 PDF/DOCX/TXT/MD 文本，再用 langchain RecursiveCharacterTextSplitter
按 RAGConfig.chunk_size / chunk_overlap 切块。
"""
from __future__ import annotations

import os
from typing import List, Optional

from langchain_text_splitters import RecursiveCharacterTextSplitter

from core.utils.file_parser import FileParser


DEFAULT_CHUNK_SIZE = 1000
DEFAULT_CHUNK_OVERLAP = 200


def extract_text_from_path(path: str) -> str:
    """从本地文件路径抽取纯文本。"""
    filename = os.path.basename(path)
    lower = filename.lower()
    if lower.endswith(".pdf"):
        from pypdf import PdfReader
        reader = PdfReader(path)
        return "\n".join((page.extract_text() or "") for page in reader.pages).strip()
    if lower.endswith(".docx"):
        from docx import Document
        doc = Document(path)
        return "\n".join(p.text for p in doc.paragraphs).strip()
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read().strip()


def chunk_text(
    text: str,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> List[str]:
    """按字符递归切块。空文本返回空列表。"""
    if not text or not text.strip():
        return []
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=max(200, int(chunk_size or DEFAULT_CHUNK_SIZE)),
        chunk_overlap=max(0, int(chunk_overlap or DEFAULT_CHUNK_OVERLAP)),
        separators=["\n\n", "\n", ". ", " ", ""],
        length_function=len,
    )
    chunks = [c.strip() for c in splitter.split_text(text) if c and c.strip()]
    return chunks


async def extract_from_upload(file) -> str:
    """兼容 FastAPI UploadFile。"""
    return await FileParser.parse_upload_file(file)

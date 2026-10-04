"""知识库 CRUD、文档上传解析、检索测试台、RAG 配置。"""
from __future__ import annotations

import os
import shutil
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from core.db_manager import get_shared_db
from core.dependencies import get_current_user
from core.rag.indexer import index_document
from core.rag.retriever import KnowledgeRetriever
from database.shared_models import KnowledgeBase, KnowledgeDoc, RAGConfig, User

router = APIRouter(prefix="/api/v1/kb", tags=["Knowledge Base"])

UPLOAD_ROOT = os.path.join("storage", "uploads", "kb")
os.makedirs(UPLOAD_ROOT, exist_ok=True)


def _user(payload: dict, db: Session) -> User:
    user = db.query(User).filter(User.id == payload["id"]).first()
    if not user:
        raise HTTPException(401, "用户不存在")
    if user.organization_id is None:
        raise HTTPException(403, "请先创建或加入组织")
    return user


def _org_id(user: User) -> Optional[int]:
    return user.organization_id


def _kb_or_404(db: Session, kb_id: int, org_id: Optional[int], *, write: bool = False) -> KnowledgeBase:
    kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
    if not kb:
        raise HTTPException(404, "知识库不存在")
    if org_id is None or kb.organization_id not in (org_id, None):
        raise HTTPException(403, "无权访问该知识库")
    if write and kb.organization_id != org_id:
        raise HTTPException(403, "共享知识库仅支持读取")
    return kb


# ---------- schemas ----------

class KBIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: Optional[str] = None
    is_public: bool = False

    @field_validator("name")
    @classmethod
    def name_not_blank(cls, value):
        if not value.strip():
            raise ValueError("知识库名称不能为空")
        return value.strip()


class RAGConfigIn(BaseModel):
    top_k: Optional[int] = Field(None, ge=1, le=20)
    score_threshold: Optional[float] = Field(None, ge=0, le=1)
    chunk_size: Optional[int] = Field(None, ge=100, le=10000)
    chunk_overlap: Optional[int] = Field(None, ge=0, le=9999)
    sensitive_words: Optional[str] = None


class SearchIn(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    kb_ids: Optional[List[int]] = None
    top_k: Optional[int] = Field(5, ge=1, le=20)
    score_threshold: Optional[float] = Field(0.2, ge=0, le=1)


# ---------- KB CRUD ----------

@router.get("/bases")
def list_kbs(payload: dict = Depends(get_current_user), db: Session = Depends(get_shared_db)):
    user = _user(payload, db)
    q = db.query(KnowledgeBase)
    if user.organization_id:
        q = q.filter(
            (KnowledgeBase.organization_id == user.organization_id) | (KnowledgeBase.organization_id == None)  # noqa: E711
        )
    rows = q.order_by(KnowledgeBase.id.desc()).all()
    out = []
    for kb in rows:
        docs = db.query(KnowledgeDoc).filter(KnowledgeDoc.kb_id == kb.id).all()
        out.append({
            "id": kb.id,
            "name": kb.name,
            "description": kb.description,
            "is_public": kb.is_public,
            "organization_id": kb.organization_id,
            "created_at": kb.created_at.isoformat() if kb.created_at else None,
            "doc_count": len(docs),
            "chunk_count": sum(d.chunk_count or 0 for d in docs),
        })
    return {"items": out, "total": len(out)}


@router.post("/bases")
def create_kb(body: KBIn, payload: dict = Depends(get_current_user), db: Session = Depends(get_shared_db)):
    user = _user(payload, db)
    kb = KnowledgeBase(
        name=body.name.strip(),
        description=body.description,
        is_public=body.is_public,
        organization_id=user.organization_id,
    )
    db.add(kb)
    db.commit()
    db.refresh(kb)
    return {"id": kb.id, "name": kb.name, "is_public": kb.is_public}


@router.patch("/bases/{kb_id}")
def update_kb(kb_id: int, body: KBIn, payload: dict = Depends(get_current_user), db: Session = Depends(get_shared_db)):
    user = _user(payload, db)
    kb = _kb_or_404(db, kb_id, user.organization_id, write=True)
    kb.name = body.name.strip()
    kb.description = body.description
    kb.is_public = body.is_public
    db.commit()
    return {"id": kb.id, "name": kb.name}


@router.delete("/bases/{kb_id}")
def delete_kb(kb_id: int, payload: dict = Depends(get_current_user), db: Session = Depends(get_shared_db)):
    user = _user(payload, db)
    kb = _kb_or_404(db, kb_id, user.organization_id, write=True)
    paths = [d.file_path for d in kb.documents if d.file_path]
    db.delete(kb)
    db.commit()
    for path in paths:
        _remove_upload(path)
    return {"ok": True}


def _remove_upload(path: str):
    target = Path(path).resolve()
    if target.is_relative_to(Path(UPLOAD_ROOT).resolve()):
        target.unlink(missing_ok=True)


# ---------- Documents ----------

@router.get("/bases/{kb_id}/docs")
def list_docs(kb_id: int, payload: dict = Depends(get_current_user), db: Session = Depends(get_shared_db)):
    user = _user(payload, db)
    _kb_or_404(db, kb_id, user.organization_id)
    docs = db.query(KnowledgeDoc).filter(KnowledgeDoc.kb_id == kb_id).order_by(KnowledgeDoc.id.desc()).all()
    return {"items": [
        {
            "id": d.id,
            "filename": d.filename,
            "file_type": d.file_type,
            "file_size": d.file_size,
            "status": d.status,
            "error_msg": d.error_msg,
            "chunk_count": d.chunk_count,
            "created_at": d.created_at.isoformat() if d.created_at else None,
        } for d in docs
    ]}


def _run_index(doc_id: int, org_id: Optional[int]):
    from core.db_manager import SharedSessionLocal
    db = SharedSessionLocal()
    try:
        doc = db.query(KnowledgeDoc).filter(KnowledgeDoc.id == doc_id).first()
        if doc:
            index_document(db, doc, org_id)
    finally:
        db.close()


@router.post("/bases/{kb_id}/docs")
async def upload_doc(
    kb_id: int,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    payload: dict = Depends(get_current_user),
    db: Session = Depends(get_shared_db),
):
    user = _user(payload, db)
    kb = _kb_or_404(db, kb_id, user.organization_id, write=True)
    filename = (file.filename or "untitled").replace("\\", "/").rsplit("/", 1)[-1]
    ext = os.path.splitext(filename)[1].lower().lstrip(".")
    if ext not in {"pdf", "docx", "txt", "md", "csv", "json"}:
        raise HTTPException(400, "仅支持 PDF / Word / Markdown / TXT")

    dest_dir = os.path.join(UPLOAD_ROOT, str(kb.id))
    os.makedirs(dest_dir, exist_ok=True)
    stored_name = f"{uuid.uuid4().hex}.{ext}"
    dest_path = os.path.join(dest_dir, stored_name)
    with open(dest_path, "wb") as f:
        shutil.copyfileobj(file.file, f)
    size = os.path.getsize(dest_path)

    doc = KnowledgeDoc(
        kb_id=kb.id,
        filename=filename,
        file_path=dest_path.replace("\\", "/"),
        file_type=ext,
        file_size=size,
        status="pending",
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    background_tasks.add_task(_run_index, doc.id, user.organization_id)
    return {"id": doc.id, "filename": filename, "status": doc.status}


@router.post("/docs/{doc_id}/reindex")
def reindex_doc(
    doc_id: int,
    background_tasks: BackgroundTasks,
    payload: dict = Depends(get_current_user),
    db: Session = Depends(get_shared_db),
):
    user = _user(payload, db)
    doc = db.query(KnowledgeDoc).filter(KnowledgeDoc.id == doc_id).first()
    if not doc:
        raise HTTPException(404, "文档不存在")
    _kb_or_404(db, doc.kb_id, user.organization_id, write=True)
    background_tasks.add_task(_run_index, doc.id, user.organization_id)
    return {"ok": True, "id": doc.id}


@router.delete("/docs/{doc_id}")
def delete_doc(doc_id: int, payload: dict = Depends(get_current_user), db: Session = Depends(get_shared_db)):
    user = _user(payload, db)
    doc = db.query(KnowledgeDoc).filter(KnowledgeDoc.id == doc_id).first()
    if not doc:
        raise HTTPException(404, "文档不存在")
    _kb_or_404(db, doc.kb_id, user.organization_id, write=True)
    if doc.file_path:
        _remove_upload(doc.file_path)
    db.delete(doc)
    db.commit()
    return {"ok": True}


# ---------- Search / RAG config ----------

@router.post("/search")
def search(body: SearchIn, payload: dict = Depends(get_current_user), db: Session = Depends(get_shared_db)):
    user = _user(payload, db)
    if body.kb_ids:
        for kb_id in body.kb_ids:
            _kb_or_404(db, kb_id, user.organization_id)
        kb_ids = body.kb_ids
    else:
        kbs = db.query(KnowledgeBase).filter(
            (KnowledgeBase.organization_id == user.organization_id) | (KnowledgeBase.organization_id == None)  # noqa: E711
        ).all()
        kb_ids = [k.id for k in kbs]
    retriever = KnowledgeRetriever(db)
    hits = retriever.search_multi_kb(kb_ids, body.query, top_k=body.top_k if body.top_k is not None else 5, score_threshold=body.score_threshold if body.score_threshold is not None else 0.2)
    return {
        "query": body.query,
        "hits": hits,
        "total": len(hits),
        "embedder": retriever.embedder.describe,
    }


@router.get("/config")
def get_rag_config(payload: dict = Depends(get_current_user), db: Session = Depends(get_shared_db)):
    user = _user(payload, db)
    cfg = None
    if user.organization_id:
        cfg = db.query(RAGConfig).filter(RAGConfig.organization_id == user.organization_id).first()
    if cfg is None:
        cfg = db.query(RAGConfig).filter(RAGConfig.organization_id == None).first()  # noqa: E711
    if cfg is None:
        return {
            "top_k": 5, "score_threshold": 0.35, "chunk_size": 1000,
            "chunk_overlap": 200, "sensitive_words": "",
        }
    return {
        "top_k": cfg.top_k,
        "score_threshold": cfg.score_threshold,
        "chunk_size": cfg.chunk_size,
        "chunk_overlap": cfg.chunk_overlap,
        "sensitive_words": cfg.sensitive_words or "",
    }


@router.put("/config")
def put_rag_config(body: RAGConfigIn, payload: dict = Depends(get_current_user), db: Session = Depends(get_shared_db)):
    user = _user(payload, db)
    cfg = db.query(RAGConfig).filter(RAGConfig.organization_id == user.organization_id).first() if user.organization_id else None
    if cfg is None:
        cfg = RAGConfig(organization_id=user.organization_id)
        db.add(cfg)
    for field in ("top_k", "score_threshold", "chunk_size", "chunk_overlap", "sensitive_words"):
        val = getattr(body, field)
        if val is not None:
            setattr(cfg, field, val)
    if (cfg.chunk_overlap if cfg.chunk_overlap is not None else 200) >= (cfg.chunk_size if cfg.chunk_size is not None else 1000):
        raise HTTPException(422, "分块重叠必须小于分块大小")
    cfg.updated_at = datetime.now()
    db.commit()
    return {"ok": True}

"""本地线索池：列表 / 状态流转 / CSV 导出 / 去重写入。"""
from __future__ import annotations

import csv
import io
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from core.db_manager import get_shared_db
from core.dependencies import get_current_user
from database.shared_models import Lead, User

router = APIRouter(prefix="/api/v1/leads", tags=["Leads"])

VALID_STATUS = {"new", "contacted", "converted", "dropped"}


def _user(payload: dict, db: Session) -> User:
    user = db.query(User).filter(User.id == payload["id"]).first()
    if not user:
        raise HTTPException(401, "用户不存在")
    return user


class LeadIn(BaseModel):
    source: Optional[str] = "Website AI Chat"
    email: Optional[str] = None
    name: Optional[str] = None
    company: Optional[str] = None
    country: Optional[str] = None
    phone: Optional[str] = None
    products: Optional[str] = None
    intent_json: Optional[dict] = None
    conversation: Optional[str] = None
    session_uuid: Optional[str] = None
    language: Optional[str] = None


class StatusIn(BaseModel):
    status: str


def upsert_lead(db: Session, organization_id: Optional[int], data: dict) -> Lead:
    """同组织 + 同邮箱去重：已存在则合并更新。无组织时仍按邮箱去重。"""
    email = (data.get("email") or "").strip().lower() or None
    existing = None
    if email:
        q = db.query(Lead).filter(Lead.email == email)
        if organization_id is not None:
            q = q.filter(Lead.organization_id == organization_id)
        existing = q.order_by(Lead.id.asc()).first()
    if existing is None and data.get("session_uuid"):
        existing = db.query(Lead).filter(Lead.session_uuid == data["session_uuid"]).first()

    if existing:
        for k, v in data.items():
            if v in (None, "", [], {}):
                continue
            setattr(existing, k, v)
        existing.updated_at = datetime.now()
        db.commit()
        db.refresh(existing)
        return existing

    lead = Lead(organization_id=organization_id, email=email, **{k: v for k, v in data.items() if k != "email"})
    db.add(lead)
    db.commit()
    db.refresh(lead)
    return lead


def _to_dict(lead: Lead) -> dict:
    return {
        "id": lead.id,
        "source": lead.source,
        "status": lead.status,
        "email": lead.email,
        "name": lead.name,
        "company": lead.company,
        "country": lead.country,
        "phone": lead.phone,
        "products": lead.products,
        "intent_json": lead.intent_json,
        "conversation": lead.conversation,
        "session_uuid": lead.session_uuid,
        "language": lead.language,
        "created_at": lead.created_at.isoformat() if lead.created_at else None,
        "updated_at": lead.updated_at.isoformat() if lead.updated_at else None,
    }


@router.get("")
def list_leads(
    status: Optional[str] = None,
    source: Optional[str] = None,
    q: Optional[str] = None,
    payload: dict = Depends(get_current_user),
    db: Session = Depends(get_shared_db),
):
    user = _user(payload, db)
    query = db.query(Lead)
    if user.organization_id:
        query = query.filter(Lead.organization_id == user.organization_id)
    if status:
        query = query.filter(Lead.status == status)
    if source:
        query = query.filter(Lead.source == source)
    if q:
        like = f"%{q}%"
        query = query.filter(
            (Lead.email.ilike(like)) | (Lead.name.ilike(like)) | (Lead.company.ilike(like)) | (Lead.products.ilike(like))
        )
    rows = query.order_by(Lead.id.desc()).all()
    return {"items": [_to_dict(r) for r in rows], "total": len(rows)}


@router.post("")
def create_lead(body: LeadIn, payload: dict = Depends(get_current_user), db: Session = Depends(get_shared_db)):
    user = _user(payload, db)
    lead = upsert_lead(db, user.organization_id, body.model_dump())
    return _to_dict(lead)


@router.get("/export.csv")
def export_csv(payload: dict = Depends(get_current_user), db: Session = Depends(get_shared_db)):
    user = _user(payload, db)
    query = db.query(Lead)
    if user.organization_id:
        query = query.filter(Lead.organization_id == user.organization_id)
    rows = query.order_by(Lead.id.desc()).all()
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["id", "status", "source", "name", "company", "email", "country", "phone", "products", "language", "created_at"])
    for r in rows:
        writer.writerow([r.id, r.status, r.source, r.name, r.company, r.email, r.country, r.phone, r.products, r.language, r.created_at])
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=leads.csv"},
    )


@router.patch("/{lead_id}")
def update_status(lead_id: int, body: StatusIn, payload: dict = Depends(get_current_user), db: Session = Depends(get_shared_db)):
    if body.status not in VALID_STATUS:
        raise HTTPException(400, f"非法状态，可选：{sorted(VALID_STATUS)}")
    user = _user(payload, db)
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(404, "线索不存在")
    if user.organization_id and lead.organization_id not in (user.organization_id, None):
        raise HTTPException(403, "无权操作")
    lead.status = body.status
    lead.updated_at = datetime.now()
    db.commit()
    return _to_dict(lead)

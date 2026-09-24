"""本地线索池：列表 / 状态流转 / CSV 导出 / 去重写入。"""
from __future__ import annotations

import csv
import io
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from core.db_manager import get_shared_db
from core.dependencies import get_current_user
from core.crm.outbox import enqueue_lead_sync
from database.shared_models import CrmEntityLink, CrmSyncJob, Lead, User

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
        db.flush()  # 拿到 id 但暂不提交：与同步 job 同事务
        enqueue_lead_sync(db, existing)
        db.commit()
        db.refresh(existing)
        return existing

    lead = Lead(organization_id=organization_id, email=email, **{k: v for k, v in data.items() if k != "email"})
    db.add(lead)
    db.flush()  # 分配 id 供 externalId=lead:<id> 使用；与 job 同一事务提交
    enqueue_lead_sync(db, lead)
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


def _crm_status_map(db: Session, organization_id: Optional[int], lead_ids: list[int]) -> dict:
    """每条线索的 CRM 同步摘要：只反映当前项目绑定的有效映射与 job（归档/旧项目不展示）。"""
    if not lead_ids:
        return {}
    from database.shared_models import CrmIntegrationConfig

    cfg = None
    if organization_id is not None:
        cfg = (
            db.query(CrmIntegrationConfig)
            .filter(CrmIntegrationConfig.organization_id == organization_id)
            .first()
        )
    link_query = db.query(CrmEntityLink).filter(
        CrmEntityLink.provider == "genesis_crm",
        CrmEntityLink.lead_id.in_(lead_ids),
        CrmEntityLink.archived_at.is_(None),
    )
    if organization_id is not None:
        link_query = link_query.filter(CrmEntityLink.organization_id == organization_id)
    if cfg is not None and cfg.project_id:
        link_query = link_query.filter(CrmEntityLink.project_id == cfg.project_id)
    link_by_lead = {l.lead_id: l for l in link_query.all()}

    latest_job: dict[int, CrmSyncJob] = {}
    job_query = db.query(CrmSyncJob).filter(CrmSyncJob.lead_id.in_(lead_ids)).order_by(CrmSyncJob.id.desc())
    if organization_id is not None:
        job_query = job_query.filter(CrmSyncJob.organization_id == organization_id)
    if cfg is not None and cfg.project_id:
        job_query = job_query.filter(CrmSyncJob.project_id == cfg.project_id)
    for job in job_query.all():
        latest_job.setdefault(job.lead_id, job)

    result = {}
    for lid in lead_ids:
        link = link_by_lead.get(lid)
        job = latest_job.get(lid)
        result[lid] = {
            "synced": link is not None,
            "remote_customer_id": link.remote_customer_id if link else None,
            "remote_status": link.remote_status if link else None,
            "job_status": job.status if job else None,
            "last_error": job.last_error_summary if job else None,
        }
    return result


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
    crm_map = _crm_status_map(db, user.organization_id, [r.id for r in rows])
    items = []
    for r in rows:
        d = _to_dict(r)
        d["crm"] = crm_map.get(r.id)
        items.append(d)
    return {"items": items, "total": len(rows)}


@router.get("/summary")
def lead_summary(payload: dict = Depends(get_current_user), db: Session = Depends(get_shared_db)):
    """首页使用的轻量线索统计，避免为四个数字加载完整线索列表。"""
    user = _user(payload, db)
    filters = []
    if user.organization_id:
        filters.append(Lead.organization_id == user.organization_id)

    total = db.query(func.count(Lead.id)).filter(*filters).scalar() or 0
    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    today = (
        db.query(func.count(Lead.id))
        .filter(*filters, Lead.created_at >= today_start)
        .scalar()
        or 0
    )
    status_rows = (
        db.query(Lead.status, func.count(Lead.id))
        .filter(*filters)
        .group_by(Lead.status)
        .all()
    )
    by_status = {status: count for status, count in status_rows}
    return {
        "total": total,
        "today": today,
        "by_status": {status: by_status.get(status, 0) for status in sorted(VALID_STATUS)},
    }


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

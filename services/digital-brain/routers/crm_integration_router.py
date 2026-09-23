"""CRM 集成连接配置接口（阶段 2 Wave B）。

- 仅企业管理员（enterprise_admin）与系统管理员（admin）可读写；
- service_token 写后不落任何响应明文，只返回脱敏预览；
- 「测试连接」必须真实调用 Integration API health，
  校验凭证 / 项目绑定 / scope / 契约版本，不只做 URL 格式检查。
"""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from core.db_manager import get_shared_db
from core.dependencies import get_current_user
from core.credentials import CredentialError
from core.crm.client import CrmApiError, GenesisCRMClient, client_from_config
from core.crm.contract import REQUIRED_SCOPES
from core.crm.outbox import enqueue_lead_sync
from database.shared_models import (
    CrmEntityLink,
    CrmIntegrationConfig,
    CrmSyncJob,
    Lead,
    User,
    UserRole,
)

router = APIRouter(prefix="/api/v1/crm/integration", tags=["CRM Integration"])

ALLOWED_ROLES = {UserRole.ADMIN.value, UserRole.ENTERPRISE_ADMIN.value}


def _admin_user(payload: dict, db: Session) -> User:
    user = db.query(User).filter(User.id == payload["id"]).first()
    if not user:
        raise HTTPException(401, "用户不存在")
    if user.role not in ALLOWED_ROLES:
        raise HTTPException(403, "仅企业管理员可管理 CRM 集成配置")
    if not user.organization_id:
        raise HTTPException(400, "当前用户未绑定企业组织，无法配置 CRM 集成")
    return user


def _member_user(payload: dict, db: Session) -> User:
    """门户概览只读：组织成员即可（不暴露任何凭证）。"""
    user = db.query(User).filter(User.id == payload["id"]).first()
    if not user:
        raise HTTPException(401, "用户不存在")
    if not user.organization_id:
        raise HTTPException(400, "当前用户未绑定企业组织")
    return user


def _get_config(db: Session, organization_id: int) -> Optional[CrmIntegrationConfig]:
    return (
        db.query(CrmIntegrationConfig)
        .filter(CrmIntegrationConfig.organization_id == organization_id)
        .first()
    )


def _derive_web_base(cfg: CrmIntegrationConfig) -> Optional[str]:
    """Genesis 前端地址：显式配置优先；否则按本地默认端口约定推导（5000/api → 5173）。"""
    if cfg.web_base_url:
        return cfg.web_base_url.rstrip("/")
    if not cfg.base_url:
        return None
    base = cfg.base_url.rstrip("/")
    if base.endswith("/api"):
        base = base[: -len("/api")]
    if ":5000" in base:
        base = base.replace(":5000", ":5173")
    return base


def _to_public(cfg: CrmIntegrationConfig) -> dict:
    return {
        "id": cfg.id,
        "organization_id": cfg.organization_id,
        "provider": cfg.provider,
        "base_url": cfg.base_url,
        "web_base_url": _derive_web_base(cfg),
        "project_id": cfg.project_id,
        "project_name": cfg.project_name,
        "token_preview": cfg.token_preview,      # 永不返回明文
        "has_token": bool(cfg.service_token),
        "contract_version": cfg.contract_version,
        "enabled": cfg.enabled,
        "last_health_status": cfg.last_health_status,
        "last_health_detail": cfg.last_health_detail,
        "last_health_checked_at": cfg.last_health_checked_at.isoformat() if cfg.last_health_checked_at else None,
        "outcome_polled_at": cfg.outcome_polled_at.isoformat() if cfg.outcome_polled_at else None,
        "updated_at": cfg.updated_at.isoformat() if cfg.updated_at else None,
    }


class ConfigIn(BaseModel):
    base_url: str = Field(..., min_length=1, max_length=300)
    project_id: str = Field(..., min_length=1, max_length=64)
    service_token: Optional[str] = Field(default=None, max_length=200)  # 不传则保留原值
    web_base_url: Optional[str] = Field(default=None, max_length=300)   # Genesis 前端地址（深链）
    enabled: bool = False


class TestResult(BaseModel):
    ok: bool
    detail: str
    scopes: Optional[List[str]] = None
    project_name: Optional[str] = None
    contract_version: Optional[str] = None


def _validate_config_input(body: ConfigIn) -> None:
    if not body.base_url.startswith(("http://", "https://")):
        raise HTTPException(400, "base_url 必须是 http(s) 地址")
    if not body.project_id.strip():
        raise HTTPException(400, "project_id 必填（禁止默认项目回退）")


@router.get("/config")
def get_config(payload: dict = Depends(get_current_user), db: Session = Depends(get_shared_db)):
    user = _admin_user(payload, db)
    cfg = _get_config(db, user.organization_id)
    return {"config": _to_public(cfg) if cfg else None}


@router.put("/config")
def save_config(body: ConfigIn, payload: dict = Depends(get_current_user), db: Session = Depends(get_shared_db)):
    user = _admin_user(payload, db)
    _validate_config_input(body)

    cfg = _get_config(db, user.organization_id)
    if cfg is None:
        cfg = CrmIntegrationConfig(organization_id=user.organization_id, provider="genesis_crm")
        db.add(cfg)

    cfg.base_url = body.base_url.rstrip("/")
    cfg.project_id = body.project_id.strip()
    if body.web_base_url is not None:
        cfg.web_base_url = body.web_base_url.strip().rstrip("/") or None
    if body.service_token:  # 不传 = 保留原 token
        try:
            cfg.set_service_token(body.service_token.strip())
        except CredentialError as exc:
            raise HTTPException(400, f"token 加密失败（{exc.code}）：请配置 CRM_CREDENTIAL_ENCRYPTION_KEY")
    else:
        # 旧明文记录借保存时机迁移为密文
        try:
            cfg.migrate_token_if_legacy()
        except CredentialError as exc:
            raise HTTPException(400, f"旧明文凭证迁移失败（{exc.code}）：请配置 CRM_CREDENTIAL_ENCRYPTION_KEY")
    cfg.enabled = body.enabled
    cfg.updated_at = datetime.now()
    # 配置变化后旧的健康结论失效
    cfg.last_health_status = "unchecked"
    db.commit()
    db.refresh(cfg)
    return {"config": _to_public(cfg)}


def run_connection_test(cfg: CrmIntegrationConfig, db: Session | None = None) -> TestResult:
    """真实调用 health：校验凭证 / 项目绑定 / 契约版本 / 必需 scope。"""
    try:
        client = client_from_config(cfg, db=db)
    except CredentialError as exc:
        return TestResult(ok=False, detail=f"[{exc.code}] {exc}")
    try:
        health = client.health()
    except CrmApiError as exc:
        code_hint = f"[{exc.code}] " if exc.code else ""
        return TestResult(ok=False, detail=f"{code_hint}{exc}")

    missing = sorted(REQUIRED_SCOPES - set(health.scopes))
    if missing:
        return TestResult(
            ok=False,
            detail=f"凭证缺少必需 scope: {', '.join(missing)}",
            scopes=health.scopes,
            project_name=health.projectName,
            contract_version=health.contractVersion,
        )
    return TestResult(
        ok=True,
        detail="连接正常：凭证、项目绑定、契约版本与 scope 校验通过",
        scopes=health.scopes,
        project_name=health.projectName,
        contract_version=health.contractVersion,
    )


@router.post("/test")
def test_connection(payload: dict = Depends(get_current_user), db: Session = Depends(get_shared_db)):
    user = _admin_user(payload, db)
    cfg = _get_config(db, user.organization_id)
    if not cfg:
        raise HTTPException(404, "尚未保存 CRM 集成配置")

    result = run_connection_test(cfg, db=db)
    cfg.last_health_status = "ok" if result.ok else "error"
    cfg.last_health_detail = result.detail
    cfg.last_health_checked_at = datetime.now()
    if result.ok and result.project_name:
        cfg.project_name = result.project_name
    db.commit()
    return result


# ---------- /crm 门户概览（Wave D：真实摘要，非伪功能） ----------

@router.get("/overview")
def portal_overview(payload: dict = Depends(get_current_user), db: Session = Depends(get_shared_db)):
    """
    /crm 门户数据：连接状态 + 投递队列计数 + 本地同步摘要 + Genesis 实时漏斗。
    Genesis 不可达时返回已缓存的本地摘要与错误说明（门户不因此白屏）。
    """
    user = _member_user(payload, db)
    org_id = user.organization_id
    cfg = _get_config(db, org_id)

    # 投递队列计数
    counts_rows = (
        db.query(CrmSyncJob.status, func.count())
        .filter(CrmSyncJob.organization_id == org_id)
        .group_by(CrmSyncJob.status)
        .all()
    )
    counts = {s: 0 for s in ("pending", "leased", "retrying", "succeeded", "dead")}
    counts.update({s: c for s, c in counts_rows})

    # 本地同步摘要（实体映射视角）
    link_query = db.query(CrmEntityLink).filter(
        CrmEntityLink.provider == "genesis_crm",
        CrmEntityLink.organization_id == org_id,
    )
    links = link_query.all()
    won = sum(1 for l in links if l.remote_status == "won")
    lost = sum(1 for l in links if l.remote_status == "lost")

    recent_links = (
        link_query.order_by(CrmEntityLink.synced_at.desc().nullslast(), CrmEntityLink.id.desc())
        .limit(10)
        .all()
    )
    lead_ids = {l.lead_id for l in recent_links}
    leads = {l.id: l for l in db.query(Lead).filter(Lead.id.in_(lead_ids)).all()} if lead_ids else {}
    recent = [
        {
            "lead_id": l.lead_id,
            "name": leads[l.lead_id].name if l.lead_id in leads else None,
            "company": leads[l.lead_id].company if l.lead_id in leads else None,
            "remote_customer_id": l.remote_customer_id,
            "remote_status": l.remote_status,
            "synced_at": l.synced_at.isoformat() if l.synced_at else None,
            "genesis_url": f"{_derive_web_base(cfg)}/customers/{l.remote_customer_id}" if cfg else None,
        }
        for l in recent_links
    ]

    # Genesis 实时漏斗（best-effort）
    genesis_stats = None
    genesis_error = None
    if cfg and cfg.service_token and cfg.last_health_status not in ("auth_invalid", "credential_error"):
        try:
            client = client_from_config(cfg, db=db)
            overview = client.stats_overview()
            genesis_stats = overview.model_dump(mode="json")
        except CredentialError as exc:
            genesis_error = f"[{exc.code}] {exc}"
        except CrmApiError as exc:
            genesis_error = f"[{exc.code}] {exc}" if exc.code else str(exc)

    return {
        "config": _to_public(cfg) if cfg else None,
        "queue": counts,
        "local": {
            "synced_total": len(links),
            "won": won,
            "lost": lost,
        },
        "recent_synced": recent,
        "genesis": genesis_stats,
        "genesis_error": genesis_error,
    }

def _job_to_dict(job: CrmSyncJob, lead: Optional[Lead] = None) -> dict:
    return {
        "id": job.id,
        "lead_id": job.lead_id,
        "lead_email": lead.email if lead else None,
        "lead_name": lead.name if lead else None,
        "event_type": job.event_type,
        "status": job.status,
        "attempt_count": job.attempt_count,
        "next_attempt_at": job.next_attempt_at.isoformat() if job.next_attempt_at else None,
        "last_error_code": job.last_error_code,
        "last_error_summary": job.last_error_summary,
        "last_http_status": job.last_http_status,
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "succeeded_at": job.succeeded_at.isoformat() if job.succeeded_at else None,
        "dead_at": job.dead_at.isoformat() if job.dead_at else None,
    }


@router.get("/jobs")
def list_jobs(
    status: Optional[str] = None,
    limit: int = 50,
    payload: dict = Depends(get_current_user),
    db: Session = Depends(get_shared_db),
):
    """同步 job 列表（默认用于死信页：?status=dead）。"""
    user = _admin_user(payload, db)
    query = db.query(CrmSyncJob).filter(CrmSyncJob.organization_id == user.organization_id)
    if status:
        query = query.filter(CrmSyncJob.status == status)
    rows = query.order_by(CrmSyncJob.id.desc()).limit(min(limit, 200)).all()
    lead_ids = {r.lead_id for r in rows}
    leads = {l.id: l for l in db.query(Lead).filter(Lead.id.in_(lead_ids)).all()} if lead_ids else {}
    # 汇总计数（门户/配置页展示）
    counts = dict(
        db.query(CrmSyncJob.status, func.count())
        .filter(CrmSyncJob.organization_id == user.organization_id)
        .group_by(CrmSyncJob.status)
        .all()
    )
    return {
        "items": [_job_to_dict(r, leads.get(r.lead_id)) for r in rows],
        "counts": {s: counts.get(s, 0) for s in ("pending", "leased", "retrying", "succeeded", "dead")},
    }


@router.post("/jobs/{job_id}/retry")
def retry_job(job_id: int, payload: dict = Depends(get_current_user), db: Session = Depends(get_shared_db)):
    """死信/失败 job 重投：只改变 job 状态，不生成新业务线索。"""
    user = _admin_user(payload, db)
    job = (
        db.query(CrmSyncJob)
        .filter(CrmSyncJob.id == job_id, CrmSyncJob.organization_id == user.organization_id)
        .first()
    )
    if not job:
        raise HTTPException(404, "同步任务不存在")
    if job.status not in ("dead", "retrying", "pending"):
        raise HTTPException(400, f"当前状态 {job.status} 不可重投")
    job.status = "pending"
    job.attempt_count = 0
    job.next_attempt_at = datetime.now()
    job.lease_owner = None
    job.lease_expires_at = None
    job.dead_at = None
    job.updated_at = datetime.now()
    db.commit()
    return {"job": _job_to_dict(job)}


@router.post("/leads/{lead_id}/resync")
def resync_lead(lead_id: int, payload: dict = Depends(get_current_user), db: Session = Depends(get_shared_db)):
    """单条线索手动重投（含 dropped 的显式重投场景）。"""
    user = _admin_user(payload, db)
    lead = (
        db.query(Lead)
        .filter(Lead.id == lead_id, Lead.organization_id == user.organization_id)
        .first()
    )
    if not lead:
        raise HTTPException(404, "线索不存在")
    job = enqueue_lead_sync(db, lead)
    if job is None:
        # dropped 状态默认不入队；显式重投时强制映射为 pending 推送
        from core.crm.mapping import build_upsert_payload, lead_idempotency_key
        from core.crm.outbox import _payload_hash
        from core.crm.contract import CustomerUpsertRequest

        body = build_upsert_payload(lead)
        if body is None:
            body = CustomerUpsertRequest(
                externalId=f"lead:{lead.id}",
                initialStatus="pending",
                name=lead.name, company=lead.company,
                email=(lead.email or "").strip().lower() or None,
                phone=lead.phone, country=lead.country,
                interestedProducts=lead.products,
                leadSource=f"AutoForceAI / {lead.source or 'unknown'}",
                tags=["autoforce", "manual-resync"],
            )
        payload_dict = body.model_dump(exclude_none=True)
        digest = _payload_hash(payload_dict)
        job = CrmSyncJob(
            organization_id=lead.organization_id,
            lead_id=lead.id,
            event_type="lead.upsert",
            idempotency_key=lead_idempotency_key(lead.id, digest),
            payload_version=body.schemaVersion,
            payload_json=payload_dict,
            payload_hash=digest,
            status="pending",
            next_attempt_at=datetime.now(),
        )
        db.add(job)
    db.commit()
    return {"job": _job_to_dict(job)}

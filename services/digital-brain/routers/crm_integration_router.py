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
from sqlalchemy.orm import Session

from core.db_manager import get_shared_db
from core.dependencies import get_current_user
from core.crm.client import CrmApiError, GenesisCRMClient
from core.crm.contract import REQUIRED_SCOPES
from database.shared_models import CrmIntegrationConfig, User, UserRole

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


def _get_config(db: Session, organization_id: int) -> Optional[CrmIntegrationConfig]:
    return (
        db.query(CrmIntegrationConfig)
        .filter(CrmIntegrationConfig.organization_id == organization_id)
        .first()
    )


def _to_public(cfg: CrmIntegrationConfig) -> dict:
    return {
        "id": cfg.id,
        "organization_id": cfg.organization_id,
        "provider": cfg.provider,
        "base_url": cfg.base_url,
        "project_id": cfg.project_id,
        "project_name": cfg.project_name,
        "token_preview": cfg.token_preview,      # 永不返回明文
        "has_token": bool(cfg.service_token),
        "contract_version": cfg.contract_version,
        "enabled": cfg.enabled,
        "last_health_status": cfg.last_health_status,
        "last_health_detail": cfg.last_health_detail,
        "last_health_checked_at": cfg.last_health_checked_at.isoformat() if cfg.last_health_checked_at else None,
        "updated_at": cfg.updated_at.isoformat() if cfg.updated_at else None,
    }


class ConfigIn(BaseModel):
    base_url: str = Field(..., min_length=1, max_length=300)
    project_id: str = Field(..., min_length=1, max_length=64)
    service_token: Optional[str] = Field(default=None, max_length=200)  # 不传则保留原值
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
    if body.service_token:  # 不传 = 保留原 token
        cfg.service_token = body.service_token.strip()
    cfg.enabled = body.enabled
    cfg.updated_at = datetime.now()
    # 配置变化后旧的健康结论失效
    cfg.last_health_status = "unchecked"
    db.commit()
    db.refresh(cfg)
    return {"config": _to_public(cfg)}


def run_connection_test(cfg: CrmIntegrationConfig) -> TestResult:
    """真实调用 health：校验凭证 / 项目绑定 / 契约版本 / 必需 scope。"""
    if not cfg.service_token:
        return TestResult(ok=False, detail="尚未配置 service token")
    client = GenesisCRMClient(cfg.base_url, cfg.service_token, cfg.project_id)
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

    result = run_connection_test(cfg)
    cfg.last_health_status = "ok" if result.ok else "error"
    cfg.last_health_detail = result.detail
    cfg.last_health_checked_at = datetime.now()
    if result.ok and result.project_name:
        cfg.project_name = result.project_name
    db.commit()
    return result

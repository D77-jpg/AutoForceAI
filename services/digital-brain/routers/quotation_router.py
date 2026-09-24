"""阶段 4.3 报价建议、人工确认与 Genesis PDF 代理。"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Response
from sqlalchemy.orm import Session

from core.credentials import CredentialError
from core.crm.client import CrmApiError, client_from_config
from core.crm.quotation import (
    ConfirmQuotationRequest,
    GenerateQuotationProposalRequest,
    confirm_quotation,
    generate_quotation_proposal,
)
from core.db_manager import get_shared_db
from core.dependencies import get_current_user
from database.shared_models import CrmIntegrationConfig, User

router = APIRouter(prefix="/api/v1/crm/quotations", tags=["AI Quotations"])


def _member(payload: dict, db: Session) -> User:
    user = db.query(User).filter(User.id == payload["id"]).first()
    if not user:
        raise HTTPException(401, "用户不存在")
    if not user.organization_id:
        raise HTTPException(400, "当前用户未绑定企业组织")
    return user


def _config(db: Session, organization_id: int) -> CrmIntegrationConfig:
    cfg = db.query(CrmIntegrationConfig).filter(
        CrmIntegrationConfig.organization_id == organization_id,
    ).first()
    if not cfg or not cfg.project_id or not cfg.service_token:
        raise HTTPException(409, "尚未完成 Genesis CRM 连接配置")
    return cfg


def _web_base(cfg: CrmIntegrationConfig) -> Optional[str]:
    if cfg.web_base_url:
        return cfg.web_base_url.rstrip("/")
    base = (cfg.base_url or "").rstrip("/")
    if base.endswith("/api"):
        base = base[:-4]
    return base.replace(":5000", ":5173") if base else None


def _crm_http_error(exc: CrmApiError) -> HTTPException:
    status = exc.http_status if exc.http_status and 400 <= exc.http_status < 600 else 502
    return HTTPException(status, detail={
        "code": exc.code or "CRM_UNAVAILABLE",
        "message": str(exc),
        "request_id": exc.request_id,
    })


@router.post("/proposals")
def create_proposal(
    body: GenerateQuotationProposalRequest,
    payload: dict = Depends(get_current_user),
    db: Session = Depends(get_shared_db),
):
    user = _member(payload, db)
    try:
        return generate_quotation_proposal(db, user.organization_id, body)
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc


@router.post("/confirm")
def confirm_proposal(
    body: ConfirmQuotationRequest,
    payload: dict = Depends(get_current_user),
    db: Session = Depends(get_shared_db),
):
    user = _member(payload, db)
    cfg = _config(db, user.organization_id)
    try:
        client = client_from_config(cfg, db=db)
        db.commit()  # 若读取到旧明文凭证，在网络调用前完成一次性迁移
        return confirm_quotation(db, user.organization_id, body, client, _web_base(cfg))
    except PermissionError as exc:
        raise HTTPException(403, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc
    except CredentialError as exc:
        raise HTTPException(409, detail={"code": exc.code, "message": str(exc)}) from exc
    except CrmApiError as exc:
        raise _crm_http_error(exc) from exc


@router.get("/{quotation_id}/pdf")
def quotation_pdf(
    quotation_id: str,
    if_none_match: Optional[str] = Header(default=None, alias="If-None-Match"),
    payload: dict = Depends(get_current_user),
    db: Session = Depends(get_shared_db),
):
    user = _member(payload, db)
    cfg = _config(db, user.organization_id)
    try:
        client = client_from_config(cfg, db=db)
        pdf = client.download_quotation_pdf(quotation_id, if_none_match)
    except CredentialError as exc:
        raise HTTPException(409, detail={"code": exc.code, "message": str(exc)}) from exc
    except CrmApiError as exc:
        raise _crm_http_error(exc) from exc

    headers = {"Cache-Control": "private, no-cache", "X-Content-Type-Options": "nosniff"}
    if pdf.etag:
        headers["ETag"] = pdf.etag
    if pdf.version:
        headers["X-Quotation-Version"] = pdf.version
    if pdf.content_disposition:
        headers["Content-Disposition"] = pdf.content_disposition
    if pdf.not_modified:
        return Response(status_code=304, headers=headers)
    return Response(content=pdf.content, media_type="application/pdf", headers=headers)

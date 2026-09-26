"""H-09 read-only CRM status tools, bound to trusted actor + DB context.

Tool params contain only a local lead id (and optional quotation id). Unbound
registry prototypes cannot access CRM. Never return customer PII or credentials.
"""
from __future__ import annotations

import json
from typing import Any
from urllib.parse import quote, urlsplit

from pydantic import ValidationError
from sqlalchemy.orm import Session

from core.credentials import CredentialError
from core.crm.client import CrmApiError, client_from_config
from core.crm.contract import SCOPE_CUSTOMERS_UPSERT, SCOPE_QUOTATIONS_READ
from database.shared_models import CrmEntityLink, CrmIntegrationConfig, CrmStatusQueryAudit, Lead, User
from .base import BaseTool


class ToolStatusError(Exception):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def _safe_deep_link(base: str | None, customer_id: str) -> str | None:
    """Use only administrator-configured HTTPS web origin, never remote fields."""
    if not base:
        return None
    try:
        url = urlsplit(base)
        if (url.scheme != "https" or not url.hostname or url.username or url.password or
                url.query or url.fragment or url.path not in ("", "/") or
                any(ord(char) < 33 for char in base) or
                url.hostname.lower() in ("localhost", "localhost.localdomain")):
            return None
        return f"{base.rstrip('/')}/customers/{quote(customer_id, safe='')}"
    except ValueError:
        return None


class _CrmStatusTool(BaseTool):
    def __init__(self, db: Session | None = None, user_id: int | None = None):
        self._db = db
        self._user_id = user_id

    def _context(self, lead_id: int):
        db = self._db
        user = db.query(User).filter(User.id == self._user_id, User.is_active.is_(True)).first()
        if not user or user.organization_id is None:
            raise ToolStatusError("CRM_ACCESS_DENIED")
        organization_id = user.organization_id
        lead = db.query(Lead).filter(Lead.id == lead_id, Lead.organization_id == organization_id).first()
        if not lead:
            raise ToolStatusError("CRM_MAPPING_NOT_FOUND")
        cfg = db.query(CrmIntegrationConfig).filter_by(organization_id=organization_id, provider="genesis_crm").first()
        if not cfg or not cfg.project_id or not cfg.service_token or not cfg.enabled or cfg.last_health_status != "ok":
            raise ToolStatusError("CRM_NOT_ENABLED")
        link = db.query(CrmEntityLink).filter(
            CrmEntityLink.organization_id == organization_id,
            CrmEntityLink.lead_id == lead_id,
            CrmEntityLink.provider == "genesis_crm",
            CrmEntityLink.project_id == cfg.project_id,
            CrmEntityLink.archived_at.is_(None),
        ).first()
        if not link or not link.remote_customer_id:
            raise ToolStatusError("CRM_MAPPING_NOT_FOUND")
        return cfg, link, organization_id

    def _run(self, params: dict[str, Any], *, quotation: bool) -> str:
        if self._db is None or self._user_id is None:
            return _error("TOOL_CONTEXT_REQUIRED")
        allowed = {"lead_id", "quotation_id"} if quotation else {"lead_id"}
        if (not isinstance(params, dict) or set(params) - allowed or
                type(params.get("lead_id")) is not int or params["lead_id"] <= 0 or
                ("quotation_id" in params and (
                    not isinstance(params["quotation_id"], str) or
                    not 1 <= len(params["quotation_id"]) <= 128))):
            return _error("INVALID_TOOL_ARGUMENTS")
        lead_id = params["lead_id"]
        code = "get_crm_quotation_status" if quotation else "get_crm_customer_status"
        audit = CrmStatusQueryAudit(user_id=self._user_id, tool_name=code,
                                    lead_id=lead_id, outcome_code="CRM_UNAVAILABLE")
        try:
            cfg, link, organization_id = self._context(lead_id)
            audit.organization_id = organization_id
            client = client_from_config(cfg)  # read-only; never migrate/write config here
            health = client.health()
            if not health.ok:
                raise ToolStatusError("CRM_UNAVAILABLE")
            required_scope = SCOPE_QUOTATIONS_READ if quotation else SCOPE_CUSTOMERS_UPSERT
            if required_scope not in health.scopes:
                raise ToolStatusError("CRM_SCOPE_INSUFFICIENT")
            external_ref = f"lead:{lead_id}"
            if quotation:
                collection = client.get_customer_quotations(external_ref)
                if collection.customerId != link.remote_customer_id:
                    raise ToolStatusError("CRM_MAPPING_NOT_FOUND")
                quotation_id = params.get("quotation_id")
                items = [item for item in collection.items if not quotation_id or item.quotationId == quotation_id]
                if not items:
                    raise ToolStatusError("CRM_MAPPING_NOT_FOUND")
                result = {"results": [{
                    "status": item.status, "number": item.quotationNo,
                    "amount": item.totalAmount, "currency": item.currency,
                    "updated_at": item.updatedAt.isoformat(),
                    "genesis_url": _safe_deep_link(cfg.web_base_url, link.remote_customer_id),
                } for item in items[:20]]}
            else:
                customer = client.get_customer_status(external_ref)
                if customer.customerId != link.remote_customer_id or customer.externalId != external_ref:
                    raise ToolStatusError("CRM_MAPPING_NOT_FOUND")
                result = {"status": customer.status, "number": None, "amount": None,
                          "currency": None, "updated_at": customer.updatedAt.isoformat(),
                          "genesis_url": _safe_deep_link(cfg.web_base_url, link.remote_customer_id)}
            audit.outcome_code = "OK"
            return json.dumps(result, ensure_ascii=False)
        except ToolStatusError as exc:
            audit.outcome_code = exc.code
            return _error(exc.code)
        except CredentialError:
            audit.outcome_code = "CRM_CREDENTIAL_INVALID"
            return _error(audit.outcome_code)
        except CrmApiError as exc:
            audit.outcome_code = ("CRM_CREDENTIAL_INVALID" if exc.auth_invalid or exc.http_status == 401 else
                                  "CRM_SCOPE_INSUFFICIENT" if exc.code == "FORBIDDEN_SCOPE" or exc.http_status == 403 else
                                  "CRM_UNAVAILABLE")
            return _error(audit.outcome_code)
        except (ValidationError, ValueError, TypeError):
            audit.outcome_code = "CRM_UNAVAILABLE"
            return _error(audit.outcome_code)
        finally:
            # Persist only actor, org, local lead id, tool and stable outcome.
            # No token, remote payload, customer PII or PDF is ever audited.
            try:
                self._db.add(audit)
                self._db.commit()
            except Exception:
                self._db.rollback()
                raise ToolStatusError("CRM_AUDIT_UNAVAILABLE") from None


def _error(code: str) -> str:
    return json.dumps({"error": {"code": code, "message": code}})


class CrmCustomerStatusTool(_CrmStatusTool):
    name = "get_crm_customer_status"
    description = "Read masked status of a linked CRM customer. Requires trusted actor context."

    def run(self, params: dict[str, Any]) -> str:
        return self._run(params, quotation=False)

    @property
    def schema(self) -> dict[str, Any]:
        return {"name": self.name, "description": self.description,
                "parameters": {"type": "object", "additionalProperties": False,
                               "properties": {"lead_id": {"type": "integer", "minimum": 1}},
                               "required": ["lead_id"]}}


class CrmQuotationStatusTool(_CrmStatusTool):
    name = "get_crm_quotation_status"
    description = "Read linked CRM quotation statuses with quotations:read. Requires trusted actor context."

    def run(self, params: dict[str, Any]) -> str:
        return self._run(params, quotation=True)

    @property
    def schema(self) -> dict[str, Any]:
        return {"name": self.name, "description": self.description,
                "parameters": {"type": "object", "additionalProperties": False,
                               "properties": {"lead_id": {"type": "integer", "minimum": 1},
                                              "quotation_id": {"type": "string", "minLength": 1, "maxLength": 128}},
                               "required": ["lead_id"]}}

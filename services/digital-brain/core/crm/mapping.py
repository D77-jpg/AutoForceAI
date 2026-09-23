"""Lead → Integration API v1 upsert 载荷的字段映射（总纲 §7）。"""
from __future__ import annotations

from typing import Optional

from database.shared_models import Lead
from core.crm.contract import (
    CONTRACT_VERSION,
    SOURCE_SYSTEM,
    CustomerUpsertRequest,
    LEAD_STATUS_TO_INITIAL,
)


def lead_external_id(lead_id: int) -> str:
    """稳定外部主键。禁止用邮箱。"""
    return f"lead:{lead_id}"


def lead_idempotency_key(lead_id: int, payload_hash: str) -> str:
    """幂等键：lead + 载荷哈希（载荷变化 → 新键，避免 409 冲突；重试复用原键由 outbox 保证）。"""
    return f"lead-{lead_id}-{payload_hash[:16]}"


def _channel_slug(source: Optional[str]) -> str:
    return (source or "unknown").strip().lower().replace(" ", "-")[:60] or "unknown"


def build_upsert_payload(lead: Lead) -> Optional[CustomerUpsertRequest]:
    """
    构造 upsert 请求体。返回 None 表示该线索不自动推送（如 dropped）。
    """
    initial = LEAD_STATUS_TO_INITIAL.get(lead.status or "new")
    if initial is None:
        return None

    intent = lead.intent_json or {}
    email = (lead.email or "").strip().lower() or None

    requirement_notes = (intent.get("requirement_summary") or intent.get("summary") or "")
    if requirement_notes:
        requirement_notes = requirement_notes[:5000]

    return CustomerUpsertRequest(
        schemaVersion=CONTRACT_VERSION,
        sourceSystem=SOURCE_SYSTEM,
        externalId=lead_external_id(lead.id),
        initialStatus=initial,  # type: ignore[arg-type]
        name=(lead.name or "").strip() or None,
        company=(lead.company or "").strip() or None,
        email=email,
        phone=(lead.phone or "").strip() or None,
        country=(lead.country or "").strip() or None,
        interestedProducts=(lead.products or "").strip() or None,
        leadSource=f"AutoForceAI / {lead.source or 'unknown'}",
        productModel=(intent.get("product_model") or None),
        productCategory=(intent.get("category") or None),
        expectedQuantity=(intent.get("quantity") or None),
        targetPrice=(intent.get("target_price") or None),
        moq=(intent.get("moq") or None),
        requirementNotes=requirement_notes or None,
        tags=["autoforce", f"channel:{_channel_slug(lead.source)}"],
    )

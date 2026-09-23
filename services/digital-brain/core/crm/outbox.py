"""
CRM Outbox 入队（阶段 2 Wave C）。

线索写入与 job 创建必须在**同一数据库事务**完成（由调用方控制 commit）。
幂等键 = lead-<id>-<payload_hash[:16]>：
  - 载荷未变的重复写入不会产生新 job；
  - 载荷变化 → 新键 → 新 job（Genesis 侧按业务键幂等，仍是同一个客户）；
  - 重试复用原键（Genesis 侧 IntegrationIdempotency 保证重放一致）。
"""
from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from core.crm.mapping import build_upsert_payload, lead_idempotency_key
from database.shared_models import CrmIntegrationConfig, CrmSyncJob, Lead

logger = logging.getLogger("crm.outbox")

ACTIVE_JOB_STATUSES = ("pending", "leased", "retrying")


def _payload_hash(payload: dict) -> str:
    canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _enabled_config(db: Session, organization_id: Optional[int]) -> Optional[CrmIntegrationConfig]:
    if organization_id is None:
        return None
    return (
        db.query(CrmIntegrationConfig)
        .filter(
            CrmIntegrationConfig.organization_id == organization_id,
            CrmIntegrationConfig.enabled.is_(True),
            CrmIntegrationConfig.project_id.isnot(None),  # 未绑定项目（含 reset 后）不入队
        )
        .first()
    )


def enqueue_lead_sync(db: Session, lead: Lead, *, event_type: str = "lead.upsert") -> Optional[CrmSyncJob]:
    """
    为线索创建同步 job（不 commit；调用方负责与线索写入同一事务提交）。

    返回 None 的情形：
      - 线索未绑定组织 / 组织未启用集成配置；
      - 线索状态不自动推送（dropped）；
      - 相同载荷的活动 job 已存在（去重）。
    """
    cfg = _enabled_config(db, lead.organization_id)
    if cfg is None:
        return None

    payload = build_upsert_payload(lead)
    if payload is None:  # dropped 等不自动推送的状态
        return None

    payload_dict = payload.model_dump(exclude_none=True)
    digest = _payload_hash(payload_dict)
    key = lead_idempotency_key(lead.id, digest)

    existing = (
        db.query(CrmSyncJob)
        .filter(
            CrmSyncJob.idempotency_key == key,
            CrmSyncJob.organization_id == lead.organization_id,
            CrmSyncJob.project_id == cfg.project_id,  # 只与当前项目绑定的 job 去重
            CrmSyncJob.status.in_(ACTIVE_JOB_STATUSES + ("succeeded",)),
        )
        .first()
    )
    if existing:
        return existing

    job = CrmSyncJob(
        organization_id=lead.organization_id,
        lead_id=lead.id,
        project_id=cfg.project_id,
        event_type=event_type,
        idempotency_key=key,
        payload_version=payload.schemaVersion,
        payload_json=payload_dict,
        payload_hash=digest,
        status="pending",
        next_attempt_at=datetime.now(),
    )
    db.add(job)
    return job

"""
成交/流失回流轮询器（阶段 2 Wave D，总纲 §9）。

- 按 organization（绑定的 project）保存 opaque cursor，存于 crm_integration_configs；
- 每批事件处理与 cursor 提交在**同一事务**：中途失败整批回滚，下次重放；
- 事件按 eventId 幂等（crm_outcome_events 唯一约束），重复事件直接跳过；
- `won` → 更新 crm_entity_links.remote_status，并把本地线索标记为 converted（成交归因）；
- `lost` → 只更新 CRM 摘要（remote_status），不改本地线索状态（由业务规则另行决定）；
- 归因始终按线索最初的 source 统计，不用 CRM 最近来源覆盖。
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from core.credentials import CredentialError
from core.crm import PAUSED_HEALTH_STATUSES
from core.crm.client import CrmApiError, GenesisCRMClient, client_from_config
from core.crm.worker_state import (
    claim_outcome_lease,
    record_error,
    record_poller_success,
    renew_outcome_lease,
)
from database.shared_models import (
    CrmEntityLink,
    CrmIntegrationConfig,
    CrmOutcomeEvent,
    Lead,
)

logger = logging.getLogger("crm.outcome_poller")

PAGE_SIZE = 100
MAX_PAGES_PER_ROUND = 10  # 单轮上限，避免一次追太多阻塞投递循环


def _parse_dt(value) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.replace(tzinfo=None)
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).replace(tzinfo=None)
    except Exception:
        return None


def _apply_event(db: Session, cfg: CrmIntegrationConfig, event) -> bool:
    """应用单个 outcome 事件。返回 True 表示新事件，False 表示幂等跳过。"""
    dup = (
        db.query(CrmOutcomeEvent)
        .filter(
            CrmOutcomeEvent.provider == "genesis_crm",
            CrmOutcomeEvent.organization_id == cfg.organization_id,
            CrmOutcomeEvent.event_id == event.eventId,
        )
        .first()
    )
    if dup:
        return False

    link = (
        db.query(CrmEntityLink)
        .filter(
            CrmEntityLink.provider == "genesis_crm",
            CrmEntityLink.organization_id == cfg.organization_id,
            CrmEntityLink.project_id == cfg.project_id,
            CrmEntityLink.remote_customer_id == event.customerId,
            CrmEntityLink.archived_at.is_(None),  # 归档映射不接收回流
        )
        .first()
    )

    lead_id: Optional[int] = None
    if link is not None:
        link.remote_status = event.toStatus
        link.remote_updated_at = _parse_dt(event.occurredAt)
        link.synced_at = datetime.now()
        lead_id = link.lead_id

        if event.toStatus == "won":
            # 成交归因：本地线索标记 converted；来源字段保持最初获客来源不动
            lead = db.query(Lead).filter(
                Lead.id == link.lead_id,
                Lead.organization_id == cfg.organization_id,
            ).first()
            if lead and lead.status != "converted":
                lead.status = "converted"
                lead.updated_at = datetime.now()
        # lost：只更新 CRM 摘要（remote_status），本地线索状态由业务规则决定
    else:
        # CRM 原生客户（非 AutoForceAI 交接）：记录事件但不关联本地线索
        logger.info("outcome 事件无本地映射，仅记录: customer=%s to=%s", event.customerId, event.toStatus)

    db.add(
        CrmOutcomeEvent(
            organization_id=cfg.organization_id,
            provider="genesis_crm",
            event_id=event.eventId,
            remote_customer_id=event.customerId,
            external_id=event.externalId,
            lead_id=lead_id,
            from_status=event.fromStatus,
            to_status=event.toStatus,
            occurred_at=_parse_dt(event.occurredAt) or datetime.now(),
        )
    )
    return True


def poll_org_outcomes(
    db: Session,
    cfg: CrmIntegrationConfig,
    client: Optional[GenesisCRMClient] = None,
    *,
    worker_id: Optional[str] = None,
) -> int:
    """
    轮询一个组织的 outcome feed；返回新处理的事件数。
    每批：取一页 → 逐条应用 → 同事务提交批处理与 cursor。
    """
    if not cfg.service_token:
        return 0
    client = client or client_from_config(cfg, db=db)  # CredentialError 向上抛，由 poll_all_outcomes 统一处理

    processed = 0
    cursor = cfg.outcome_cursor
    for _ in range(MAX_PAGES_PER_ROUND):
        # 每页请求前续租，防止多页轮询超过 60s 后被另一实例并发接管。
        if worker_id and not renew_outcome_lease(db, cfg, worker_id):
            return processed
        feed = client.fetch_outcomes(cursor=cursor, limit=PAGE_SIZE)
        # 网络返回后再确认 owner。若请求期间租约过期并被接管，当前 worker 不得应用该页。
        if worker_id and not renew_outcome_lease(db, cfg, worker_id):
            db.rollback()
            return processed
        if not feed.items:
            break

        new_in_batch = 0
        last_cursor = cursor
        for event in feed.items:
            if _apply_event(db, cfg, event):
                new_in_batch += 1
            last_cursor = event.cursor

        # 批处理与 cursor 提交同一事务：任何一步失败整批回滚，cursor 不前进
        cfg.outcome_cursor = last_cursor
        cfg.outcome_polled_at = datetime.now()
        # 在同一事务内再验证一次 owner，避免事件应用期间租约丢失后覆盖新 cursor。
        if worker_id and not renew_outcome_lease(db, cfg, worker_id, commit=False):
            db.rollback()
            return processed
        db.commit()
        processed += new_in_batch

        cursor = feed.nextCursor
        if not feed.hasMore or not cursor:
            break

    return processed


def poll_all_outcomes(db: Session, worker_id: str = "poller") -> int:
    """
    对所有「启用且凭证有效」的集成配置执行一轮 outcome 轮询。
    §3.6：每个 org+project 先抢配置行级租约，抢不到（另一实例持有且未过期）则跳过。
    """
    configs = (
        db.query(CrmIntegrationConfig)
        .filter(
            CrmIntegrationConfig.enabled.is_(True),
            CrmIntegrationConfig.service_token.isnot(None),
            CrmIntegrationConfig.project_id.isnot(None),
        )
        .all()
    )
    total = 0
    for cfg in configs:
        if cfg.last_health_status in PAUSED_HEALTH_STATUSES:
            continue  # 凭证/密钥失效：等管理员修复，轮询与投递一并暂停
        if not claim_outcome_lease(db, cfg, worker_id):
            logger.debug("outcome 租约被其它实例持有，跳过 org=%s", cfg.organization_id)
            continue
        try:
            total += poll_org_outcomes(db, cfg, worker_id=worker_id)
            record_poller_success(db, worker_id)
            db.commit()
        except CredentialError as exc:
            db.rollback()
            cfg.last_health_status = "credential_error"
            cfg.last_health_detail = f"凭证不可用（{exc.code}）：请检查 CRM_CREDENTIAL_ENCRYPTION_KEY 或重设 token"
            cfg.last_health_checked_at = datetime.now()
            db.commit()
            logger.warning("outcome 轮询因凭证不可用暂停 org=%s: %s", cfg.organization_id, exc.code)
        except CrmApiError as exc:
            db.rollback()
            if exc.auth_invalid:
                cfg.last_health_status = "auth_invalid"
                cfg.last_health_detail = f"凭证失效（{exc.code}），已暂停投递与回流"
                cfg.last_health_checked_at = datetime.now()
                db.commit()
            record_error(db, f"poller org={cfg.organization_id}: [{exc.code or 'NETWORK'}] HTTP {exc.http_status}")
            db.commit()
            logger.warning("outcome 轮询失败 org=%s: %s", cfg.organization_id, exc)
        except Exception as exc:
            db.rollback()
            record_error(db, f"poller org={cfg.organization_id}: {exc.__class__.__name__}")
            db.commit()
            logger.exception("outcome 轮询异常 org=%s", cfg.organization_id)
    return total

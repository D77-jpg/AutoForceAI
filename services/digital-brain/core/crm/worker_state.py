"""
CRM 后台 worker 并发保护（总纲 §3.6，阶段 2.9）。

- CRM_BACKGROUND_WORKER_ENABLED=0/false/off 时，API 进程不启动后台线程，
  接口与 /crm 只读门户不受影响；
- dispatcher 的 job 级租约（lease_owner/lease_expires_at）保证多实例不重复消费；
- outcome poller 使用「配置行级租约」（条件 UPDATE 抢占 outcome_lease_owner），
  保证同一 organization/project 同时只有一个实例推进 cursor；
- crm_worker_state 单行表记录心跳与最近错误，供 /crm 门户与运维观察。

阶段 5 再考虑 Redis/Celery；当前为数据库行级互斥。
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from database.shared_models import CrmIntegrationConfig, CrmWorkerState

logger = logging.getLogger("crm.worker")

WORKER_ENABLED_ENV = "CRM_BACKGROUND_WORKER_ENABLED"
POLLER_LEASE_SECONDS = 60


def worker_enabled() -> bool:
    return os.getenv(WORKER_ENABLED_ENV, "1").strip().lower() not in ("0", "false", "off", "no")


def get_state(db: Session) -> CrmWorkerState:
    state = db.query(CrmWorkerState).filter(CrmWorkerState.id == 1).first()
    if state is None:
        state = CrmWorkerState(id=1)
        db.add(state)
        db.flush()
    return state


def record_dispatcher_success(db: Session, worker_id: str) -> None:
    state = get_state(db)
    state.dispatcher_worker_id = worker_id
    state.dispatcher_last_success_at = datetime.now()


def record_poller_success(db: Session, worker_id: str) -> None:
    state = get_state(db)
    state.poller_worker_id = worker_id
    state.poller_last_success_at = datetime.now()


def record_error(db: Session, summary: str) -> None:
    """记录脱敏错误摘要（不含 token/载荷）。"""
    state = get_state(db)
    state.last_error = summary[:500]
    state.last_error_at = datetime.now()


def claim_outcome_lease(db: Session, cfg: CrmIntegrationConfig, worker_id: str,
                        lease_seconds: int = POLLER_LEASE_SECONDS) -> bool:
    """
    条件 UPDATE 抢占 outcome 轮询租约（与 dispatcher 的 job 租约同语义）。
    只有租约为空、已过期或本就属于自己时才能拿到；返回是否抢到。
    """
    now = datetime.now()
    updated = (
        db.query(CrmIntegrationConfig)
        .filter(
            CrmIntegrationConfig.id == cfg.id,
            (
                CrmIntegrationConfig.outcome_lease_owner.is_(None)
                | (CrmIntegrationConfig.outcome_lease_expires_at < now)
                | (CrmIntegrationConfig.outcome_lease_owner == worker_id)
            ),
        )
        .update(
            {
                CrmIntegrationConfig.outcome_lease_owner: worker_id,
                CrmIntegrationConfig.outcome_lease_expires_at: now + timedelta(seconds=lease_seconds),
            },
            synchronize_session=False,
        )
    )
    if updated:
        db.commit()
        db.refresh(cfg)
        return True
    db.rollback()
    return False


def renew_outcome_lease(db: Session, cfg: CrmIntegrationConfig, worker_id: str,
                        lease_seconds: int = POLLER_LEASE_SECONDS) -> None:
    """轮询成功后续租（保持 owner，便于健康观察；崩溃后到期自然被接管）。"""
    db.query(CrmIntegrationConfig).filter(
        CrmIntegrationConfig.id == cfg.id,
        CrmIntegrationConfig.outcome_lease_owner == worker_id,
    ).update(
        {CrmIntegrationConfig.outcome_lease_expires_at: datetime.now() + timedelta(seconds=lease_seconds)},
        synchronize_session=False,
    )
    db.commit()

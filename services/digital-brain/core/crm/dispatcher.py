"""
CRM Outbox 投递器（阶段 2 Wave C）。

- 租约抢占：多进程/多实例下同一 job 只会被一个 worker 消费（lease_owner + lease_expires_at）；
- 退避策略：30s → 2min → 10min → 1h → 6h → 之后每天一次，最多 8 次；
- 错误分类（依据 GenesisCRMClient 的 CrmApiError）：
    retryable（网络/408/429/5xx）  → retrying，按退避表重试；重试复用原幂等键；
    请求字段 4xx                   → dead（死信，人工修复后重投）；
    401/403（凭证失效）            → 标记配置失效并暂停该组织新投递，job 进入长退避；
- 成功 → 写 crm_entity_links（lead ↔ Genesis customer 稳定映射）。

并发安全说明：lease 采用「先选候选 → 条件 UPDATE 抢占」，抢占失败（影响行数 0）
即说明被其它 worker 拿走，直接跳过。
"""
from __future__ import annotations

import logging
import os
import threading
import time
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from core.crm.client import CrmApiError, GenesisCRMClient
from core.crm.contract import CustomerUpsertRequest
from database.shared_models import (
    CrmEntityLink,
    CrmIntegrationConfig,
    CrmSyncJob,
)

logger = logging.getLogger("crm.dispatcher")

# 退避表（秒）：30s, 2min, 10min, 1h, 6h, 之后每天；最多 MAX_ATTEMPTS 次
BACKOFF_SECONDS = [30, 120, 600, 3600, 21600, 86400, 86400]
MAX_ATTEMPTS = 8
LEASE_SECONDS = 60
# 凭证失效后的长退避（等待管理员修复配置；保存配置会解除暂停）
AUTH_INVALID_RETRY_SECONDS = 3600

_dispatcher_thread: Optional[threading.Thread] = None
_stop_event = threading.Event()


class _ClientFactory:
    """可替换的 client 工厂（测试注入用）。"""

    def __call__(self, cfg: CrmIntegrationConfig) -> GenesisCRMClient:
        return GenesisCRMClient(cfg.base_url, cfg.service_token, cfg.project_id)


client_factory = _ClientFactory()


def _backoff_delay(attempt_count: int) -> int:
    idx = min(attempt_count - 1, len(BACKOFF_SECONDS) - 1)
    return BACKOFF_SECONDS[max(idx, 0)]


def _lease_jobs(db: Session, worker_id: str, batch_size: int) -> list[CrmSyncJob]:
    """租约抢占一批到期 job；返回成功抢到的。"""
    now = datetime.now()
    candidates = (
        db.query(CrmSyncJob.id)
        .filter(
            CrmSyncJob.status.in_(("pending", "retrying")),
            CrmSyncJob.next_attempt_at <= now,
        )
        .order_by(CrmSyncJob.next_attempt_at.asc(), CrmSyncJob.id.asc())
        .limit(batch_size)
        .all()
    )
    leased: list[CrmSyncJob] = []
    for (job_id,) in candidates:
        # 条件更新抢占：只有仍处于可投递状态的行才会被本 worker 租下
        updated = (
            db.query(CrmSyncJob)
            .filter(
                CrmSyncJob.id == job_id,
                CrmSyncJob.status.in_(("pending", "retrying")),
                CrmSyncJob.next_attempt_at <= now,
            )
            .update(
                {
                    CrmSyncJob.status: "leased",
                    CrmSyncJob.lease_owner: worker_id,
                    CrmSyncJob.lease_expires_at: now + timedelta(seconds=LEASE_SECONDS),
                    CrmSyncJob.updated_at: now,
                },
                synchronize_session=False,
            )
        )
        if updated:
            leased.append(db.query(CrmSyncJob).filter(CrmSyncJob.id == job_id).first())
    if leased:
        db.commit()
    return leased


def recover_expired_leases(db: Session) -> int:
    """把租约过期的 job 放回 pending（worker 崩溃/停机后的自动补投入口）。"""
    now = datetime.now()
    count = (
        db.query(CrmSyncJob)
        .filter(CrmSyncJob.status == "leased", CrmSyncJob.lease_expires_at < now)
        .update(
            {
                CrmSyncJob.status: "pending",
                CrmSyncJob.lease_owner: None,
                CrmSyncJob.lease_expires_at: None,
                CrmSyncJob.updated_at: now,
            },
            synchronize_session=False,
        )
    )
    if count:
        db.commit()
        logger.warning("回收过期租约 job: %s 个", count)
    return count


def _deliver(db: Session, job: CrmSyncJob) -> None:
    """投递单个已租约 job；就地更新 job 状态（调用方 commit）。"""
    now = datetime.now()
    job.attempt_count = (job.attempt_count or 0) + 1

    cfg = (
        db.query(CrmIntegrationConfig)
        .filter(CrmIntegrationConfig.organization_id == job.organization_id)
        .first()
    )
    # 配置缺失/停用/凭证失效：不占尝试次数的退避，等待管理员处理
    if cfg is None or not cfg.enabled or not cfg.service_token:
        job.status = "pending"
        job.next_attempt_at = now + timedelta(seconds=600)
        job.last_error_code = "CONFIG_DISABLED"
        job.last_error_summary = "集成配置缺失或未启用"
        return
    if cfg.last_health_status == "auth_invalid":
        job.status = "retrying"
        job.next_attempt_at = now + timedelta(seconds=AUTH_INVALID_RETRY_SECONDS)
        job.last_error_code = "AUTH_INVALID"
        job.last_error_summary = "服务凭证已失效，等待管理员更新配置"
        return

    try:
        request = CustomerUpsertRequest.model_validate(job.payload_json)
    except Exception as exc:  # 载荷本身不合法（不应发生，防御）
        job.status = "dead"
        job.dead_at = now
        job.last_error_code = "PAYLOAD_INVALID"
        job.last_error_summary = f"本地载荷不合法: {exc.__class__.__name__}"
        return

    try:
        client = client_factory(cfg)
        resp = client.upsert_customer(request, idempotency_key=job.idempotency_key)
    except CrmApiError as exc:
        job.last_error_code = exc.code
        job.last_error_summary = str(exc)[:500]
        job.last_http_status = exc.http_status

        if exc.auth_invalid:
            # 401/403：标记配置失效，暂停该组织新投递；job 长退避等待修复
            cfg.last_health_status = "auth_invalid"
            cfg.last_health_detail = f"凭证失效（{exc.code}），已暂停投递；请更新配置"
            cfg.last_health_checked_at = now
            job.status = "retrying"
            job.next_attempt_at = now + timedelta(seconds=AUTH_INVALID_RETRY_SECONDS)
            return
        if exc.retryable:
            if job.attempt_count >= MAX_ATTEMPTS:
                job.status = "dead"
                job.dead_at = now
                job.last_error_summary = f"超过最大重试次数（{MAX_ATTEMPTS}）: {job.last_error_summary}"
            else:
                job.status = "retrying"
                job.next_attempt_at = now + timedelta(seconds=_backoff_delay(job.attempt_count))
            return
        # 请求字段 4xx 等不可重试错误 → 死信
        job.status = "dead"
        job.dead_at = now
        return
    except Exception as exc:  # 未预期异常按可重试处理
        job.last_error_code = "UNEXPECTED"
        job.last_error_summary = f"{exc.__class__.__name__}: {exc}"[:500]
        if job.attempt_count >= MAX_ATTEMPTS:
            job.status = "dead"
            job.dead_at = now
        else:
            job.status = "retrying"
            job.next_attempt_at = now + timedelta(seconds=_backoff_delay(job.attempt_count))
        return

    # 成功：写实体映射（幂等 upsert）
    job.status = "succeeded"
    job.succeeded_at = now
    job.last_error_code = None
    job.last_error_summary = None

    link = (
        db.query(CrmEntityLink)
        .filter(
            CrmEntityLink.provider == "genesis_crm",
            CrmEntityLink.organization_id == job.organization_id,
            CrmEntityLink.lead_id == job.lead_id,
        )
        .first()
    )
    if link is None:
        link = CrmEntityLink(
            organization_id=job.organization_id,
            lead_id=job.lead_id,
            provider="genesis_crm",
            project_id=resp.projectId,
            remote_customer_id=resp.customerId,
        )
        db.add(link)
    link.remote_customer_id = resp.customerId
    link.project_id = resp.projectId
    try:
        link.remote_updated_at = datetime.fromisoformat(resp.remoteUpdatedAt.replace("Z", "+00:00")).replace(tzinfo=None)
    except Exception:
        link.remote_updated_at = now
    link.synced_at = now


def dispatch_once(db: Session, worker_id: str, batch_size: int = 20) -> int:
    """单轮投递：回收过期租约 → 抢占 → 逐个投递。返回处理数。"""
    recover_expired_leases(db)
    jobs = _lease_jobs(db, worker_id, batch_size)
    for job in jobs:
        try:
            _deliver(db, job)
            db.commit()
        except Exception:
            db.rollback()
            logger.exception("投递 job %s 时出现未处理异常", job.id)
    return len(jobs)


def _loop(interval: float, batch_size: int, worker_id: str) -> None:
    from core.db_manager import SharedSessionLocal

    logger.info("CRM dispatcher 启动: worker=%s interval=%ss batch=%s", worker_id, interval, batch_size)
    while not _stop_event.is_set():
        try:
            db = SharedSessionLocal()
            try:
                dispatch_once(db, worker_id, batch_size)
            finally:
                db.close()
        except Exception:
            logger.exception("CRM dispatcher 轮询异常")
        _stop_event.wait(interval)
    logger.info("CRM dispatcher 停止")


def start_dispatcher(interval: Optional[float] = None, batch_size: int = 20) -> None:
    """在服务生命周期内启动后台投递线程（幂等）。"""
    global _dispatcher_thread
    if _dispatcher_thread and _dispatcher_thread.is_alive():
        return
    if interval is None:
        interval = float(os.getenv("CRM_DISPATCHER_INTERVAL", "15"))
    worker_id = f"{os.uname().nodename if hasattr(os, 'uname') else os.environ.get('COMPUTERNAME', 'host')}:{os.getpid()}"
    _stop_event.clear()
    _dispatcher_thread = threading.Thread(
        target=_loop, args=(interval, batch_size, worker_id), daemon=True, name="crm-dispatcher",
    )
    _dispatcher_thread.start()


def stop_dispatcher() -> None:
    _stop_event.set()
    if _dispatcher_thread:
        _dispatcher_thread.join(timeout=5)

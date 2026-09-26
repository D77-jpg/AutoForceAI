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

from core.credentials import CredentialError
from core.crm import PAUSED_HEALTH_STATUSES
from core.crm.client import CrmApiError, GenesisCRMClient, client_from_config
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

    def __call__(self, cfg: CrmIntegrationConfig, db: Session | None = None) -> GenesisCRMClient:
        return client_from_config(cfg, db=db)


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
    # 配置缺失/停用/凭证失效/解密失败：不占尝试次数的退避，等待管理员处理
    if cfg is None or not cfg.enabled or not cfg.service_token or not cfg.project_id:
        job.status = "pending"
        job.next_attempt_at = now + timedelta(seconds=600)
        job.last_error_code = "CONFIG_DISABLED"
        job.last_error_summary = "集成配置缺失、未启用或未绑定项目"
        return
    # 纵深防御：旧项目绑定的 job 绝不投递到新项目（正常路径已在 reset 时取消）
    if job.project_id and job.project_id != cfg.project_id:
        job.status = "cancelled"
        job.last_error_code = "PROJECT_BINDING_CHANGED"
        job.last_error_summary = "项目绑定已变更，旧 job 取消（不投递到新项目）"
        logger.warning("job %s 属于旧项目绑定，已取消", job.id)
        return
    if cfg.last_health_status in PAUSED_HEALTH_STATUSES:
        job.status = "retrying"
        job.next_attempt_at = now + timedelta(seconds=AUTH_INVALID_RETRY_SECONDS)
        job.last_error_code = cfg.last_health_status.upper()
        job.last_error_summary = "凭证或密钥失效，等待管理员更新配置"
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
        client = client_factory(cfg, db)
        resp = client.upsert_customer(request, idempotency_key=job.idempotency_key)
    except CredentialError as exc:
        # 密钥缺失/错误、密文损坏：与凭证失效同语义——标记配置并暂停该组织投递
        cfg.last_health_status = "credential_error"
        cfg.last_health_detail = f"凭证不可用（{exc.code}）：请检查 CRM_CREDENTIAL_ENCRYPTION_KEY 或重设 token"
        cfg.last_health_checked_at = now
        job.status = "retrying"
        job.next_attempt_at = now + timedelta(seconds=AUTH_INVALID_RETRY_SECONDS)
        job.last_error_code = exc.code
        job.last_error_summary = "凭证解密失败，已暂停投递"
        return
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

    # 成功：写实体映射（按 org+lead+project 幂等 upsert；同项目归档映射可复活复用）
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
            CrmEntityLink.project_id == resp.projectId,
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
    link.archived_at = None  # 重新投递成功即视为有效映射
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
    from core.alerts import record_failure, record_recovery
    from database.shared_models import Alert
    for job in jobs:
        try:
            _deliver(db, job)
            # Count only actual delivery attempts, not paused configuration/lease polling.
            if job.status in ("retrying", "dead") and job.last_error_code not in (
                "CONFIG_DISABLED", "AUTH_INVALID",
            ) and job.last_error_code:
                record_failure(db, organization_id=job.organization_id, source="crm_dispatcher",
                               category=job.last_error_code,
                               severity="critical" if job.status == "dead" or
                               (job.last_error_code or "").upper() in ("CREDENTIAL_ERROR", "UNAUTHORIZED", "FORBIDDEN")
                               else "warning")
            elif job.status == "succeeded":
                # A successful individual job does not recover an org-wide incident
                # while other jobs of the same category are still failing.
                pending_categories = [category for (category,) in db.query(Alert.category).filter(
                    Alert.organization_id == job.organization_id,
                    Alert.source == "crm_dispatcher", Alert.status != "resolved",
                ).all()]
                for category in pending_categories:
                    still_failing = db.query(CrmSyncJob.id).filter(
                        CrmSyncJob.organization_id == job.organization_id,
                        CrmSyncJob.status.in_(("retrying", "dead")),
                        CrmSyncJob.last_error_code == category,
                    ).first()
                    if not still_failing:
                        record_recovery(db, organization_id=job.organization_id,
                                        source="crm_dispatcher", category=category)
            db.commit()
        except Exception:
            db.rollback()
            logger.exception("投递 job %s 时出现未处理异常", job.id)
    return len(jobs)


def _loop(interval: float, batch_size: int, worker_id: str) -> None:
    from core.db_manager import SharedSessionLocal
    from core.crm.outcome_poller import poll_all_outcomes
    from core.crm.worker_state import record_dispatcher_success, record_error

    outcome_interval = float(os.getenv("CRM_OUTCOME_POLL_INTERVAL", "60"))
    last_outcome_poll = 0.0
    last_alert_cleanup = 0.0

    logger.info("CRM dispatcher 启动: worker=%s interval=%ss batch=%s outcome=%ss",
                worker_id, interval, batch_size, outcome_interval)
    while not _stop_event.is_set():
        try:
            db = SharedSessionLocal()
            try:
                dispatch_once(db, worker_id, batch_size)
                if time.monotonic() - last_alert_cleanup >= 86400:
                    from core.alerts import cleanup_resolved
                    cleanup_resolved(db)
                    last_alert_cleanup = time.monotonic()
                record_dispatcher_success(db, worker_id)
                db.commit()
                # 成交/流失回流：按自身节奏轮询（默认 60s），行级租约保证单实例推进
                if time.monotonic() - last_outcome_poll >= outcome_interval:
                    last_outcome_poll = time.monotonic()
                    poll_all_outcomes(db, worker_id=worker_id)
            finally:
                db.close()
        except Exception as exc:
            logger.exception("CRM dispatcher 轮询异常")
            try:
                err_db = SharedSessionLocal()
                try:
                    record_error(err_db, f"dispatcher {exc.__class__.__name__}")
                    err_db.commit()
                finally:
                    err_db.close()
            except Exception:
                pass
        _stop_event.wait(interval)
    logger.info("CRM dispatcher 停止")


def start_dispatcher(interval: Optional[float] = None, batch_size: int = 20) -> None:
    """
    在服务生命周期内启动后台投递线程（幂等）。
    §3.6：CRM_BACKGROUND_WORKER_ENABLED=0/false/off 时不启动——
    API 与 /crm 只读门户照常工作，投递与回流由另一个启用 worker 的实例承担。
    """
    global _dispatcher_thread
    from core.crm.worker_state import worker_enabled
    from core.alerts import validate_notifications_disabled
    validate_notifications_disabled()
    if not worker_enabled():
        logger.info("CRM_BACKGROUND_WORKER_ENABLED=off：本实例不启动 CRM 后台 worker（API/门户不受影响）")
        return
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

"""阶段 2.9 §3.6：后台 worker 并发保护测试。

运行（services/digital-brain 目录）：
    venv/Scripts/python -m pytest tests/test_crm_worker.py -q

覆盖：多实例租约竞争（只有一个推进 cursor）、租约过期接管、worker 禁用不启动线程、
重启后续跑过期任务、健康状态记录。
"""
from __future__ import annotations

import sys
import threading
from datetime import datetime, timedelta
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import database.models  # noqa: E402,F401
from core.db_manager import SHARED_ENGINE, SharedSessionLocal  # noqa: E402
from core.crm import dispatcher  # noqa: E402
from core.crm.contract import OutcomeEvent, OutcomeFeedResponse  # noqa: E402
from core.crm.outcome_poller import poll_all_outcomes  # noqa: E402
from core.crm.worker_state import (  # noqa: E402
    claim_outcome_lease,
    get_state,
    record_dispatcher_success,
    worker_enabled,
)
from database.base import Base  # noqa: E402
from database.shared_models import (  # noqa: E402
    CrmEntityLink,
    CrmIntegrationConfig,
    CrmOutcomeEvent,
    CrmSyncJob,
    Lead,
    Organization,
)
from routers.lead_router import upsert_lead  # noqa: E402

PROJECT = "66cf2f1a9b2c4d5e6f708192"


@pytest.fixture()
def db():
    Base.metadata.create_all(bind=SHARED_ENGINE)
    session = SharedSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=SHARED_ENGINE)


@pytest.fixture()
def cfg(db):
    org = Organization(name=f"org-{datetime.now().timestamp()}")
    db.add(org)
    db.flush()
    c = CrmIntegrationConfig(
        organization_id=org.id, base_url="http://localhost:5000/api",
        project_id=PROJECT, service_token="gci_test", enabled=True,
        last_health_status="ok",
    )
    db.add(c)
    db.commit()
    return c


class FakePollClient:
    def __init__(self, feed):
        self.feed = feed
        self.calls = 0

    def fetch_outcomes(self, cursor=None, limit=50):
        self.calls += 1
        return self.feed


def _feed():
    ev = OutcomeEvent(
        eventId="ev-w1", cursor="c1", customerId="cust-x", externalId=None,
        fromStatus="quoting", toStatus="won", occurredAt=datetime(2026, 9, 23),
    )
    return OutcomeFeedResponse(items=[ev], nextCursor="c1", hasMore=False)


def test_concurrent_instances_single_cursor_advancer(db, cfg, monkeypatch):
    """两个实例同时轮询：只有抢到租约的实例推进 cursor 并处理事件。"""
    import core.crm.outcome_poller as poller
    client_a, client_b = FakePollClient(_feed()), FakePollClient(_feed())
    monkeypatch.setattr(poller, "client_from_config",
                        lambda c, db=None: client_a)  # 实例 A 的构建器

    # 实例 A 抢到租约并处理
    processed_a = poll_all_outcomes(db, worker_id="instance-A")
    assert processed_a == 1
    assert client_a.calls == 1
    db.refresh(cfg)
    assert cfg.outcome_lease_owner == "instance-A"

    # 实例 B 同刻到来：租约未过期 → 拿不到 → 不发 HTTP、不推进 cursor
    monkeypatch.setattr(poller, "client_from_config",
                        lambda c, db=None: client_b)
    processed_b = poll_all_outcomes(db, worker_id="instance-B")
    assert processed_b == 0
    assert client_b.calls == 0
    # 事件只记录一次
    assert db.query(CrmOutcomeEvent).filter_by(event_id="ev-w1").count() == 1


def test_lease_expiry_takeover(db, cfg, monkeypatch):
    """持有实例崩溃（租约过期）后，另一实例可接管。"""
    assert claim_outcome_lease(db, cfg, "instance-A")
    db.refresh(cfg)
    assert cfg.outcome_lease_owner == "instance-A"

    # 未过期：B 抢不到
    assert claim_outcome_lease(db, cfg, "instance-B") is False

    # 模拟 A 崩溃：租约过期
    db.query(CrmIntegrationConfig).filter_by(id=cfg.id).update(
        {"outcome_lease_expires_at": datetime.now() - timedelta(seconds=1)},
        synchronize_session=False,
    )
    db.commit()
    assert claim_outcome_lease(db, cfg, "instance-B") is True
    db.refresh(cfg)
    assert cfg.outcome_lease_owner == "instance-B"


def test_worker_disabled_starts_no_thread(monkeypatch):
    monkeypatch.setenv("CRM_BACKGROUND_WORKER_ENABLED", "0")
    assert worker_enabled() is False
    dispatcher._dispatcher_thread = None
    dispatcher.start_dispatcher(interval=0.1)
    assert dispatcher._dispatcher_thread is None  # 未启动线程

    monkeypatch.setenv("CRM_BACKGROUND_WORKER_ENABLED", "1")
    assert worker_enabled() is True


def test_restart_recovers_expired_job_lease(db, cfg, monkeypatch):
    """worker 重启：过期租约 job 自动回收并继续投递。"""
    class FakeClient:
        def upsert_customer(self, body, idempotency_key):
            from core.crm.contract import CustomerUpsertResponse
            return CustomerUpsertResponse(
                action="created", customerId="cust-r", projectId=PROJECT,
                externalId=body.externalId, remoteUpdatedAt=datetime.now(),
            )

    monkeypatch.setattr(dispatcher, "client_factory", lambda c, db=None: FakeClient())
    lead = upsert_lead(db, cfg.organization_id, {"email": "restart@x.com"})
    job = db.query(CrmSyncJob).filter_by(lead_id=lead.id).one()

    # 模拟 worker 崩溃：job 卡在 leased 且租约过期
    job.status = "leased"
    job.lease_owner = "crashed-worker"
    job.lease_expires_at = datetime.now() - timedelta(seconds=5)
    db.commit()

    dispatcher.dispatch_once(db, worker_id="restarted-worker")
    db.expire_all()
    job = db.query(CrmSyncJob).filter_by(lead_id=lead.id).one()
    assert job.status == "succeeded"          # 重启后补投成功
    assert job.lease_owner == "restarted-worker"


def test_health_state_recorded(db, cfg):
    record_dispatcher_success(db, "worker-1")
    db.commit()
    state = get_state(db)
    assert state.dispatcher_worker_id == "worker-1"
    assert state.dispatcher_last_success_at is not None

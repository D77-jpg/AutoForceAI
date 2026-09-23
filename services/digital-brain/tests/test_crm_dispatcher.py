"""阶段 2 Wave C：Outbox 入队 + 投递器测试。

运行（services/digital-brain 目录）：
    venv/Scripts/python -m pytest tests/test_crm_dispatcher.py -q

覆盖验收点：
  - 线索写入与 job 创建同一事务（配置启用时自动入队；未启用不入队）
  - 投递成功 → succeeded + crm_entity_links 映射
  - 可重试错误 → 退避重试且复用原幂等键
  - 4xx 字段错误 → 直接死信
  - 401/403 → 配置标记失效并暂停该组织投递；修复配置后自动补投
  - 超过最大重试次数 → 死信
  - 相同载荷重复写入 → 去重为同一 job
  - 租约：被占用的 job 不被重复消费；过期租约自动回收（停机恢复）
"""
from __future__ import annotations

import sys
from datetime import datetime, timedelta
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import database.models  # noqa: E402,F401  mapper 注册
from core.db_manager import SHARED_ENGINE, SharedSessionLocal  # noqa: E402
from core.crm import dispatcher  # noqa: E402
from core.crm.client import CrmApiError  # noqa: E402
from core.crm.contract import CustomerUpsertResponse  # noqa: E402
from database.base import Base  # noqa: E402
from database.shared_models import (  # noqa: E402
    CrmEntityLink,
    CrmIntegrationConfig,
    CrmSyncJob,
    Lead,
    Organization,
)
from routers.lead_router import upsert_lead  # noqa: E402


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
def org(db):
    o = Organization(name=f"org-{datetime.now().timestamp()}")
    db.add(o)
    db.commit()
    return o


@pytest.fixture()
def cfg(db, org):
    c = CrmIntegrationConfig(
        organization_id=org.id,
        base_url="http://crm.local/api",
        project_id="66cf2f1a9b2c4d5e6f708192",
        service_token="gci_test",
        enabled=True,
    )
    db.add(c)
    db.commit()
    return c


def _resp(action="created", customer_id="cust-1", project_id="66cf2f1a9b2c4d5e6f708192"):
    return CustomerUpsertResponse(
        action=action,
        customerId=customer_id,
        projectId=project_id,
        externalId="lead:1",
        remoteUpdatedAt=datetime.now(),
    )


class FakeClient:
    """按队列返回结果/抛错的假 GenesisCRMClient，记录每次调用的幂等键。"""

    def __init__(self, *results):
        self.results = list(results)
        self.calls: list[str] = []

    def upsert_customer(self, body, idempotency_key):
        self.calls.append(idempotency_key)
        item = self.results.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


@pytest.fixture(autouse=True)
def fake_factory(monkeypatch):
    holder: dict = {"client": None}
    monkeypatch.setattr(
        dispatcher, "client_factory", lambda cfg: holder["client"] or FakeClient(_resp())
    )
    return holder


# ---------------------------------------------------------------- enqueue

def test_lead_upsert_enqueues_job_same_transaction(db, org, cfg):
    lead = upsert_lead(db, org.id, {"email": "a@b.com", "name": "Alice", "source": "Website AI Chat"})
    jobs = db.query(CrmSyncJob).filter(CrmSyncJob.lead_id == lead.id).all()
    assert len(jobs) == 1
    job = jobs[0]
    assert job.status == "pending"
    assert job.payload_json["externalId"] == f"lead:{lead.id}"
    assert job.payload_json["email"] == "a@b.com"
    assert job.idempotency_key.startswith(f"lead-{lead.id}-")


def test_no_job_when_config_disabled(db, org):
    lead = upsert_lead(db, org.id, {"email": "b@b.com"})
    assert db.query(CrmSyncJob).filter(CrmSyncJob.lead_id == lead.id).count() == 0


def test_same_payload_dedupes_to_single_job(db, org, cfg):
    lead = upsert_lead(db, org.id, {"email": "c@c.com", "name": "C"})
    upsert_lead(db, org.id, {"email": "c@c.com", "name": "C"})  # 相同载荷重复写入
    jobs = db.query(CrmSyncJob).filter(CrmSyncJob.lead_id == lead.id).all()
    assert len(jobs) == 1


def test_changed_payload_enqueues_new_job(db, org, cfg):
    lead = upsert_lead(db, org.id, {"email": "d@d.com"})
    upsert_lead(db, org.id, {"email": "d@d.com", "company": "New Corp"})  # 载荷变化
    jobs = db.query(CrmSyncJob).filter(CrmSyncJob.lead_id == lead.id).all()
    assert len(jobs) == 2
    assert len({j.idempotency_key for j in jobs}) == 2


def test_dropped_lead_not_enqueued(db, org, cfg):
    lead = upsert_lead(db, org.id, {"email": "e@e.com"})
    lead.status = "dropped"
    db.commit()
    from core.crm.outbox import enqueue_lead_sync
    assert enqueue_lead_sync(db, lead) is None


# ---------------------------------------------------------------- dispatch

def test_dispatch_success_creates_entity_link(db, org, cfg, fake_factory):
    lead = upsert_lead(db, org.id, {"email": "f@f.com", "name": "F"})
    fake_factory["client"] = FakeClient(_resp(customer_id="cust-900"))

    n = dispatcher.dispatch_once(db, worker_id="w1")
    assert n == 1

    job = db.query(CrmSyncJob).filter(CrmSyncJob.lead_id == lead.id).one()
    assert job.status == "succeeded"
    assert job.succeeded_at is not None
    assert job.attempt_count == 1

    link = db.query(CrmEntityLink).filter(CrmEntityLink.lead_id == lead.id).one()
    assert link.remote_customer_id == "cust-900"
    assert link.project_id == cfg.project_id
    assert link.provider == "genesis_crm"


def test_retryable_error_backs_off_and_reuses_key(db, org, cfg, fake_factory):
    lead = upsert_lead(db, org.id, {"email": "g@g.com"})
    client = FakeClient(CrmApiError("CRM 不可达", retryable=True), _resp())
    fake_factory["client"] = client

    dispatcher.dispatch_once(db, worker_id="w1")
    job = db.query(CrmSyncJob).filter(CrmSyncJob.lead_id == lead.id).one()
    assert job.status == "retrying"
    assert job.attempt_count == 1
    assert job.next_attempt_at > datetime.now()
    assert job.next_attempt_at <= datetime.now() + timedelta(seconds=31)

    # 到期后重试：复用同一个幂等键（Genesis 侧据此幂等）
    job.next_attempt_at = datetime.now() - timedelta(seconds=1)
    db.commit()
    dispatcher.dispatch_once(db, worker_id="w1")
    job = db.query(CrmSyncJob).filter(CrmSyncJob.lead_id == lead.id).one()
    assert job.status == "succeeded"
    assert client.calls[0] == client.calls[1] == job.idempotency_key


def test_validation_error_goes_dead_immediately(db, org, cfg, fake_factory):
    lead = upsert_lead(db, org.id, {"email": "h@h.com"})
    fake_factory["client"] = FakeClient(
        CrmApiError("数据校验未通过", code="VALIDATION_ERROR", http_status=422)
    )
    dispatcher.dispatch_once(db, worker_id="w1")
    job = db.query(CrmSyncJob).filter(CrmSyncJob.lead_id == lead.id).one()
    assert job.status == "dead"
    assert job.dead_at is not None
    assert job.last_error_code == "VALIDATION_ERROR"
    assert job.attempt_count == 1  # 4xx 不重试


def test_auth_invalid_pauses_org_and_recovers_after_fix(db, org, cfg, fake_factory):
    lead = upsert_lead(db, org.id, {"email": "i@i.com"})
    fake_factory["client"] = FakeClient(
        CrmApiError("服务凭证无效或已失效", code="UNAUTHORIZED", http_status=401, auth_invalid=True)
    )
    dispatcher.dispatch_once(db, worker_id="w1")

    job = db.query(CrmSyncJob).filter(CrmSyncJob.lead_id == lead.id).one()
    assert job.status == "retrying"
    assert job.last_error_code == "UNAUTHORIZED"
    cfg = db.query(CrmIntegrationConfig).filter_by(organization_id=org.id).one()
    assert cfg.last_health_status == "auth_invalid"  # 配置被标记失效 → 暂停新投递

    # 暂停期间：到期也不会真正发起 HTTP 调用
    paused_client = FakeClient(_resp())
    fake_factory["client"] = paused_client
    job.next_attempt_at = datetime.now() - timedelta(seconds=1)
    db.commit()
    dispatcher.dispatch_once(db, worker_id="w1")
    assert paused_client.calls == []
    job = db.query(CrmSyncJob).filter(CrmSyncJob.lead_id == lead.id).one()
    assert job.status == "retrying"  # 暂停期不投递

    # 管理员修复配置（保存后 last_health_status 重置）→ 恢复补投
    cfg.last_health_status = "unchecked"
    db.commit()
    fake_factory["client"] = FakeClient(_resp(customer_id="cust-recovered"))
    job = db.query(CrmSyncJob).filter(CrmSyncJob.lead_id == lead.id).one()
    job.next_attempt_at = datetime.now() - timedelta(seconds=1)
    db.commit()
    dispatcher.dispatch_once(db, worker_id="w1")
    job = db.query(CrmSyncJob).filter(CrmSyncJob.lead_id == lead.id).one()
    assert job.status == "succeeded"


def test_max_attempts_then_dead(db, org, cfg, fake_factory):
    lead = upsert_lead(db, org.id, {"email": "j@j.com"})
    fake_factory["client"] = FakeClient(CrmApiError("timeout", retryable=True))

    job = db.query(CrmSyncJob).filter(CrmSyncJob.lead_id == lead.id).one()
    for attempt in range(1, dispatcher.MAX_ATTEMPTS + 2):
        job.status = "pending"
        job.next_attempt_at = datetime.now() - timedelta(seconds=1)
        db.commit()
        dispatcher.dispatch_once(db, worker_id="w1")
        job = db.query(CrmSyncJob).filter(CrmSyncJob.lead_id == lead.id).one()
        if job.status == "dead":
            break
    assert job.status == "dead"
    assert job.attempt_count == dispatcher.MAX_ATTEMPTS


def test_lease_prevents_double_processing_and_expired_lease_recovers(db, org, cfg, fake_factory):
    lead = upsert_lead(db, org.id, {"email": "k@k.com"})
    job = db.query(CrmSyncJob).filter(CrmSyncJob.lead_id == lead.id).one()

    # 别的 worker 持有有效租约 → 本 worker 抢不到
    job.status = "leased"
    job.lease_owner = "other-worker"
    job.lease_expires_at = datetime.now() + timedelta(minutes=5)
    db.commit()
    assert dispatcher.dispatch_once(db, worker_id="w1") == 0

    # 租约过期（对方崩溃/停机）→ 自动回收并补投
    job.lease_expires_at = datetime.now() - timedelta(seconds=1)
    db.commit()
    fake_factory["client"] = FakeClient(_resp())
    assert dispatcher.dispatch_once(db, worker_id="w1") == 1
    job = db.query(CrmSyncJob).filter(CrmSyncJob.lead_id == lead.id).one()
    assert job.status == "succeeded"

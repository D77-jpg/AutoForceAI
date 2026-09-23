"""阶段 2.9 P0-2：项目绑定变更保护与 reset-binding。

运行（services/digital-brain 目录）：
    venv/Scripts/python -m pytest tests/test_crm_binding.py -q
"""
from __future__ import annotations

import sys
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import database.models  # noqa: E402,F401
from core.db_manager import SHARED_ENGINE, SharedSessionLocal  # noqa: E402
from core.crm import dispatcher  # noqa: E402
from core.crm.outbox import enqueue_lead_sync  # noqa: E402
from database.base import Base  # noqa: E402
from database.shared_models import (  # noqa: E402
    CrmEntityLink,
    CrmIntegrationConfig,
    CrmSyncJob,
    Lead,
    Organization,
    User,
    UserRole,
)
from routers.crm_integration_router import (  # noqa: E402
    ConfigIn,
    ResetBindingIn,
    reset_binding,
    retry_job,
    save_config,
)
from routers.lead_router import upsert_lead  # noqa: E402

PROJECT_A = "66cf2f1a9b2c4d5e6f700001"
PROJECT_B = "66cf2f1a9b2c4d5e6f700002"
BASE_URL = "http://localhost:5000/api"


class FakeClient:
    def __init__(self, customer_id="cust-a"):
        self.calls = []
        self.customer_id = customer_id

    def upsert_customer(self, request, idempotency_key):
        from core.crm.contract import CustomerUpsertResponse
        self.calls.append((request.externalId, idempotency_key))
        return CustomerUpsertResponse(
            action="created",
            customerId=self.customer_id,
            projectId=PROJECT_A if "a" in self.customer_id else PROJECT_B,
            externalId=request.externalId,
            remoteUpdatedAt=datetime.now(),
        )


def _payload(user_id):
    return {"id": user_id}


@pytest.fixture()
def db():
    Base.metadata.create_all(bind=SHARED_ENGINE)
    session = SharedSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=SHARED_ENGINE)


@pytest.fixture(autouse=True)
def _enc_key(monkeypatch):
    """保存配置时旧明文 token 会触发迁移，测试统一提供加密密钥。"""
    from cryptography.fernet import Fernet
    monkeypatch.setenv("CRM_CREDENTIAL_ENCRYPTION_KEY", Fernet.generate_key().decode())


@pytest.fixture()
def env(db):
    org = Organization(name=f"org-{datetime.now().timestamp()}")
    db.add(org)
    db.flush()
    admin = User(username=f"adm{int(datetime.now().timestamp()*1000)}", email="a@x.com",
                 hashed_password="x", role=UserRole.ENTERPRISE_ADMIN.value, organization_id=org.id)
    db.add(admin)
    cfg = CrmIntegrationConfig(
        organization_id=org.id, base_url=BASE_URL, project_id=PROJECT_A,
        service_token="gci_test", enabled=True, last_health_status="ok",
        outcome_cursor="cursor-old",
    )
    db.add(cfg)
    db.commit()
    return {"org": org, "admin": admin, "cfg": cfg}


def _save(db, admin, project_id, base_url=BASE_URL):
    return save_config(
        ConfigIn(base_url=base_url, project_id=project_id),
        _payload(admin.id), db,
    )


def _enable(db, org_id):
    """P0-5 后保存不再控制启用；测试直接置位（启用门槛由 test_crm_enable_gate 覆盖）。"""
    cfg = db.query(CrmIntegrationConfig).filter_by(organization_id=org_id).one()
    cfg.enabled = True
    db.commit()


def test_project_change_allowed_without_history(db, env):
    """没有任何同步历史时允许直接改 project_id。"""
    _save(db, env["admin"], PROJECT_B)
    db.refresh(env["cfg"])
    assert env["cfg"].project_id == PROJECT_B


def test_same_project_cannot_bind_two_organizations(db, env):
    """一个 Genesis project 只能由一个 AutoForceAI organization 持有。"""
    other_org = Organization(name=f"org-other-{datetime.now().timestamp()}")
    db.add(other_org)
    db.flush()
    other_admin = User(
        username=f"adm-other-{int(datetime.now().timestamp()*1000)}",
        email="other@x.com",
        hashed_password="x",
        role=UserRole.ENTERPRISE_ADMIN.value,
        organization_id=other_org.id,
    )
    db.add(other_admin)
    db.commit()

    with pytest.raises(HTTPException) as exc:
        _save(db, other_admin, PROJECT_A)
    assert exc.value.status_code == 409
    assert "已绑定" in exc.value.detail


def test_database_constraint_closes_project_binding_race(db, env):
    """并发请求即使越过应用层预检，数据库唯一索引仍拒绝重复绑定。"""
    other_org = Organization(name=f"org-race-{datetime.now().timestamp()}")
    db.add(other_org)
    db.flush()
    db.add(CrmIntegrationConfig(
        organization_id=other_org.id,
        provider="genesis_crm",
        base_url=BASE_URL,
        project_id=PROJECT_A,
        service_token="gci_other",
    ))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_project_change_blocked_with_history(db, env, monkeypatch):
    """有 succeeded job / 实体映射时，普通保存拒绝切换 project。"""
    lead = upsert_lead(db, env["org"].id, {"email": "h1@x.com"})
    monkeypatch.setattr(dispatcher, "client_factory", lambda cfg, db=None: FakeClient("cust-a"))
    dispatcher.dispatch_once(db, worker_id="w-bind")
    assert db.query(CrmSyncJob).filter_by(lead_id=lead.id).one().status == "succeeded"
    assert db.query(CrmEntityLink).count() == 1

    with pytest.raises(HTTPException) as exc:
        _save(db, env["admin"], PROJECT_B)
    assert exc.value.status_code == 409
    assert "reset-binding" in exc.value.detail


def test_reset_binding_archives_links_and_cancels_jobs(db, env, monkeypatch):
    lead = upsert_lead(db, env["org"].id, {"email": "h2@x.com"})
    monkeypatch.setattr(dispatcher, "client_factory", lambda cfg, db=None: FakeClient("cust-a"))
    dispatcher.dispatch_once(db, worker_id="w-bind")

    lead2 = upsert_lead(db, env["org"].id, {"email": "h3@x.com"})  # 未投递 → pending
    pending_job = db.query(CrmSyncJob).filter_by(lead_id=lead2.id).one()
    pending_job.next_attempt_at = datetime.now() + timedelta(hours=1)  # 保持 pending
    db.commit()

    # 确认串错误 → 拒绝
    with pytest.raises(HTTPException) as exc:
        reset_binding(ResetBindingIn(expected_project_id=PROJECT_A, confirmation="reset"), _payload(env["admin"].id), db)
    assert exc.value.status_code == 400
    # expected_project_id 不符 → 拒绝
    with pytest.raises(HTTPException) as exc:
        reset_binding(ResetBindingIn(expected_project_id=PROJECT_B, confirmation="RESET"), _payload(env["admin"].id), db)
    assert exc.value.status_code == 409

    result = reset_binding(
        ResetBindingIn(expected_project_id=PROJECT_A, confirmation="RESET"),
        _payload(env["admin"].id), db,
    )
    assert result["previous_project_id"] == PROJECT_A
    assert result["archived_links"] == 1
    assert result["cancelled_jobs"] == 1

    db.expire_all()
    cfg = db.query(CrmIntegrationConfig).filter_by(organization_id=env["org"].id).one()
    assert cfg.enabled is False
    assert cfg.project_id is None
    assert cfg.outcome_cursor is None
    assert cfg.last_reset_by == env["admin"].id
    link = db.query(CrmEntityLink).filter_by(lead_id=lead.id).one()
    assert link.archived_at is not None                     # 归档而非删除
    job2 = db.query(CrmSyncJob).filter_by(lead_id=lead2.id).one()
    assert job2.status == "cancelled"                       # 未完成 job 已取消
    assert db.query(Lead).filter_by(id=lead.id).count() == 1  # 本地线索保留


def test_after_reset_old_jobs_never_deliver_to_new_project(db, env, monkeypatch):
    """reset → 绑定新项目 → 旧 job 不重投、旧 payload 不进新项目、游标不带入。"""
    client_a = FakeClient("cust-a")
    monkeypatch.setattr(dispatcher, "client_factory", lambda cfg, db=None: client_a)
    lead = upsert_lead(db, env["org"].id, {"email": "h4@x.com"})
    dispatcher.dispatch_once(db, worker_id="w-bind")
    old_job = db.query(CrmSyncJob).filter_by(lead_id=lead.id).one()
    assert old_job.status == "succeeded"

    reset_binding(ResetBindingIn(expected_project_id=PROJECT_A, confirmation="RESET"),
                  _payload(env["admin"].id), db)

    # 绑定新项目（无历史 → 允许；P0-5 语义下保存自动停用，测试重新启用）
    _save(db, env["admin"], PROJECT_B)
    _enable(db, env["org"].id)
    cfg = db.query(CrmIntegrationConfig).filter_by(organization_id=env["org"].id).one()
    stale = CrmSyncJob(
        organization_id=env["org"].id, lead_id=lead.id, project_id=PROJECT_A,
        idempotency_key=f"stale-{datetime.now().timestamp()}", payload_hash="x",
        payload_json={"externalId": f"lead:{lead.id}", "initialStatus": "pending", "schemaVersion": "1.0"},
        status="pending", next_attempt_at=datetime.now() - timedelta(seconds=1),
    )
    db.add(stale)
    db.commit()

    client_b = FakeClient("cust-b")
    monkeypatch.setattr(dispatcher, "client_factory", lambda cfg, db=None: client_b)
    dispatcher.dispatch_once(db, worker_id="w-bind")

    db.expire_all()
    stale = db.query(CrmSyncJob).filter_by(id=stale.id).one()
    assert stale.status == "cancelled"                       # 纵深防御：旧项目 job 被取消
    assert stale.last_error_code == "PROJECT_BINDING_CHANGED"
    assert client_b.calls == []                              # 没有向新项目发起任何旧载荷投递
    assert cfg.outcome_cursor is None                        # 旧游标不带入新项目

    # 同一线索可正常投递到新项目（载荷去重只限同项目）
    job = enqueue_lead_sync(db, db.query(Lead).filter_by(id=lead.id).one())
    assert job is not None and job.project_id == PROJECT_B


def test_old_project_dead_job_cannot_be_retried(db, env, monkeypatch):
    lead = upsert_lead(db, env["org"].id, {"email": "h5@x.com"})
    job = db.query(CrmSyncJob).filter_by(lead_id=lead.id).one()
    job.status = "dead"
    db.commit()

    reset_binding(ResetBindingIn(expected_project_id=PROJECT_A, confirmation="RESET"),
                  _payload(env["admin"].id), db)
    _save(db, env["admin"], PROJECT_B)
    _enable(db, env["org"].id)

    with pytest.raises(HTTPException) as exc:
        retry_job(job.id, _payload(env["admin"].id), db)
    assert exc.value.status_code == 400
    assert "旧项目" in exc.value.detail

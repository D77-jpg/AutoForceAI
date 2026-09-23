"""阶段 2.9 P0-5：保存/测试/启用拆分与启用门槛。

运行（services/digital-brain 目录）：
    venv/Scripts/python -m pytest tests/test_crm_enable_gate.py -q

覆盖：未测试不能启用、测试失败不能启用、测试过期（>10min）不能启用、
指纹匹配且未过期可启用、改 token/project/base_url 自动停用且测试结论失效。
"""
from __future__ import annotations

import sys
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from fastapi import HTTPException

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import database.models  # noqa: E402,F401
from core.db_manager import SHARED_ENGINE, SharedSessionLocal  # noqa: E402
from database.base import Base  # noqa: E402
from database.shared_models import (  # noqa: E402
    CrmIntegrationConfig,
    Organization,
    User,
    UserRole,
)
import routers.crm_integration_router as r  # noqa: E402

PROJECT = "66cf2f1a9b2c4d5e6f700001"
BASE_URL = "http://localhost:5000/api"


@pytest.fixture(autouse=True)
def _enc_key(monkeypatch):
    monkeypatch.setenv("CRM_CREDENTIAL_ENCRYPTION_KEY", "phase2-enable-gate-key")


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
def admin(db):
    org = Organization(name=f"org-{datetime.now().timestamp()}")
    db.add(org)
    db.flush()
    user = User(username=f"gate{int(datetime.now().timestamp()*1000)}", email="g@x.com",
                hashed_password="x", role=UserRole.ENTERPRISE_ADMIN.value, organization_id=org.id)
    db.add(user)
    db.commit()
    return user


def _payload(user_id):
    return {"id": user_id}


def _save(db, admin, **kw):
    body = r.ConfigIn(
        base_url=kw.get("base_url", BASE_URL),
        project_id=kw.get("project_id", PROJECT),
        service_token=kw.get("service_token"),
    )
    return r.save_config(body, _payload(admin.id), db)


def _fake_test(ok: bool):
    def _run(cfg, db=None):
        return r.TestResult(
            ok=ok,
            detail="ok" if ok else "bad token",
            scopes=["customers:write", "outcomes:read", "stats:read", "customers:read"] if ok else None,
            project_name="Genesis Bags" if ok else None,
            contract_version="1.0",
        )
    return _run


def _test_ok(db, admin, monkeypatch):
    monkeypatch.setattr(r, "run_connection_test", _fake_test(True))
    return r.test_connection(_payload(admin.id), db)


def test_enable_requires_successful_fresh_test(db, admin, monkeypatch):
    _save(db, admin, service_token="gci_new_token_0001")
    # 未测试 → 409
    with pytest.raises(HTTPException) as exc:
        r.enable_sync(_payload(admin.id), db)
    assert exc.value.status_code == 409

    # 测试失败 → 409
    monkeypatch.setattr(r, "run_connection_test", _fake_test(False))
    r.test_connection(_payload(admin.id), db)
    with pytest.raises(HTTPException):
        r.enable_sync(_payload(admin.id), db)

    # 测试成功 → 可启用
    _test_ok(db, admin, monkeypatch)
    result = r.enable_sync(_payload(admin.id), db)
    assert result["config"]["enabled"] is True
    assert result["config"]["test_valid"] is True


def test_expired_test_cannot_enable(db, admin, monkeypatch):
    _save(db, admin, service_token="gci_new_token_0002")
    _test_ok(db, admin, monkeypatch)

    cfg = db.query(CrmIntegrationConfig).filter_by(organization_id=admin.organization_id).one()
    cfg.last_health_checked_at = datetime.now() - timedelta(seconds=601)  # 超过 10 分钟
    db.commit()

    with pytest.raises(HTTPException) as exc:
        r.enable_sync(_payload(admin.id), db)
    assert exc.value.status_code == 409
    assert r._test_valid(cfg) is False


def test_failed_test_auto_disables(db, admin, monkeypatch):
    _save(db, admin, service_token="gci_new_token_0003")
    _test_ok(db, admin, monkeypatch)
    r.enable_sync(_payload(admin.id), db)

    # 轮换后凭证失效：测试失败 → 自动停用
    monkeypatch.setattr(r, "run_connection_test", _fake_test(False))
    r.test_connection(_payload(admin.id), db)
    cfg = db.query(CrmIntegrationConfig).filter_by(organization_id=admin.organization_id).one()
    assert cfg.enabled is False
    assert cfg.health_fingerprint is None


def test_changing_token_disables_and_invalidates(db, admin, monkeypatch):
    _save(db, admin, service_token="gci_new_token_0004")
    _test_ok(db, admin, monkeypatch)
    r.enable_sync(_payload(admin.id), db)

    result = _save(db, admin, service_token="gci_rotated_token_0004")
    cfg = result["config"]
    assert cfg["enabled"] is False              # 修改 token → 自动停用
    assert cfg["test_valid"] is False           # 旧测试结论失效
    assert cfg["token_preview"] == "****0004"

    with pytest.raises(HTTPException):
        r.enable_sync(_payload(admin.id), db)   # 必须重新测试


def test_changing_project_or_base_url_disables(db, admin, monkeypatch):
    _save(db, admin, service_token="gci_new_token_0005")
    _test_ok(db, admin, monkeypatch)
    r.enable_sync(_payload(admin.id), db)

    # 无同步历史时允许改 project，但自动停用并清游标
    cfg_obj = db.query(CrmIntegrationConfig).filter_by(organization_id=admin.organization_id).one()
    cfg_obj.outcome_cursor = "some-cursor"
    db.commit()
    result = _save(db, admin, project_id="66cf2f1a9b2c4d5e6f700002")
    assert result["config"]["enabled"] is False
    cfg_obj = db.query(CrmIntegrationConfig).filter_by(organization_id=admin.organization_id).one()
    assert cfg_obj.outcome_cursor is None

    # 改 base_url 同样停用
    r.enable_sync(_payload(admin.id), db) if r._test_valid(cfg_obj) else None
    _test_ok(db, admin, monkeypatch)
    r.enable_sync(_payload(admin.id), db)
    result = _save(db, admin, base_url="http://localhost:5001/api", project_id="66cf2f1a9b2c4d5e6f700002")
    assert result["config"]["enabled"] is False


def test_identical_save_preserves_enable_but_invalidates_test(db, admin, monkeypatch):
    _save(db, admin, service_token="gci_new_token_0006")
    _test_ok(db, admin, monkeypatch)
    r.enable_sync(_payload(admin.id), db)

    # 内容未变的保存：不自动停用，但测试结论必须重新取得（保守策略）
    result = _save(db, admin)
    assert result["config"]["enabled"] is True
    assert result["config"]["test_valid"] is False


def test_disable_endpoint(db, admin, monkeypatch):
    _save(db, admin, service_token="gci_new_token_0007")
    _test_ok(db, admin, monkeypatch)
    r.enable_sync(_payload(admin.id), db)
    result = r.disable_sync(_payload(admin.id), db)
    assert result["config"]["enabled"] is False

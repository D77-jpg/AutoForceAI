"""Worker incident isolation/semantics without network or outbound notifications."""
from datetime import datetime, timedelta
import os
import sys
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import database.models  # noqa: E402,F401
from database.base import Base
from database.shared_models import Alert, Organization, User
from core.alerts import (record_failure, record_recovery, record_rpa_job_outcome,
                         cleanup_resolved, validate_notifications_disabled)
from core.db_manager import get_shared_db
from core.dependencies import get_current_user
from routers.alert_router import router


@pytest.fixture()
def db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False},
                           poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def test_fingerprint_lifecycle_and_isolation(db):
    one = record_failure(db, organization_id=1, source="crm_dispatcher", category="TIMEOUT")
    db.commit()
    assert one.event_type == "first" and one.occurrences == 1
    record_failure(db, organization_id=1, source="crm_dispatcher", category="TIMEOUT")
    db.commit()
    assert one.event_type == "new" and one.occurrences == 2
    record_failure(db, organization_id=1, source="crm_dispatcher", category="TIMEOUT", severity="critical")
    db.commit()
    assert (one.event_type, one.severity, one.occurrences) == ("escalated", "critical", 3)
    two = record_failure(db, organization_id=2, source="crm_dispatcher", category="TIMEOUT")
    assert two.fingerprint != one.fingerprint
    assert record_recovery(db, organization_id=1, source="crm_dispatcher") == 1
    db.commit()
    assert one.status == "resolved" and one.event_type == "recovered"
    assert record_recovery(db, organization_id=1, source="crm_dispatcher") == 0
    record_failure(db, organization_id=1, source="crm_dispatcher", category="TIMEOUT")
    db.commit()
    assert one.status == "open" and one.occurrences == 4 and one.event_type == "first"


def test_redaction_and_unowned_rpa(db):
    secret = "Bearer secret@example.com http://169.254.169.254"
    row = record_failure(db, organization_id=1, source="crm_outcome", category=secret)
    assert row.category == "UNKNOWN" and secret not in row.summary
    assert record_failure(db, organization_id=None, source="rpa", category="FAIL") is None
    org = Organization(name="org")
    db.add(org)
    db.flush()
    user = User(username="one", organization_id=org.id)
    db.add(user)
    db.flush()
    job = type("Job", (), {"user_id": user.id, "result_log": secret})()
    record_rpa_job_outcome(db, job, failed=True)
    assert secret not in db.query(Alert).filter(Alert.source == "rpa").one().summary
    record_rpa_job_outcome(db, job, failed=False)
    assert db.query(Alert).filter(Alert.source == "rpa").one().status == "resolved"


def test_retention_only_resolved_and_outbound_prohibited(db, monkeypatch):
    old = record_failure(db, organization_id=1, source="rpa", category="JOB_FAILED")
    other = record_failure(db, organization_id=2, source="rpa", category="JOB_FAILED")
    record_recovery(db, organization_id=1, source="rpa")
    old.resolved_at = datetime.now() - timedelta(days=100)
    db.commit()
    monkeypatch.setenv("ALERT_RETENTION_DAYS", "90")
    assert cleanup_resolved(db) == 1
    assert db.query(Alert).one().id == other.id
    for key in ("ALERT_WEBHOOK_URL", "ALERT_EMAIL_TO", "ALERT_NOTIFICATIONS_ENABLED"):
        monkeypatch.setenv(key, "http://169.254.169.254/latest/meta-data/")
        with pytest.raises(ValueError, match="unsupported"):
            validate_notifications_disabled()
        monkeypatch.delenv(key)
    monkeypatch.setenv("ALERT_RETENTION_DAYS", "0")
    with pytest.raises(ValueError):
        cleanup_resolved(db)


def test_api_organization_and_admin_permission(db):
    org1, org2 = Organization(name="one"), Organization(name="two")
    db.add_all([org1, org2]); db.flush()
    admin = User(username="admin", organization_id=org1.id, role="enterprise_admin", is_active=True)
    member = User(username="member", organization_id=org1.id, role="user", is_active=True)
    outsider = User(username="other", organization_id=org2.id, role="enterprise_admin", is_active=True)
    db.add_all([admin, member, outsider]); db.flush()
    own = record_failure(db, organization_id=org1.id, source="rpa", category="JOB_FAILED")
    foreign = record_failure(db, organization_id=org2.id, source="rpa", category="JOB_FAILED")
    db.commit()
    app = FastAPI(); app.include_router(router)
    app.dependency_overrides[get_shared_db] = lambda: db
    current = {"user": admin}
    app.dependency_overrides[get_current_user] = lambda: {"id": current["user"].id,
                                                          "org_id": org2.id, "role": "admin"}
    client = TestClient(app)
    result = client.get("/api/v1/monitor/alerts").json()
    assert result["total"] == 1 and result["items"][0]["id"] == own.id
    assert "fingerprint" not in result["items"][0]
    assert client.post(f"/api/v1/monitor/alerts/{foreign.id}/ack").status_code == 404
    current["user"] = member
    assert client.post(f"/api/v1/monitor/alerts/{own.id}/ack").status_code == 403
    current["user"] = admin
    assert client.post(f"/api/v1/monitor/alerts/{own.id}/ack").json()["status"] == "acknowledged"
    assert client.post(f"/api/v1/monitor/alerts/{own.id}/resolve").json()["status"] == "resolved"
    assert client.get("/api/v1/monitor/alerts?status=resolved").json()["total"] == 1

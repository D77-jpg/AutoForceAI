"""首页线索轻量统计接口。"""
from __future__ import annotations

import sys
from datetime import datetime, timedelta
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import database.models  # noqa: E402,F401
from core.db_manager import SHARED_ENGINE, SharedSessionLocal  # noqa: E402
from database.base import Base  # noqa: E402
from database.shared_models import Lead, Organization, User, UserRole  # noqa: E402
from routers.lead_router import lead_summary  # noqa: E402


@pytest.fixture()
def db():
    Base.metadata.create_all(bind=SHARED_ENGINE)
    session = SharedSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=SHARED_ENGINE)


def test_lead_summary_is_scoped_and_counts_today(db):
    org = Organization(name="dashboard-org")
    other_org = Organization(name="other-org")
    db.add_all([org, other_org])
    db.flush()
    user = User(
        username="dashboard-admin",
        email="dashboard@example.com",
        hashed_password="x",
        role=UserRole.ENTERPRISE_ADMIN.value,
        organization_id=org.id,
    )
    db.add(user)
    db.flush()
    db.add_all([
        Lead(organization_id=org.id, source="test", status="new", created_at=datetime.now()),
        Lead(organization_id=org.id, source="test", status="converted", created_at=datetime.now()),
        Lead(
            organization_id=org.id,
            source="test",
            status="contacted",
            created_at=datetime.now() - timedelta(days=1),
        ),
        Lead(organization_id=other_org.id, source="test", status="new", created_at=datetime.now()),
    ])
    db.commit()

    result = lead_summary({"id": user.id}, db)

    assert result == {
        "total": 3,
        "today": 2,
        "by_status": {"contacted": 1, "converted": 1, "dropped": 0, "new": 1},
    }

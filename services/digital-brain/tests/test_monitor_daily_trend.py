"""UTC daily usage buckets, half-open boundaries, and missing-cost semantics."""
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from database.shared_models import LLMRequestLog  # noqa: E402
import routers.monitor_router as monitor  # noqa: E402


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    LLMRequestLog.__table__.create(engine)
    with Session(engine) as session:
        yield session
    engine.dispose()


def freeze_utc(monkeypatch):
    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            instant = datetime(2025, 10, 3, 12, tzinfo=timezone.utc)
            return instant.astimezone(tz) if tz else instant.replace(tzinfo=None)

    monkeypatch.setattr(monitor, "datetime", Clock)


def add_log(db, when, tokens, status="success", provider="demo"):
    db.add(LLMRequestLog(created_at=when, total_tokens=tokens,
                         status=status, provider=provider))
    db.commit()


def test_continuous_dates_and_utc_midnight_boundaries(db, monkeypatch):
    freeze_utc(monkeypatch)
    # UTC 00:00 belongs to Oct 3; end of yesterday belongs to Oct 2.
    add_log(db, datetime(2025, 10, 1, 23, 59, 59, 999999), 2)
    add_log(db, datetime(2025, 10, 2, 0, 0), 3)
    add_log(db, datetime(2025, 10, 2, 23, 59, 59, 999999), 5, "error")
    add_log(db, datetime(2025, 10, 3, 0, 0), 7, "success", None)
    add_log(db, datetime(2025, 10, 4, 0, 0), 100)  # Tomorrow is excluded.
    result = monitor.get_llm_usage(days=3, db=db)
    assert result["daily_trend"] == [
        {"date": "2025-10-01", "tokens": 2, "calls": 1,
         "success": 1, "failure": 0, "cost_usd": None},
        {"date": "2025-10-02", "tokens": 8, "calls": 2,
         "success": 1, "failure": 1, "cost_usd": None},
        {"date": "2025-10-03", "tokens": 7, "calls": 1,
         "success": 1, "failure": 0, "cost_usd": None},
    ]
    assert result["summary"] == {"total_tokens": 17, "total_calls": 4,
                                 "success": 3, "failure": 1, "cost_usd": None}
    assert result["by_provider"] == {"demo": 10, "unknown": 7}


def test_empty_days_are_zero_and_cost_remains_unknown(db, monkeypatch):
    freeze_utc(monkeypatch)
    add_log(db, datetime(2025, 9, 30, 23, 59, 59), 99)  # Outside window.
    add_log(db, datetime(2025, 10, 1, 0, 0), None, "timeout")
    result = monitor.get_llm_usage(days=3, db=db)
    assert [row["date"] for row in result["daily_trend"]] == [
        "2025-10-01", "2025-10-02", "2025-10-03"]
    assert result["daily_trend"][0]["failure"] == 1
    assert result["daily_trend"][1] == {
        "date": "2025-10-02", "tokens": 0, "calls": 0,
        "success": 0, "failure": 0, "cost_usd": None}
    assert result["summary"]["cost_usd"] is None
    assert result["summary"]["total_tokens"] == 0


def test_endpoint_rejects_invalid_day_count():
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    app = FastAPI()
    app.include_router(monitor.router)
    for days in (0, -1, 367):
        response = TestClient(app).get(f"/api/v1/monitor/llm/usage?days={days}")
        assert response.status_code == 422

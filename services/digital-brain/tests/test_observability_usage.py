"""Observability contracts: provider-response provenance and metadata-only telemetry.

No real provider HTTP or server startup: the model factory and API routes are mocked.
Run from services/digital-brain: venv/Scripts/python -m pytest tests/test_observability_usage.py -q
"""
from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import Mock
from uuid import UUID

import pytest
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.llm import monitor, runtime  # noqa: E402
from database.shared_models import LLMRequestLog  # noqa: E402


@pytest.fixture
def usage_db(monkeypatch):
    """An independent, in-memory audit table: no production DB writes."""
    engine = create_engine("sqlite+pysqlite:///:memory:")
    LLMRequestLog.__table__.create(engine)
    monkeypatch.setattr(monitor, "SharedSessionLocal", lambda: Session(engine))
    with Session(engine) as db:
        yield db
    engine.dispose()


def _saved(db):
    db.expire_all()
    return db.query(LLMRequestLog).order_by(LLMRequestLog.id).all()


def test_cost_monitor_persists_actual_usage_and_unknown_cost(usage_db):
    monitor.CostMonitor.log_request(
        provider="openai_compatible", model="served-model-v2",
        input_tokens=17, output_tokens=9, latency_ms=123,
        status="success", cost_usd=None, trace_id="req-mocked-01",
    )
    (log,) = _saved(usage_db)
    assert (log.provider, log.model) == ("openai_compatible", "served-model-v2")
    assert (log.input_tokens, log.output_tokens, log.total_tokens) == (17, 9, 26)
    assert (log.latency_ms, log.status, log.trace_id) == (123, "success", "req-mocked-01")
    assert log.cost_usd is None  # Unknown price is not an invented zero.
    assert log.error_category is None
    assert log.error_msg is None


def test_cost_monitor_failure_stores_category_not_exception_or_secret(usage_db, capsys):
    secret = "sk-dummy-token-DO-NOT-LOG"
    password = "dummy-password-DO-NOT-LOG"
    raw_exception = f"HTTP 401 bearer {secret} password={password} body=private-prompt"
    monitor.CostMonitor.log_request(
        provider="unknown", model="unknown", input_tokens=0, output_tokens=0,
        latency_ms=48, status="error", error_category="authentication_error",
        error_msg=raw_exception, cost_usd=None,
    )
    (log,) = _saved(usage_db)
    assert (log.status, log.error_category, log.cost_usd) == ("error", "AUTHENTICATION_ERROR", None)
    assert (log.input_tokens, log.output_tokens, log.total_tokens, log.latency_ms) == (0, 0, 0, 48)
    assert not log.error_msg or log.error_msg == "AUTHENTICATION_ERROR"
    stored = repr(vars(log))
    output = capsys.readouterr()
    for sensitive in (secret, password, "private-prompt", raw_exception):
        assert sensitive not in stored
        assert sensitive not in output.out + output.err


def test_runtime_response_provenance_and_fake_failure_without_external_http(monkeypatch):
    """Configured name is a request hint; only response metadata proves served model."""
    model = NS(name="requested-model", api_key="dummy-provider-key", base_url="https://mock.invalid/v1", provider=None)
    usage_calls = []
    monkeypatch.setattr(monitor.CostMonitor, "log_request", lambda **kwargs: usage_calls.append(kwargs))
    monkeypatch.setattr(runtime, "get_default_llm_model", lambda db: model)
    calls = []

    class FakeProvider:
        provider_name = "openai_compatible"

        def chat(self, messages, **kwargs):
            calls.append((messages, kwargs))
            return NS(
                content="safe fake answer", usage={"input_tokens": 17, "output_tokens": 9},
                raw_response=NS(model="served-model-v2", _request_id="req-mocked-01"),
                model_name="requested-model",
            )

    fake = FakeProvider()

    def get_provider(name, **kwargs):
        assert name == "requested-model"
        assert kwargs["api_key"] == "dummy-provider-key"
        assert kwargs["base_url"] == "https://mock.invalid/v1"
        return fake

    monkeypatch.setattr(runtime.ModelFactory, "get_provider", get_provider)
    result = runtime.query_default_llm_with_attribution(Mock(), "dummy prompt")
    assert len(calls) == 1
    assert calls[0][0] == [{"role": "user", "content": "dummy prompt"}]
    assert (result.provider, result.model, result.request_id, result.content) == (
        "openai_compatible", "served-model-v2", "req-mocked-01", "safe fake answer")
    assert result.model != model.name
    assert len(usage_calls) == 1
    success = usage_calls[0]
    for key, expected in {
        "provider": "openai_compatible", "model": "served-model-v2",
        "input_tokens": 17, "output_tokens": 9, "status": "success", "cost_usd": None,
    }.items():
        assert success[key] == expected
    assert isinstance(success["latency_ms"], (int, float)) and success["latency_ms"] >= 0

    def fail(*args, **kwargs):
        raise RuntimeError("dummy provider failure; sk-dummy-secret-DO-NOT-LOG")

    monkeypatch.setattr(fake, "chat", fail)
    with pytest.raises(RuntimeError, match="dummy provider failure"):
        runtime.query_default_llm_with_attribution(Mock(), "dummy prompt")
    assert len(usage_calls) == 2
    failure = usage_calls[1]
    assert failure["status"] == "error"
    assert failure["provider"] in ("openai_compatible", "unknown")
    assert failure["model"] == "unknown"  # Never attribute a failed call to the requested model.
    assert failure["input_tokens"] == failure["output_tokens"] == 0
    assert failure["cost_usd"] is None
    assert isinstance(failure["latency_ms"], (int, float)) and failure["latency_ms"] >= 0
    assert failure["error_category"] and "sk-dummy-secret" not in failure["error_category"]
    assert "sk-dummy-secret" not in repr(failure)


@pytest.mark.parametrize("status", [200, 503])
def test_api_middleware_logs_only_safe_metadata_and_ignores_untrusted_org(status, caplog):
    # Mount the production middleware on a tiny app, avoiding server lifespan,
    # scheduler, DB initialization, and every external HTTP transport.
    from server import request_metadata_log

    app = FastAPI()
    app.middleware("http")(request_metadata_log)

    @app.post("/probe/{item_id}")
    async def probe(item_id: int):
        if status == 503:
            raise HTTPException(status_code=503, detail="safe failure")
        return {"ok": True}

    token = "dummy-token-DO-NOT-LOG"
    password = "dummy-password-DO-NOT-LOG"
    body_secret = "dummy-body-DO-NOT-LOG"
    with caplog.at_level(logging.INFO, logger="autoforce.api"):
        response = TestClient(app).post(
            "/probe/42", params={"password": password, "organization": "spoofed-query-org"},
            headers={"Authorization": f"Bearer {token}", "X-Organization-ID": "spoofed-header-org"},
            json={"password": body_secret, "access_token": token},
        )
    assert response.status_code == status
    request_id = response.headers["X-Request-ID"]
    UUID(request_id)
    records = [r for r in caplog.records if r.name == "autoforce.api"]
    assert len(records) == 1
    payload = json.loads(records[0].getMessage())
    assert set(payload) == {"request_id", "route", "status", "latency_ms", "organization"}
    assert payload["request_id"] == request_id
    assert payload["route"] == "/probe/{item_id}"
    assert payload["status"] == status
    assert isinstance(payload["latency_ms"], (float, int)) and payload["latency_ms"] >= 0
    assert payload["organization"] is None  # Never trust caller-provided org hints.
    text = "\n".join(r.getMessage() for r in records)
    for sensitive in (token, password, body_secret, "spoofed-query-org", "spoofed-header-org", "access_token"):
        assert sensitive not in text


def test_api_middleware_logs_verified_organization_from_auth_dependency_only(caplog):
    """Simulate a trusted auth dependency resolving a live user, not a caller hint."""
    from server import request_metadata_log

    app = FastAPI()
    app.middleware("http")(request_metadata_log)

    def verified_auth(request: Request):
        request.state.organization_id = 123
        return 123

    @app.get("/verified/{item_id}")
    def verified(item_id: int, organization_id: int = Depends(verified_auth)):
        return {"organization_id": organization_id}

    with caplog.at_level(logging.INFO, logger="autoforce.api"):
        response = TestClient(app).get(
            "/verified/7?organization=spoofed-query-org&password=dummy-password-DO-NOT-LOG",
            headers={"X-Organization-ID": "spoofed-header-org", "Authorization": "Bearer dummy-token-DO-NOT-LOG"},
        )
    assert response.status_code == 200
    record, = [r for r in caplog.records if r.name == "autoforce.api"]
    payload = json.loads(record.getMessage())
    assert payload["organization"] == 123
    assert payload["route"] == "/verified/{item_id}"
    assert payload["request_id"] == response.headers["X-Request-ID"]
    assert set(payload) == {"request_id", "route", "status", "latency_ms", "organization"}
    for sensitive in ("spoofed-query-org", "spoofed-header-org", "dummy-token-DO-NOT-LOG", "dummy-password-DO-NOT-LOG"):
        assert sensitive not in record.getMessage()

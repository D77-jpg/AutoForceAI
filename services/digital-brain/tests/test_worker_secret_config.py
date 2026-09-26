"""Worker signing keys are supplied privately, never baked into production."""

import pytest

from fastapi import HTTPException
from core.config import AppSettings


def test_dev_has_no_hardcoded_worker_secret(monkeypatch):
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    monkeypatch.delenv("NODE_ENV", raising=False)
    monkeypatch.delenv("DIGITAL_BRAIN_ENV", raising=False)
    monkeypatch.delenv("WORKER_SECRET", raising=False)
    assert AppSettings().worker_secret == ""


def test_production_fails_without_strong_worker_secret(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("WORKER_SECRET", "")
    with pytest.raises(RuntimeError, match="WORKER_SECRET"):
        AppSettings()
    monkeypatch.setenv("WORKER_SECRET", "weak-secret")
    with pytest.raises(RuntimeError, match="WORKER_SECRET"):
        AppSettings()
    monkeypatch.setenv("WORKER_SECRET", "long-private-key-not-committed-anywhere")
    assert AppSettings().worker_secret == "long-private-key-not-committed-anywhere"


def test_worker_endpoint_fails_closed_without_configured_secret(monkeypatch):
    import server

    monkeypatch.setattr(server.settings, "worker_secret", "")
    for candidate in (None, "", "arbitrary"):
        with pytest.raises(HTTPException) as exc:
            server.require_worker_key(candidate)
        assert exc.value.status_code == 401
    monkeypatch.setattr(server.settings, "worker_secret", "strong-private-worker-key-for-unit-tests")
    with pytest.raises(HTTPException):
        server.require_worker_key(None)
    with pytest.raises(HTTPException):
        server.require_worker_key("wrong")
    server.require_worker_key("strong-private-worker-key-for-unit-tests")

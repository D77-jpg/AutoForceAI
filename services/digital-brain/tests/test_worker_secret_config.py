"""Worker signing keys are supplied privately, never baked into production."""

import pytest

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

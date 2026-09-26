"""CORS is an explicit origin allowlist; production rejects local/private origins."""
import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core.security_cors import allowed_origins


def test_development_is_not_wildcard(monkeypatch):
    monkeypatch.delenv("CORS_ALLOWED_ORIGINS", raising=False)
    assert "*" not in allowed_origins(environment="development")
    assert allowed_origins(environment="development", configured="https://web.example.com") == ["https://web.example.com"]


@pytest.mark.parametrize("origin", ["", "*", "http://localhost:3000", "https://127.0.0.1",
                                    "https://192.168.1.2", "https://[::1]:444", "http://example.com",
                                    "https://example.com/path", "https://user:pass@example.com",
                                    "https://example.local", "https://example.com?x=y"])
def test_production_rejects_unsafe_origins(origin):
    with pytest.raises(ValueError):
        allowed_origins(environment="production", configured=origin)


def test_production_allows_only_explicit_public_https_origins():
    assert allowed_origins(environment="production", configured="https://console.example.com, https://console.example.com") == ["https://console.example.com"]

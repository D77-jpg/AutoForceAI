"""阶段 2.9 P0-3：URL allowlist、重定向校验与 SSRF 防护。

运行（services/digital-brain 目录）：
    venv/Scripts/python -m pytest tests/test_crm_url_guard.py -q
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import database.models  # noqa: E402,F401
from core.crm.client import CrmApiError, GenesisCRMClient  # noqa: E402
from core.crm.url_guard import (  # noqa: E402
    UrlGuardError,
    validate_crm_url,
    validate_redirect_location,
)

METADATA_IP = "169.254.169.254"  # 云元数据地址（链路本地）


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.delenv("CRM_ALLOWED_HOSTS", raising=False)


def _code(fn, url):
    with pytest.raises(UrlGuardError) as exc:
        fn(url)
    return exc.value.code


# ---------------------------------------------------------------- 基础校验

def test_scheme_rejected():
    assert _code(validate_crm_url, "file:///etc/passwd") == "URL_SCHEME"
    assert _code(validate_crm_url, "ftp://crm.example.com/api") == "URL_SCHEME"
    assert _code(validate_crm_url, "javascript:alert(1)") == "URL_SCHEME"


def test_userinfo_and_fragment_rejected():
    assert _code(validate_crm_url, "http://admin:secret@crm.example.com/api") == "URL_USERINFO"
    assert _code(validate_crm_url, "http://localhost:5000/api#frag") == "URL_INVALID"


def test_localhost_allowed_in_dev():
    assert validate_crm_url("http://localhost:5000/api") == "http://localhost:5000/api"
    assert validate_crm_url("http://127.0.0.1:5000/api") == "http://127.0.0.1:5000/api"
    assert validate_crm_url("http://[::1]:5000/api") == "http://[::1]:5000/api"


def test_metadata_and_private_ip_rejected():
    assert _code(validate_crm_url, f"http://{METADATA_IP}/latest/meta-data") == "URL_NOT_ALLOWED"
    assert _code(validate_crm_url, "http://10.0.0.5/api") == "URL_NOT_ALLOWED"
    assert _code(validate_crm_url, "http://192.168.1.10/api") == "URL_NOT_ALLOWED"
    assert _code(validate_crm_url, "http://172.16.0.1/api") == "URL_NOT_ALLOWED"


def test_allowlisted_private_host_allowed(monkeypatch):
    monkeypatch.setenv("CRM_ALLOWED_HOSTS", "10.0.0.5:5000,crm.internal")
    assert validate_crm_url("http://10.0.0.5:5000/api") == "http://10.0.0.5:5000/api"
    # 白名单条目未写端口 → 仅标准端口
    assert _code(validate_crm_url, "http://crm.internal:9000/api") == "URL_PORT"
    # 未列入白名单的私网仍拒绝
    assert _code(validate_crm_url, "http://10.0.0.6/api") == "URL_NOT_ALLOWED"


def test_production_requires_https_and_no_localhost(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("CRM_ALLOWED_HOSTS", "crm.example.com")
    assert validate_crm_url("https://crm.example.com/api") == "https://crm.example.com/api"
    assert _code(validate_crm_url, "http://crm.example.com/api") == "URL_SCHEME"
    assert _code(validate_crm_url, "http://localhost:5000/api") == "URL_SCHEME"
    assert _code(validate_crm_url, "https://localhost/api") == "URL_NOT_ALLOWED"


def test_dns_private_resolution_rejected(monkeypatch):
    """白名单域名被解析到元数据/回环地址（DNS 劫持形态）仍拒绝；私网解析需显式授权。"""
    import core.crm.url_guard as guard

    monkeypatch.setenv("CRM_ALLOWED_HOSTS", "trusted.example.com")
    monkeypatch.setattr(
        guard.socket, "getaddrinfo",
        lambda host, port: [(2, 1, 6, "", (METADATA_IP, 0))],
    )
    # 即使主机在白名单中，解析到链路本地/元数据地址也拒绝
    assert _code(validate_crm_url, "https://trusted.example.com/api") == "URL_PRIVATE_IP"

    # 解析到普通私网：显式白名单授权 → 放行（如内网试运行环境）
    monkeypatch.setattr(
        guard.socket, "getaddrinfo",
        lambda host, port: [(2, 1, 6, "", ("10.9.9.9", 0))],
    )
    assert validate_crm_url("https://trusted.example.com/api") == "https://trusted.example.com/api"

    # 未列入白名单的域名直接拒绝
    monkeypatch.delenv("CRM_ALLOWED_HOSTS", raising=False)
    assert _code(validate_crm_url, "https://evil.example.com/api") == "URL_NOT_ALLOWED"


def test_dns_failure_rejected(monkeypatch):
    monkeypatch.setenv("CRM_ALLOWED_HOSTS", "")  # 空 → 非 localhost 一律拒绝
    assert _code(validate_crm_url, "https://no-such-host.invalid/api") == "URL_NOT_ALLOWED"


# ---------------------------------------------------------------- 重定向

def test_redirect_to_metadata_rejected():
    code = _code(
        lambda u: validate_redirect_location("https://crm.example.com/api/x", u),
        f"http://{METADATA_IP}/latest/meta-data",
    )
    assert code in ("URL_NOT_ALLOWED", "URL_PRIVATE_IP", "URL_SCHEME")


def test_redirect_relative_and_allowed(monkeypatch):
    monkeypatch.setenv("CRM_ALLOWED_HOSTS", "crm.example.com")
    url = validate_redirect_location("https://crm.example.com/integrations/v1/health", "./status")
    assert url == "https://crm.example.com/integrations/v1/status"


def test_client_follows_safe_redirect_and_rejects_bad(monkeypatch):
    monkeypatch.setenv("CRM_ALLOWED_HOSTS", "crm.local")

    def make_resp(status, payload=None, location=None):
        resp = MagicMock()
        resp.status_code = status
        resp.headers = {"Location": location} if location else {}
        resp.iter_content.return_value = [json.dumps(payload or {}).encode()]
        return resp

    health_payload = {"success": True, "data": {
        "ok": True, "provider": "genesis_crm", "contractVersion": "1.0",
        "projectId": "p1", "projectName": "P", "credentialId": "c1",
        "scopes": ["customers:read"], "serverTime": "2026-09-23T00:00:00Z",
    }}

    # 合法重定向 → 跟随成功
    session = MagicMock()
    session.headers = {}
    session.request.side_effect = [
        make_resp(302, location="https://crm.local/api/integrations/v1/health"),
        make_resp(200, health_payload),
    ]
    client = GenesisCRMClient("http://crm.local/api", "gci_x", "p1", session=session)
    assert client.health().ok is True
    assert session.request.call_count == 2

    # 重定向到元数据地址 → 拒绝
    session2 = MagicMock()
    session2.headers = {}
    session2.request.side_effect = [make_resp(302, location=f"http://{METADATA_IP}/latest/meta-data")]
    client2 = GenesisCRMClient("http://crm.local/api", "gci_x", "p1", session=session2)
    with pytest.raises(CrmApiError) as exc:
        client2.health()
    assert not exc.value.retryable


def test_client_rejects_oversized_response(monkeypatch):
    monkeypatch.setenv("CRM_ALLOWED_HOSTS", "crm.local")
    session = MagicMock()
    session.headers = {}
    resp = MagicMock()
    resp.status_code = 200
    resp.headers = {}
    resp.iter_content.return_value = [b"x" * (2 * 1024 * 1024 + 10)]  # 超过 2MB
    session.request.return_value = resp
    client = GenesisCRMClient("http://crm.local/api", "gci_x", "p1", session=session)
    with pytest.raises(CrmApiError) as exc:
        client.health()
    assert "上限" in str(exc.value)


def test_client_constructor_blocks_disallowed_base_url():
    with pytest.raises(UrlGuardError):
        GenesisCRMClient(f"http://{METADATA_IP}/api", "gci_x", "p1")

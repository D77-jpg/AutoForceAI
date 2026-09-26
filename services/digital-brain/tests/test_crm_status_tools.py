"""H-09: bound, read-only Genesis status tools (all HTTP is mocked).

Run from services/digital-brain: venv/Scripts/python -m pytest tests/test_crm_status_tools.py -q
The tool's db/user_id are trusted server-side context; caller-controlled params are not.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from cryptography.fernet import Fernet

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import database.models  # noqa: E402,F401 - register shared model relationships
from core.db_manager import SHARED_ENGINE, SharedSessionLocal  # noqa: E402
from core.tools.registry import ToolRegistry  # noqa: E402
from database.base import Base  # noqa: E402
from database.shared_models import (  # noqa: E402
    CrmEntityLink, CrmIntegrationConfig, CrmStatusQueryAudit, Lead, Organization, User,
)
from core.tools.crm_status import CrmCustomerStatusTool, CrmQuotationStatusTool  # noqa: E402

PROJECT = "66cf2f1a9b2c4d5e6f708192"
OTHER_PROJECT = "66cf2f1a9b2c4d5e6f708193"
CUSTOMER = "66cf5000dd2c3d4e5f607183"
QUOTATION = "66cf5000dd2c3d4e5f607184"
SECRET = "gci_TEST_STATUS_TOOL_ONLY_not_a_real_token"
PRIVATE = "private.person@example.invalid"
NOW = datetime.now(timezone.utc).isoformat()


def _response(status, payload):
    response = MagicMock()
    response.status_code = status
    response.headers = {"X-Request-Id": "safe-request-id"}
    response.iter_content.return_value = [json.dumps(payload).encode()]
    return response


@pytest.fixture(autouse=True)
def http_guard(monkeypatch):
    """Never permit a real request, including unexpected paths or write methods."""
    monkeypatch.setenv("CRM_ALLOWED_HOSTS", "crm.local")
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("CRM_CREDENTIAL_ENCRYPTION_KEY", Fernet.generate_key().decode())
    calls = []
    responses = {
        "/health": {"ok": True, "contractVersion": "1.0", "serverTime": NOW,
                    "projectId": PROJECT, "projectName": "Bound project",
                    "scopes": ["customers:upsert", "quotations:read"], "credentialId": "credential-id"},
        "/customers/": {"customerId": CUSTOMER, "externalId": "lead:1",
                        "name": PRIVATE, "company": PRIVATE, "ownerName": PRIVATE,
                        "status": "quoting", "updatedAt": NOW},
        "/quotations": {"customerId": CUSTOMER, "items": [
            {"quotationId": QUOTATION, "quotationNo": "Q-2026-001", "status": "sent",
             "totalAmount": 123.45, "currency": "USD", "updatedAt": NOW}]},
    }

    def request(_session, method, url, **kwargs):
        calls.append((method, url, kwargs))
        assert _session.headers["X-Project-Id"] == PROJECT
        assert _session.headers["Authorization"] == f"Bearer {SECRET}"
        assert method == "GET", "status tools may not send write requests"
        assert url.startswith("http://crm.local/api/integrations/v1/")
        if url.endswith("/health"):
            body = responses["/health"]
        elif url.endswith("/quotations"):
            body = responses["/quotations"]
        elif "/customers/" in url:
            body = responses["/customers/"]
        else:
            pytest.fail(f"Unexpected CRM endpoint: {url}")
        return _response(200, {"success": True, "data": body})

    monkeypatch.setattr("requests.sessions.Session.request", request)
    return calls, responses


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
def bound(db):
    org = Organization(name="crm-status-bound")
    outsider = Organization(name="crm-status-outsider")
    db.add_all([org, outsider])
    db.flush()
    actor = User(username="crm_status_actor", organization_id=org.id, hashed_password="x")
    other = User(username="crm_status_other", organization_id=outsider.id, hashed_password="x")
    own_lead = Lead(organization_id=org.id, name=PRIVATE, email=PRIVATE)
    other_lead = Lead(organization_id=outsider.id, name="Other")
    db.add_all([actor, other, own_lead, other_lead])
    db.flush()
    cfg = CrmIntegrationConfig(organization_id=org.id, base_url="http://crm.local/api",
                               web_base_url="https://crm.example.invalid", project_id=PROJECT,
                               enabled=True, last_health_status="ok")
    cfg.set_service_token(SECRET)
    link = CrmEntityLink(organization_id=org.id, lead_id=own_lead.id,
                         provider="genesis_crm", project_id=PROJECT,
                         remote_customer_id=CUSTOMER)
    db.add_all([cfg, link])
    db.commit()
    return dict(db=db, org=org, actor=actor, outsider=outsider, other=other,
                lead=own_lead, other_lead=other_lead, cfg=cfg, link=link)


def _run(name, bound, **params):
    cls = {"get_crm_customer_status": CrmCustomerStatusTool,
           "get_crm_quotation_status": CrmQuotationStatusTool}[name]
    return json.loads(cls(db=bound["db"], user_id=bound["actor"].id).run(params))


def _code(result):
    assert isinstance(result.get("error"), dict), result
    code = result["error"].get("code")
    assert isinstance(code, str) and code and code == code.upper(), result
    return code


@pytest.mark.parametrize("name", ["get_crm_customer_status", "get_crm_quotation_status", "check_order_status"])
def test_registry_exposes_safely_scoped_tools(name):
    tool = ToolRegistry.get_tool(name)
    assert tool is not None
    schema = tool.schema
    assert schema["name"] == name
    props = schema["parameters"]["properties"]
    assert {"base_url", "url", "project_id", "token", "service_token", "organization_id"}.isdisjoint(props)
    if name != "check_order_status":
        assert "lead_id" in schema["parameters"]["required"]
        assert _code(json.loads(tool.run({"lead_id": 1}))) == "TOOL_CONTEXT_REQUIRED"


def test_customer_reads_only_bound_customer_and_redacts_pii(bound, http_guard):
    calls, _ = http_guard
    result = _run("get_crm_customer_status", bound, lead_id=bound["lead"].id)
    assert result["status"] == "quoting"
    assert result["updated_at"]
    assert result["genesis_url"].startswith("https://crm.example.invalid/")
    assert PRIVATE not in json.dumps(result)
    assert SECRET not in json.dumps(result)
    assert len(calls) >= 2
    assert all(method == "GET" and kw.get("json") is None for method, _, kw in calls)
    assert all("lead%3A" in url or url.endswith("/health") for _, url, _ in calls)


def test_customer_requires_contract_customer_scope(bound, http_guard):
    calls, responses = http_guard
    responses["/health"]["scopes"] = ["quotations:read"]
    first = _run("get_crm_customer_status", bound, lead_id=bound["lead"].id)
    assert _code(first) == _code(_run("get_crm_customer_status", bound, lead_id=bound["lead"].id))
    assert not any("/customers/" in url for _, url, _ in calls)


def test_quotation_is_authoritative_and_requires_read_scope(bound, http_guard):
    calls, responses = http_guard
    result = _run("get_crm_quotation_status", bound, lead_id=bound["lead"].id)
    assert isinstance(result["results"], list) and len(result["results"]) == 1
    quote = result["results"][0]
    assert quote["status"] == "sent"
    assert quote["number"] == "Q-2026-001"
    assert quote["amount"] == 123.45
    assert quote["currency"] == "USD"
    assert quote["updated_at"]
    assert quote["genesis_url"].startswith("https://crm.example.invalid/")
    assert PRIVATE not in json.dumps(result)
    assert any(url.endswith("/quotations") for _, url, _ in calls)
    calls.clear()
    responses["/health"]["scopes"] = ["customers:upsert", "quotations:draft"]
    denied = _run("get_crm_quotation_status", bound, lead_id=bound["lead"].id)
    assert _code(denied) == _code(_run("get_crm_quotation_status", bound, lead_id=bound["lead"].id))
    assert not any(url.endswith("/quotations") for _, url, _ in calls)


@pytest.mark.parametrize("name", ["get_crm_customer_status", "get_crm_quotation_status"])
@pytest.mark.parametrize("unsafe", [
    {"project_id": OTHER_PROJECT}, {"organization_id": 99999},
    {"base_url": "http://169.254.169.254/latest"}, {"token": SECRET},
    {"service_token": SECRET}, {"url": "https://evil.invalid"},
])
def test_rejects_caller_selected_project_org_url_and_credentials(bound, http_guard, name, unsafe):
    calls, _ = http_guard
    result = _run(name, bound, lead_id=bound["lead"].id, **unsafe)
    assert _code(result) == "INVALID_TOOL_ARGUMENTS"
    assert calls == []
    assert SECRET not in json.dumps(result)


@pytest.mark.parametrize("name", ["get_crm_customer_status", "get_crm_quotation_status"])
def test_other_tenant_and_missing_mapping_never_reach_crm(bound, http_guard, name):
    calls, _ = http_guard
    assert _code(_run(name, bound, lead_id=bound["other_lead"].id))
    assert not calls
    bound["link"].archived_at = datetime.now(timezone.utc).replace(tzinfo=None)
    bound["db"].commit()
    missing = _run(name, bound, lead_id=bound["lead"].id)
    assert _code(missing) == _code(_run(name, bound, lead_id=bound["lead"].id))
    assert calls == []
    bound["link"].archived_at = None
    bound["link"].project_id = OTHER_PROJECT
    bound["db"].commit()
    assert _code(_run(name, bound, lead_id=bound["lead"].id)) == _code(missing)
    assert calls == []


@pytest.mark.parametrize("name", ["get_crm_customer_status", "get_crm_quotation_status"])
def test_unconfigured_and_disabled_return_stable_errors_without_http(bound, http_guard, name):
    calls, _ = http_guard
    bound["db"].delete(bound["cfg"])
    bound["db"].commit()
    missing = _code(_run(name, bound, lead_id=bound["lead"].id))
    assert missing == _code(_run(name, bound, lead_id=bound["lead"].id))
    assert not calls
    cfg = CrmIntegrationConfig(organization_id=bound["org"].id, base_url="http://crm.local/api",
                               project_id=PROJECT, service_token=SECRET, enabled=False)
    bound["db"].add(cfg)
    bound["db"].commit()
    disabled = _code(_run(name, bound, lead_id=bound["lead"].id))
    assert disabled == _code(_run(name, bound, lead_id=bound["lead"].id))
    assert not calls


def test_invalid_credentials_and_scope_fail_without_leaking_secret(bound, http_guard, monkeypatch):
    calls, responses = http_guard
    def unauthorized(_session, method, url, **kwargs):
        calls.append((method, url, kwargs))
        return _response(401, {"success": False, "error": {
            "code": "UNAUTHORIZED", "message": "credential expired " + SECRET}})
    monkeypatch.setattr("requests.sessions.Session.request", unauthorized)
    result = _run("get_crm_customer_status", bound, lead_id=bound["lead"].id)
    credential_code = _code(result)
    assert credential_code == credential_code.upper()
    assert SECRET not in json.dumps(result)
    assert len(calls) >= 1
    bound["cfg"].enabled = True
    bound["cfg"].last_health_status = "ok"
    bound["db"].commit()
    # A missing quotations:read scope is not interchangeable with a 401 credential error.
    # Replace the mocked HTTP endpoint; never restore a real network transport.
    def insufficient(_session, method, url, **kwargs):
        calls.append((method, url, kwargs))
        data = dict(responses["/health"])
        data["scopes"] = ["quotations:draft"]
        return _response(200, {"success": True, "data": data})
    monkeypatch.setattr("requests.sessions.Session.request", insufficient)
    result2 = _run("get_crm_quotation_status", bound, lead_id=bound["lead"].id)
    assert _code(result2) != credential_code
    assert SECRET not in json.dumps(result2)


def test_quotation_id_must_belong_to_customer_list(bound, http_guard):
    calls, _ = http_guard
    result = _run("get_crm_quotation_status", bound, lead_id=bound["lead"].id,
                  quotation_id="another-customer-quote")
    assert _code(result)
    assert not any("another-customer-quote" in url for _, url, _ in calls)


def test_order_status_is_explicitly_unsupported_without_fake_data_or_http(http_guard):
    calls, _ = http_guard
    tool = ToolRegistry.get_tool("check_order_status")
    first = json.loads(tool.run({"order_id": "ORD-123"}))
    assert _code(first) == "ORDER_STATUS_NOT_SUPPORTED"
    assert first == json.loads(tool.run({"order_id": "ORD-456"}))
    assert "Shipped" not in json.dumps(first)
    assert calls == []


def test_query_audit_retains_codes_but_never_token_customer_pii_or_pdf(bound, http_guard):
    _run("get_crm_customer_status", bound, lead_id=bound["lead"].id)
    _run("get_crm_quotation_status", bound, lead_id=bound["lead"].id)
    rows = bound["db"].query(CrmStatusQueryAudit).all()
    assert len(rows) >= 2
    for row in rows:
        serialized = repr({col.name: getattr(row, col.name) for col in row.__table__.columns})
        assert SECRET not in serialized
        assert PRIVATE not in serialized
        assert "%PDF" not in serialized
    assert all(method == "GET" for method, _, _ in http_guard[0])

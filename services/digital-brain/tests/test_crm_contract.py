"""阶段 2 Wave A/B：Integration API v1 契约、字段映射与客户端测试。

运行（services/digital-brain 目录）：
    venv/Scripts/python -m pytest tests/test_crm_contract.py -q
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.crm import contract as c  # noqa: E402
from core.crm.client import CrmApiError, GenesisCRMClient  # noqa: E402
from core.crm.mapping import build_upsert_payload, lead_external_id  # noqa: E402
import database.models  # noqa: E402,F401  # User.projects 关系需要租户模型注册后才能建 mapper
from database.shared_models import Lead  # noqa: E402

GENESIS_REPO = Path(os.environ.get(
    "GENESIS_CRM_REPO",
    r"D:\Trade\genesis\CRM\Genesis_CRM",
))
OPENAPI_PATH = GENESIS_REPO / "docs" / "integration" / "integration-v1.openapi.yaml"


# ---------------------------------------------------------------- contract

def _load_openapi() -> dict:
    if not OPENAPI_PATH.exists():
        pytest.skip(f"Genesis 仓库契约文件不存在: {OPENAPI_PATH}")
    return yaml.safe_load(OPENAPI_PATH.read_text(encoding="utf-8"))


def test_openapi_freezes_required_endpoints():
    """Wave A 验收：首版必须冻结的端点都在契约里。"""
    spec = _load_openapi()
    paths = spec["paths"]
    for path in ("/health", "/customers/upsert", "/outcomes", "/stats/overview"):
        assert path in paths, f"契约缺少冻结端点 {path}"
    # 5.2 预留只读
    assert "/customers/{externalRef}" in paths
    assert "/customers/{externalRef}/quotations" in paths
    assert spec["info"]["version"].startswith("1.0")


def test_openapi_upsert_example_matches_pydantic_schema():
    """OpenAPI 示例载荷必须通过 AutoForceAI 侧 pydantic 契约校验。"""
    spec = _load_openapi()
    example = spec["paths"]["/customers/upsert"]["post"]["requestBody"]["content"]["application/json"]["example"]
    req = c.CustomerUpsertRequest.model_validate(example)
    assert req.schemaVersion == c.CONTRACT_VERSION
    assert req.sourceSystem == c.SOURCE_SYSTEM
    assert req.externalId.startswith("lead:")


def test_openapi_response_examples_match_pydantic_schemas():
    """OpenAPI 各 200/201 示例响应必须通过响应 schema 校验。"""
    spec = _load_openapi()

    health = spec["paths"]["/health"]["get"]["responses"]["200"]["content"]["application/json"]["example"]["data"]
    assert c.HealthResponse.model_validate(health).contractVersion == "1.0"

    upsert = spec["paths"]["/customers/upsert"]["post"]["responses"]
    for code in ("200", "201"):
        data = upsert[code]["content"]["application/json"]["example"]["data"]
        resp = c.CustomerUpsertResponse.model_validate(data)
        assert resp.action in ("created", "linked", "unchanged")

    outcomes = spec["paths"]["/outcomes"]["get"]["responses"]["200"]["content"]["application/json"]["example"]["data"]
    feed = c.OutcomeFeedResponse.model_validate(outcomes)
    assert feed.items and feed.items[0].toStatus in ("won", "lost")

    stats = spec["paths"]["/stats/overview"]["get"]["responses"]["200"]["content"]["application/json"]["example"]["data"]
    overview = c.StatsOverviewResponse.model_validate(stats)
    assert len(overview.funnel) == len(c.CUSTOMER_STATUSES)

    status = spec["paths"]["/customers/{externalRef}"]["get"]["responses"]["200"]["content"]["application/json"]["example"]["data"]
    assert c.CustomerStatusResponse.model_validate(status).status in c.CUSTOMER_STATUSES

    quotes = spec["paths"]["/customers/{externalRef}/quotations"]["get"]["responses"]["200"]["content"]["application/json"]["example"]["data"]
    assert c.CustomerQuotationsResponse.model_validate(quotes).items[0].status in c.QUOTATION_STATUSES


def test_customer_status_enum_matches_genesis():
    """八段状态必须与 Genesis constants.CUSTOMER_STATUS 完全一致（防撞库漂移）。"""
    assert c.CUSTOMER_STATUSES == (
        "pending", "contacted", "replied", "interested",
        "quoting", "negotiating", "won", "lost",
    )


# ---------------------------------------------------------------- mapping

def _lead(**overrides) -> Lead:
    base = dict(
        id=1024, organization_id=1, source="Website AI Chat", status="new",
        email="  Jane@Example.COM ", name="Jane", company="Sunrise Retail",
        country="Germany", phone="+49 30 123456", products="canvas tote bags",
        intent_json={
            "product_model": "GB-2026-A",
            "category": "Cotton Bags",
            "quantity": "5000 pcs",
            "target_price": "USD 1.20/pc",
            "moq": "1000 pcs",
            "summary": "客户关注环保棉布袋，Q4 备货。",
        },
        session_uuid="s-1", language="en",
    )
    base.update(overrides)
    return Lead(**base)


def test_lead_external_id_stable_and_not_email():
    assert lead_external_id(1024) == "lead:1024"


def test_mapping_full_fields():
    payload = build_upsert_payload(_lead())
    assert payload is not None
    assert payload.externalId == "lead:1024"
    assert payload.email == "jane@example.com"  # 规范化小写
    assert payload.initialStatus == "pending"
    assert payload.leadSource == "AutoForceAI / Website AI Chat"
    assert payload.productModel == "GB-2026-A"
    assert payload.expectedQuantity == "5000 pcs"  # 保留单位
    assert payload.targetPrice == "USD 1.20/pc"    # 保留币种
    assert payload.requirementNotes.startswith("客户关注")
    assert "autoforce" in payload.tags
    assert any(t.startswith("channel:") for t in payload.tags)


def test_mapping_status_rules():
    assert build_upsert_payload(_lead(status="contacted")).initialStatus == "contacted"
    # 本地 converted 只表示合格线索 → interested，绝不代表成交
    assert build_upsert_payload(_lead(status="converted")).initialStatus == "interested"
    # dropped 不自动推送
    assert build_upsert_payload(_lead(status="dropped")) is None


def test_mapping_missing_name_left_to_server_fallback():
    payload = build_upsert_payload(_lead(name=None, company=None))
    assert payload.name is None  # Genesis 端兜底「未命名询盘 <externalId>」


# ---------------------------------------------------------------- client

def _fake_response(status: int, payload: dict, headers: dict | None = None):
    import json as _json
    resp = MagicMock()
    resp.status_code = status
    resp.headers = headers or {}
    resp.json.return_value = payload
    # P0-3 后客户端改为限量流式读取
    resp.iter_content.return_value = [_json.dumps(payload).encode()]
    return resp


@pytest.fixture(autouse=True)
def _allowlist(monkeypatch):
    """P0-3：测试主机显式列入 allowlist（开发环境）。"""
    monkeypatch.setenv("CRM_ALLOWED_HOSTS", "crm.local")
    monkeypatch.setenv("APP_ENV", "development")


def _client_with(handler) -> GenesisCRMClient:
    session = MagicMock()
    session.headers = {}
    session.request.side_effect = handler
    return GenesisCRMClient(
        "http://crm.local/api", "gci_test_token", "66cf2f1a9b2c4d5e6f708192",
        session=session,
    )


HEALTH_OK = {
    "success": True,
    "data": {
        "ok": True,
        "contractVersion": "1.0",
        "serverTime": datetime.now(timezone.utc).isoformat(),
        "projectId": "66cf2f1a9b2c4d5e6f708192",
        "projectName": "项目 A",
        "scopes": ["customers:upsert", "outcomes:read", "stats:read"],
        "credentialId": "abc",
    },
}


def test_client_health_ok():
    client = _client_with(lambda *a, **k: _fake_response(200, HEALTH_OK, {"X-Request-Id": "r1"}))
    health = client.health()
    assert health.ok and health.contractVersion == "1.0"
    # 认证头与项目头必须随请求发出
    sent_headers = client._session.headers
    assert sent_headers["Authorization"] == "Bearer gci_test_token"
    assert sent_headers["X-Project-Id"] == "66cf2f1a9b2c4d5e6f708192"


def test_client_health_contract_mismatch():
    bad = {"success": True, "data": {**HEALTH_OK["data"], "contractVersion": "2.0"}}
    client = _client_with(lambda *a, **k: _fake_response(200, bad))
    with pytest.raises(CrmApiError) as exc:
        client.health()
    assert exc.value.code == "UNSUPPORTED_CONTRACT_VERSION"
    assert not exc.value.retryable


def test_client_401_marks_auth_invalid_not_retryable():
    body = {"success": False, "error": {"code": "UNAUTHORIZED", "message": "服务凭证无效或已失效"}}
    client = _client_with(lambda *a, **k: _fake_response(401, body))
    with pytest.raises(CrmApiError) as exc:
        client.health()
    assert exc.value.code == "UNAUTHORIZED"
    assert exc.value.auth_invalid
    assert not exc.value.retryable


def test_client_500_retryable_and_422_not():
    server_err = {"success": False, "error": {"code": "INTERNAL_ERROR", "message": "boom"}}
    client = _client_with(lambda *a, **k: _fake_response(500, server_err))
    with pytest.raises(CrmApiError) as exc:
        client.stats_overview()
    assert exc.value.retryable

    validation = {"success": False, "error": {"code": "VALIDATION_ERROR", "message": "数据校验未通过"}}
    client = _client_with(lambda *a, **k: _fake_response(422, validation))
    with pytest.raises(CrmApiError) as exc2:
        client.stats_overview()
    assert exc2.value.code == "VALIDATION_ERROR"
    assert not exc2.value.retryable


def test_client_upsert_sends_idempotency_key():
    captured: dict = {}

    def handler(method, url, **kwargs):
        captured.update(kwargs)
        return _fake_response(201, {
            "success": True,
            "data": {
                "action": "created",
                "customerId": "c1",
                "projectId": "66cf2f1a9b2c4d5e6f708192",
                "externalId": "lead:1024",
                "remoteUpdatedAt": datetime.now(timezone.utc).isoformat(),
            },
        })

    client = _client_with(handler)
    body = build_upsert_payload(_lead())
    resp = client.upsert_customer(body, idempotency_key="lead-1024-abcd1234")
    assert resp.action == "created"
    assert captured["headers"]["Idempotency-Key"] == "lead-1024-abcd1234"
    # 空字段不得发送（exclude_none），避免覆盖语义歧义
    sent = captured["json"]
    assert sent["phone"] == "+49 30 123456"
    assert "name" in sent and "requirementNotes" in sent


def test_client_network_error_retryable():
    import requests as rq

    session = MagicMock()
    session.headers = {}
    session.request.side_effect = rq.ConnectionError("refused")
    client = GenesisCRMClient("http://crm.local/api", "gci_x", "p1", session=session)
    with pytest.raises(CrmApiError) as exc:
        client.health()
    assert exc.value.retryable

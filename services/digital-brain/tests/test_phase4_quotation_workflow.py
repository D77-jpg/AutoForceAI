"""阶段 4.3：AutoForceAI 报价建议、确认门槛与 Genesis 客户端。"""
from __future__ import annotations

import json
import hashlib
import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import database.models  # noqa: E402,F401
from core.crm.client import GenesisCRMClient  # noqa: E402
from core.crm.contract import (  # noqa: E402
    ProposalSource,
    QuotationResponse,
)
from core.crm.quotation import (  # noqa: E402
    ConfirmQuotationRequest,
    GenerateQuotationProposalRequest,
    confirm_quotation,
    generate_quotation_proposal,
)
from core.db_manager import SHARED_ENGINE, SharedSessionLocal  # noqa: E402
from database.base import Base  # noqa: E402
from database.shared_models import (  # noqa: E402
    CrmEntityLink,
    CrmIntegrationConfig,
    Lead,
    Organization,
)


EXTENSION_CONTRACT_SHA256 = "c2b7921dfe076dd1748ca220a2435de26eabc05161264f01514c4a5def397e33"


def test_quotation_extension_contract_is_frozen_and_executable():
    contract_path = Path(__file__).resolve().parents[3] / "docs" / "integration" / "quotation-draft-v1.1.openapi.yaml"
    raw = contract_path.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == EXTENSION_CONTRACT_SHA256

    spec = yaml.safe_load(raw)
    assert spec["info"]["version"] == "1.1.0"
    assert spec["x-base-contract-version"] == "1.0"
    assert spec["x-capability"] == "quotation-draft.v1"
    assert set(spec["paths"]) == {
        "/customers/{externalRef}/quotation-drafts",
        "/quotations/{quotationId}",
        "/quotations/{quotationId}/pdf",
    }
    assert spec["paths"]["/customers/{externalRef}/quotation-drafts"]["post"]["security"] == [
        {"serviceToken": ["quotations:draft"]},
    ]
    assert spec["paths"]["/quotations/{quotationId}/pdf"]["get"]["security"] == [
        {"serviceToken": ["quotations:read"]},
    ]


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
def context(db):
    org = Organization(name="quotation-workflow-org")
    db.add(org)
    db.flush()
    lead = Lead(
        organization_id=org.id,
        name="Jane",
        company="Sunrise Retail",
        products="Recycled canvas bag",
        intent_json={
            "product_model": "RCB-01",
            "quantity": "500 pcs",
            "target_price": "USD 2.68/pc",
            "moq": "500 pcs",
            "summary": "客户需要再生帆布袋。",
        },
    )
    db.add(lead)
    db.flush()
    cfg = CrmIntegrationConfig(
        organization_id=org.id,
        base_url="http://crm.local/api",
        web_base_url="http://crm.local:5173",
        project_id="66cf2f1a9b2c4d5e6f708192",
        service_token="test-token",
        enabled=True,
        last_health_status="ok",
    )
    link = CrmEntityLink(
        organization_id=org.id,
        lead_id=lead.id,
        provider="genesis_crm",
        project_id=cfg.project_id,
        remote_customer_id="66cf5000dd2c3d4e5f607183",
    )
    db.add_all([cfg, link])
    db.commit()
    return org, lead, cfg, link


def test_proposal_uses_explicit_lead_numbers_and_never_writes_genesis(db, context, monkeypatch):
    org, lead, _cfg, _link = context
    monkeypatch.setattr("core.crm.quotation.query_default_llm", lambda *a, **k: "")
    proposal = generate_quotation_proposal(
        db, org.id,
        GenerateQuotationProposalRequest(leadId=lead.id, currency="USD"),
    )
    assert proposal.items[0].quantity == 500
    assert proposal.items[0].unitPrice == 2.68
    assert proposal.items[0].model == "RCB-01"
    assert proposal.missingFields == []
    assert proposal.sources[0].referenceId == f"lead:{lead.id}"
    assert proposal.proposalId.startswith("quote-proposal:")


def test_llm_invented_price_is_removed_when_sources_do_not_support_it(db, context, monkeypatch):
    org, lead, _cfg, _link = context
    lead.intent_json = {"summary": "客户询问帆布袋，但没有数量或价格。"}
    db.commit()
    monkeypatch.setattr(
        "core.crm.quotation.query_default_llm",
        lambda *a, **k: json.dumps({
            "title": "Canvas bag quotation",
            "items": [{"productName": "Canvas bag", "quantity": 1000, "unitPrice": 9.99}],
            "leadTime": "30 days",
            "paymentTerms": "100% payment before production",
            "notes": "Includes a certification not mentioned by the customer.",
        }),
    )
    proposal = generate_quotation_proposal(
        db, org.id,
        GenerateQuotationProposalRequest(leadId=lead.id, currency="USD"),
    )
    assert proposal.items[0].quantity is None
    assert proposal.items[0].unitPrice is None
    assert proposal.leadTime is None
    assert proposal.paymentTerms is None
    assert proposal.notes == "客户询问帆布袋，但没有数量或价格。"
    assert proposal.model == "environment-default"
    assert "items.0.quantity" in proposal.missingFields
    assert "items.0.unitPrice" in proposal.missingFields


class FakeQuotationClient:
    def __init__(self):
        self.keys = []
        self.requests = []

    def health(self):
        return type("Health", (), {"scopes": ["quotations:draft", "quotations:read"]})()

    def create_quotation_draft(self, external_ref, body, idempotency_key):
        self.keys.append(idempotency_key)
        self.requests.append((external_ref, body))
        now = datetime.now(timezone.utc)
        return QuotationResponse(
            quotationId="66cf5000dd2c3d4e5f607184",
            quotationNo="QT-20260924-001",
            customerId="66cf5000dd2c3d4e5f607183",
            externalRef=external_ref,
            title=body.title,
            items=[{
                "productName": body.items[0].productName,
                "model": body.items[0].model,
                "quantity": body.items[0].quantity,
                "unitPrice": body.items[0].unitPrice,
                "amount": 1340,
            }],
            currency=body.currency,
            totalAmount=1340,
            status="draft",
            version=1,
            proposalTrace=body.proposalTrace,
            createdAt=now,
            updatedAt=now,
        )


def _confirm_body(lead_id: int) -> ConfirmQuotationRequest:
    return ConfirmQuotationRequest.model_validate({
        "leadId": lead_id,
        "proposalId": "quote-proposal:test-001",
        "model": "rules-fallback",
        "sources": [{"kind": "lead", "referenceId": f"lead:{lead_id}"}],
        "confirmed": True,
        "quotation": {
            "title": "Recycled canvas bag quotation",
            "currency": "USD",
            "items": [{
                "productName": "Recycled canvas bag",
                "model": "RCB-01",
                "quantity": 500,
                "unitPrice": 2.68,
            }],
        },
    })


def test_confirm_is_explicit_idempotent_and_sends_no_authoritative_amount(db, context):
    org, lead, _cfg, _link = context
    client = FakeQuotationClient()
    first = confirm_quotation(db, org.id, _confirm_body(lead.id), client, "http://crm.local:5173")
    second = confirm_quotation(db, org.id, _confirm_body(lead.id), client, "http://crm.local:5173")
    assert client.keys[0] == client.keys[1]
    assert client.keys[0].startswith(f"quote-{lead.id}-")
    request = client.requests[0][1].model_dump(mode="json")
    assert "totalAmount" not in request
    assert "amount" not in request["items"][0]
    assert "status" not in request
    assert first.quotation.totalAmount == 1340
    assert first.pdfUrl.endswith("/66cf5000dd2c3d4e5f607184/pdf")
    assert first.genesisUrl.endswith("/customers/66cf5000dd2c3d4e5f607183")
    assert second.quotation.quotationId == first.quotation.quotationId


def test_confirm_rejects_forged_sources(db, context):
    org, lead, _cfg, _link = context
    body = _confirm_body(lead.id)
    body.sources = [ProposalSource(kind="lead", referenceId="lead:999999")]
    with pytest.raises(ValueError, match="建议来源无效"):
        confirm_quotation(db, org.id, body, FakeQuotationClient(), None)


def _fake_response(status: int, content: bytes, headers: dict | None = None):
    response = MagicMock()
    response.status_code = status
    response.headers = headers or {}
    response.iter_content.return_value = [content]
    return response


def test_client_creates_detail_and_downloads_versioned_pdf(monkeypatch):
    monkeypatch.setenv("CRM_ALLOWED_HOSTS", "crm.local")
    monkeypatch.setenv("APP_ENV", "development")
    now = datetime.now(timezone.utc).isoformat()
    quotation = {
        "quotationId": "66cf5000dd2c3d4e5f607184",
        "quotationNo": "QT-1",
        "customerId": "66cf5000dd2c3d4e5f607183",
        "externalRef": "lead:1",
        "title": "Quote",
        "items": [{"productName": "Bag", "quantity": 2, "unitPrice": 3, "amount": 6}],
        "currency": "USD",
        "totalAmount": 6,
        "status": "draft",
        "version": 1,
        "createdAt": now,
        "updatedAt": now,
    }
    session = MagicMock()
    session.headers = {}
    session.request.side_effect = [
        _fake_response(201, json.dumps({"success": True, "data": quotation}).encode()),
        _fake_response(200, json.dumps({"success": True, "data": quotation}).encode()),
        _fake_response(200, b"%PDF-1.3\nDRAFT", {
            "Content-Type": "application/pdf",
            "ETag": '"abc"',
            "X-Quotation-Version": "1",
            "Content-Disposition": 'attachment; filename="Quotation-QT-1.pdf"',
        }),
    ]
    client = GenesisCRMClient(
        "http://crm.local/api", "gci_test", "66cf2f1a9b2c4d5e6f708192", session=session,
    )
    body = _confirm_body(1).quotation
    from core.crm.contract import CreateQuotationDraftRequest, ProposalTrace
    request = CreateQuotationDraftRequest(
        title=body.title, items=body.items, currency=body.currency,
        proposalTrace=ProposalTrace(
            proposalId="quote-proposal:test", sources=[{"kind": "lead", "referenceId": "lead:1"}],
        ),
    )
    assert client.create_quotation_draft("lead:1", request, "quote-key-123").quotationNo == "QT-1"
    assert client.get_quotation(quotation["quotationId"]).version == 1
    pdf = client.download_quotation_pdf(quotation["quotationId"])
    assert pdf.content.startswith(b"%PDF-")
    assert pdf.etag == '"abc"'
    assert pdf.version == "1"

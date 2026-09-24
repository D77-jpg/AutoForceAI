"""阶段 4.3 报价扩展契约冻结测试（不依赖 Genesis 仓库或数据库）。"""
from __future__ import annotations

import hashlib
from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[3]
BASE_CONTRACT = REPO_ROOT / "docs" / "integration" / "integration-v1.openapi.yaml"
EXTENSION_CONTRACT = REPO_ROOT / "docs" / "integration" / "quotation-draft-v1.1.openapi.yaml"
BASE_CONTRACT_SHA256 = "7798eb621795e8dc405ff56c0fdfb806622ec5a6144d85d6e839ee85d9061679"
EXTENSION_CONTRACT_SHA256 = "c2b7921dfe076dd1748ca220a2435de26eabc05161264f01514c4a5def397e33"


def _load(path: Path) -> dict:
    assert path.exists(), f"契约文件缺失: {path}"
    spec = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(spec, dict) and spec.get("paths"), f"契约无法解析: {path}"
    return spec


def test_phase2_base_contract_remains_byte_frozen():
    """报价扩展不得顺手修改阶段 2 的 v1.0 基础契约。"""
    assert hashlib.sha256(BASE_CONTRACT.read_bytes()).hexdigest() == BASE_CONTRACT_SHA256


def test_phase4_extension_contract_is_byte_frozen():
    assert hashlib.sha256(EXTENSION_CONTRACT.read_bytes()).hexdigest() == EXTENSION_CONTRACT_SHA256


def test_extension_metadata_and_endpoints_are_frozen():
    spec = _load(EXTENSION_CONTRACT)
    assert str(spec["info"]["version"]) == "1.1.0"
    assert spec["x-base-contract-version"] == "1.0"
    assert spec["x-capability"] == "quotation-draft.v1"
    assert set(spec["paths"]) == {
        "/customers/{externalRef}/quotation-drafts",
        "/quotations/{quotationId}",
        "/quotations/{quotationId}/pdf",
    }


def test_write_endpoint_requires_project_scope_and_idempotency():
    spec = _load(EXTENSION_CONTRACT)
    operation = spec["paths"]["/customers/{externalRef}/quotation-drafts"]["post"]
    assert operation["security"] == [{"serviceToken": ["quotations:draft"]}]
    refs = {item["$ref"] for item in operation["parameters"]}
    assert "#/components/parameters/ProjectId" in refs
    assert "#/components/parameters/ExternalRef" in refs
    assert "#/components/parameters/IdempotencyKey" in refs
    assert {"200", "201", "409", "422"}.issubset(operation["responses"])


def test_create_request_cannot_supply_authoritative_fields():
    spec = _load(EXTENSION_CONTRACT)
    schemas = spec["components"]["schemas"]
    request = schemas["CreateQuotationDraftRequest"]
    item = schemas["CreateQuotationItem"]
    assert request["additionalProperties"] is False
    assert item["additionalProperties"] is False
    assert set(request["required"]) == {"schemaVersion", "sourceSystem", "title", "items", "currency"}
    assert {"quotationId", "quotationNo", "totalAmount", "status", "version"}.isdisjoint(request["properties"])
    assert "amount" not in item["properties"]

    quotation = schemas["Quotation"]
    quotation_item = schemas["QuotationItem"]
    assert {"quotationNo", "totalAmount", "status", "version"}.issubset(quotation["properties"])
    assert "amount" in quotation_item["properties"]


def test_pdf_is_binary_versioned_and_project_scoped():
    spec = _load(EXTENSION_CONTRACT)
    operation = spec["paths"]["/quotations/{quotationId}/pdf"]["get"]
    assert operation["security"] == [{"serviceToken": ["quotations:read"]}]
    refs = {item["$ref"] for item in operation["parameters"] if "$ref" in item}
    assert "#/components/parameters/ProjectId" in refs
    assert "#/components/parameters/QuotationId" in refs
    response = operation["responses"]["200"]
    assert response["content"]["application/pdf"]["schema"]["format"] == "binary"
    assert {"ETag", "Content-Disposition", "X-Quotation-Version", "X-Content-Type-Options"}.issubset(
        response["headers"]
    )

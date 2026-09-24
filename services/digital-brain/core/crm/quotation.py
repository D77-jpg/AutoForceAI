"""阶段 4.3：AI 报价建议与人工确认服务。

建议只存在于请求/响应中；只有 confirm 才写 Genesis。正式报价、金额和 PDF
始终以 Genesis 为权威，AutoForceAI 不建立第二套报价数据库。
"""
from __future__ import annotations

import hashlib
import json
import re
import uuid
from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, Field
from sqlalchemy import or_
from sqlalchemy.orm import Session

from core.crm.client import GenesisCRMClient
from core.crm.contract import (
    CONTRACT_VERSION,
    SOURCE_SYSTEM,
    CreateQuotationDraftRequest,
    CreateQuotationItem,
    ProposalSource,
    ProposalTrace,
    QuotationCurrency,
    QuotationResponse,
    SCOPE_QUOTATIONS_DRAFT,
    SCOPE_QUOTATIONS_READ,
)
from core.llm.runtime import get_default_llm_model, query_default_llm
from core.rag.retriever import KnowledgeRetriever
from database.shared_models import (
    CrmEntityLink,
    CrmIntegrationConfig,
    KnowledgeBase,
    KnowledgeDoc,
    Lead,
)


class QuotationProposalItem(BaseModel):
    productName: str = ""
    model: Optional[str] = None
    quantity: Optional[float] = None
    unitPrice: Optional[float] = None


class QuotationProposal(BaseModel):
    proposalId: str
    leadId: int
    externalRef: str
    customerName: Optional[str] = None
    company: Optional[str] = None
    title: str
    currency: QuotationCurrency
    items: List[QuotationProposalItem]
    validityDate: Optional[datetime] = None
    paymentTerms: Optional[str] = None
    leadTime: Optional[str] = None
    moq: Optional[str] = None
    notes: Optional[str] = None
    missingFields: List[str]
    warnings: List[str]
    sources: List[ProposalSource]
    model: str
    generatedAt: datetime


class GenerateQuotationProposalRequest(BaseModel):
    leadId: int = Field(gt=0)
    currency: QuotationCurrency
    instructions: Optional[str] = Field(default=None, max_length=1000)
    knowledgeBaseIds: List[int] = Field(default_factory=list, max_length=20)


class EditableQuotation(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    items: List[CreateQuotationItem] = Field(min_length=1, max_length=200)
    currency: QuotationCurrency
    validityDate: Optional[datetime] = None
    paymentTerms: Optional[str] = Field(default=None, max_length=300)
    leadTime: Optional[str] = Field(default=None, max_length=200)
    moq: Optional[str] = Field(default=None, max_length=120)
    notes: Optional[str] = Field(default=None, max_length=5000)


class ConfirmQuotationRequest(BaseModel):
    leadId: int = Field(gt=0)
    proposalId: str = Field(min_length=1, max_length=128)
    model: Optional[str] = Field(default=None, max_length=120)
    sources: List[ProposalSource] = Field(min_length=1, max_length=50)
    quotation: EditableQuotation
    confirmed: Literal[True]


class ConfirmQuotationResult(BaseModel):
    quotation: QuotationResponse
    pdfUrl: str
    genesisUrl: Optional[str] = None


def _require_context(db: Session, organization_id: int, lead_id: int, *, require_enabled: bool):
    lead = db.query(Lead).filter(
        Lead.id == lead_id,
        Lead.organization_id == organization_id,
    ).first()
    if not lead:
        raise ValueError("线索不存在或不属于当前企业")
    cfg = db.query(CrmIntegrationConfig).filter(
        CrmIntegrationConfig.organization_id == organization_id,
    ).first()
    if not cfg or not cfg.project_id or not cfg.service_token:
        raise ValueError("尚未完成 Genesis CRM 连接配置")
    if require_enabled and (not cfg.enabled or cfg.last_health_status != "ok"):
        raise ValueError("Genesis CRM 集成尚未启用或健康检查未通过")
    link = db.query(CrmEntityLink).filter(
        CrmEntityLink.provider == "genesis_crm",
        CrmEntityLink.organization_id == organization_id,
        CrmEntityLink.lead_id == lead_id,
        CrmEntityLink.project_id == cfg.project_id,
        CrmEntityLink.archived_at.is_(None),
    ).first()
    if not link:
        raise ValueError("该线索尚未同步到当前 Genesis 项目")
    return lead, cfg, link


def _number(value: object) -> Optional[float]:
    if value in (None, ""):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    match = re.search(r"(?<![A-Za-z])([0-9][0-9,]*(?:\.[0-9]+)?)", str(value))
    return float(match.group(1).replace(",", "")) if match else None


def _currency(value: object) -> Optional[str]:
    text = str(value or "").upper()
    for code in ("USD", "EUR", "GBP", "CNY", "JPY", "HKD", "AUD", "CAD", "CHF", "SGD", "AED", "NZD"):
        if re.search(rf"\b{code}\b", text):
            return code
    return None


def _clean_json(text: str) -> dict:
    value = (text or "").strip()
    value = re.sub(r"^```(?:json)?\s*|\s*```$", "", value, flags=re.I | re.S)
    start, end = value.find("{"), value.rfind("}")
    if start < 0 or end <= start:
        return {}
    try:
        parsed = json.loads(value[start:end + 1])
        return parsed if isinstance(parsed, dict) else {}
    except (TypeError, ValueError):
        return {}


def _supported_number(value: object, evidence: str) -> Optional[float]:
    number = _number(value)
    if number is None:
        return None
    variants = {str(number), f"{number:g}", f"{number:.2f}"}
    compact = evidence.replace(",", "")
    return number if any(v in compact for v in variants) else None


def _trim(value: object, limit: int) -> Optional[str]:
    text = str(value or "").strip()
    return text[:limit] if text else None


def _supported_text(value: object, evidence: str, limit: int) -> Optional[str]:
    """关键文本同样必须能在来源中逐字定位，避免模型补写交期、条款或产品。"""
    text = _trim(value, limit)
    if not text:
        return None
    return text if text.casefold() in evidence.casefold() else None


def _missing_fields(title: str, items: List[QuotationProposalItem], sources: List[ProposalSource]) -> List[str]:
    missing: List[str] = []
    if not title.strip():
        missing.append("title")
    if not items:
        missing.append("items")
    for index, item in enumerate(items):
        if not item.productName.strip():
            missing.append(f"items.{index}.productName")
        if item.quantity is None or item.quantity <= 0:
            missing.append(f"items.{index}.quantity")
        if item.unitPrice is None or item.unitPrice < 0:
            missing.append(f"items.{index}.unitPrice")
    if not sources:
        missing.append("sources")
    return missing


def generate_quotation_proposal(
    db: Session,
    organization_id: int,
    body: GenerateQuotationProposalRequest,
) -> QuotationProposal:
    lead, _cfg, _link = _require_context(db, organization_id, body.leadId, require_enabled=True)
    intent = lead.intent_json if isinstance(lead.intent_json, dict) else {}
    query = " ".join(str(value) for value in (
        lead.products, intent.get("summary"), intent.get("product_model"),
        intent.get("quantity"), intent.get("target_price"), body.instructions,
    ) if value)

    kb_query = db.query(KnowledgeBase).filter(or_(
        KnowledgeBase.organization_id == organization_id,
        KnowledgeBase.is_public.is_(True),
    ))
    if body.knowledgeBaseIds:
        kb_query = kb_query.filter(KnowledgeBase.id.in_(body.knowledgeBaseIds))
    kb_ids = [row.id for row in kb_query.all()]
    hits = KnowledgeRetriever(db).search_multi_kb(kb_ids, query, top_k=5, score_threshold=0.1) if query else []

    sources = [ProposalSource(
        kind="lead", referenceId=f"lead:{lead.id}",
        title=_trim(lead.company or lead.name or f"线索 #{lead.id}", 300),
    )]
    for hit in hits:
        sources.append(ProposalSource(
            kind="knowledge",
            referenceId=f"kb-doc:{hit['doc_id']}#chunk:{hit.get('chunk_id', hit.get('chunk_index', 0))}",
            title=_trim(hit.get("doc_name"), 300),
        ))

    lead_evidence = json.dumps(intent, ensure_ascii=False) + "\n" + (lead.conversation or "")
    knowledge_evidence = "\n\n".join(str(hit.get("content") or "")[:1200] for hit in hits)
    evidence = f"{lead_evidence}\n{knowledge_evidence}"
    prompt = f"""请基于给定证据生成 B2B 出口报价建议，只输出 JSON。不得猜测数量或单价；证据没有明确数值时必须为 null。
JSON 字段：title, items[productName,model,quantity,unitPrice], paymentTerms, leadTime, moq, notes, warnings。
用户选择币种：{body.currency}
补充要求：{body.instructions or '无'}
线索证据：{lead_evidence[:2500]}
知识库证据：{knowledge_evidence[:5000] or '无'}"""
    model = get_default_llm_model(db)
    model_name = model.name if model else "environment-default"
    llm_data: dict = {}
    warnings: List[str] = []
    try:
        llm_data = _clean_json(query_default_llm(
            db, prompt,
            system="你是外贸报价建议助手。关键商业数字只能来自提供的证据，禁止自行补全。",
            temperature=0.2, max_tokens=1800,
        ))
        if not llm_data:
            model_name = "rules-fallback"
    except Exception:
        model_name = "rules-fallback"
        warnings.append("AI 模型暂不可用，已使用线索中的明确字段生成基础草稿")

    explicit_quantity = _number(intent.get("quantity") or intent.get("expected_quantity"))
    explicit_price = _number(intent.get("target_price"))
    explicit_currency = _currency(intent.get("target_price"))
    raw_items = llm_data.get("items") if isinstance(llm_data.get("items"), list) else []
    if not raw_items:
        raw_items = [{
            "productName": lead.products or intent.get("product_name") or "",
            "model": intent.get("product_model"),
            "quantity": explicit_quantity,
            "unitPrice": explicit_price,
        }]
    items: List[QuotationProposalItem] = []
    for index, raw in enumerate(raw_items[:20]):
        if not isinstance(raw, dict):
            continue
        quantity = explicit_quantity if index == 0 and explicit_quantity is not None else _supported_number(raw.get("quantity"), evidence)
        unit_price = explicit_price if index == 0 and explicit_price is not None else _supported_number(raw.get("unitPrice"), knowledge_evidence)
        items.append(QuotationProposalItem(
            productName=(
                _trim(lead.products or intent.get("product_name"), 200)
                if index == 0
                else _supported_text(raw.get("productName"), evidence, 200)
            ) or _supported_text(raw.get("productName"), evidence, 200) or "",
            model=(
                _trim(intent.get("product_model"), 200)
                if index == 0
                else _supported_text(raw.get("model"), evidence, 200)
            ) or _supported_text(raw.get("model"), evidence, 200),
            quantity=quantity,
            unitPrice=unit_price,
        ))

    title = _trim(llm_data.get("title"), 200) or _trim(
        f"{lead.company or lead.name or '客户'} - {lead.products or '产品'} 报价", 200,
    ) or ""
    if explicit_currency and explicit_currency != body.currency:
        warnings.append(f"线索目标价币种为 {explicit_currency}，当前选择为 {body.currency}，请人工核对")
    for value in llm_data.get("warnings", []) if isinstance(llm_data.get("warnings"), list) else []:
        text = _trim(value, 300)
        if text:
            warnings.append(text)
    warnings.append("AI 建议不会自动写入 Genesis；请核对全部商业条款后再确认")

    proposal = QuotationProposal(
        proposalId=f"quote-proposal:{uuid.uuid4().hex}",
        leadId=lead.id,
        externalRef=f"lead:{lead.id}",
        customerName=lead.name,
        company=lead.company,
        title=title,
        currency=body.currency,
        items=items,
        paymentTerms=_trim(intent.get("payment_terms"), 300) or _supported_text(llm_data.get("paymentTerms"), evidence, 300),
        leadTime=_trim(intent.get("lead_time"), 200) or _supported_text(llm_data.get("leadTime"), evidence, 200),
        moq=_trim(intent.get("moq"), 120) or _supported_text(llm_data.get("moq"), evidence, 120),
        notes=_trim(intent.get("summary"), 5000) or _supported_text(llm_data.get("notes"), evidence, 5000),
        missingFields=[],
        warnings=warnings,
        sources=sources,
        model=model_name,
        generatedAt=datetime.now(),
    )
    proposal.missingFields = _missing_fields(proposal.title, proposal.items, proposal.sources)
    return proposal


def _validate_sources(db: Session, organization_id: int, lead: Lead, link: CrmEntityLink,
                      sources: List[ProposalSource]) -> List[ProposalSource]:
    valid: List[ProposalSource] = []
    for source in sources:
        if source.kind == "lead" and source.referenceId == f"lead:{lead.id}":
            valid.append(source)
        elif source.kind == "customer" and source.referenceId == link.remote_customer_id:
            valid.append(source)
        elif source.kind == "knowledge":
            match = re.fullmatch(r"kb-doc:(\d+)#chunk:(\d+)", source.referenceId)
            if not match:
                continue
            doc = db.query(KnowledgeDoc).join(KnowledgeBase).filter(
                KnowledgeDoc.id == int(match.group(1)),
                or_(KnowledgeBase.organization_id == organization_id, KnowledgeBase.is_public.is_(True)),
            ).first()
            if doc:
                valid.append(source)
    if not valid or not any(item.kind == "lead" for item in valid):
        raise ValueError("建议来源无效：至少需要当前线索来源")
    return valid


def confirm_quotation(
    db: Session,
    organization_id: int,
    body: ConfirmQuotationRequest,
    client: GenesisCRMClient,
    web_base_url: Optional[str],
) -> ConfirmQuotationResult:
    lead, _cfg, link = _require_context(db, organization_id, body.leadId, require_enabled=True)
    valid_sources = _validate_sources(db, organization_id, lead, link, body.sources)
    health = client.health()
    missing_scopes = {SCOPE_QUOTATIONS_DRAFT, SCOPE_QUOTATIONS_READ} - set(health.scopes)
    if missing_scopes:
        raise PermissionError(f"CRM 凭证缺少 scope: {', '.join(sorted(missing_scopes))}")

    trace = ProposalTrace(
        proposalId=body.proposalId,
        generatedBy="autoforce_ai",
        model=body.model,
        sources=valid_sources,
    )
    quotation = body.quotation
    request = CreateQuotationDraftRequest(
        schemaVersion=CONTRACT_VERSION,
        sourceSystem=SOURCE_SYSTEM,
        title=quotation.title,
        items=quotation.items,
        currency=quotation.currency,
        validityDate=quotation.validityDate,
        paymentTerms=quotation.paymentTerms,
        leadTime=quotation.leadTime,
        moq=quotation.moq,
        notes=quotation.notes,
        markCustomerAsQuoting=True,
        proposalTrace=trace,
    )
    canonical = json.dumps(request.model_dump(mode="json", exclude_none=True), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(f"{organization_id}:{lead.id}:{body.proposalId}:{canonical}".encode("utf-8")).hexdigest()
    idempotency_key = f"quote-{lead.id}-{digest[:40]}"
    remote = client.create_quotation_draft(f"lead:{lead.id}", request, idempotency_key)
    genesis_url = f"{web_base_url.rstrip('/')}/customers/{remote.customerId}" if web_base_url else None
    return ConfirmQuotationResult(
        quotation=remote,
        pdfUrl=f"/api/v1/crm/quotations/{remote.quotationId}/pdf",
        genesisUrl=genesis_url,
    )

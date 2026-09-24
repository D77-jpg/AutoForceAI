"""
Genesis Integration API v1 —— AutoForceAI 侧机器可校验契约（Pydantic schema）。

权威契约文档：Genesis_CRM 仓库 docs/integration/integration-v1.openapi.yaml。
本文件与其保持一致；v1 内只允许向后兼容地新增可选字段，
删除/改名/改变语义必须发布 v2 并同步 contract_version。
"""
from __future__ import annotations

from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, Field

CONTRACT_VERSION = "1.0"
SOURCE_SYSTEM = "autoforce"

# 服务凭证 scope（Genesis 侧签发，最少集合）
SCOPE_CUSTOMERS_UPSERT = "customers:upsert"
SCOPE_OUTCOMES_READ = "outcomes:read"
SCOPE_STATS_READ = "stats:read"
SCOPE_QUOTATIONS_READ = "quotations:read"
SCOPE_QUOTATIONS_DRAFT = "quotations:draft"
REQUIRED_SCOPES = {
    SCOPE_CUSTOMERS_UPSERT,
    SCOPE_OUTCOMES_READ,
    SCOPE_STATS_READ,
}

# 稳定错误码（两端共用，前端按 code 解释）
ERR_UNAUTHORIZED = "UNAUTHORIZED"            # token 缺失/无效/已撤销/过期
ERR_FORBIDDEN_SCOPE = "FORBIDDEN_SCOPE"      # 凭证缺少所需 scope
ERR_PROJECT_MISMATCH = "PROJECT_MISMATCH"    # 凭证未绑定该项目 / 跨项目访问
ERR_VALIDATION = "VALIDATION_ERROR"          # 请求字段不合法（4xx，不重试）
ERR_NOT_FOUND = "NOT_FOUND"
ERR_CONFLICT = "CONFLICT"                    # 幂等键冲突且载荷不同
ERR_RATE_LIMITED = "RATE_LIMITED"
ERR_INTERNAL = "INTERNAL_ERROR"
ERR_CONTRACT_VERSION = "UNSUPPORTED_CONTRACT_VERSION"


class ApiErrorBody(BaseModel):
    """统一错误响应体：{ "error": {...} }"""
    code: str
    message: str
    requestId: Optional[str] = None


class ApiErrorResponse(BaseModel):
    error: ApiErrorBody


# Genesis 客户八段状态（与 Genesis constants.CUSTOMER_STATUS 对齐）
CUSTOMER_STATUSES = (
    "pending", "contacted", "replied", "interested",
    "quoting", "negotiating", "won", "lost",
)
# Genesis 报价单状态（与 QUOTATION_STATUS 对齐）
QUOTATION_STATUSES = (
    "draft", "sent", "negotiating", "accepted", "rejected", "expired",
)


# ---------- health ----------

class HealthResponse(BaseModel):
    ok: bool
    contractVersion: str
    serverTime: datetime
    projectId: str
    projectName: Optional[str] = None
    scopes: List[str]
    credentialId: Optional[str] = None
    capabilities: List[str] = Field(default_factory=list)


# ---------- customers/upsert ----------

# 初始状态映射（§7）：new->pending, contacted->contacted, converted->interested
InitialStatus = Literal["pending", "contacted", "interested"]

LEAD_STATUS_TO_INITIAL = {
    "new": "pending",
    "contacted": "contacted",
    "converted": "interested",
    # dropped：不自动推送
}


class CustomerUpsertRequest(BaseModel):
    schemaVersion: str = CONTRACT_VERSION
    sourceSystem: str = SOURCE_SYSTEM
    externalId: str                                  # 稳定主键 "lead:<id>"，禁止用邮箱
    initialStatus: Optional[InitialStatus] = None    # 默认 pending

    name: Optional[str] = None                       # 缺失时 Genesis 端兜底
    company: Optional[str] = None
    email: Optional[str] = None                      # 规范化小写，仅辅助判重
    phone: Optional[str] = None
    country: Optional[str] = None
    interestedProducts: Optional[str] = None         # 逗号分隔的自由文本（≤500 字）
    leadSource: Optional[str] = None                 # "AutoForceAI / <channel>"

    productModel: Optional[str] = None
    productCategory: Optional[str] = None
    expectedQuantity: Optional[str] = None           # 保留单位，如 "500 pcs"
    targetPrice: Optional[str] = None                # 保留币种，如 "USD 12.5/pc"
    moq: Optional[str] = None

    requirementNotes: Optional[str] = Field(default=None, max_length=5000)
    tags: Optional[List[str]] = None                 # ["autoforce", "channel:<slug>"]


class CustomerUpsertResponse(BaseModel):
    action: Literal["created", "linked", "unchanged"]
    customerId: str
    projectId: str
    externalId: str
    remoteUpdatedAt: datetime


# ---------- outcomes（游标式增量事件） ----------

class OutcomeEvent(BaseModel):
    eventId: str                                     # 消费方按此幂等
    cursor: str                                      # opaque，提交后下次从此继续
    customerId: str
    externalId: Optional[str] = None                 # 可能无外部引用（CRM 原生客户）
    fromStatus: Optional[str] = None
    toStatus: str
    occurredAt: datetime


class OutcomeFeedResponse(BaseModel):
    items: List[OutcomeEvent]
    nextCursor: Optional[str] = None
    hasMore: bool = False


# ---------- stats/overview ----------

class FunnelStage(BaseModel):
    status: str
    count: int


class QuotationStatusCount(BaseModel):
    status: str
    count: int


class StatsOverviewResponse(BaseModel):
    projectId: str
    totalCustomers: int
    funnel: List[FunnelStage]
    wonCount: int = 0
    lostCount: int = 0
    quotations: List[QuotationStatusCount] = []
    generatedAt: datetime


# ---------- 阶段 5.2 预留只读 ----------

class CustomerStatusResponse(BaseModel):
    customerId: str
    externalId: Optional[str] = None
    name: Optional[str] = None
    company: Optional[str] = None
    status: str
    ownerName: Optional[str] = None
    lastFollowUpAt: Optional[datetime] = None
    updatedAt: datetime


class QuotationSummary(BaseModel):
    quotationId: str
    quotationNo: Optional[str] = None
    status: str
    totalAmount: Optional[float] = None
    currency: Optional[str] = None
    updatedAt: datetime


class CustomerQuotationsResponse(BaseModel):
    customerId: str
    items: List[QuotationSummary]


# ---------- quotation-draft.v1 ----------

QuotationCurrency = Literal[
    "USD", "EUR", "GBP", "CNY", "JPY", "HKD",
    "AUD", "CAD", "CHF", "SGD", "AED", "NZD",
]
QuotationStatus = Literal["draft", "sent", "negotiating", "accepted", "rejected", "expired"]
ProposalSourceKind = Literal["lead", "knowledge", "customer", "quotation"]


class ProposalSource(BaseModel):
    kind: ProposalSourceKind
    referenceId: str = Field(min_length=1, max_length=200)
    title: Optional[str] = Field(default=None, max_length=300)


class ProposalTrace(BaseModel):
    proposalId: str = Field(min_length=1, max_length=128)
    generatedBy: Literal["autoforce_ai"] = "autoforce_ai"
    model: Optional[str] = Field(default=None, max_length=120)
    sources: List[ProposalSource] = Field(min_length=1, max_length=50)


class CreateQuotationItem(BaseModel):
    productName: str = Field(min_length=1, max_length=200)
    model: Optional[str] = Field(default=None, max_length=200)
    quantity: float = Field(gt=0, le=1_000_000_000)
    unitPrice: float = Field(ge=0, le=1_000_000_000)


class CreateQuotationDraftRequest(BaseModel):
    schemaVersion: Literal["1.0"] = CONTRACT_VERSION
    sourceSystem: Literal["autoforce"] = SOURCE_SYSTEM
    title: str = Field(min_length=1, max_length=200)
    items: List[CreateQuotationItem] = Field(min_length=1, max_length=200)
    currency: QuotationCurrency
    validityDate: Optional[datetime] = None
    paymentTerms: Optional[str] = Field(default=None, max_length=300)
    leadTime: Optional[str] = Field(default=None, max_length=200)
    moq: Optional[str] = Field(default=None, max_length=120)
    notes: Optional[str] = Field(default=None, max_length=5000)
    markCustomerAsQuoting: bool = False
    proposalTrace: ProposalTrace


class QuotationItem(BaseModel):
    productName: str
    model: Optional[str] = None
    quantity: float
    unitPrice: float
    amount: float


class QuotationResponse(BaseModel):
    quotationId: str
    quotationNo: str
    customerId: str
    externalRef: str
    title: str
    items: List[QuotationItem]
    currency: QuotationCurrency
    totalAmount: float
    validityDate: Optional[datetime] = None
    paymentTerms: Optional[str] = None
    leadTime: Optional[str] = None
    moq: Optional[str] = None
    notes: Optional[str] = None
    status: QuotationStatus
    version: int = Field(ge=1)
    proposalTrace: Optional[ProposalTrace] = None
    createdAt: datetime
    updatedAt: datetime

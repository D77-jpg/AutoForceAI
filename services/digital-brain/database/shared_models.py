from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float, Text, ForeignKey, JSON, Enum as SAEnum, Index
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from pgvector.sqlalchemy import Vector
from database.base import Base

SharedBase = Base

class UserRole(str, enum.Enum):
    ADMIN = "admin" # System Admin
    ENTERPRISE_ADMIN = "enterprise_admin" # Organization Admin
    USER = "user" # Regular Enterprise User

class Organization(SharedBase):
    """企业组织表"""
    __tablename__ = "organizations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    description = Column(String, nullable=True)
    invite_code = Column(String, unique=True, index=True, nullable=True) # Unique invite code
    created_at = Column(DateTime, default=datetime.now)
    
    users = relationship("User", back_populates="organization")
    
    # Forward reference to Project if needed, but usually we just keep it loose
    # projects = relationship("database.models.Project", back_populates="organization")

class User(SharedBase):
    """SaaS 租户/用户表 - 存储在主数据库"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    
    # Back-reference for Single DB Architecture
    # Logic: Importing 'database.models' here might cause circular imports, 
    # so we use string path.
    projects = relationship("database.models.Project", back_populates="owner")
    username = Column(String, unique=True, index=True) # 系统唯一标识 (可能包含随机后缀)
    nickname = Column(String, nullable=True) # 微信昵称 / 显示名称 (用于界面展示)
    avatar = Column(String, nullable=True) # 微信头像 URL
    email = Column(String, unique=True, index=True, nullable=True)
    hashed_password = Column(String, nullable=True) # 微信登录可能不需要密码
    
    # WeChat Fields
    wechat_openid = Column(String, unique=True, index=True, nullable=True)
    wechat_unionid = Column(String, unique=True, index=True, nullable=True)

    # Profile Fields
    phone = Column(String, nullable=True)
    bio = Column(Text, nullable=True)
    
    # RBAC & Organization
    role = Column(String, default=UserRole.USER.value) # admin, enterprise_admin, user
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=True)
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)
    
    organization = relationship("Organization", back_populates="users")

class LLMRequestLog(SharedBase):
    """(新增) LLM 调用日志表 - 用于成本审计与可观测性"""
    __tablename__ = "llm_request_logs"

    id = Column(Integer, primary_key=True, index=True)
    trace_id = Column(String, index=True, nullable=True) # 链路追踪 ID
    user_id = Column(Integer, index=True, nullable=True) # 调用者
    
    provider = Column(String) # openai, qwen, zhipu
    model = Column(String)    # gpt-4, qwen-max
    
    input_tokens = Column(Integer, default=0)
    output_tokens = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    
    latency_ms = Column(Integer, default=0) # 耗时
    status = Column(String, default="success") # success, error
    error_msg = Column(Text, nullable=True)  # legacy field; never write raw exceptions
    error_category = Column(String(64), nullable=True)
    cost_usd = Column(Float, nullable=True)  # None means no verified price; never fabricate zero

    created_at = Column(DateTime, default=datetime.now)

class KnowledgeBase(SharedBase):
    """知识库 (Knowledge Base) - 存储 RAG 知识集合"""
    __tablename__ = "knowledge_bases"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=True) # 归属组织
    name = Column(String, index=True)
    description = Column(String, nullable=True)
    avatar = Column(String, nullable=True) # 知识库图标
    is_public = Column(Boolean, default=False) # Enable for Global Search (Reference)
    created_at = Column(DateTime, default=datetime.now)
    
    # Relationships
    documents = relationship("KnowledgeDoc", back_populates="knowledge_base", cascade="all, delete-orphan")

class KnowledgeDoc(SharedBase):
    """知识库文档 - 原始文件记录"""
    __tablename__ = "knowledge_docs"

    id = Column(Integer, primary_key=True, index=True)
    kb_id = Column(Integer, ForeignKey("knowledge_bases.id"))
    
    filename = Column(String) # 原始文件名 "Product_Manual_v1.pdf"
    file_path = Column(String) # 存储路径/S3 Key
    file_type = Column(String) # pdf, docx, txt
    file_size = Column(Integer)
    
    status = Column(String, default="pending") # pending, parsing, embedded, failed
    error_msg = Column(Text, nullable=True)
    
    chunk_count = Column(Integer, default=0) # 切片数量
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    knowledge_base = relationship("KnowledgeBase", back_populates="documents")
    chunks = relationship("KnowledgeChunk", back_populates="document", cascade="all, delete-orphan")

class KnowledgeChunk(SharedBase):
    """
    文档切片与向量存储 (PGVector)
    存储 RAG 所需的文本块及其向量表示
    """
    __tablename__ = "knowledge_chunks"

    id = Column(Integer, primary_key=True, index=True)
    doc_id = Column(Integer, ForeignKey("knowledge_docs.id", ondelete="CASCADE"))
    
    chunk_text = Column(Text) # 切片原始内容
    chunk_index = Column(Integer) # 切片顺序
    
    # PGVector: Dimensions must match the embedding model (ZhipuAI = 1024, OpenAI V3 Small = 1536)
    # Changed to 1024 to support ZhipuAI as primary/fallback in China
    embedding = Column(Vector(1024)) 
    
    meta_info = Column(JSON, nullable=True) # 页码、位置信息等
    
    document = relationship("KnowledgeDoc", back_populates="chunks")

    __table_args__ = (
        Index(
            'idx_knowledge_chunks_embedding_hnsw',
            embedding, 
            postgresql_using='hnsw', 
            postgresql_with={'m': 16, 'ef_construction': 64}, 
            postgresql_ops={'embedding': 'vector_cosine_ops'}
        ),
    )

class Bot(SharedBase):
    """AI 客服机器人 (Customer Service Bot)"""
    __tablename__ = "bots"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"))
    
    name = Column(String, index=True)
    description = Column(String, nullable=True)
    avatar = Column(String, nullable=True)
    
    # Configuration
    system_prompt = Column(Text, default="你是一个专业的AI助手。")
    welcome_message = Column(String, default="你好！有什么我可以帮你的吗？")
    model_name = Column(String, default="qwen-turbo") # Default cost-effective model
    temperature = Column(Float, default=0.7)
    
    # Association
    kb_id = Column(Integer, ForeignKey("knowledge_bases.id"), nullable=True) # 关联知识库
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # Relationships
    knowledge_base = relationship("KnowledgeBase")


class LLMProvider(SharedBase):
    """LLM 提供商配置 (如 OpenAI, Azure, Zhipu)"""
    __tablename__ = "llm_providers"
    
    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=True) # 组织级配置，为空则为系统级
    name = Column(String, index=True) # e.g. "OpenAI", "ZhipuAI"
    base_url = Column(String, nullable=True)
    api_key = Column(String, nullable=True) # 简化处理，实际生产应加密
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)
    
    models = relationship("LLMModel", back_populates="provider", cascade="all, delete-orphan")

class LLMModel(SharedBase):
    """LLM 模型定义 (如 gpt-4, glm-4)"""
    __tablename__ = "llm_models"
    
    id = Column(Integer, primary_key=True, index=True)
    provider_id = Column(Integer, ForeignKey("llm_providers.id"), nullable=True) # Check: Made nullable as per previous context where provider might be hidden/optional
    name = Column(String, index=True, unique=True) # e.g. "gpt-4-turbo" (API Model ID) - Enforce Unique
    display_name = Column(String) # e.g. "GPT-4 Turbo"
    type = Column(String, default="LLM") # LLM, Embedding, Image
    context_window = Column(String, nullable=True) # "128k"
    is_active = Column(Boolean, default=True)
    
    # Capability Flags
    supports_geo = Column(Boolean, default=False) # 是否支持 GEO 联网搜索分析
    supports_chat = Column(Boolean, default=True)

    # New Fields
    api_key = Column(String, nullable=True)
    base_url = Column(String, nullable=True)
    is_default = Column(Boolean, default=False)
    is_kb_search_default = Column(Boolean, default=False)
    
    provider = relationship("LLMProvider", back_populates="models")


class RPAJobStatus(str, enum.Enum):
    QUEUED = "queued"
    CLAIMED = "claimed"
    SUCCESS = "success"
    FAILED = "failed"

# class RPAJob(SharedBase):
#     """RPA 任务队列表 (Moved from Tenant DB to Shared DB for Global Worker Access)"""
#     __tablename__ = "rpa_jobs"

#     id = Column(Integer, primary_key=True, index=True)
    
#     # Context (Loose Coupling)
#     user_id = Column(Integer, ForeignKey("users.id"), nullable=True) 
#     project_id = Column(Integer, nullable=True) # Loose FK to Tenant DB Project
#     asset_id = Column(Integer, nullable=True)   # Loose FK to Tenant DB Asset
    
#     job_type = Column(String, default="publish") # publish, monitor_scrape
#     platform = Column(String) # zhihu, wechat, reddit
    
#     # Payload
#     payload = Column(JSON) 
    
#     # Status
#     status = Column(String, default=RPAJobStatus.QUEUED.value)
#     worker_id = Column(String, nullable=True)
#     retry_count = Column(Integer, default=0)
    
#     result_log = Column(Text)
#     execution_logs = Column(JSON, default=list)
    
#     created_at = Column(DateTime, default=datetime.now)
#     updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

#     user = relationship("User") 


class RAGConfig(SharedBase):
    """全局 RAG 配置 & 敏感词过滤"""
    __tablename__ = "rag_configs"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=True) # 组织级，空则为系统默认
    
    # RAG Strategy
    top_k = Column(Integer, default=3)
    score_threshold = Column(Float, default=0.6)
    
    # Indexing Strategy
    chunk_size = Column(Integer, default=1000)
    chunk_overlap = Column(Integer, default=200)
    
    # Security
    sensitive_words = Column(Text, default="") # Comma separated
    
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now) 

class BrainSession(SharedBase):
    """Brain 聊天会话"""
    __tablename__ = "brain_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=True)
    
    title = Column(String, default="New Chat")
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    messages = relationship("BrainMessage", back_populates="session", cascade="all, delete-orphan")

class BrainMessage(SharedBase):
    """Brain 聊天记录"""
    __tablename__ = "brain_messages"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("brain_sessions.id"))
    
    role = Column(String) # user, assistant
    content = Column(Text)
    
    # Metadata for Assistant
    thought_process = Column(Text, nullable=True) # Chain of Thought
    citations = Column(JSON, nullable=True) # Source docs
    
    created_at = Column(DateTime, default=datetime.now)
    
    session = relationship("BrainSession", back_populates="messages")


class QualityRule(SharedBase):
    """
    质检规则表 (Quality Inspection Rules)
    定义 "AI 裁判" 评分时的 SOP 标准
    """
    __tablename__ = "quality_rules"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=True) 

    name = Column(String, index=True) # e.g. "SOP规范性", "情绪检测"
    description = Column(Text) # LLM Prompt Snippet: "检查客服是否使用了敬语..."
    weight = Column(Float, default=1.0) # 权重
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)

class InspectionRecord(SharedBase):
    """
    会话质检记录表 (Inspection Result)
    每条记录对应一次 "AI 判卷" 的结果
    """
    __tablename__ = "inspection_records"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("brain_sessions.id"))
    
    # Quantitative Score
    total_score = Column(Float) # 0-100
    
    # Qualitative Result
    status = Column(String) # Excellent, Pass, Warning, Critical
    
    # Details from LLM
    issues = Column(JSON, default=list) # [{rule_name: "SOP", deduction: 5, reason: "No upsell"}]
    suggestion = Column(Text, nullable=True) # "建议客服在..."
    
    model_used = Column(String, nullable=True) # actual response model, or 'unknown'
    model_provider = Column(String, nullable=True) # actual adapter provider, or 'unknown'
    model_request_id = Column(String, nullable=True) # response request identifier, if available
    created_at = Column(DateTime, default=datetime.now)
    
    session = relationship("BrainSession")


class Lead(SharedBase):
    """
    本地线索池（Outbox）。阶段 1 询盘先落此地，CRM 稳定后再由投递器消费。
    去重键：同一 organization 下 email 相同则更新而非新建。
    """
    __tablename__ = "leads"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=True, index=True)

    source = Column(String, default="Website AI Chat", index=True)
    status = Column(String, default="new", index=True)  # new / contacted / converted / dropped

    email = Column(String, nullable=True, index=True)
    name = Column(String, nullable=True)
    company = Column(String, nullable=True)
    country = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    products = Column(String, nullable=True)

    intent_json = Column(JSON, nullable=True)
    conversation = Column(Text, nullable=True)
    session_uuid = Column(String, nullable=True, index=True)
    language = Column(String, nullable=True)

    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class CrmIntegrationConfig(SharedBase):
    """
    CRM 集成连接配置（阶段 2 Wave B）。
    一个 organization 显式绑定一个 Genesis_CRM projectId，禁止默认项目回退。
    service_token 为服务端机密：任何 API 响应都不得返回明文，只返回脱敏预览。
    """
    __tablename__ = "crm_integration_configs"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), unique=True, index=True)

    provider = Column(String, default="genesis_crm")           # 固定 genesis_crm
    base_url = Column(String)                                  # e.g. http://localhost:5000/api
    web_base_url = Column(String, nullable=True)               # Genesis 前端地址（深链用），空则按 base_url 推导
    project_id = Column(String)                                # Genesis ObjectId，必填
    project_name = Column(String, nullable=True)               # 最近一次连接测试返回的显示名

    service_token = Column(String, nullable=True)              # enc:v1: 密文（旧记录可能为明文，读取时迁移）
    token_last4 = Column(String, nullable=True)                # 明文末 4 位，仅用于脱敏预览
    contract_version = Column(String, default="1.0")

    enabled = Column(Boolean, default=False)                   # 是否允许新任务投递
    last_health_status = Column(String, nullable=True)         # ok / error / auth_invalid / credential_error / unchecked
    last_health_detail = Column(Text, nullable=True)           # 脱敏的连接测试摘要
    last_health_checked_at = Column(DateTime, nullable=True)
    # 启用门槛（P0-5）：最近一次成功测试时的配置指纹（base_url|project_id|token密文|契约版本）
    health_fingerprint = Column(String, nullable=True)

    # outcome 轮询游标（org+project 粒度，opaque；与批处理同事务提交）
    outcome_cursor = Column(String, nullable=True)
    outcome_polled_at = Column(DateTime, nullable=True)

    # reset-binding 审计
    last_reset_at = Column(DateTime, nullable=True)
    last_reset_by = Column(Integer, nullable=True)             # 执行重置的管理员用户 ID

    # outcome poller 分布式租约（§3.6：多实例下同 org+project 只有一个推进 cursor）
    outcome_lease_owner = Column(String, nullable=True)
    outcome_lease_expires_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    organization = relationship("Organization")

    __table_args__ = (
        # 首版严格一对一：一个 Genesis project 不得同时绑定到多个 AutoForceAI organization。
        # NULL 代表 reset-binding 后待重绑，允许多条。
        Index(
            "uq_crm_config_provider_project",
            "provider", "project_id", unique=True,
            sqlite_where=project_id.isnot(None),
            postgresql_where=project_id.isnot(None),
        ),
    )

    @property
    def token_preview(self):
        """脱敏预览只来自单独保存的 token_last4，绝不通过解密密文生成。"""
        if not self.token_last4:
            return None
        return f"****{self.token_last4}"

    def set_service_token(self, plain: str) -> None:
        """写入 token：加密落库 + 单独保存 last4。"""
        from core.credentials import encrypt_secret
        self.service_token = encrypt_secret(plain)
        self.token_last4 = plain[-4:]

    def get_service_token(self) -> str | None:
        """
        读取 token 明文（仅服务端内部使用）。
        密文 → 解密；旧明文 → 返回明文（调用方负责迁移写回，见 migrate_token_if_legacy）。
        失败抛 core.credentials.CredentialError。
        """
        from core.credentials import resolve_secret
        plain, _needs_migration = resolve_secret(self.service_token)
        return plain

    def migrate_token_if_legacy(self) -> bool:
        """旧明文 → 密文的一次性迁移（调用方负责 commit）。返回是否发生了迁移。"""
        from core.credentials import encrypt_secret, is_encrypted
        if not self.service_token or is_encrypted(self.service_token):
            return False
        plain = self.service_token
        # 先在局部变量完成所有可失败工作；只有加密成功后才一次性更新 ORM 状态。
        # 即使调用方捕获 CredentialError 后又 commit health 状态，
        # 也不会把原明文 token 误提交为 NULL。
        encrypted = encrypt_secret(plain)
        self.service_token = encrypted
        self.token_last4 = plain[-4:]
        return True


class CrmSyncJob(SharedBase):
    """
    CRM 同步 Outbox（阶段 2 Wave C）。
    线索写入与 job 创建在同一数据库事务完成；投递器用租约抢占避免多进程重复消费。
    重试必须复用原 idempotency_key（Genesis 侧据此幂等重放）。
    """
    __tablename__ = "crm_sync_jobs"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), index=True)
    lead_id = Column(Integer, ForeignKey("leads.id"), index=True)
    project_id = Column(String, nullable=True, index=True)     # 入队时绑定的 Genesis 项目（reset 后旧 job 不得投新项目）

    event_type = Column(String, default="lead.upsert")           # 首版只有 lead.upsert
    idempotency_key = Column(String, unique=True, index=True)    # lead-<id>-<payload_hash[:16]>
    payload_version = Column(String, default="1.0")
    payload_json = Column(JSON)                                  # CustomerUpsertRequest dump
    payload_hash = Column(String)                                # sha256(规范化载荷)

    # pending / leased / retrying / succeeded / dead / cancelled
    status = Column(String, default="pending", index=True)
    attempt_count = Column(Integer, default=0)
    next_attempt_at = Column(DateTime, default=datetime.now, index=True)

    lease_owner = Column(String, nullable=True)                  #  worker 标识
    lease_expires_at = Column(DateTime, nullable=True)

    last_error_code = Column(String, nullable=True)              # 稳定错误码（VALIDATION_ERROR 等）
    last_error_summary = Column(Text, nullable=True)             # 脱敏错误摘要
    last_http_status = Column(Integer, nullable=True)

    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    succeeded_at = Column(DateTime, nullable=True)
    dead_at = Column(DateTime, nullable=True)

    lead = relationship("Lead")


class CrmEntityLink(SharedBase):
    """
    外部实体映射（阶段 2 Wave C）。
    AutoForceAI lead ↔ Genesis customer 的稳定引用；两端只读引用，不靠姓名/邮箱猜测。
    outcome 轮询游标存于 crm_integration_configs（org+project 粒度）。
    reset-binding 时旧项目映射标记 archived_at（不物理删除，保留审计）。
    """
    __tablename__ = "crm_entity_links"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), index=True)
    lead_id = Column(Integer, ForeignKey("leads.id"), index=True)

    provider = Column(String, default="genesis_crm")
    project_id = Column(String)                                  # Genesis projectId
    remote_customer_id = Column(String)                          # Genesis customerId

    remote_status = Column(String, nullable=True)                # Genesis 八段状态快照
    remote_updated_at = Column(DateTime, nullable=True)
    synced_at = Column(DateTime, nullable=True)
    archived_at = Column(DateTime, nullable=True)                # 重置绑定后归档

    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    lead = relationship("Lead")

    __table_args__ = (
        # 一个线索在同一（提供商+项目）下只关联一个远端客户；重置绑定后可绑新项目
        Index("uq_crm_link_org_lead_project", "provider", "organization_id", "lead_id", "project_id", unique=True),
        Index("uq_crm_link_remote", "provider", "project_id", "remote_customer_id", unique=True),
    )


class CrmStatusQueryAudit(SharedBase):
    """Minimal read-only CRM tool audit; never store token or remote customer data."""
    __tablename__ = "crm_status_query_audits"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=True)
    lead_id = Column(Integer, nullable=True)
    tool_name = Column(String, nullable=False)
    outcome_code = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.now, nullable=False)


class Alert(SharedBase):
    """Organization-scoped, deduplicated worker incident (no raw exception payload)."""
    __tablename__ = "alerts"
    __table_args__ = (Index("uq_alert_fingerprint", "fingerprint", unique=True),)

    id = Column(Integer, primary_key=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    source = Column(String(40), nullable=False)
    category = Column(String(80), nullable=False)
    fingerprint = Column(String(64), nullable=False)
    severity = Column(String(16), nullable=False, default="warning")
    status = Column(String(16), nullable=False, default="open")
    summary = Column(String(180), nullable=False)
    occurrences = Column(Integer, nullable=False, default=1)
    event_type = Column(String(16), nullable=False, default="first")
    first_seen_at = Column(DateTime, nullable=False, default=datetime.now)
    last_seen_at = Column(DateTime, nullable=False, default=datetime.now)
    acknowledged_at = Column(DateTime, nullable=True)
    resolved_at = Column(DateTime, nullable=True)


class CrmWorkerState(SharedBase):
    """
    CRM 后台 worker 全局健康状态（阶段 2.9 §3.6，单行表 id=1）。
    供 /crm 门户与运维观察：worker 开关、dispatcher/poller 心跳、最近错误。
    """
    __tablename__ = "crm_worker_state"

    id = Column(Integer, primary_key=True)
    dispatcher_worker_id = Column(String, nullable=True)
    dispatcher_last_success_at = Column(DateTime, nullable=True)
    poller_worker_id = Column(String, nullable=True)
    poller_last_success_at = Column(DateTime, nullable=True)
    last_error = Column(Text, nullable=True)                   # 脱敏错误摘要
    last_error_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class CrmOutcomeEvent(SharedBase):
    """
    已消费的成交/流失事件流水（阶段 2 Wave D）。
    按 (provider, organization_id, event_id) 幂等：重复事件直接跳过，不重复归因。
    """
    __tablename__ = "crm_outcome_events"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), index=True)
    provider = Column(String, default="genesis_crm")

    event_id = Column(String)                                  # Genesis CustomerEvent id
    remote_customer_id = Column(String)
    external_id = Column(String, nullable=True)                # lead:<id>；CRM 原生客户为 None
    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=True)

    from_status = Column(String, nullable=True)
    to_status = Column(String)                                 # won / lost
    occurred_at = Column(DateTime)
    processed_at = Column(DateTime, default=datetime.now)

    lead = relationship("Lead")

    __table_args__ = (
        Index("uq_crm_outcome_event", "provider", "organization_id", "event_id", unique=True),
    )




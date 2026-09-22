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
    error_msg = Column(Text, nullable=True)
    
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
    
    model_used = Column(String, nullable=True) # e.g. "gpt-4"
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


from sqlalchemy import create_engine, Column, Integer, String, Float, Text, JSON, DateTime, ForeignKey, Boolean, Enum
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
from core.config import settings
import enum
from database.base import Base

# 数据库连接配置已移至 core.config
SQLALCHEMY_DATABASE_URL = settings.database.url

# 处理 SQLite 特有的 connect_args
connect_args = {}
if SQLALCHEMY_DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args=connect_args, echo=settings.database.echo
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base = declarative_base() # Moved to database.base

# --- Enums for status tracking ---

class TaskStatus(enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

class PlatformType(enum.Enum):
    WEBSITE = "website"
    WIKI = "wiki"
    SOCIAL_QA = "social_qa" # 知乎/Quora
    MEDIA = "media" # 公众号/百家号
    OTHER = "other"


class RPAJob(Base):
    """RPA 任务队列表 (Moved from Tenant DB to Shared DB for Global Worker Access)"""
    __tablename__ = "rpa_jobs"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    
    # Context (Loose Coupling)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True) 
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True) # Loose FK to Tenant DB Project
    asset_id = Column(Integer, ForeignKey("content_assets.id"), nullable=True)   # Loose FK to Tenant DB Asset
    
    job_type = Column(String, default="publish") # publish, monitor_scrape
    platform = Column(String) # zhihu, wechat, reddit
    
    # Payload
    payload = Column(JSON) 
    
    # Status
    # status = Column(String, default=RPAJobStatus.QUEUED.value) # Use Enum or String
    status = Column(String, default="queued")

    worker_id = Column(String, nullable=True)
    retry_count = Column(Integer, default=0)
    
    result_log = Column(Text)
    execution_logs = Column(JSON, default=list)
    
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    user = relationship("database.shared_models.User")
    project = relationship("database.models.Project", back_populates="rpa_jobs")
    asset = relationship("database.models.ContentAsset", back_populates="rpa_jobs")



# --- SaaS Core Tables ---

# [Merged to shared_models.py for Single DB Architecture]
# class User(Base):
#     """SaaS 租户/用户表"""
#     __tablename__ = "users"
#
#     id = Column(Integer, primary_key=True, index=True)
#     email = Column(String, unique=True, index=True, nullable=False)
#     hashed_password = Column(String, nullable=False)
#     is_active = Column(Boolean, default=True)
#     created_at = Column(DateTime, default=datetime.now)
#    
#     # Relationships
#     projects = relationship("Project", back_populates="owner")

class Project(Base):
    """项目/品牌工作区 (一个用户可以有多个品牌)"""
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    name = Column(String, index=True) # 品牌名称
    domain = Column(String) # 官网域名
    description = Column(Text) # 品牌描述 (用于生成上下文)
    competitors = Column(JSON) # 竞品列表 ["CompA", "CompB"]
    created_at = Column(DateTime, default=datetime.now)

    # Relationships
    # Refers to database.shared_models.User
    owner = relationship("database.shared_models.User", back_populates="projects")
    analysis_tasks = relationship("AnalysisTask", back_populates="project")
    content_assets = relationship("ContentAsset", back_populates="project")


    # rpa_jobs = relationship("RPAJob", back_populates="project")
    # rpa_jobs = relationship("RPAJob", back_populates="project")
    rpa_jobs = relationship("database.models.RPAJob", back_populates="project")



# --- Functionality Tables ---

class AnalysisTask(Base):
    """GEO 监测任务表 (原 AnalysisRecord 的升级版)"""
    __tablename__ = "analysis_tasks"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True) # 允许为空以便兼容旧数据或匿名任务
    
    # 任务参数
    target_brand = Column(String, index=True) # [Added back for Quick Scan compatibility]
    query = Column(String, index=True)
    engine_name = Column(String, default="auto") # Zhipu, Qwen, Perplexity
    
    # 任务状态
    status = Column(String, default=TaskStatus.PENDING.value)
    
    # 结果数据
    is_mentioned = Column(Boolean, default=False)
    rank_position = Column(Integer, default=-1)
    sentiment_score = Column(Float, default=0.0)
    reasoning = Column(Text) # AI 分析的理由
    citations = Column(JSON) # 引用来源
    suggestions = Column(JSON) # 优化建议
    raw_response = Column(Text) # 原始 AI 回答
    
    # 进度跟踪
    progress = Column(Integer, default=0)
    current_step = Column(String, default="")
    logs = Column(JSON, default=[])

    created_at = Column(DateTime, default=datetime.now)
    completed_at = Column(DateTime, nullable=True)

    project = relationship("Project", back_populates="analysis_tasks")


class GeoWatchQuery(Base):
    """Scheduled GEO keyword watch (English-first for overseas engines)."""
    __tablename__ = "geo_watch_queries"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    target_brand = Column(String, index=True, nullable=False)
    query = Column(String, nullable=False)
    engine_name = Column(String, default="perplexity")
    language = Column(String, default="en")
    interval_hours = Column(Integer, default=24)
    enabled = Column(Boolean, default=True)
    last_run_at = Column(DateTime, nullable=True)
    next_run_at = Column(DateTime, nullable=True)
    last_task_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.now)


class MarketingContent(Base):
    """Generated marketing copy / images for the acquisition engine."""
    __tablename__ = "marketing_contents"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    content_type = Column(String, index=True)  # product_article / linkedin_post / seo_blog / outreach_email / image
    product_name = Column(String, nullable=True)
    selling_points = Column(Text, nullable=True)
    language = Column(String, default="en")
    title = Column(String, nullable=True)
    body = Column(Text, nullable=True)
    tags = Column(JSON, default=list)
    image_url = Column(String, nullable=True)
    prompt = Column(Text, nullable=True)
    extra = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.now)


class ContentAsset(Base):
    """内容资产表 (Content Lab 生成的内容)"""
    __tablename__ = "content_assets"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)
    
    title = Column(String)
    content_body = Column(Text) # 优化后的内容 (HTML/Markdown)
    original_input = Column(Text)
    
    target_platform = Column(String) # wiki, social_qa, website
    meta_data = Column(JSON) # JSON-LD, InfoBox, etc.
    
    created_at = Column(DateTime, default=datetime.now)
    
    project = relationship("Project", back_populates="content_assets")


    # rpa_jobs = relationship("RPAJob", back_populates="asset")
    # rpa_jobs = relationship("RPAJob", back_populates="asset")
    rpa_jobs = relationship("database.models.RPAJob", back_populates="asset")

class Product(Base):
    """商品表 (E-commerce Product)"""
    __tablename__ = "ecommerce_products"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True) 
    
    spu_code = Column(String, index=True, nullable=True)
    sku_code = Column(String, index=True, unique=True)
    name = Column(String, index=True)
    description = Column(Text, nullable=True)
    
    price = Column(Float, default=0.0)
    stock_quantity = Column(Integer, default=0)
    
    attributes = Column(JSON, default={})
    images = Column(JSON, default=[])
    
    embedding_status = Column(String, default="pending") 
    status = Column(String, default="draft") 
    
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)




# 为了兼容旧代码，保留 AnalysisRecord 的别名，指向新的 AnalysisTask
AnalysisRecord = AnalysisTask 

# --- Digital Employee Subsystem ---

class AgentRole(enum.Enum):
    STRATEGIST = "strategist"  # Arthur
    EXECUTOR = "executor"      # Leo
    ARCHIVIST = "archivist"    # Doc
    CUSTOMER_SERVICE = "customer_service" # Sales/Support Bot

class DigitalEmployee(Base):
    __tablename__ = "digital_employees"
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"))
    name = Column(String)  # Arthur, Leo, Doc
    role = Column(Enum(AgentRole))
    description = Column(Text)
    avatar_url = Column(String)
    
    # Configuration
    model_name = Column(String, default="zhipu-glm-4") # e.g. "qwen-max", "gpt-4"
    kb_search_behavior = Column(String, default="fallback_to_llm") # "fallback_to_llm" | "refuse"
    system_prompt = Column(Text) # Custom persona prompt
    reasoning_config = Column(JSON, default={}) # CoT, Content Organization settings
    is_visible_on_landing = Column(Boolean, default=False)
    
    # Capabilities can be simple strings or detailed tool configs
    capabilities = Column(JSON) 
    
    # Relationships
    project = relationship("Project")
    skills = relationship("EmployeeSkill", back_populates="employee", cascade="all, delete-orphan")
    knowledge_bases = relationship("EmployeeKB", back_populates="employee", cascade="all, delete-orphan")
    chat_sessions = relationship("ChatSession", back_populates="employee", cascade="all, delete-orphan")

class EmployeeSkill(Base):
    """
    Specific tool configurations for a digital employee.
    e.g. tool_name='web_search', config={'api_key': '...'}
    """
    __tablename__ = "employee_skills"
    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("digital_employees.id"))
    
    tool_name = Column(String) 
    config = Column(JSON, default={})
    
    employee = relationship("DigitalEmployee", back_populates="skills")

class EmployeeKB(Base):
    """
    Knowledge Base binding for RAG.
    """
    __tablename__ = "employee_kbs"
    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("digital_employees.id"))
    kb_id = Column(String) # ID of the vector store collection
    description = Column(String)

    employee = relationship("DigitalEmployee", back_populates="knowledge_bases")

class MissionStatus(enum.Enum):
    PLANNING = "planning"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"

class Mission(Base):
    """
    User-defined Business Goal (e.g., 'Launch Q3 Campaign')
    that is assigned to a Digital Employee.
    """
    __tablename__ = "missions"
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"))
    assigned_to = Column(Integer, ForeignKey("digital_employees.id"))
    
    title = Column(String)
    objective = Column(Text) # The high-level natural language goal
    
    status = Column(Enum(MissionStatus), default=MissionStatus.PLANNING)
    
    # AI Analysis of the goal
    plan_summary = Column(Text)
    
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    tasks = relationship("MissionTask", back_populates="mission", cascade="all, delete-orphan")
    employee = relationship("DigitalEmployee")

class MissionTask(Base):
    """
    Decomposed sub-tasks for a Mission.
    Executed by tools or other agents.
    """
    __tablename__ = "mission_tasks"
    id = Column(Integer, primary_key=True, index=True)
    mission_id = Column(Integer, ForeignKey("missions.id"))
    
    title = Column(String)
    description = Column(Text)
    task_type = Column(String) # research, generate_content, rpa_action
    
    status = Column(Enum(TaskStatus), default=TaskStatus.PENDING)
    order_index = Column(Integer) # Execution order
    
    # Dependencies
    dependency_task_ids = Column(JSON) # List of IDs [1, 2]
    
    # Execution Output
    result_data = Column(JSON)
    error_log = Column(Text)
    
    mission = relationship("Mission", back_populates="tasks")

# --- Customer Service Chat Subsystem ---

class ChatSession(Base):
    """
    Session for AI Customer Service interactions.
    """
    __tablename__ = "chat_sessions"
    id = Column(Integer, primary_key=True, index=True)
    session_uuid = Column(String, unique=True, index=True) # UUID for frontend access
    
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)
    employee_id = Column(Integer, ForeignKey("digital_employees.id"), nullable=True)
    bot_id = Column(Integer, nullable=True, index=True)  # 关联 shared_models.Bot
    
    visitor_id = Column(String, nullable=True, index=True) # Anonymous unique ID
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True) # Registered User ID
    visitor_email = Column(String, nullable=True)
    visitor_name = Column(String, nullable=True)
    language = Column(String, nullable=True)
    
    status = Column(String, default="active") # active, closed, archived
    summary = Column(Text, nullable=True) # Conversation summary
    intent = Column(JSON, nullable=True)
    
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    employee = relationship("DigitalEmployee", back_populates="chat_sessions")
    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan")

class ChatMessage(Base):
    """
    Individual messages within a chat session.
    """
    __tablename__ = "chat_messages"
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("chat_sessions.id"))
    
    role = Column(String) # user, assistant, system
    content = Column(Text)
    
    # Optional metadata (tokens, references, etc.)
    meta_data = Column(JSON, default={})
    
    created_at = Column(DateTime, default=datetime.now)
    
    session = relationship("ChatSession", back_populates="messages")

# 创建所有表
def init_db():
    Base.metadata.create_all(bind=engine)


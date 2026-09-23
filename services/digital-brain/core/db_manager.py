import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database.models import Base as TenantBase
from database.shared_models import SharedBase
from core.config import settings

# 主数据库 (Shared DB)
SHARED_DB_URL = settings.database.url
connect_args = {"check_same_thread": False} if "sqlite" in SHARED_DB_URL else {}

SHARED_ENGINE = create_engine(
    SHARED_DB_URL, 
    connect_args=connect_args,
    pool_pre_ping=True, 
    pool_recycle=3600
)
SharedSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=SHARED_ENGINE)

def _sqlite_add_columns():
    """SQLite create_all 不会给已有表加列，这里补齐阶段 1 新增字段。"""
    if "sqlite" not in SHARED_DB_URL:
        return
    statements = [
        "ALTER TABLE chat_sessions ADD COLUMN bot_id INTEGER",
        "ALTER TABLE chat_sessions ADD COLUMN visitor_email VARCHAR",
        "ALTER TABLE chat_sessions ADD COLUMN visitor_name VARCHAR",
        "ALTER TABLE chat_sessions ADD COLUMN language VARCHAR",
        "ALTER TABLE chat_sessions ADD COLUMN intent JSON",
        "ALTER TABLE knowledge_docs ADD COLUMN error_msg TEXT",
        # 阶段 2 Wave D：outcome 轮询游标
        "ALTER TABLE crm_integration_configs ADD COLUMN outcome_cursor VARCHAR",
        "ALTER TABLE crm_integration_configs ADD COLUMN outcome_polled_at DATETIME",
        "ALTER TABLE crm_integration_configs ADD COLUMN web_base_url VARCHAR",
        # 阶段 2.9 P0-1：token 脱敏预览（与密文分离）
        "ALTER TABLE crm_integration_configs ADD COLUMN token_last4 VARCHAR",
        # 阶段 2.9 P0-2：绑定变更保护
        "ALTER TABLE crm_sync_jobs ADD COLUMN project_id VARCHAR",
        "ALTER TABLE crm_entity_links ADD COLUMN archived_at DATETIME",
        "ALTER TABLE crm_entity_links DROP COLUMN last_outcome_cursor",
        "ALTER TABLE crm_integration_configs ADD COLUMN last_reset_at DATETIME",
        "ALTER TABLE crm_integration_configs ADD COLUMN last_reset_by INTEGER",
        "DROP INDEX IF EXISTS uq_crm_link_org_lead",
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_crm_link_org_lead_project ON crm_entity_links (provider, organization_id, lead_id, project_id)",
    ]
    with SHARED_ENGINE.begin() as conn:
        for sql in statements:
            try:
                conn.exec_driver_sql(sql)
            except Exception:
                pass


# 初始化主数据库 (Merging Tenant Schemas into Shared DB)
def init_shared_db():
    print("[DB] Initializing Shared Database Schema...")
    SharedBase.metadata.create_all(bind=SHARED_ENGINE)
    # Also create Tenant tables in the Shared DB (Single DB Mode)
    TenantBase.metadata.create_all(bind=SHARED_ENGINE)
    _sqlite_add_columns()
    # 阶段 2.9 P0-4：对齐 alembic 版本（stamp / upgrade / 版本领先时报错）
    from core.migrations import ensure_schema_current
    ensure_schema_current(SHARED_ENGINE)
    print("[DB] Schema Sync Complete.")

# 租户数据库引擎缓存
_tenant_engines = {}

def get_tenant_db_path(user_id: int):
    # Deprecated in Single DB Mode, but kept for legacy reference
    # 确保租户目录存在
    os.makedirs("./tenants_data", exist_ok=True)
    return f"sqlite:///./tenants_data/user_{user_id}.db"

def get_tenant_engine(user_id: int):
    # Unified Architecture: All tenants use Shared Engine
    return SHARED_ENGINE

def get_tenant_session(user_id: int):
    # Unified Architecture: Return Shared Session
    return SharedSessionLocal()

def get_shared_db():
    db = SharedSessionLocal()
    try:
        yield db
    finally:
        db.close()

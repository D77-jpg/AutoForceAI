"""阶段 2.9 P0-4：Alembic migration 验证。

运行（services/digital-brain 目录）：
    venv/Scripts/python -m pytest tests/test_migrations.py -q

覆盖：
- 空库 upgrade head（SQLite）；
- 阶段 1 库（0001）升级到 head，数据保留；
- downgrade 路径（head → 0001 → base）；
- PostgreSQL 方言离线 SQL 生成（upgrade head --sql 等价路径）。
"""
from __future__ import annotations

import contextlib
import io
import os
import sys
import tempfile
from pathlib import Path

import pytest
from sqlalchemy import Column, Integer, Table, create_engine, inspect, text

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import database.models  # noqa: E402,F401

SERVICE_ROOT = Path(__file__).resolve().parents[1]
CRM_TABLES = {"crm_integration_configs", "crm_sync_jobs", "crm_entity_links", "crm_outcome_events", "crm_worker_state"}
HEAD = "0005_workforce_role_templates"
EXPECTED_PHASE1 = {
    "users", "organizations", "leads", "projects", "chat_sessions", "chat_messages",
    "knowledge_bases", "knowledge_docs", "knowledge_chunks",
}


def _cfg(url: str):
    from alembic.config import Config
    cfg = Config(str(SERVICE_ROOT / "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", url.replace("%", "%%"))
    return cfg


def test_windows_encoded_sqlite_url_survives_alembic_interpolation():
    """SQLAlchemy encodes Windows C: as C%3A; configparser must not reject it."""
    from alembic.config import Config

    # SQLAlchemy on Windows percent-encodes the drive colon; inject its exact
    # rendered form so this regression test also runs on Linux/macOS hosts.
    url = "sqlite:///C%3A/temp/phase2-gate.db"
    from core.migrations import ALEMBIC_INI
    cfg = Config(ALEMBIC_INI)
    cfg.set_main_option("sqlalchemy.url", url.replace("%", "%%"))
    assert cfg.get_main_option("sqlalchemy.url") == url
    # Alembic env.py resolves the URL and sets it again during every stamp/upgrade.
    cfg.set_main_option("sqlalchemy.url", cfg.get_main_option("sqlalchemy.url").replace("%", "%%"))
    assert cfg.get_main_option("sqlalchemy.url") == url


@pytest.fixture()
def db_url():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.unlink(path)  # alembic 自己创建
    yield "sqlite:///" + path.replace("\\", "/")
    if os.path.exists(path):
        os.unlink(path)


def _tables(url: str) -> set[str]:
    engine = create_engine(url)
    try:
        return set(inspect(engine).get_table_names())
    finally:
        engine.dispose()


def _current_rev(url: str):
    engine = create_engine(url)
    try:
        from alembic.migration import MigrationContext
        with engine.connect() as conn:
            return MigrationContext.configure(conn).get_current_revision()
    finally:
        engine.dispose()


def test_upgrade_head_from_empty(db_url):
    from alembic import command
    command.upgrade(_cfg(db_url), "head")

    names = _tables(db_url)
    assert CRM_TABLES <= names
    assert EXPECTED_PHASE1 <= names
    from database.base import Base
    assert names - {"alembic_version"} == set(Base.metadata.tables)  # 与元数据完全一致
    assert _current_rev(db_url) == HEAD

    # 关键列与约束存在
    engine = create_engine(db_url)
    insp = inspect(engine)
    cfg_cols = {c["name"] for c in insp.get_columns("crm_integration_configs")}
    assert {"token_last4", "outcome_cursor", "last_reset_at", "web_base_url", "health_fingerprint",
            "outcome_lease_owner", "outcome_lease_expires_at"} <= cfg_cols
    job_cols = {c["name"] for c in insp.get_columns("crm_sync_jobs")}
    assert {"project_id", "lease_owner", "idempotency_key"} <= job_cols
    link_indexes = {i["name"]: i for i in insp.get_indexes("crm_entity_links")}
    assert "uq_crm_link_org_lead_project" in link_indexes
    assert link_indexes["uq_crm_link_org_lead_project"]["unique"]
    assert [c for c in link_indexes["uq_crm_link_org_lead_project"]["column_names"]] == [
        "provider", "organization_id", "lead_id", "project_id",
    ]
    config_indexes = {i["name"]: i for i in insp.get_indexes("crm_integration_configs")}
    assert config_indexes["uq_crm_config_provider_project"]["unique"]
    assert config_indexes["uq_crm_config_provider_project"]["column_names"] == ["provider", "project_id"]
    engine.dispose()


def test_historical_revisions_ignore_future_orm_tables(db_url):
    """给运行时 ORM 临时加表，也不能改变已发布的 0001/0002 DDL。"""
    from alembic import command
    from database.base import Base

    probe = Table("future_orm_only", Base.metadata, Column("id", Integer, primary_key=True))
    try:
        command.upgrade(_cfg(db_url), "head")
        assert "future_orm_only" not in _tables(db_url)
    finally:
        Base.metadata.remove(probe)


def test_phase1_database_upgrades_to_phase2_preserving_data(db_url):
    """阶段 1 数据库（0001）→ head：既有数据保留，CRM 表补齐。"""
    from alembic import command
    cfg = _cfg(db_url)
    command.upgrade(cfg, "0001_phase1_baseline")
    assert _current_rev(db_url) == "0001_phase1_baseline"
    assert not (CRM_TABLES & _tables(db_url))

    engine = create_engine(db_url)
    with engine.begin() as conn:
        conn.execute(text("INSERT INTO organizations (name, created_at) VALUES ('legacy-org', '2026-09-01 00:00:00')"))
        conn.execute(text(
            "INSERT INTO leads (organization_id, email, name, status, source, created_at, updated_at)"
            " VALUES (1, 'legacy@x.com', 'Legacy', 'new', 'Website AI Chat', '2026-09-01 00:00:00', '2026-09-01 00:00:00')"
        ))
    engine.dispose()

    command.upgrade(cfg, "head")
    names = _tables(db_url)
    assert CRM_TABLES <= names
    assert _current_rev(db_url) == HEAD

    engine = create_engine(db_url)
    with engine.connect() as conn:
        row = conn.execute(text("SELECT email, status FROM leads")).one()
    assert row == ("legacy@x.com", "new")
    engine.dispose()


def test_downgrade_path(db_url):
    from alembic import command
    cfg = _cfg(db_url)
    command.upgrade(cfg, "head")
    command.downgrade(cfg, "0001_phase1_baseline")
    names = _tables(db_url)
    assert not (CRM_TABLES & names)          # CRM 表已回滚
    assert "leads" in names                  # 阶段 1 数据表保留
    assert _current_rev(db_url) == "0001_phase1_baseline"

    command.downgrade(cfg, "base")
    assert _tables(db_url) <= {"alembic_version"}
    assert _current_rev(db_url) is None


def test_postgresql_offline_sql_generation(db_url):
    """PostgreSQL 升级路径：离线模式生成 DDL（不连接任何数据库），验证方言可编译。"""
    from alembic import command
    cfg = _cfg("postgresql+psycopg://gate:gate@127.0.0.1:9/phase2_gate")
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        command.upgrade(cfg, "head", sql=True)
    sql = buf.getvalue()

    # 方言证明：必须是 PostgreSQL DDL，而不是 SQLite DDL
    assert " SERIAL " in sql or "\tSERIAL" in sql or "SERIAL NOT NULL" in sql  # PG 自增主键方言
    assert "AUTOINCREMENT" not in sql                        # SQLite 标记不得出现
    assert "TIMESTAMP WITHOUT TIME ZONE" in sql              # PG DateTime 方言
    assert " sqlite" not in sql.lower()

    # 关键对象
    assert "CREATE EXTENSION IF NOT EXISTS vector" in sql
    assert "VECTOR" in sql.upper()                           # knowledge_chunks.embedding
    assert "CREATE TYPE taskstatus" in sql                   # PG enum（幂等 DO 块内）
    assert "CREATE TYPE agentrole" in sql
    assert "CREATE TABLE crm_sync_jobs" in sql
    assert "CREATE TABLE crm_entity_links" in sql
    assert "CREATE TABLE crm_integration_configs" in sql
    assert "CREATE TABLE crm_outcome_events" in sql
    assert "CREATE TABLE crm_worker_state" in sql
    assert "ALTER TABLE crm_integration_configs ADD COLUMN outcome_lease_owner" in sql
    assert "uq_crm_link_org_lead_project" in sql             # CRM 实体链接唯一约束
    assert "uq_crm_config_provider_project" in sql           # 单一项目归属约束


def test_ensure_schema_current_stamps_existing_db(db_url):
    """无 alembic 版本的 SQLite 开发库：create_all 后 stamp head；幂等。"""
    from database.base import Base
    engine = create_engine(db_url)
    Base.metadata.create_all(bind=engine)
    engine.dispose()

    from core.migrations import ensure_schema_current
    engine = create_engine(db_url)
    try:
        ensure_schema_current(engine)
        ensure_schema_current(engine)  # 幂等
    finally:
        engine.dispose()
    assert _current_rev(db_url) == HEAD


def test_ensure_schema_current_upgrades_versioned_database(db_url):
    """已记录旧版本的数据库：启动检查使用 Alembic 公共 API 自动升级到 head。"""
    from alembic import command
    from core.migrations import ensure_schema_current

    cfg = _cfg(db_url)
    command.upgrade(cfg, "0001_phase1_baseline")
    assert _current_rev(db_url) == "0001_phase1_baseline"

    engine = create_engine(db_url)
    try:
        ensure_schema_current(engine)
    finally:
        engine.dispose()

    assert _current_rev(db_url) == HEAD
    assert CRM_TABLES <= _tables(db_url)


def test_init_shared_db_migrates_before_create_all(db_url, monkeypatch):
    """真实启动路径：版本化旧库必须先迁移，避免 create_all 预建未来列后重复 DDL。"""
    from alembic import command
    from core import db_manager

    command.upgrade(_cfg(db_url), "0001_phase1_baseline")
    engine = create_engine(db_url, connect_args={"check_same_thread": False})
    monkeypatch.setattr(db_manager, "SHARED_DB_URL", db_url)
    monkeypatch.setattr(db_manager, "SHARED_ENGINE", engine)
    try:
        db_manager.init_shared_db()
    finally:
        engine.dispose()

    assert _current_rev(db_url) == HEAD
    assert CRM_TABLES <= _tables(db_url)


def test_unversioned_postgresql_fails_before_schema_mutation(db_url):
    """生产方言无版本记录时必须人工迁移，启动过程不得静默 stamp。"""
    from core.migrations import ensure_schema_current

    engine = create_engine(db_url)
    engine.dialect.name = "postgresql"
    try:
        with pytest.raises(RuntimeError, match="拒绝自动 create_all/stamp"):
            ensure_schema_current(engine)
    finally:
        engine.dispose()
    assert _current_rev(db_url) is None

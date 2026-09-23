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
from sqlalchemy import create_engine, inspect, text

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import database.models  # noqa: E402,F401

SERVICE_ROOT = Path(__file__).resolve().parents[1]
CRM_TABLES = {"crm_integration_configs", "crm_sync_jobs", "crm_entity_links", "crm_outcome_events", "crm_worker_state"}
HEAD = "0003_phase29_worker"
EXPECTED_PHASE1 = {
    "users", "organizations", "leads", "projects", "chat_sessions", "chat_messages",
    "knowledge_bases", "knowledge_docs", "knowledge_chunks",
}


def _cfg(url: str):
    from alembic.config import Config
    cfg = Config(str(SERVICE_ROOT / "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", url)
    return cfg


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
    engine.dispose()


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
    """PostgreSQL 升级路径：离线模式生成 DDL（无需真实 PG 服务），验证方言可编译。"""
    from alembic import command
    cfg = _cfg("postgresql://autoforce:***@localhost:5432/autoforce")
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        command.upgrade(cfg, "head", sql=True)
    sql = buf.getvalue()
    assert "CREATE EXTENSION IF NOT EXISTS vector" in sql
    assert "CREATE TABLE crm_sync_jobs" in sql
    assert "CREATE TABLE crm_entity_links" in sql
    assert "CREATE TABLE crm_integration_configs" in sql
    assert "CREATE TABLE crm_outcome_events" in sql
    assert "CREATE TABLE crm_worker_state" in sql
    assert "ALTER TABLE crm_integration_configs ADD COLUMN outcome_lease_owner" in sql
    assert "VECTOR" in sql.upper()              # knowledge_chunks.embedding
    assert "uq_crm_link_org_lead_project" in sql


def test_ensure_schema_current_stamps_existing_db(db_url):
    """无 alembic 版本的历史库：create_all 后 stamp head；幂等。"""
    from database.base import Base
    engine = create_engine(db_url)
    Base.metadata.create_all(bind=engine)
    engine.dispose()

    from core.migrations import ensure_schema_current
    engine = create_engine(db_url)
    ensure_schema_current(engine)
    ensure_schema_current(engine)  # 幂等
    engine.dispose()
    assert _current_rev(db_url) == HEAD

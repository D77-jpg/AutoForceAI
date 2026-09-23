"""阶段 1 基线：阶段 2 之前的全部业务表（28 张，不含 CRM 集成表）。

Revision ID: 0001_phase1_baseline
Revises:
Create Date: 2026-09-23

说明：本迁移以共享 SQLAlchemy 元数据为事实来源，按表名集合创建；
对已存在这些表的历史库（阶段 1 由 create_all 建立）应使用
`alembic stamp 0001_phase1_baseline` 对齐，而不是执行 upgrade。
"""
from alembic import op

from migrations.helpers import PHASE2_TABLES, create_tables, drop_tables, maybe_create_pgvector_extension
from database.base import Base

revision = "0001_phase1_baseline"
down_revision = None
branch_labels = None
depends_on = None

_PHASE1 = {t.name for t in Base.metadata.sorted_tables} - set(PHASE2_TABLES)


def upgrade() -> None:
    maybe_create_pgvector_extension(op)
    create_tables(_PHASE1, op)


def downgrade() -> None:
    drop_tables(_PHASE1, op)

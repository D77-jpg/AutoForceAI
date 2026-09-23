"""阶段 1 基线：阶段 2 之前的全部业务表（28 张，不含 CRM 集成表）。

Revision ID: 0001_phase1_baseline
Revises:
Create Date: 2026-09-23

说明：本迁移使用创建时冻结的 DDL 快照，不导入运行时 ORM 元数据；
对已存在这些表的历史库（阶段 1 由 create_all 建立）应使用
`alembic stamp 0001_phase1_baseline` 对齐，而不是执行 upgrade。
"""
from alembic import op

from migrations.helpers import execute_frozen, maybe_create_pgvector_extension

revision = "0001_phase1_baseline"
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    maybe_create_pgvector_extension(op)
    execute_frozen("PHASE1", "UP", op)


def downgrade() -> None:
    execute_frozen("PHASE1", "DOWN", op)

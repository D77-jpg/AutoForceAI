"""Genesis project 与 AutoForceAI organization 一对一绑定。

Revision ID: 0004_phase2_project_ownership
Revises: 0003_phase29_worker
Create Date: 2026-09-23
"""
import sqlalchemy as sa
from alembic import op

revision = "0004_phase2_project_ownership"
down_revision = "0003_phase29_worker"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "uq_crm_config_provider_project",
        "crm_integration_configs",
        ["provider", "project_id"],
        unique=True,
        sqlite_where=sa.text("project_id IS NOT NULL"),
        postgresql_where=sa.text("project_id IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_crm_config_provider_project", table_name="crm_integration_configs")

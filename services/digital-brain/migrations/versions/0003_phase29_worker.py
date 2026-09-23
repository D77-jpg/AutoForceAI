"""阶段 2.9 worker 并发保护：worker_state 心跳 + outcome poller 租约 + migration 0003。

Revision ID: 0003_phase29_worker
Revises: 0002_phase2_crm
Create Date: 2026-09-23
"""
import sqlalchemy as sa
from alembic import op

revision = "0003_phase29_worker"
down_revision = "0002_phase2_crm"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("crm_integration_configs", sa.Column("outcome_lease_owner", sa.String(), nullable=True))
    op.add_column("crm_integration_configs", sa.Column("outcome_lease_expires_at", sa.DateTime(), nullable=True))
    op.create_table(
        "crm_worker_state",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("dispatcher_worker_id", sa.String(), nullable=True),
        sa.Column("dispatcher_last_success_at", sa.DateTime(), nullable=True),
        sa.Column("poller_worker_id", sa.String(), nullable=True),
        sa.Column("poller_last_success_at", sa.DateTime(), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("last_error_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("crm_worker_state")
    op.drop_column("crm_integration_configs", "outcome_lease_expires_at")
    op.drop_column("crm_integration_configs", "outcome_lease_owner")

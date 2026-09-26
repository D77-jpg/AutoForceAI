"""Minimal audit for H-09 read-only CRM status tool queries."""
import sqlalchemy as sa
from alembic import op

revision = "0007_crm_status_query_audit"
down_revision = "0006_inspector_model_attribution"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "crm_status_query_audits",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id"), nullable=True),
        sa.Column("lead_id", sa.Integer(), nullable=True),
        sa.Column("tool_name", sa.String(), nullable=False),
        sa.Column("outcome_code", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )


def downgrade():
    op.drop_table("crm_status_query_audits")

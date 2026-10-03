"""Persist owner- and organization-scoped presentation drafts."""
import sqlalchemy as sa
from alembic import op

revision = "0010_solution_drafts"
down_revision = "0009_llm_usage_fields"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "solution_drafts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("state", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_solution_drafts_user_id", "solution_drafts", ["user_id"])
    op.create_index("ix_solution_drafts_organization_id", "solution_drafts", ["organization_id"])


def downgrade():
    op.drop_index("ix_solution_drafts_organization_id", table_name="solution_drafts")
    op.drop_index("ix_solution_drafts_user_id", table_name="solution_drafts")
    op.drop_table("solution_drafts")

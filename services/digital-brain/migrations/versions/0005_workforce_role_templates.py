"""Persist independent, editable employee template snapshots and audit metadata."""
import sqlalchemy as sa
from alembic import op

revision = "0005_workforce_role_templates"
down_revision = "0004_phase2_project_ownership"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("digital_employees") as batch:
        batch.add_column(sa.Column("template_key", sa.String(), nullable=True))
        batch.add_column(sa.Column("template_version", sa.String(), nullable=True))
        batch.add_column(sa.Column("prompt_version", sa.String(), nullable=True))
        batch.add_column(sa.Column("allowed_tools", sa.JSON(), nullable=True))
        batch.add_column(sa.Column("data_scope", sa.JSON(), nullable=True))
        batch.add_column(sa.Column("max_steps", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("timeout_seconds", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("max_cost_usd", sa.Float(), nullable=True))
        batch.add_column(sa.Column("requires_human_approval_for_external_actions", sa.Boolean(), nullable=False, server_default=sa.true()))
        batch.add_column(sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id", name="fk_digital_employees_created_by_users"), nullable=True))
        batch.add_column(sa.Column("updated_by", sa.Integer(), sa.ForeignKey("users.id", name="fk_digital_employees_updated_by_users"), nullable=True))
        batch.add_column(sa.Column("created_at", sa.DateTime(), nullable=True))
        batch.add_column(sa.Column("updated_at", sa.DateTime(), nullable=True))


def downgrade():
    with op.batch_alter_table("digital_employees") as batch:
        for field in ("updated_at", "created_at", "updated_by", "created_by", "requires_human_approval_for_external_actions", "max_cost_usd", "timeout_seconds", "max_steps", "data_scope", "allowed_tools", "prompt_version", "template_version", "template_key"):
            batch.drop_column(field)

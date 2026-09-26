"""Persist actual inspection model provider and request ID (unknown on failure)."""
import sqlalchemy as sa
from alembic import op

revision = "0006_inspector_model_attribution"
down_revision = "0005_workforce_role_templates"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("inspection_records") as batch:
        batch.add_column(sa.Column("model_provider", sa.String(), nullable=True))
        batch.add_column(sa.Column("model_request_id", sa.String(), nullable=True))


def downgrade():
    with op.batch_alter_table("inspection_records") as batch:
        batch.drop_column("model_request_id")
        batch.drop_column("model_provider")

"""Store verified LLM cost when available and safe error categories."""
import sqlalchemy as sa
from alembic import op

revision = "0009_llm_usage_fields"
down_revision = "0008_worker_alerts"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("llm_request_logs") as batch:
        batch.add_column(sa.Column("error_category", sa.String(64), nullable=True))
        batch.add_column(sa.Column("cost_usd", sa.Float(), nullable=True))


def downgrade():
    with op.batch_alter_table("llm_request_logs") as batch:
        batch.drop_column("cost_usd")
        batch.drop_column("error_category")

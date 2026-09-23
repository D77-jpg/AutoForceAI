"""阶段 2 CRM 集成 schema：4 张表（2.9 收口后结构，worker 租约列由 0003 追加）。

Revision ID: 0002_phase2_crm
Revises: 0001_phase1_baseline
Create Date: 2026-09-23

包含：
- crm_integration_configs（service_token 密文 + token_last4、outcome 游标、reset 审计、
  启用门槛指纹 health_fingerprint；显式建表以固定历史形态，租约列见 0003）
- crm_sync_jobs（Outbox：幂等键唯一、租约字段、project_id 绑定、含 cancelled 状态语义）
- crm_entity_links（唯一约束 (provider, organization_id, lead_id, project_id)；archived_at 归档）
- crm_outcome_events（eventId 幂等流水）
"""
import sqlalchemy as sa
from alembic import op

from migrations.helpers import execute_frozen

revision = "0002_phase2_crm"
down_revision = "0001_phase1_baseline"
branch_labels = None
depends_on = None

def _create_configs() -> None:
    op.create_table(
        "crm_integration_configs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id"), index=True),
        sa.Column("provider", sa.String(), server_default="genesis_crm"),
        sa.Column("base_url", sa.String(), nullable=False),
        sa.Column("web_base_url", sa.String(), nullable=True),
        sa.Column("project_id", sa.String(), nullable=True),
        sa.Column("project_name", sa.String(), nullable=True),
        sa.Column("service_token", sa.String(), nullable=True),
        sa.Column("token_last4", sa.String(), nullable=True),
        sa.Column("contract_version", sa.String(), server_default="1.0"),
        sa.Column("enabled", sa.Boolean(), server_default=sa.false()),
        sa.Column("last_health_status", sa.String(), nullable=True),
        sa.Column("last_health_detail", sa.Text(), nullable=True),
        sa.Column("last_health_checked_at", sa.DateTime(), nullable=True),
        sa.Column("health_fingerprint", sa.String(), nullable=True),
        sa.Column("outcome_cursor", sa.String(), nullable=True),
        sa.Column("outcome_polled_at", sa.DateTime(), nullable=True),
        sa.Column("last_reset_at", sa.DateTime(), nullable=True),
        sa.Column("last_reset_by", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("organization_id", "provider", name="uq_crm_config_org_provider"),
    )


def upgrade() -> None:
    _create_configs()
    execute_frozen("PHASE2_HELPERS", "UP", op)


def downgrade() -> None:
    execute_frozen("PHASE2_HELPERS", "DOWN", op)
    op.drop_table("crm_integration_configs")

"""阶段 2 CRM 集成 schema：4 张表（含 2.9 收口后的最终列结构）。

Revision ID: 0002_phase2_crm
Revises: 0001_phase1_baseline
Create Date: 2026-09-23

包含：
- crm_integration_configs（service_token 密文 + token_last4、outcome 游标、reset 审计）
- crm_sync_jobs（Outbox：幂等键唯一、租约字段、project_id 绑定、含 cancelled 状态语义）
- crm_entity_links（唯一约束 (provider, organization_id, lead_id, project_id)；archived_at 归档）
- crm_outcome_events（eventId 幂等流水）
"""
from alembic import op

from migrations.helpers import PHASE2_TABLES, create_tables, drop_tables

revision = "0002_phase2_crm"
down_revision = "0001_phase1_baseline"
branch_labels = None
depends_on = None


def upgrade() -> None:
    create_tables(set(PHASE2_TABLES), op)


def downgrade() -> None:
    drop_tables(set(PHASE2_TABLES), op)

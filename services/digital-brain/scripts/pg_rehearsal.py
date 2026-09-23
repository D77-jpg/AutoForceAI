"""阶段 2 PostgreSQL 真实演练脚本（仅允许指向临时数据库！）。

用法（services/digital-brain 目录）：
    venv/Scripts/python -X utf8 scripts/pg_rehearsal.py "postgresql+psycopg://user:pass@host:port/临时库名"

安全检查：拒绝连接任何名字不含 rehearsal/tmp/test 的库，防止误操作业务库。
流程：upgrade head → 校验结构 → downgrade 0001 → 校验 CRM 表消失/阶段1保留 → 再 upgrade head → 复核。
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text

CRM_TABLES = {"crm_integration_configs", "crm_sync_jobs", "crm_entity_links",
              "crm_outcome_events", "crm_worker_state"}
PHASE1_SAMPLE = {"users", "organizations", "leads", "knowledge_bases"}


def main() -> int:
    url = sys.argv[1] if len(sys.argv) > 1 else ""
    dbname = url.rsplit("/", 1)[-1].split("?")[0].lower()
    if not re.search(r"rehearsal|tmp|test", dbname):
        print(f"REFUSED: 数据库名 {dbname!r} 不含 rehearsal/tmp/test，疑似业务库，拒绝操作")
        return 2

    root = Path(__file__).resolve().parents[1]
    cfg = Config(str(root / "alembic.ini"))
    cfg.set_main_option("script_location", str(root / "migrations"))
    cfg.set_main_option("sqlalchemy.url", url)
    engine = create_engine(url)

    print("[1/5] upgrade head")
    command.upgrade(cfg, "head")

    def check_full():
        insp = inspect(engine)
        names = set(insp.get_table_names())
        assert CRM_TABLES <= names, f"缺 CRM 表: {CRM_TABLES - names}"
        assert PHASE1_SAMPLE <= names, f"缺阶段1表: {PHASE1_SAMPLE - names}"
        idx = {i["name"]: i for i in insp.get_indexes("crm_entity_links")}
        assert idx["uq_crm_link_org_lead_project"]["unique"]
        config_idx = {i["name"]: i for i in insp.get_indexes("crm_integration_configs")}
        assert config_idx["uq_crm_config_provider_project"]["unique"]
        with engine.connect() as conn:
            ext = conn.execute(text("SELECT 1 FROM pg_extension WHERE extname='vector'")).scalar()
            assert ext == 1, "vector 扩展缺失"
            enums = {r[0] for r in conn.execute(text("SELECT typname FROM pg_type WHERE typtype='e'"))}
            assert {"taskstatus", "agentrole", "missionstatus"} <= enums, f"枚举缺失: {enums}"
            rev = conn.execute(text("SELECT version_num FROM alembic_version")).scalar()
            assert rev == "0004_phase2_project_ownership", rev
        print("       结构校验通过：5 张 CRM 表、唯一索引、vector 扩展、枚举、版本=0004")

    check_full()

    print("[2/5] 写入验证数据")
    with engine.begin() as conn:
        conn.execute(text("INSERT INTO organizations (name) VALUES ('PG 演练组织')"))
        oid = conn.execute(text("SELECT id FROM organizations WHERE name='PG 演练组织'")).scalar()
        conn.execute(text(
            "INSERT INTO crm_integration_configs (organization_id, base_url, provider, enabled)"
            " VALUES (:o, 'http://localhost:5000/api', 'genesis_crm', false)"), {"o": oid})

    print("[3/5] downgrade 0001_phase1_baseline（仅删 CRM 表）")
    command.downgrade(cfg, "0001_phase1_baseline")
    names = set(inspect(engine).get_table_names())
    assert not (CRM_TABLES & names - {"alembic_version"}), "CRM 表未被删除"
    assert PHASE1_SAMPLE <= names, "阶段1表被误删"
    with engine.connect() as conn:
        assert conn.execute(text("SELECT COUNT(*) FROM organizations WHERE name='PG 演练组织'")).scalar() == 1
    print("       校验通过：CRM 表已删、阶段1数据保留")

    print("[4/5] 再次 upgrade head（幂等回切）")
    command.upgrade(cfg, "head")
    check_full()

    print("[5/5] PG 演练完成 ✅")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""
Alembic 版本对齐（阶段 2.9 P0-4）。

启动流程：
- SQLite 开发库仍由 create_all/补列保证 schema 存在，再由本模块 stamp；
- PostgreSQL 不允许 create_all/stamp 冒充迁移，无版本库必须先显式执行
  `alembic upgrade head`（历史库须人工核验后 stamp 0001）；
- 落后 head → 自动 upgrade（迁移均为幂等建表，安全）；
- 领先 head（代码回滚）→ 明确报错，不静默继续。

本模块只为 SQLite 开发库提供无版本兜底，生产路径由 Alembic 独占。
"""
from __future__ import annotations

import logging
import os

logger = logging.getLogger("db.migrations")

SERVICE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ALEMBIC_INI = os.path.join(SERVICE_ROOT, "alembic.ini")


def get_current_revision(engine) -> str | None:
    """读取数据库当前 Alembic 版本，不执行任何 schema 变更。"""
    from alembic.migration import MigrationContext

    with engine.connect() as conn:
        return MigrationContext.configure(conn).get_current_revision()


def ensure_schema_current(engine) -> None:
    from alembic import command
    from alembic.config import Config
    from alembic.script import ScriptDirectory
    from alembic.script.revision import ResolutionError

    cfg = Config(ALEMBIC_INI)
    # 以运行中的 engine 为准（避免测试/多环境下 env 串错库）
    cfg.set_main_option("sqlalchemy.url", engine.url.render_as_string(hide_password=False))
    script = ScriptDirectory.from_config(cfg)
    head = script.get_current_head()

    current = get_current_revision(engine)

    if current == head:
        return
    if current is None:
        if engine.dialect.name != "sqlite":
            raise RuntimeError(
                "PostgreSQL 数据库缺少 alembic_version；已拒绝自动 create_all/stamp。"
                "空库请执行 `alembic upgrade head`；历史库请核验后执行 "
                "`alembic stamp 0001_phase1_baseline && alembic upgrade head`。"
            )
        command.stamp(cfg, head)
        logger.info("SQLite 开发库无 alembic 版本记录，已按现有 schema 标记为 head（%s）", head)
        return
    heads = script.get_heads()
    try:
        script.get_revision(current)
    except ResolutionError as exc:
        raise RuntimeError(
            f"数据库 schema 版本（{current}）不在当前代码迁移链中："
            "代码可能已回滚或数据库来自不兼容分支，请先恢复匹配的代码或显式降级数据库"
        ) from exc
    if current not in heads:
        command.upgrade(cfg, head)
        logger.warning("数据库 schema 已从 %s 自动升级到 %s", current, head)
        return
    if current in heads:
        raise RuntimeError(
            f"数据库 schema 版本（{current}）领先于代码（{head}）：代码可能已回滚，请先恢复代码或降级数据库"
        )
    command.upgrade(cfg, head)

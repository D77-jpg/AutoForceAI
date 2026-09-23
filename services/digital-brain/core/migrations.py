"""
Alembic 版本对齐（阶段 2.9 P0-4）。

启动流程：init_shared_db 的 create_all/补列保证 schema 存在（幂等），
本模块负责把 alembic_version 对齐到 head：
- 无 alembic_version → stamp head（历史库由 create_all/补列保证结构；正式空库请走
  `alembic upgrade head`，见 docs 与 README「数据库迁移」）；
- 落后 head → 自动 upgrade（迁移均为幂等建表，安全）；
- 领先 head（代码回滚）→ 明确报错，不静默继续。

正式生产路径（PostgreSQL）应以 `alembic upgrade head` 为准，
本模块是开发/试运行环境的兜底对齐。
"""
from __future__ import annotations

import logging
import os

logger = logging.getLogger("db.migrations")

SERVICE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ALEMBIC_INI = os.path.join(SERVICE_ROOT, "alembic.ini")


def ensure_schema_current(engine) -> None:
    from alembic import command
    from alembic.config import Config
    from alembic.migration import MigrationContext
    from alembic.script import ScriptDirectory

    cfg = Config(ALEMBIC_INI)
    # 以运行中的 engine 为准（避免测试/多环境下 env 串错库）
    cfg.set_main_option("sqlalchemy.url", engine.url.render_as_string(hide_password=False))
    script = ScriptDirectory.from_config(cfg)
    head = script.get_current_head()

    with engine.connect() as conn:
        current = MigrationContext.configure(conn).get_current_revision()

    if current == head:
        return
    if current is None:
        command.stamp(cfg, head)
        logger.info("数据库无 alembic 版本记录，已按现有 schema 标记为 head（%s）", head)
        return
    heads = script.get_heads()
    if current in script._revision_map and current not in heads:
        command.upgrade(cfg, head)
        logger.warning("数据库 schema 已从 %s 自动升级到 %s", current, head)
        return
    if current in heads:
        raise RuntimeError(
            f"数据库 schema 版本（{current}）领先于代码（{head}）：代码可能已回滚，请先恢复代码或降级数据库"
        )
    command.upgrade(cfg, head)

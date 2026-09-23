"""Alembic 环境：共享元数据为唯一事实来源。

URL 优先级：-x url=... > 环境变量 DATABASE_URL > core.config.settings.database.url
URL 不写入 alembic.ini（避免把连接串/密码提交进仓库）。
"""
import os
import sys

from alembic import context

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

config = context.config


def _resolve_url() -> str:
    # 显式 set_main_option（如测试/脚本注入）优先
    existing = config.get_main_option("sqlalchemy.url")
    if existing:
        return existing
    x_args = context.get_x_argument(as_dictionary=True)
    if x_args.get("url"):
        return x_args["url"]
    if os.getenv("DATABASE_URL"):
        return os.environ["DATABASE_URL"]
    from core.config import settings
    return settings.database.url


config.set_main_option("sqlalchemy.url", _resolve_url())

import database.shared_models  # noqa: E402,F401  注册共享表（users/leads/crm_*）
import database.models  # noqa: E402,F401  注册租户表（tenant + shared 同一 Base）
from database.base import Base  # noqa: E402

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    from sqlalchemy import engine_from_config, pool

    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

"""Migration helpers: metadata-driven DDL that works online and offline.

Uses sqlalchemy.schema.CreateTable/CreateIndex/DropTable/DropIndex compiled
against the target dialect, executed through op.execute (offline mode emits
the literal SQL, so `alembic upgrade head --sql` works for PostgreSQL review).

PostgreSQL native ENUM types are emitted as idempotent CREATE TYPE blocks.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import sqlalchemy as sa
from sqlalchemy.schema import CreateIndex, CreateTable, DropIndex, DropTable

import database.shared_models  # noqa: F401  register shared tables (users/orgs/leads/crm_*)
import database.models  # noqa: F401  register tenant tables
from database.base import Base

PHASE2_TABLES = (
    "crm_integration_configs",
    "crm_sync_jobs",
    "crm_entity_links",
    "crm_outcome_events",
)


def _tables(names: set[str]):
    return [t for t in Base.metadata.sorted_tables if t.name in names]


def _pg_enum_types(tables) -> dict[str, list[str]]:
    types: dict[str, list[str]] = {}
    for table in tables:
        for col in table.columns:
            typ = col.type
            if isinstance(typ, sa.Enum) and typ.native_enum:
                if typ.enum_class is not None:
                    values = [str(e.value) for e in typ.enum_class]
                else:
                    values = list(typ.enums)
                types.setdefault(typ.name, values)
    return types


def _create_pg_enums(tables, op) -> None:
    if op.get_context().dialect.name != "postgresql":
        return
    for name, values in _pg_enum_types(tables).items():
        vals = ", ".join(f"'{v}'" for v in values)
        op.execute(
            f"DO $$ BEGIN CREATE TYPE {name} AS ENUM ({vals}); "
            f"EXCEPTION WHEN duplicate_object THEN NULL; END $$;"
        )


def _drop_pg_enums(tables, op) -> None:
    if op.get_context().dialect.name != "postgresql":
        return
    for name in _pg_enum_types(tables):
        op.execute(f"DROP TYPE IF EXISTS {name}")


def maybe_create_pgvector_extension(op) -> None:
    """knowledge_chunks.embedding needs the pgvector extension on PostgreSQL."""
    if op.get_context().dialect.name == "postgresql":
        op.execute("CREATE EXTENSION IF NOT EXISTS vector")


def create_tables(names: set[str], op) -> None:
    tables = _tables(names)
    _create_pg_enums(tables, op)
    dialect = op.get_context().dialect
    for table in tables:
        op.execute(str(CreateTable(table).compile(dialect=dialect)).rstrip())
        for index in table.indexes:
            op.execute(str(CreateIndex(index).compile(dialect=dialect)).rstrip())


def drop_tables(names: set[str], op) -> None:
    tables = _tables(names)
    dialect = op.get_context().dialect
    for table in reversed(tables):
        for index in table.indexes:
            op.execute(str(DropIndex(index, if_exists=True).compile(dialect=dialect)).rstrip())
        op.execute(str(DropTable(table, if_exists=True).compile(dialect=dialect)).rstrip())
    _drop_pg_enums(tables, op)

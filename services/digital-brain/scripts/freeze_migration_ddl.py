"""Regenerate the immutable DDL snapshot used by revisions 0001 and 0002.

This is a maintainer tool, never imported by Alembic at runtime.  Review the
generated diff before committing: changing an applied migration is normally
forbidden and should instead be represented by a new revision.
"""
from __future__ import annotations

import pprint
import sys
from pathlib import Path

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql, sqlite
from sqlalchemy.schema import CreateIndex, CreateTable, DropIndex, DropTable

SERVICE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SERVICE_ROOT))

import database.models  # noqa: E402,F401
import database.shared_models  # noqa: E402,F401
from database.base import Base  # noqa: E402

PHASE2_TABLES = {
    "crm_integration_configs",
    "crm_sync_jobs",
    "crm_entity_links",
    "crm_outcome_events",
    "crm_worker_state",
}
PHASE1_TABLES = set(Base.metadata.tables) - PHASE2_TABLES
PHASE2_HELPER_TABLES = {"crm_sync_jobs", "crm_entity_links", "crm_outcome_events"}


def _tables(names: set[str]):
    return [table for table in Base.metadata.sorted_tables if table.name in names]


def _enum_types(tables) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    for table in tables:
        for column in table.columns:
            typ = column.type
            if isinstance(typ, sa.Enum) and typ.native_enum:
                values = [str(item.value) for item in typ.enum_class] if typ.enum_class else list(typ.enums)
                result.setdefault(typ.name, values)
    return result


def _statements(names: set[str], dialect, *, postgres: bool):
    tables = _tables(names)
    up: list[str] = []
    down: list[str] = []
    if postgres:
        for name, values in _enum_types(tables).items():
            quoted = ", ".join(f"'{value}'" for value in values)
            up.append(
                f"DO $$ BEGIN CREATE TYPE {name} AS ENUM ({quoted}); "
                "EXCEPTION WHEN duplicate_object THEN NULL; END $$;"
            )
    for table in tables:
        up.append(str(CreateTable(table).compile(dialect=dialect)).strip())
        for index in sorted(table.indexes, key=lambda item: item.name or ""):
            up.append(str(CreateIndex(index).compile(dialect=dialect)).strip())
    for table in reversed(tables):
        for index in sorted(table.indexes, key=lambda item: item.name or "", reverse=True):
            down.append(str(DropIndex(index, if_exists=True).compile(dialect=dialect)).strip())
        down.append(str(DropTable(table, if_exists=True).compile(dialect=dialect)).strip())
    if postgres:
        down.extend(f"DROP TYPE IF EXISTS {name}" for name in reversed(list(_enum_types(tables))))
    return tuple(up), tuple(down)


def main() -> None:
    groups = {
        "PHASE1": PHASE1_TABLES,
        "PHASE2_HELPERS": PHASE2_HELPER_TABLES,
    }
    values: dict[str, tuple[str, ...]] = {}
    for label, names in groups.items():
        values[f"{label}_SQLITE_UP"], values[f"{label}_SQLITE_DOWN"] = _statements(
            names, sqlite.dialect(), postgres=False,
        )
        values[f"{label}_POSTGRES_UP"], values[f"{label}_POSTGRES_DOWN"] = _statements(
            names, postgresql.dialect(), postgres=True,
        )

    target = SERVICE_ROOT / "migrations" / "frozen_ddl.py"
    lines = [
        '"""Generated immutable DDL snapshot for Alembic revisions 0001/0002.\n\n',
        "Do not hand-edit or import application ORM metadata here.\n",
        '"""\n\n',
    ]
    for name, statements in values.items():
        lines.append(f"{name} = {pprint.pformat(statements, width=118, sort_dicts=False)}\n\n")
    target.write_text("".join(lines).rstrip() + "\n", encoding="utf-8", newline="\n")
    print(f"wrote {target}")


if __name__ == "__main__":
    main()

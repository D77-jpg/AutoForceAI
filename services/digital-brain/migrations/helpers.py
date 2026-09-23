"""Helpers for executing immutable revision-owned DDL snapshots.

Historical revisions must never import the live application ORM.  Revisions
0001 and 0002 therefore execute SQL captured when those revisions were frozen,
with separate SQLite and PostgreSQL variants for online and ``--sql`` use.
"""
from __future__ import annotations

from migrations import frozen_ddl


def maybe_create_pgvector_extension(op) -> None:
    """``knowledge_chunks.embedding`` requires pgvector on PostgreSQL."""
    if op.get_context().dialect.name == "postgresql":
        op.execute("CREATE EXTENSION IF NOT EXISTS vector")


def execute_frozen(group: str, direction: str, op) -> None:
    dialect = op.get_context().dialect.name
    if dialect not in {"sqlite", "postgresql"}:
        raise RuntimeError(f"Unsupported migration dialect: {dialect}")
    if group not in {"PHASE1", "PHASE2_HELPERS"}:
        raise RuntimeError(f"Unknown frozen migration group: {group}")
    if direction not in {"UP", "DOWN"}:
        raise RuntimeError(f"Unknown frozen migration direction: {direction}")

    dialect_label = "POSTGRES" if dialect == "postgresql" else "SQLITE"
    statements = getattr(frozen_ddl, f"{group}_{dialect_label}_{direction}")
    for statement in statements:
        op.execute(statement)

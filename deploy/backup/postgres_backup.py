#!/usr/bin/env python3
"""H-12 PostgreSQL backup and non-destructive rehearsal restore.

Requires pg_dump, pg_restore, psql and (only when encryption is used) age.
Connection credentials come exclusively from libpq PG* environment variables;
PGDATABASE identifies the source, never a URL containing passwords.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time

IDENT = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]{0,62}$")
CRITICAL = ("alembic_version", "crm_integration_configs", "crm_entity_links", "crm_sync_jobs", "crm_outcome_events")


def name(value):
    if not IDENT.fullmatch(value):
        raise ValueError("Database name must be a simple PostgreSQL identifier")
    return value


def safe_directory(value):
    original = Path(value).expanduser()
    if original.is_symlink() or not original.exists():
        raise ValueError("Refusing unsafe/unresolved/root backup directory")
    path = original.resolve(strict=True)
    if not path.is_dir() or path == Path(path.anchor):
        raise ValueError("Refusing unsafe/unresolved/root backup directory")
    return path


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as data:
        for chunk in iter(lambda: data.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def run(argv, *, out=None):
    # Never include environment variables, command output or credentials in reports.
    with (open(out, "wb") if out else open(os.devnull, "wb")) as sink:
        subprocess.run(argv, check=True, stdout=sink, stderr=subprocess.DEVNULL)


def json_atomic(path, data):
    tmp = path.with_name("." + path.name + ".tmp")
    try:
        with tmp.open("x", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)


def backup(directory, db, recipient=None):
    db = name(db)
    base = safe_directory(directory)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    stem = f"postgres_{db}_{stamp}"
    suffix = ".dump.age" if recipient else ".dump"
    archive = base / (stem + suffix)
    manifest = base / (stem + ".manifest.json")
    with tempfile.TemporaryDirectory(prefix=".pg_stage_", dir=base) as stage:
        raw = Path(stage) / "backup.dump"
        run(["pg_dump", "--format=custom", "--no-owner", "--no-acl", "--dbname", db, "--file", str(raw)])
        if not raw.is_file() or raw.stat().st_size == 0:
            raise RuntimeError("pg_dump produced no data")
        run(["pg_restore", "--list", str(raw)])
        if recipient:
            if not recipient.strip():
                raise ValueError("age recipient must not be blank")
            encrypted = Path(stage) / "backup.dump.age"
            run(["age", "-r", recipient, "-o", str(encrypted), str(raw)])
            raw = encrypted
        sha = digest(raw)
        if raw.stat().st_size == 0:
            raise RuntimeError("Backup archive is empty")
        metadata = {"schema": 1, "engine": "postgresql", "database": db, "created_utc": stamp,
                    "archive": archive.name, "sha256": sha, "bytes": raw.stat().st_size,
                    "encrypted": bool(recipient)}
        if archive.exists() or manifest.exists():
            raise FileExistsError("Backup already exists")
        os.replace(raw, archive)
        try:
            json_atomic(manifest, metadata)
        except Exception:
            archive.unlink(missing_ok=True)
            raise
    return metadata


def verified_manifest(directory, manifest):
    root = safe_directory(directory)
    raw_entry = root / manifest
    if raw_entry.is_symlink() or not raw_entry.is_file():
        raise ValueError("Manifest must be a regular file directly inside backup directory")
    entry = raw_entry.resolve(strict=True)
    if entry.parent != root or not entry.name.endswith(".manifest.json"):
        raise ValueError("Manifest must be a regular file directly inside backup directory")
    data = json.loads(entry.read_text(encoding="utf-8"))
    if data.get("schema") != 1 or data.get("engine") != "postgresql":
        raise ValueError("Unsupported manifest")
    name(data["database"])
    archive_name = data["archive"]
    if not isinstance(archive_name, str) or archive_name not in (entry.name.removesuffix(".manifest.json") + ".dump", entry.name.removesuffix(".manifest.json") + ".dump.age"):
        raise ValueError("Invalid archive name")
    raw_archive = root / archive_name
    if raw_archive.is_symlink() or not raw_archive.is_file():
        raise ValueError("Archive must be a regular file directly inside backup directory")
    archive = raw_archive.resolve(strict=True)
    if archive.parent != root:
        raise ValueError("Archive must be a regular file directly inside backup directory")
    if not isinstance(data.get("bytes"), int) or data["bytes"] < 1 or not isinstance(data.get("sha256"), str) or not re.fullmatch(r"[a-f0-9]{64}", data["sha256"]):
        raise ValueError("Invalid backup checksum metadata")
    if data.get("encrypted") not in (True, False) or archive.suffix != (".age" if data["encrypted"] else ".dump"):
        raise ValueError("Invalid archive encryption metadata")
    if archive.stat().st_size != data["bytes"] or digest(archive) != data["sha256"]:
        raise ValueError("Backup checksum mismatch")
    return data, archive


def query(db, sql):
    result = subprocess.run(["psql", "--dbname", db, "--no-psqlrc", "--tuples-only", "--no-align", "--set", "ON_ERROR_STOP=1", "--command", sql],
                            capture_output=True, check=True, text=True)
    return result.stdout.strip()


def current_database(db):
    """Prevent libpq PG* service/connection overrides from silently redirecting."""
    if query(db, "SELECT current_database()") != db:
        raise ValueError("Connected PostgreSQL database does not match requested target")


def restore(directory, manifest, target, identity=None):
    target = name(target)
    if "rehearsal" not in target.lower() and "restore_test" not in target.lower():
        raise ValueError("Restore target must contain rehearsal or restore_test")
    data, archive = verified_manifest(directory, manifest)
    start = time.monotonic()
    current_database(target)
    with tempfile.TemporaryDirectory(prefix=".pg_restore_", dir=safe_directory(directory)) as stage:
        raw = archive
        if data["encrypted"]:
            if not identity or not Path(identity).is_file():
                raise ValueError("Private age identity file is required for encrypted restore")
            raw = Path(stage) / "restore.dump"
            run(["age", "-d", "-i", identity, "-o", str(raw), str(archive)])
        run(["pg_restore", "--list", str(raw)])
        # No --clean / --create: target must preexist and be empty. No production downgrade.
        existing = query(target, "SELECT COUNT(*) FROM pg_catalog.pg_tables WHERE schemaname NOT IN ('pg_catalog','information_schema')")
        if int(existing) != 0:
            raise ValueError("Restore target must be an empty database")
        run(["pg_restore", "--exit-on-error", "--no-owner", "--no-acl", "--dbname", target, str(raw)])
    table_names = set(query(target, "SELECT tablename FROM pg_catalog.pg_tables WHERE schemaname='public'").splitlines())
    missing = sorted(set(CRITICAL) - table_names)
    if missing:
        raise RuntimeError("Rehearsal missing critical tables")
    counts = {table: int(query(target, f'SELECT COUNT(*) FROM public."{table}"')) for table in CRITICAL}
    versions = query(target, "SELECT version_num FROM public.alembic_version")
    if not versions or counts["alembic_version"] != 1 or not re.fullmatch(r"[a-zA-Z0-9_]+", versions):
        raise RuntimeError("Rehearsal missing Alembic revision")
    mapped_projects = int(query(target, "SELECT COUNT(DISTINCT project_id) FROM public.crm_entity_links WHERE project_id IS NOT NULL"))
    return {"status": "passed", "engine": "postgresql", "source_database": data["database"],
            "target_database": target, "sha256": data["sha256"], "critical_table_counts": counts,
            "alembic_version": versions, "crm_mapped_project_count": mapped_projects,
            "rto_seconds": round(time.monotonic() - start, 3),
            "rpo_seconds_at_rehearsal": max(0, int((datetime.now(timezone.utc) - datetime.strptime(data["created_utc"], "%Y%m%dT%H%M%S%fZ").replace(tzinfo=timezone.utc)).total_seconds()))}


def prune(directory, days, max_copies):
    root = safe_directory(directory)
    if days < 0 or max_copies < 1:
        raise ValueError("Retention days must be >= 0 and max copies >= 1")
    now = datetime.now(timezone.utc)
    records = []
    for path in root.glob("postgres_*.manifest.json"):
        if path.is_symlink():
            raise ValueError("Refusing symlinked manifest")
        data, archive = verified_manifest(root, path.name)
        created = datetime.strptime(data["created_utc"], "%Y%m%dT%H%M%S%fZ").replace(tzinfo=timezone.utc)
        records.append((created, path, archive))
    records.sort(reverse=True)
    removed = []
    for index, (created, manifest, archive) in enumerate(records):
        if index < max_copies and (now - created).total_seconds() <= days * 86400:
            continue
        # Only exact validated file pairs, never recursive directory deletion.
        archive.unlink()
        manifest.unlink()
        removed.append(manifest.name)
    return removed


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("backup", "restore", "prune"))
    parser.add_argument("--directory", required=True)
    parser.add_argument("--database", help="Source PGDATABASE for backup")
    parser.add_argument("--manifest", help="Manifest filename for restore")
    parser.add_argument("--target", help="Existing empty rehearsal database for restore")
    parser.add_argument("--recipient", help="Optional public age recipient (not a secret)")
    parser.add_argument("--identity", help="Path to private age key, never commit this file")
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--max-copies", type=int, default=14)
    parser.add_argument("--report", help="Optional machine-readable report path (outside backups)")
    args = parser.parse_args(argv)
    start = time.monotonic()
    result = {"status": "failed", "action": args.action, "engine": "postgresql", "timestamp_utc": datetime.now(timezone.utc).isoformat()}
    try:
        if args.action == "backup":
            result.update(backup(args.directory, args.database or os.getenv("PGDATABASE", ""), args.recipient))
            result["status"] = "passed"
        elif args.action == "restore":
            result.update(restore(args.directory, args.manifest, args.target, args.identity))
        else:
            result.update({"removed": prune(args.directory, args.days, args.max_copies), "status": "passed"})
    except (Exception,) as exc:
        # Never include raw exception or subprocess stderr: could contain secrets.
        result["failure_reason"] = exc.__class__.__name__
    result.setdefault("rto_seconds", round(time.monotonic() - start, 3))
    if args.report:
        json_atomic(Path(args.report), result)
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    sys.exit(main())

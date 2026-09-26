"""Persistent worker incidents. Never persist exception text, request bodies or credentials.

Outbound webhook/email is intentionally UNSUPPORTED: even an opt-in arbitrary URL or
recipient can exfiltrate tenant data or enable SSRF. No network transport is imported.
"""
from __future__ import annotations

import hashlib
import os
import re
from datetime import datetime, timedelta

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from database.shared_models import Alert, User

_CATEGORIES = re.compile(r"^[A-Z][A-Z0-9_]{0,79}$")
_RETENTION_DEFAULT = 90
# Explicit allowlist prevents vendor-supplied codes from smuggling identifiers or
# bearer-like strings into DB/API. Unknown codes collapse into one safe category.
_KNOWN_CATEGORIES = frozenset({
    "UNKNOWN", "JOB_FAILED", "UNEXPECTED", "NETWORK", "TIMEOUT", "CONNECTION_ERROR",
    "HTTP_ERROR", "RATE_LIMITED", "VALIDATION_ERROR", "PAYLOAD_INVALID",
    "PROJECT_BINDING_CHANGED", "CREDENTIAL_ERROR", "AUTH_INVALID", "UNAUTHORIZED",
    "FORBIDDEN", "NOT_FOUND", "CONFLICT", "BAD_REQUEST", "INTERNAL_ERROR",
    "SERVICE_UNAVAILABLE", "TOO_MANY_REDIRECTS", "PROJECT_MISMATCH",
    "UNSUPPORTED_CONTRACT_VERSION", "INVALID_PDF_RESPONSE", "HTTP_401", "HTTP_403",
    "HTTP_408", "HTTP_429", "HTTP_500", "HTTP_502", "HTTP_503", "HTTP_504",
})


def _category(value: str | None) -> str:
    # Never echo vendor error codes without validation; free-form messages can contain secrets.
    candidate = (value or "UNKNOWN").upper()
    return candidate if _CATEGORIES.fullmatch(candidate) and candidate in _KNOWN_CATEGORIES else "UNKNOWN"


def _severity(value: str) -> str:
    if value not in ("warning", "critical"):
        raise ValueError("unsupported alert severity")
    return value


def _fingerprint(org_id: int, source: str, category: str) -> str:
    return hashlib.sha256(f"{org_id}:{source}:{category}".encode("utf-8")).hexdigest()


def record_failure(db: Session, *, organization_id: int | None, source: str,
                   category: str | None, severity: str = "warning") -> Alert | None:
    """Record a *failure occurrence*, not a polling tick; transaction belongs to caller.

    On competing first inserts, a savepoint contains only the uniqueness collision;
    the caller's outer transaction is not rolled back. A following write lock retries.
    """
    if organization_id is None or organization_id <= 0:
        return None  # Never create a global alert for an unowned RPA job.
    if source not in ("rpa", "crm_dispatcher", "crm_outcome"):
        raise ValueError("unsupported alert source")
    category = _category(category)
    severity = _severity(severity)
    fingerprint = _fingerprint(organization_id, source, category)
    now = datetime.now()
    row = db.query(Alert).filter(Alert.fingerprint == fingerprint).with_for_update().first()
    if row is None:
        try:
            with db.begin_nested():
                row = Alert(organization_id=organization_id, source=source,
                            category=category, fingerprint=fingerprint, severity=severity,
                            status="open", occurrences=1, event_type="first",
                            summary=f"{source} {category} failure", first_seen_at=now,
                            last_seen_at=now)
                db.add(row)
                db.flush()
            return row
        except IntegrityError:
            row = db.query(Alert).filter(Alert.fingerprint == fingerprint).with_for_update().one()
    row.occurrences += 1
    row.last_seen_at = now
    if row.status == "resolved":
        row.first_seen_at = now
        row.resolved_at = None
        row.acknowledged_at = None
        row.status = "open"
        row.event_type = "first"
        row.severity = severity
    elif severity == "critical" and row.severity != "critical":
        row.severity = "critical"
        row.status = "open"
        row.event_type = "escalated"
    else:
        row.event_type = "new"
    return row


def record_recovery(db: Session, *, organization_id: int | None, source: str,
                    category: str | None = None) -> int:
    """Resolve only currently open/acknowledged incidents; idle polling does nothing."""
    if organization_id is None or organization_id <= 0:
        return 0
    q = db.query(Alert).filter(Alert.organization_id == organization_id,
                               Alert.source == source, Alert.status != "resolved")
    if category is not None:
        q = q.filter(Alert.category == _category(category))
    rows = q.with_for_update().all()
    now = datetime.now()
    for row in rows:
        row.status = "resolved"
        row.event_type = "recovered"
        row.resolved_at = now
    return len(rows)


def record_rpa_job_outcome(db: Session, job, *, failed: bool) -> None:
    """Call once on a worker callback state transition, never on task retrieval.

    Category intentionally excludes error text, URLs, payload, user input, and job ID.
    """
    user = db.query(User).filter(User.id == job.user_id).first() if job.user_id else None
    org_id = user.organization_id if user else None
    if failed:
        record_failure(db, organization_id=org_id, source="rpa", category="JOB_FAILED")
    else:
        record_recovery(db, organization_id=org_id, source="rpa", category="JOB_FAILED")


def retention_days() -> int:
    """Bound retention to 1..3650 days, refuse invalid configuration."""
    raw = os.getenv("ALERT_RETENTION_DAYS", str(_RETENTION_DEFAULT))
    try:
        days = int(raw)
    except ValueError as exc:
        raise ValueError("ALERT_RETENTION_DAYS must be an integer") from exc
    if not 1 <= days <= 3650:
        raise ValueError("ALERT_RETENTION_DAYS must be between 1 and 3650")
    return days


def cleanup_resolved(db: Session, *, now: datetime | None = None) -> int:
    """Delete only resolved incidents after retention; caller commits separately."""
    cutoff = (now or datetime.now()) - timedelta(days=retention_days())
    return db.query(Alert).filter(Alert.status == "resolved", Alert.resolved_at < cutoff).delete(
        synchronize_session=False)


def validate_notifications_disabled() -> None:
    """Fail closed if outbound alert delivery is configured; never initiate network I/O."""
    for key in ("ALERT_WEBHOOK_URL", "ALERT_EMAIL_TO", "ALERT_NOTIFICATIONS_ENABLED"):
        if os.getenv(key, "").strip().lower() not in ("", "0", "false", "off"):
            raise ValueError(f"{key}: outbound alert notifications are unsupported (SSRF/data leakage)")

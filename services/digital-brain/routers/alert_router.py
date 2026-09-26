"""Organization-isolated alert listing and acknowledgment API."""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from core.db_manager import get_shared_db
from core.dependencies import get_current_user
from database.shared_models import Alert, User

router = APIRouter(prefix="/api/v1/monitor", tags=["Monitoring"])


def _actor(payload: dict, db: Session) -> User:
    # Never trust mutable org/role claims in JWT: fetch live membership from DB.
    user = db.query(User).filter(User.id == payload.get("id"), User.is_active.is_(True)).first()
    if not user:
        raise HTTPException(401, "User not found")
    if not user.organization_id:
        raise HTTPException(403, "Organization membership required")
    return user


def _dto(row: Alert) -> dict:
    return {key: getattr(row, key) for key in (
        "id", "organization_id", "source", "category", "severity", "status",
        "summary", "occurrences", "event_type", "first_seen_at", "last_seen_at",
        "acknowledged_at", "resolved_at",
    )}


@router.get("/alerts")
def list_alerts(limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0),
                status: str | None = Query(None), payload: dict = Depends(get_current_user),
                db: Session = Depends(get_shared_db)):
    user = _actor(payload, db)
    query = db.query(Alert).filter(Alert.organization_id == user.organization_id)
    if status is not None:
        if status not in ("open", "acknowledged", "resolved"):
            raise HTTPException(422, "Invalid alert status")
        query = query.filter(Alert.status == status)
    return {"items": [_dto(row) for row in query.order_by(Alert.last_seen_at.desc(), Alert.id.desc())
                       .offset(offset).limit(limit).all()], "total": query.count()}


def _mutate(alert_id: int, action: str, payload: dict, db: Session) -> dict:
    user = _actor(payload, db)
    if user.role not in ("admin", "enterprise_admin"):
        raise HTTPException(403, "Organization administrator required")
    row = db.query(Alert).filter(Alert.id == alert_id,
                                 Alert.organization_id == user.organization_id).with_for_update().first()
    if not row:
        raise HTTPException(404, "Alert not found")
    if action == "ack" and row.status == "open":
        row.status = "acknowledged"
        row.acknowledged_at = datetime.now()
    elif action == "resolve" and row.status != "resolved":
        row.status = "resolved"
        row.resolved_at = datetime.now()
    db.commit()
    return _dto(row)


@router.post("/alerts/{alert_id}/ack")
def acknowledge_alert(alert_id: int, payload: dict = Depends(get_current_user),
                      db: Session = Depends(get_shared_db)):
    return _mutate(alert_id, "ack", payload, db)


@router.post("/alerts/{alert_id}/resolve")
def resolve_alert(alert_id: int, payload: dict = Depends(get_current_user),
                  db: Session = Depends(get_shared_db)):
    return _mutate(alert_id, "resolve", payload, db)

"""Authentication dependencies and tenant session access."""
from typing import Generator

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from core.auth import decode_token
from core.db_manager import SharedSessionLocal, get_tenant_session
from core.security_rate_limit import enforce_user_rate_limit
from database.shared_models import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/wechat/login")


def get_current_user(request: Request, token: str = Depends(oauth2_scheme)) -> dict:
    """Validate a token, then resolve the live user's organization for telemetry."""
    try:
        payload = decode_token(token)
    except Exception:
        payload = None
    if not isinstance(payload, dict):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Could not validate credentials",
                            headers={"WWW-Authenticate": "Bearer"})
    candidate = payload.get("id") or payload.get("user_id") or payload.get("sub")
    try:
        user_id = int(candidate)
    except (ValueError, TypeError):
        # Some older tokens use a username as subject. Resolve through live DB.
        with SharedSessionLocal() as db:
            user = db.query(User).filter(User.username == candidate).first() if isinstance(candidate, str) else None
            user_id = user.id if user else None
    if not user_id:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token missing valid user identifier")
    payload["id"] = user_id
    with SharedSessionLocal() as db:
        user = db.query(User).filter(User.id == user_id, User.is_active.is_(True)).first()
        if not user:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Could not validate credentials",
                                headers={"WWW-Authenticate": "Bearer"})
        request.state.user_id = user.id
        request.state.organization_id = user.organization_id
        payload["org_id"] = user.organization_id
        payload["organization_id"] = user.organization_id
        payload["role"] = user.role.value if hasattr(user.role, "value") else user.role
    enforce_user_rate_limit(request)
    return payload


def get_current_user_id(user: dict = Depends(get_current_user)) -> int:
    return user["id"]


def get_db(user_id: int = Depends(get_current_user_id)) -> Generator[Session, None, None]:
    db = get_tenant_session(user_id)
    try:
        yield db
    finally:
        db.close()

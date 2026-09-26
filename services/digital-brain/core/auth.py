from datetime import datetime, timedelta
from typing import Optional
import os
import sys
from jose import JWTError, jwt
from passlib.context import CryptContext

# Only local development may use the fallback. Never reveal configured secrets in errors.
_DEV_SECRET = "autoforce-dev-only-insecure-secret-key"
_KNOWN_WEAK_SECRETS = frozenset({_DEV_SECRET, "secret", "changeme", "change-me", "your-secret-key", "your-secret-key-here"})


def is_production() -> bool:
    return any(os.getenv(name, "").strip().lower() in {"production", "prod"}
               for name in ("APP_ENV", "ENVIRONMENT", "NODE_ENV", "DIGITAL_BRAIN_ENV"))


def get_jwt_secret() -> str:
    secret = os.getenv("JWT_SECRET", "")
    if is_production():
        if len(secret.encode("utf-8")) < 32 or secret.strip().lower() in _KNOWN_WEAK_SECRETS:
            raise RuntimeError("Production requires a strong JWT_SECRET (at least 32 bytes, not a known default)")
    elif not secret:
        return _DEV_SECRET
    return secret


SECRET_KEY = get_jwt_secret()  # Fail fast during production startup.
if SECRET_KEY == _DEV_SECRET and not is_production():
    print("WARNING: JWT_SECRET is not set; using a development-only key.", file=sys.stderr)
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7 # 7 days persistence

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, get_jwt_secret(), algorithm=ALGORITHM)
    return encoded_jwt

def decode_token(token: str):
    try:
        payload = jwt.decode(token, get_jwt_secret(), algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None

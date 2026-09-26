"""Process-local request throttling: IP before auth, user after verified auth.

This is NOT a distributed limiter. For production, explicitly attest either a single
worker (RATE_LIMIT_SINGLE_PROCESS=1) or a real shared gateway/Redis limiter
(RATE_LIMIT_SHARED_ENFORCED=1). The latter flag is an operator assertion, NOT a
Redis implementation: deploy and verify that external limit separately. Without
an assertion production requests fail closed with 503; with multiple workers the
single-process assertion is insufficient. Never use forwarded client headers
unless a separately configured, trusted proxy has already rewritten scope.client.
"""

from __future__ import annotations

import hashlib
import math
import os
import re
import threading
import time
from dataclasses import dataclass
from typing import Optional

from fastapi import HTTPException
from starlette.requests import Request
from starlette.responses import JSONResponse, Response


@dataclass(frozen=True)
class Limit:
    capacity: int
    period: float  # seconds for a full refill


# Tier budget is shared across all canonical routes in that tier. A second
# route budget prevents one endpoint from consuming the whole tier budget.
LIMITS = {
    "login": Limit(5, 60),
    "agent": Limit(30, 60),
    "search": Limit(20, 60),
    "quotation_confirm": Limit(6, 60),
    "admin": Limit(20, 60),
    "normal": Limit(120, 60),
}

_DYNAMIC_SEGMENT = re.compile(r"^(?:\d+|[0-9a-fA-F]{8}-[0-9a-fA-F-]{27,}|[0-9a-fA-F]{24,})$")


def canonical_route(request: Request) -> tuple[str, str]:
    """Canonical method and path; never include query strings or credentials."""
    method = request.method.upper()
    path = request.scope.get("path", "/")
    if not isinstance(path, str):
        path = "/"
    path = "/" + "/".join(
        "{id}" if _DYNAMIC_SEGMENT.fullmatch(segment) else segment.lower()
        for segment in path.strip("/").split("/") if segment
    )
    # Keep malformed and arbitrarily long URLs from consuming unbounded RAM.
    if len(path) > 512:
        path = path[:128] + "/{long-path}:" + hashlib.sha256(path.encode()).hexdigest()[:24]
    return method, path


def classify_route(method: str, path: str) -> str:
    """Tier selection based solely on canonical route, never user input headers."""
    parts = path.strip("/").split("/")
    # Auth create/join and WeChat login are credential/registration operations.
    if path.startswith("/auth/") and method in ("POST", "PUT", "PATCH"):
        if any(part in ("login", "register", "create", "join") for part in parts):
            return "login"
    if path.startswith("/api/v1/crm/quotations/") and method == "POST" and path.endswith("/confirm"):
        return "quotation_confirm"
    if parts[0] == "agents" or "agent" in parts or "agents" in parts:
        return "agent"
    if "search" in parts or any(part.startswith("search_") or part.endswith("_search") for part in parts):
        return "search"
    if "admin" in parts:
        return "admin"
    return "normal"


@dataclass
class _Bucket:
    tokens: float
    updated: float
    last_seen: float


class InProcessRateLimiter:
    """Atomic dual-principal, dual-scope token buckets with bounded storage.

    A full keyspace fails closed for new keys instead of evicting active keys
    (eviction would let an attacker reset a bucket). Idle buckets expire only
    once their tokens have completely refilled. All evaluation and deductions
    occur under one lock; rejected requests deduct nothing.
    """

    def __init__(self, limits: Optional[dict[str, Limit]] = None, max_entries: int = 10000,
                 clock=None):
        if max_entries < 1:
            raise ValueError("max_entries must be positive")
        self.limits = dict(LIMITS if limits is None else limits)
        if not self.limits or any(v.capacity < 1 or v.period <= 0 for v in self.limits.values()):
            raise ValueError("invalid limits")
        self.max_entries = max_entries
        self._clock = clock or time.monotonic
        self._buckets: dict[tuple[str, str, str, str], _Bucket] = {}
        self._lock = threading.Lock()

    def _prune(self, now: float) -> None:
        for key, bucket in list(self._buckets.items()):
            limit = self.limits[key[2]]
            if now - bucket.last_seen >= limit.period and now - bucket.updated >= limit.period:
                del self._buckets[key]

    def check(self, method: str, path: str, tier: str, user_id: object = None,
              ip: Optional[str] = None, principal: str = "both") -> Optional[int]:
        """Return Retry-After seconds on denial; principal selects IP/user/both."""
        if principal not in ("ip", "user", "both"):
            raise ValueError("invalid principal")
        limit = self.limits[tier]
        principals = []
        if principal in ("user", "both") and user_id is not None:
            principals.append(("user", str(user_id)))
        if principal in ("ip", "both"):
            # Missing direct peer identity must not yield an unthrottled request.
            principals.append(("ip", ip if ip else "unknown"))
        if not principals:
            raise ValueError("verified user_id required for user rate limit")
        keys = list(dict.fromkeys(
            (kind, identity, tier, scope)
            for kind, identity in principals
            for scope in ("*", method + " " + path)
        ))
        now = self._clock()
        with self._lock:
            self._prune(now)
            missing = sum(key not in self._buckets for key in keys)
            if len(self._buckets) + missing > self.max_entries:
                return max(1, math.ceil(limit.period))
            waits = []
            for key in keys:
                bucket = self._buckets.get(key)
                if bucket is None:
                    continue
                available = min(limit.capacity, bucket.tokens +
                                max(0.0, now - bucket.updated) * limit.capacity / limit.period)
                if available < 1 - 1e-9:
                    waits.append((1 - available) * limit.period / limit.capacity)
            if waits:
                return max(1, math.ceil(max(waits)))
            for key in keys:
                bucket = self._buckets.get(key)
                if bucket is None:
                    self._buckets[key] = _Bucket(limit.capacity - 1, now, now)
                else:
                    bucket.tokens = min(limit.capacity, bucket.tokens +
                                        max(0.0, now - bucket.updated) * limit.capacity / limit.period) - 1
                    bucket.updated = now
                    bucket.last_seen = now
            return None


def production_limiter_ready(environ=None) -> bool:
    """Explicitly require a single worker or an independently enforced shared limit."""
    env = os.environ if environ is None else environ
    if not any(env.get(name, "").lower() in ("production", "prod")
               for name in ("ENVIRONMENT", "APP_ENV", "NODE_ENV", "DIGITAL_BRAIN_ENV")):
        return True
    if env.get("RATE_LIMIT_SHARED_ENFORCED") == "1":
        return True
    workers = env.get("RATE_LIMIT_WORKERS", env.get("WEB_CONCURRENCY", "1"))
    try:
        return env.get("RATE_LIMIT_SINGLE_PROCESS") == "1" and int(workers) == 1
    except ValueError:
        return False


DEFAULT_LIMITER = InProcessRateLimiter()


def _excluded(method: str, path: str) -> bool:
    return (method == "GET" and
            (path == "/monitor" or path.startswith("/monitor/") or
             path == "/api/v1/monitor" or path.startswith("/api/v1/monitor/"))) or path in (
                 "/health", "/api/v1/health")


def enforce_rate_limit(request: Request, limiter: Optional[InProcessRateLimiter] = None) -> Optional[Response]:
    """Pre-auth middleware IP guard: return 429/503 response or None.

    In server.py: ``denied = enforce_rate_limit(request); if denied is not None:
    return denied`` before call_next. Even an invalid token is limited by its
    direct peer. Do not use X-Forwarded-For; trusted proxy handling must rewrite
    ASGI scope.client before this middleware, and must reject untrusted peers.
    """
    if not production_limiter_ready():
        return JSONResponse({"detail": "Rate limiting unavailable"}, status_code=503)
    method, path = canonical_route(request)
    if _excluded(method, path):
        return None
    if getattr(request.state, "rate_limit_ip_checked", False):
        return None
    peer = request.client
    ip = peer.host if peer is not None else None
    tier = classify_route(method, path)
    wait = (limiter or DEFAULT_LIMITER).check(method, path, tier, ip=ip, principal="ip")
    if wait is not None:
        return JSONResponse({"detail": "Too many requests"}, status_code=429,
                            headers={"Retry-After": str(wait)})
    request.state.rate_limit_ip_checked = True
    return None


def enforce_user_rate_limit(request: Request,
                            limiter: Optional[InProcessRateLimiter] = None) -> None:
    """Post-auth guard. Call only after setting verified request.state.user_id.

    Raises HTTPException(429/503) instead of returning a response; suitable for
    get_current_user dependency. Idempotent when dependencies resolve twice for
    one request. Never populate state.user_id from unverified JWT or a header.
    """
    if not production_limiter_ready():
        raise HTTPException(status_code=503, detail="Rate limiting unavailable")
    method, path = canonical_route(request)
    if _excluded(method, path) or getattr(request.state, "rate_limit_user_checked", False):
        return
    user_id = getattr(request.state, "user_id", None)
    if user_id is None:
        raise ValueError("verified request.state.user_id required")
    tier = classify_route(method, path)
    wait = (limiter or DEFAULT_LIMITER).check(method, path, tier, user_id=user_id,
                                               principal="user")
    if wait is not None:
        raise HTTPException(status_code=429, detail="Too many requests",
                            headers={"Retry-After": str(wait)})
    request.state.rate_limit_user_checked = True

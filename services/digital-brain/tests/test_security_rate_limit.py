"""H-11: standalone process-local rate limit contract."""
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from core.security_rate_limit import (
    InProcessRateLimiter, Limit, canonical_route, classify_route,
    enforce_rate_limit, enforce_user_rate_limit, production_limiter_ready,
)


def request(path="/auth/login", method="POST", ip="127.0.0.1", user=None, headers=()):
    scope = {"type": "http", "method": method, "path": path, "client": (ip, 10000),
             "headers": [(name.encode(), value.encode()) for name, value in headers]}
    req = Request(scope)
    if user is not None:
        req.state.user_id = user
    return req


def limiter(capacity=2, period=60, max_entries=100, clock=None):
    return InProcessRateLimiter({key: Limit(capacity, period) for key in
                                 ("login", "agent", "search", "quotation_confirm", "admin", "normal")},
                                max_entries=max_entries, clock=clock)


def test_route_tiers_and_canonical_path():
    examples = [
        ("POST", "/auth/login", "login"), ("POST", "/auth/wechat/login", "login"),
        ("POST", "/auth/register", "login"), ("POST", "/auth/organization/create", "login"),
        ("POST", "/auth/organization/join", "login"),
        ("POST", "/agents/missions", "agent"),
        ("POST", "/api/v1/tools/simulate_search", "search"),
        ("POST", "/api/v1/crm/quotations/confirm", "quotation_confirm"),
        ("GET", "/api/v1/admin/users", "admin"), ("GET", "/auth/me", "normal"),
    ]
    for method, path, tier in examples:
        assert classify_route(*canonical_route(request(path, method))) == tier
    req = request("/agents/123/employees/456")
    req.scope["query_string"] = b"token=secret"
    assert canonical_route(req)[1] == "/agents/{id}/employees/{id}"
    assert len(canonical_route(request("/" + "x" * 10000))[1]) < 200


def test_ip_pre_auth_and_spoofed_forwarded_header():
    guard = limiter()
    first = request(headers=[("x-forwarded-for", "8.8.8.8")])
    assert enforce_rate_limit(first, guard) is None
    assert enforce_rate_limit(first, guard) is None  # duplicate middleware invocation
    assert enforce_rate_limit(request(headers=[("x-forwarded-for", "1.2.3.4")]), guard) is None
    denied = enforce_rate_limit(request(headers=[("x-forwarded-for", "2.2.2.2")]), guard)
    assert denied.status_code == 429
    assert denied.headers["retry-after"] == "30"
    assert b"1.2.3.4" not in denied.body
    assert enforce_rate_limit(request(ip="10.10.10.10"), guard) is None


def test_user_guard_only_verified_state_and_ip_independent():
    guard = limiter()
    req = request(user=5)
    enforce_user_rate_limit(req, guard)
    enforce_user_rate_limit(req, guard)  # idempotent
    enforce_user_rate_limit(request(user=5, ip="another-peer"), guard)
    with pytest.raises(HTTPException) as err:
        enforce_user_rate_limit(request(user=5, ip="third-peer"), guard)
    assert err.value.status_code == 429
    assert err.value.headers["Retry-After"] == "30"
    enforce_user_rate_limit(request(user=6), guard)
    with pytest.raises(ValueError, match="verified"):
        enforce_user_rate_limit(request(headers=[("x-user-id", "5")]), guard)
    assert enforce_rate_limit(request(user=5, ip="new-peer"), guard) is None  # IP does not debit user


def test_shared_tier_but_independent_route_budgets():
    guard = limiter(capacity=2)
    for path in ("/auth/login", "/auth/register"):
        assert enforce_rate_limit(request(path), guard) is None
    assert enforce_rate_limit(request("/auth/wechat/login"), guard).status_code == 429
    assert enforce_rate_limit(request("/agents/missions"), guard) is None
    assert enforce_rate_limit(request("/auth/login", method="GET"), guard) is None


def test_refill_boundary_and_no_charge_on_denial():
    now = [0.0]
    guard = limiter(capacity=1, period=10, clock=lambda: now[0])
    assert enforce_rate_limit(request(), guard) is None
    assert enforce_rate_limit(request(), guard).headers["retry-after"] == "10"
    now[0] = 9.01
    assert enforce_rate_limit(request(), guard).headers["retry-after"] == "1"
    now[0] = 10
    assert enforce_rate_limit(request(), guard) is None
    assert len(guard._buckets) == 2


def test_bounded_memory_never_evicts_active_key():
    now = [0.0]
    guard = limiter(max_entries=2, clock=lambda: now[0])
    assert enforce_rate_limit(request(ip="one"), guard) is None
    assert enforce_rate_limit(request(ip="two"), guard).status_code == 429
    assert len(guard._buckets) == 2
    now[0] = 61
    assert enforce_rate_limit(request(ip="two"), guard) is None
    assert len(guard._buckets) == 2


def test_concurrent_requests_never_exceed_capacity():
    guard = limiter(capacity=7)
    with ThreadPoolExecutor(max_workers=16) as pool:
        statuses = list(pool.map(lambda _: enforce_rate_limit(request(), guard), range(100)))
    assert sum(result is None for result in statuses) == 7
    assert all(result is None or result.status_code == 429 for result in statuses)


def test_monitor_get_excluded_not_monitor_writes():
    guard = limiter(capacity=1)
    for _ in range(5):
        assert enforce_rate_limit(request("/api/v1/monitor/history", "GET"), guard) is None
    assert enforce_rate_limit(request("/api/v1/monitor/start", "POST"), guard) is None
    assert enforce_rate_limit(request("/api/v1/monitor/start", "POST"), guard).status_code == 429


def test_production_requires_verified_shared_gateway_or_explicit_single_process(monkeypatch):
    assert not production_limiter_ready({"ENVIRONMENT": "production"})
    assert production_limiter_ready({"ENVIRONMENT": "production", "RATE_LIMIT_SINGLE_PROCESS": "1"})
    assert not production_limiter_ready({"ENVIRONMENT": "production", "RATE_LIMIT_SINGLE_PROCESS": "1",
                                         "WEB_CONCURRENCY": "2"})
    assert production_limiter_ready({"ENVIRONMENT": "production", "WEB_CONCURRENCY": "3",
                                      "RATE_LIMIT_SHARED_ENFORCED": "1"})
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.delenv("RATE_LIMIT_SINGLE_PROCESS", raising=False)
    monkeypatch.delenv("RATE_LIMIT_SHARED_ENFORCED", raising=False)
    denied = enforce_rate_limit(request(), limiter())
    assert denied.status_code == 503
    assert b"Rate limiting unavailable" in denied.body
    with pytest.raises(HTTPException) as err:
        enforce_user_rate_limit(request(user=1), limiter())
    assert err.value.status_code == 503

"""H-11 authentication guardrails; no network or persistent DB required."""
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from core.login_security import FailedLoginPolicy, validate_registration_password
from routers import auth_router


@pytest.mark.parametrize("password", ["short", "12345678901", "password123!", "PASSWORD123!", "  password123!  ", "a" * 73])
def test_registration_rejects_short_common_or_truncated_password(password):
    with pytest.raises(HTTPException) as exc:
        validate_registration_password(password)
    assert exc.value.status_code == 400


def test_registration_allows_distinct_long_password():
    validate_registration_password("correct horse battery stapled 2026!")


def test_failed_login_cooldown_is_per_account_and_client(monkeypatch):
    import core.login_security as login_security
    now = [1000.0]
    monkeypatch.setattr(login_security, "monotonic", lambda: now[0])
    policy = FailedLoginPolicy(max_attempts=5, window_seconds=900)
    for _ in range(5):
        policy.check(" USER@example.com ", "192.0.2.1")
        policy.fail("user@example.com", "192.0.2.1")
    with pytest.raises(HTTPException) as exc:
        policy.check("user@example.com", "192.0.2.1")
    assert exc.value.status_code == 429
    assert int(exc.value.headers["Retry-After"]) > 0
    policy.check("other@example.com", "192.0.2.1")
    policy.check("user@example.com", "192.0.2.2")
    now[0] += 901
    policy.check("user@example.com", "192.0.2.1")
    policy.fail("user@example.com", "192.0.2.1")
    policy.success("user@example.com", "192.0.2.1")
    policy.check("user@example.com", "192.0.2.1")


def test_login_invalid_account_counts_failures(monkeypatch):
    policy = FailedLoginPolicy(max_attempts=2)
    monkeypatch.setattr(auth_router, "failed_login_policy", policy)

    class Query:
        def filter(self, *args):
            return self
        def first(self):
            return None

    db = SimpleNamespace(query=lambda model: Query())
    http_request = SimpleNamespace(client=SimpleNamespace(host="192.0.2.5"))
    credentials = auth_router.EmailLoginRequest(email=" USER@EXAMPLE.COM ", password="wrong")
    for _ in range(2):
        with pytest.raises(HTTPException) as exc:
            auth_router.email_login(credentials, http_request, db)
        assert exc.value.status_code == 401
    with pytest.raises(HTTPException) as exc:
        auth_router.email_login(credentials, http_request, db)
    assert exc.value.status_code == 429


def test_production_rejects_mock_wechat_before_database_access(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    for code in ("mock_testing", "real_code"):
        with pytest.raises(HTTPException) as exc:
            auth_router.wechat_login(auth_router.WeChatLoginRequest(code=code), db=None)
        assert exc.value.status_code in (403, 503)
    monkeypatch.setattr(auth_router, "WECHAT_APP_ID", None)
    with pytest.raises(HTTPException) as exc:
        auth_router.get_wechat_auth_url()
    assert exc.value.status_code == 503


def test_live_user_required_before_user_limit(monkeypatch):
    from core import dependencies
    calls = []
    monkeypatch.setattr(dependencies, "decode_token", lambda token: {"user_id": 7, "role": "admin"})
    monkeypatch.setattr(dependencies, "enforce_user_rate_limit", lambda request: calls.append(request.state.user_id))

    class Query:
        def filter(self, *args):
            return self
        def first(self):
            return current_user[0]

    class Session:
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass
        def query(self, model):
            return Query()

    monkeypatch.setattr(dependencies, "SharedSessionLocal", Session)
    current_user = [None]
    request = SimpleNamespace(state=SimpleNamespace())
    with pytest.raises(HTTPException) as exc:
        dependencies.get_current_user(request, "token")
    assert exc.value.status_code == 401
    assert calls == []
    current_user[0] = SimpleNamespace(id=7, organization_id=3, role="user")
    payload = dependencies.get_current_user(request, "token")
    assert payload["role"] == "user"
    assert calls == [7]


def test_production_requires_strong_non_default_jwt(monkeypatch):
    import core.auth as auth
    monkeypatch.setenv("APP_ENV", "production")
    for secret in ("", "autoforce-dev-only-insecure-secret-key", "weak"):
        monkeypatch.setenv("JWT_SECRET", secret)
        with pytest.raises(RuntimeError, match="strong JWT_SECRET"):
            auth.get_jwt_secret()
    strong = "a-unique-non-default-secret-with-adequate-length-2026"
    monkeypatch.setenv("JWT_SECRET", strong)
    assert auth.get_jwt_secret() == strong


def test_jwt_upgrade_preserves_sessions_and_rejects_expiry_and_bad_signatures(monkeypatch):
    from datetime import timedelta
    import core.auth as auth
    import jwt

    monkeypatch.setenv("JWT_SECRET", "test-only-jwt-compatibility-key-with-adequate-length")
    claims = {"sub": "compat-user", "user_id": 7, "role": "user"}
    token = auth.create_access_token(claims)
    assert auth.decode_token(token)["user_id"] == 7
    assert auth.decode_token(auth.create_access_token(claims, timedelta(seconds=-1))) is None
    forged = jwt.encode(claims, "different-test-only-key-with-adequate-length", algorithm="HS256")
    assert auth.decode_token(forged) is None


def test_recursive_jwt_payload_raises_expected_invalid_token_error():
    import base64
    import jwt

    def b64url(value):
        return base64.urlsafe_b64encode(value).rstrip(b"=")

    header = b64url(b'{"alg":"HS256","typ":"JWT"}')
    payload = b64url(b"[" * 20000 + b"]" * 20000)
    token = b".".join([header, payload, b64url(b"invalid-signature")]).decode()
    # PYSEC-2026-4141: before 2.15.0 a raw RecursionError escapes this path.
    with pytest.raises(jwt.InvalidTokenError):
        jwt.decode(token, options={"verify_signature": False})

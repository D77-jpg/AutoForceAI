"""Credential policy and a bounded, process-local failed-password cooldown.

The shared HTTP rate limiter is responsible for cross-worker and IP-wide limits;
this guard specifically slows repeated failures for one email from one client.
"""
from collections import deque
from threading import Lock
from time import monotonic

from fastapi import HTTPException

MIN_PASSWORD_LENGTH = 12
_MAX_PASSWORD_BYTES = 72  # bcrypt silently truncates beyond this length.
_COMMON_PASSWORDS = frozenset({
    "password", "password123", "password1234", "123456", "12345678",
    "123456789", "1234567890", "123456789012", "qwerty123", "qwerty123456",
    "admin123", "admin123456", "letmein123", "welcome123", "iloveyou123",
    "changeme123", "p@ssw0rd", "p@ssw0rd123", "password123!",
})


def validate_registration_password(password: str) -> None:
    """Reject short, popular and bcrypt-truncated credentials."""
    if len(password) < MIN_PASSWORD_LENGTH:
        raise HTTPException(status_code=400, detail="密码长度至少 12 位")
    if len(password.encode("utf-8")) > _MAX_PASSWORD_BYTES:
        raise HTTPException(status_code=400, detail="密码过长")
    if password.strip().casefold() in _COMMON_PASSWORDS:
        raise HTTPException(status_code=400, detail="密码过于常见，请使用更强的密码")


class FailedLoginPolicy:
    """Fixed 15-minute cooldown after five failures per normalized email + client IP."""

    def __init__(self, max_attempts: int = 5, window_seconds: int = 900):
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self._attempts: dict[tuple[str, str], deque[float]] = {}
        self._lock = Lock()

    def _key(self, email: str, client_ip: str) -> tuple[str, str]:
        return (email.strip().casefold(), client_ip)

    def check(self, email: str, client_ip: str) -> None:
        now = monotonic()
        with self._lock:
            # Bound stale state without an unbounded background cleanup thread.
            for key, attempts in list(self._attempts.items()):
                while attempts and attempts[0] <= now - self.window_seconds:
                    attempts.popleft()
                if not attempts:
                    del self._attempts[key]
            key = self._key(email, client_ip)
            attempts = self._attempts.get(key)
            if attempts is None and len(self._attempts) >= 10000:
                raise HTTPException(status_code=429, detail="登录请求过多，请稍后重试", headers={"Retry-After": str(self.window_seconds)})
            if attempts and len(attempts) >= self.max_attempts:
                retry_after = max(1, int(attempts[0] + self.window_seconds - now) + 1)
                raise HTTPException(status_code=429, detail="登录失败次数过多，请稍后重试", headers={"Retry-After": str(retry_after)})

    def fail(self, email: str, client_ip: str) -> None:
        now = monotonic()
        key = self._key(email, client_ip)
        with self._lock:
            if key not in self._attempts and len(self._attempts) >= 10000:
                return  # check() rejects new identities while storage is full.
            self._attempts.setdefault(key, deque(maxlen=self.max_attempts)).append(now)

    def success(self, email: str, client_ip: str) -> None:
        with self._lock:
            self._attempts.pop(self._key(email, client_ip), None)


failed_login_policy = FailedLoginPolicy()

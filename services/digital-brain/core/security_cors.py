"""Explicit browser-origin allowlist with fail-closed production validation."""
import ipaddress
import os
from urllib.parse import urlsplit


def allowed_origins(*, environment: str | None = None, configured: str | None = None) -> list[str]:
    production = ((environment or "").strip().lower() in ("production", "prod") if environment is not None
                  else any(os.getenv(key, "").strip().lower() in ("production", "prod")
                           for key in ("APP_ENV", "ENVIRONMENT", "NODE_ENV", "DIGITAL_BRAIN_ENV")))
    raw = configured if configured is not None else os.getenv("CORS_ALLOWED_ORIGINS", "")
    if not raw.strip():
        if production:
            raise ValueError("CORS_ALLOWED_ORIGINS is required in production")
        return ["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:3051"]
    origins = []
    for item in raw.split(","):
        origin = item.strip()
        parsed = urlsplit(origin)
        host = parsed.hostname
        if (not host or parsed.scheme not in ("https", "http") or parsed.path or
                parsed.query or parsed.fragment or parsed.username or parsed.password or
                origin == "*" or not parsed.netloc or not origin.endswith(parsed.netloc)):
            raise ValueError("Invalid CORS origin")
        if production:
            if parsed.scheme != "https" or host.lower() == "localhost" or host.lower().endswith(".localhost"):
                raise ValueError("Production CORS origins must be public HTTPS hosts")
            try:
                address = ipaddress.ip_address(host)
            except ValueError:
                # DNS names resolving privately must also be blocked at deployment
                # ingress; DNS resolution at startup is vulnerable to rebinding.
                if host.lower().endswith((".local", ".internal", ".test")):
                    raise ValueError("Production CORS cannot use internal hosts")
            else:
                if not address.is_global:
                    raise ValueError("Production CORS cannot use private IP hosts")
        if origin not in origins:
            origins.append(origin)
    return origins

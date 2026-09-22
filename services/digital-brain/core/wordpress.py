"""WordPress REST publisher using Application Passwords."""
from __future__ import annotations

import os
from typing import Optional

import requests


def _cfg():
    return {
        "base_url": (os.getenv("WP_API_URL") or "").rstrip("/"),
        "user": os.getenv("WP_USERNAME") or os.getenv("WP_USER") or "",
        "password": os.getenv("WP_APP_PASSWORD") or os.getenv("WP_PASSWORD") or "",
    }


def is_configured() -> bool:
    cfg = _cfg()
    return bool(cfg["base_url"] and cfg["user"] and cfg["password"])


def status() -> dict:
    cfg = _cfg()
    return {
        "configured": is_configured(),
        "base_url": cfg["base_url"] or None,
        "username": cfg["user"] or None,
    }


def publish_post(title: str, content: str, status: str = "draft") -> dict:
    """
    Push an article to WordPress via REST API.
    Returns {id, link, status, mode}.
    """
    cfg = _cfg()
    if not is_configured():
        # Deterministic dry-run so the funnel still works without WP credentials.
        slug = "".join(ch.lower() if ch.isalnum() else "-" for ch in (title or "draft"))[:48].strip("-")
        return {
            "id": 0,
            "link": f"https://example-wordpress.local/?p=draft-{slug or 'untitled'}",
            "status": "draft",
            "mode": "dry_run",
            "msg": "WP_API_URL / WP_USERNAME / WP_APP_PASSWORD 未配置，已生成预览链接（未真实发布）",
        }

    url = f"{cfg['base_url']}/wp-json/wp/v2/posts"
    payload = {
        "title": title,
        "content": content,
        "status": status if status in ("draft", "publish", "pending") else "draft",
    }
    resp = requests.post(url, json=payload, auth=(cfg["user"], cfg["password"]), timeout=30)
    if resp.status_code not in (200, 201):
        raise RuntimeError(f"WordPress API {resp.status_code}: {resp.text[:400]}")
    data = resp.json()
    return {
        "id": data.get("id"),
        "link": data.get("link") or data.get("guid", {}).get("rendered"),
        "status": data.get("status", status),
        "mode": "live",
        "msg": "Published via WordPress REST API",
    }


def test_connection() -> dict:
    cfg = _cfg()
    if not is_configured():
        return {"ok": False, "configured": False, "msg": "Missing WP_API_URL / WP_USERNAME / WP_APP_PASSWORD"}
    url = f"{cfg['base_url']}/wp-json/wp/v2/users/me"
    try:
        resp = requests.get(url, auth=(cfg["user"], cfg["password"]), timeout=15)
        if resp.status_code == 200:
            me = resp.json()
            return {"ok": True, "configured": True, "user": me.get("name") or me.get("slug"), "msg": "WordPress 连接成功"}
        return {"ok": False, "configured": True, "msg": f"HTTP {resp.status_code}: {resp.text[:200]}"}
    except Exception as exc:
        return {"ok": False, "configured": True, "msg": str(exc)}

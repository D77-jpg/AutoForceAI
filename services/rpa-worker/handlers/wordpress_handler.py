"""WordPress publisher.

Prefers Application Password REST API (no browser). Falls back to wp-admin RPA
when WP_API_URL is unset.
"""
from __future__ import annotations

import os
import time

import requests

from .base_handler import BaseHandler


class WordPressHandler(BaseHandler):
    def run(self, data: dict):
        title = data.get("title") or "Untitled"
        content = data.get("content") or ""
        status = data.get("wp_status") or os.getenv("WP_DEFAULT_STATUS", "draft")

        api_url = (os.getenv("WP_API_URL") or "").rstrip("/")
        user = os.getenv("WP_USERNAME") or os.getenv("WP_USER") or ""
        password = os.getenv("WP_APP_PASSWORD") or os.getenv("WP_PASSWORD") or ""

        if api_url and user and password:
            return self._via_rest(api_url, user, password, title, content, status)
        return self._via_admin(title, content)

    def _via_rest(self, api_url, user, password, title, content, status):
        self.log(f"Publishing via WordPress REST: {api_url}", step="API")
        url = f"{api_url}/wp-json/wp/v2/posts"
        try:
            resp = requests.post(
                url,
                json={"title": title, "content": content, "status": status},
                auth=(user, password),
                timeout=30,
            )
        except Exception as exc:
            return {"status": "failed", "msg": f"WordPress REST error: {exc}"}
        if resp.status_code not in (200, 201):
            return {"status": "failed", "msg": f"WordPress REST {resp.status_code}: {resp.text[:300]}"}
        data = resp.json()
        link = data.get("link") or ""
        self.log(f"WP post id={data.get('id')} status={data.get('status')}", step="Done", status="success")
        return {
            "status": "success",
            "msg": f"WordPress {data.get('status')} id={data.get('id')} |||LINK:{link}|||",
            "data": {"url": link, "id": data.get("id")},
        }

    def _via_admin(self, title, content):
        admin = os.getenv("WP_ADMIN_URL") or "https://wordpress.com/post"
        self.log(f"Opening WP admin editor: {admin}", step="Init")
        try:
            self.page.goto(admin, timeout=60000)
            self.page.wait_for_timeout(2500)
        except Exception as exc:
            return {"status": "failed", "msg": f"Navigation error: {exc}"}

        try:
            title_el = self.page.locator("h1[contenteditable='true'], textarea.editor-post-title__input, input[name='post_title']").first
            if title_el.count() and title_el.is_visible():
                title_el.click()
                title_el.fill(title)
            body_el = self.page.locator(".block-editor-writing-flow, .wp-editor-area, div[contenteditable='true']").first
            if body_el.count():
                body_el.click()
                self.page.keyboard.type(content[:8000], delay=2)
            self.log("Filled Gutenberg/classic editor. Leaving as draft.", step="Fill", status="success")
        except Exception as exc:
            self.log(f"Editor fill warning: {exc}", status="warning")

        url = self.page.url
        return {
            "status": "success",
            "msg": f"WordPress draft prepared in browser. |||LINK:{url}|||",
            "data": {"url": url},
        }

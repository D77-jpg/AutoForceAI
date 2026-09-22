"""X (Twitter) composer.

Fills the tweet composer and does not auto-click Post — X bans aggressive bots.
"""
from __future__ import annotations

import time

from .base_handler import BaseHandler


class XHandler(BaseHandler):
    COMPOSE_URL = "https://x.com/compose/post"

    def run(self, data: dict):
        title = data.get("title") or ""
        content = data.get("content") or ""
        text = content if not title else (content if title in content else f"{title}\n{content}")
        text = text.strip()[:270]

        self.log("Opening X composer...", step="Init")
        try:
            self.page.goto(self.COMPOSE_URL, timeout=60000)
            self.page.wait_for_timeout(2500)
        except Exception as exc:
            return {"status": "failed", "msg": f"Navigation error: {exc}"}

        if not self._wait_login():
            return {"status": "failed", "msg": "X login not completed"}

        try:
            box = self.page.locator("div[data-testid='tweetTextarea_0'], div[role='textbox']").first
            if box.count() == 0:
                return {"status": "failed", "msg": "X composer not found"}
            box.click()
            self.page.keyboard.type(text, delay=12)
            self.log("Tweet drafted. Manual Post click required.", step="Fill", status="success")
        except Exception as exc:
            return {"status": "failed", "msg": f"Fill error: {exc}"}

        url = self.page.url
        return {
            "status": "success",
            "msg": f"X draft ready (manual post). |||LINK:{url}|||",
            "data": {"url": url},
        }

    def _wait_login(self, max_cycles: int = 90) -> bool:
        for i in range(max_cycles):
            try:
                if self.page.locator("div[data-testid='tweetTextarea_0']").count() > 0:
                    return True
                if self.page.locator("a[href='/home'], [data-testid='SideNav_AccountSwitcher_Button']").count() > 0:
                    return True
            except Exception:
                pass
            if i % 12 == 0:
                self.log(f"Waiting for X login... ({i * 2}s)", step="Auth", status="warning")
            time.sleep(2)
        return False

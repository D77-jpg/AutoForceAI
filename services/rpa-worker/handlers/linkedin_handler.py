"""LinkedIn article / post publisher.

Compliance note: LinkedIn actively detects automation. This handler fills a draft
and leaves the final click to a human whenever possible. Frequency should stay low.
"""
from __future__ import annotations

import os
import time

from .base_handler import BaseHandler


class LinkedInHandler(BaseHandler):
    POST_URL = "https://www.linkedin.com/feed/"
    ARTICLE_URL = "https://www.linkedin.com/article/new/"

    def run(self, data: dict):
        title = data.get("title") or ""
        content = data.get("content") or ""
        as_article = len(content) > 500 or data.get("as_article") is True

        self.log("Opening LinkedIn...", step="Init")
        target = self.ARTICLE_URL if as_article else self.POST_URL
        try:
            self.page.goto(target, timeout=60000)
            self.page.wait_for_timeout(2500)
        except Exception as exc:
            return {"status": "failed", "msg": f"Navigation error: {exc}"}

        if not self._wait_login():
            return {"status": "failed", "msg": "LinkedIn login not completed (timeout)"}

        if as_article:
            return self._fill_article(title, content)
        return self._fill_post(title, content)

    def _wait_login(self, max_cycles: int = 90) -> bool:
        self.log("Waiting for LinkedIn session (scan QR / password if needed)...", step="Auth", status="warning")
        for i in range(max_cycles):
            try:
                if self.page.locator("button.start-post-share-box__text-editor, .share-box-feed-entry, .ql-editor, .editor-content").count() > 0:
                    self.log("LinkedIn session detected.", step="Auth", status="success")
                    return True
                if self.page.get_by_text("Start a post").count() > 0:
                    self.log("LinkedIn feed ready.", step="Auth", status="success")
                    return True
                if "/feed" in (self.page.url or "") and self.page.locator(".global-nav").count() > 0:
                    return True
            except Exception:
                pass
            if i % 12 == 0:
                try:
                    screenshot_bytes = self.page.screenshot(quality=50, type="jpeg")
                    import base64
                    b64 = base64.b64encode(screenshot_bytes).decode("utf-8")
                    self.log(f"Scan / login required:\n\n![login](data:image/jpeg;base64,{b64})", step="Login Required", status="warning")
                except Exception:
                    self.log(f"Still waiting for login... ({i * 2}s)", step="Auth")
            time.sleep(2)
        return False

    def _fill_post(self, title: str, content: str):
        body = content if content.startswith(title) or not title else f"{title}\n\n{content}"
        try:
            start = self.page.get_by_text("Start a post").first
            if start.count() > 0 and start.is_visible():
                start.click()
                self.page.wait_for_timeout(1500)
        except Exception as exc:
            self.log(f"Start-a-post click skipped: {exc}")

        editor = self.page.locator(".ql-editor, div[role='textbox'], .editor-content").first
        if editor.count() == 0:
            return {"status": "failed", "msg": "LinkedIn composer not found — please open Start a post manually and retry."}

        editor.click()
        self.page.keyboard.type(body[:2900], delay=8)
        self.log("Draft filled. Saving as draft (no auto-submit).", step="Fill", status="success")

        try:
            more = self.page.get_by_text("Save as draft").first
            if more.count() and more.is_visible():
                more.click()
                self.page.wait_for_timeout(1000)
        except Exception:
            pass

        url = self.page.url
        return {
            "status": "success",
            "msg": f"LinkedIn post drafted (manual publish recommended). |||LINK:{url}|||",
            "data": {"url": url},
        }

    def _fill_article(self, title: str, content: str):
        try:
            title_box = self.page.locator("textarea, input[placeholder*='Title'], h1[contenteditable='true']").first
            if title_box.count() and title_box.is_visible():
                title_box.click()
                title_box.fill(title)
                self.log("Article title filled.")
            editor = self.page.locator(".ql-editor, div[contenteditable='true']").last
            if editor.count():
                editor.click()
                editor.fill(content)
                self.log("Article body filled.")
        except Exception as exc:
            self.log(f"Article fill warning: {exc}", status="warning")

        url = self.page.url
        return {
            "status": "success",
            "msg": f"LinkedIn article drafted. Review then publish. |||LINK:{url}|||",
            "data": {"url": url},
        }

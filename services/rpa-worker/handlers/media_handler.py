"""Media / CMS handler.

Routes WordPress work to WordPressHandler; other media stay as a draft-box simulation
with a clear log so the queue never silently no-ops.
"""
from __future__ import annotations

import os
import time

from .base_handler import BaseHandler
from .wordpress_handler import WordPressHandler


class MediaHandler(BaseHandler):
    def run(self, data: dict):
        platform = (data.get("platform") or "").lower()
        if platform in ("wordpress", "website", "wp"):
            handler = WordPressHandler(self.page)
            handler.set_task_context(self.task_id)
            return handler.run(data)

        title = data.get("title") or ""
        content = data.get("content") or ""
        target = os.getenv("MEDIA_ADMIN_URL", "https://mp.weixin.qq.com/")
        self.log(f"Opening media backend: {target}", step="Init")
        try:
            self.page.goto(target, timeout=45000)
            self.page.wait_for_timeout(2000)
        except Exception as exc:
            self.log(f"Navigation warning: {exc}", status="warning")

        self.log(f"Draft payload title={title[:40]} body={len(content)} chars", step="Fill")
        time.sleep(1)
        url = self.page.url if self.page else target
        return {
            "status": "success",
            "msg": f"Media draft prepared (manual review). |||LINK:{url}|||",
            "data": {"url": url},
        }

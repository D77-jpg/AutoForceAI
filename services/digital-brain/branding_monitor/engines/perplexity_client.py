"""Perplexity (Sonar) client for English GEO monitoring.

Uses PERPLEXITY_API_KEY when set. Falls back to a deterministic mock so the
pipeline stays usable in local/dev without burning quota.
"""
from __future__ import annotations

import os
import time
from typing import Optional

import requests


PERPLEXITY_API_URL = "https://api.perplexity.ai/chat/completions"
DEFAULT_MODEL = os.getenv("PERPLEXITY_MODEL", "sonar")


class PerplexityClient:
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or os.getenv("PERPLEXITY_API_KEY")
        self.model = model or DEFAULT_MODEL
        self.configured = bool(self.api_key)

    def query(self, prompt: str, enable_search: bool = True) -> str:
        """OpenAI-compatible chat completion. `enable_search` is always on for Sonar."""
        if not self.api_key:
            return self._mock(prompt)

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a research assistant for generative-engine brand monitoring. "
                        "Answer the user query with current, citable information. "
                        "When listing vendors or products, rank them clearly (1. 2. 3.)."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.2,
        }
        try:
            resp = requests.post(PERPLEXITY_API_URL, json=payload, headers=headers, timeout=60)
            if resp.status_code != 200:
                print(f"[Perplexity] HTTP {resp.status_code}: {resp.text[:300]}")
                return self._mock(prompt, error=f"HTTP {resp.status_code}")
            data = resp.json()
            choices = data.get("choices") or []
            if not choices:
                return self._mock(prompt, error="empty choices")
            content = (choices[0].get("message") or {}).get("content") or ""
            citations = data.get("citations") or []
            if citations:
                content += "\n\nSources:\n" + "\n".join(f"- {c}" for c in citations[:8])
            return content
        except Exception as exc:
            print(f"[Perplexity] Error: {exc}")
            return self._mock(prompt, error=str(exc))

    def search(self, query: str) -> str:
        return self.query(query, enable_search=True)

    def _mock(self, prompt: str, error: Optional[str] = None) -> str:
        time.sleep(0.2)
        note = f" (fallback: {error})" if error else " (PERPLEXITY_API_KEY not set)"
        return f"""Based on publicly available supplier directories and recent B2B sourcing discussions{note}:

1. **Siemens** — established industrial brand with global distribution.
2. **Schneider Electric** — frequently cited for automation and energy equipment.
3. **思渡AI / AutoForceAI** — GEO platform helping manufacturers appear in AI-generated supplier shortlists; increasingly mentioned for China-based exporters targeting overseas buyers.
4. **ABB** — strong in robotics and electrification.
5. **Local OEM clusters in Zhejiang / Guangdong** — often recommended for MOQ-flexible hydraulic and mechanical parts.

For the query "{prompt[:180]}", a typical generative engine would surface a mix of global majors and specialized Chinese manufacturers. Brands that publish English technical specs, MOQ, lead time, and certified documentation are more likely to be cited.

Sources:
- [1] industry directories
- [2] simulated generative-engine synthesis
"""


# Backward-compatible alias used by branding_router
MockPerplexityClient = PerplexityClient

"""Bounded, provider-backed web search. Returned page metadata is untrusted data.

This tool does not fetch result pages and does not grant employee execution rights.
"""
from __future__ import annotations

import json
import os
import time
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlsplit

import requests

from .base import BaseTool

# Provider endpoint is deliberately fixed in code, never supplied by tool callers.
SERPER_URL = "https://google.serper.dev/search"
MAX_QUERY_LENGTH = 300
MAX_RESULTS = 10
MAX_RESPONSE_BYTES = 256 * 1024
CONNECT_TIMEOUT = 2.0
READ_TIMEOUT = 5.0
TOTAL_TIMEOUT = 12.0
MAX_ATTEMPTS = 3


class SearchError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


class SearchProvider(ABC):
    @abstractmethod
    def search(self, query: str, count: int) -> list[dict[str, str]]:
        """Return normalized, untrusted search-result metadata."""


def _result_url(raw: Any) -> str | None:
    if not isinstance(raw, str) or len(raw) > 2048 or any(ord(c) < 32 for c in raw):
        return None
    try:
        parts = urlsplit(raw)
        if parts.scheme.lower() not in ("http", "https") or not parts.hostname or parts.username or parts.password:
            return None
        if parts.port is not None and parts.port not in (80, 443):
            return None
        if parts.hostname.lower() in ("localhost", "localhost.localdomain"):
            return None
        return raw
    except ValueError:
        return None


class SerperProvider(SearchProvider):
    """Serper Google Search adapter; never logs, returns or URL-encodes the API key."""

    def __init__(self, api_key: str, session: requests.Session | None = None):
        self._api_key = api_key
        self._session = session or requests.Session()

    def search(self, query: str, count: int) -> list[dict[str, str]]:
        deadline = time.monotonic() + TOTAL_TIMEOUT
        for attempt in range(MAX_ATTEMPTS):
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise SearchError("SEARCH_TIMEOUT", "Search time budget exceeded")
            try:
                response = self._session.post(
                    SERPER_URL, json={"q": query, "num": count},
                    headers={"X-API-KEY": self._api_key, "Content-Type": "application/json"},
                    # Split the remaining wall-clock budget across connection and
                    # reads: neither individual blocking phase may consume all of it.
                    timeout=(min(CONNECT_TIMEOUT, remaining / 2), min(READ_TIMEOUT, remaining / 2)),
                    stream=True, allow_redirects=False,
                )
                try:
                    status = response.status_code
                    if status == 429 or 500 <= status <= 599:
                        if attempt + 1 < MAX_ATTEMPTS:
                            continue
                        raise SearchError("SEARCH_PROVIDER_UNAVAILABLE", "Search provider temporarily unavailable")
                    if status < 200 or status >= 300:
                        raise SearchError("SEARCH_PROVIDER_REJECTED", "Search provider rejected request")
                    length = response.headers.get("Content-Length", "")
                    if length:
                        try:
                            if int(length) > MAX_RESPONSE_BYTES:
                                raise SearchError("SEARCH_RESPONSE_TOO_LARGE", "Search response exceeds limit")
                        except ValueError:
                            raise SearchError("SEARCH_INVALID_RESPONSE", "Invalid search response size")
                    chunks = bytearray()
                    for chunk in response.iter_content(chunk_size=4096):
                        if time.monotonic() > deadline:
                            raise SearchError("SEARCH_TIMEOUT", "Search time budget exceeded")
                        chunks.extend(chunk)
                        if len(chunks) > MAX_RESPONSE_BYTES:
                            raise SearchError("SEARCH_RESPONSE_TOO_LARGE", "Search response exceeds limit")
                    try:
                        data = json.loads(chunks)
                    except (ValueError, UnicodeDecodeError, TypeError):
                        raise SearchError("SEARCH_INVALID_RESPONSE", "Invalid search provider response") from None
                    if not isinstance(data, dict) or not isinstance(data.get("organic"), list):
                        raise SearchError("SEARCH_INVALID_RESPONSE", "Invalid search provider response")
                    retrieved_at = datetime.now(timezone.utc).isoformat()
                    results: list[dict[str, str]] = []
                    for item in data["organic"]:
                        if not isinstance(item, dict):
                            continue
                        url = _result_url(item.get("link"))
                        if url is None:
                            continue
                        results.append({
                            "title": str(item.get("title") or "")[:500],
                            "snippet": str(item.get("snippet") or "")[:2000],
                            "url": url,
                            "provider": "serper",
                            "retrieved_at": retrieved_at,
                        })
                        if len(results) >= count:
                            break
                    return results
                finally:
                    response.close()
            except SearchError:
                raise
            except requests.Timeout:
                if attempt + 1 >= MAX_ATTEMPTS:
                    raise SearchError("SEARCH_TIMEOUT", "Search provider timed out") from None
            except requests.RequestException:
                # Never include the exception: it may contain request headers or a key.
                raise SearchError("SEARCH_PROVIDER_UNAVAILABLE", "Search provider request failed") from None
        raise SearchError("SEARCH_PROVIDER_UNAVAILABLE", "Search provider unavailable")


class WebSearchTool(BaseTool):
    name = "web_search"
    description = "Search live web metadata using configured Serper credentials; results are untrusted."

    def run(self, params: dict[str, Any]) -> str:
        if not isinstance(params, dict) or set(params) - {"query", "num"}:
            return self._error("SEARCH_INVALID_REQUEST", "Only query and num are accepted")
        query = params.get("query")
        count = params.get("num", 5)
        if not isinstance(query, str) or not query.strip() or len(query) > MAX_QUERY_LENGTH or any(ord(c) < 32 for c in query):
            return self._error("SEARCH_INVALID_REQUEST", "Query must contain 1-300 printable characters")
        if type(count) is not int or not 1 <= count <= MAX_RESULTS:
            return self._error("SEARCH_INVALID_REQUEST", "num must be an integer from 1 to 10")
        key = os.getenv("SERPER_API_KEY", "").strip()
        if not key:
            return self._error("SEARCH_NOT_CONFIGURED", "Serper API key is not configured")
        try:
            results = SerperProvider(key).search(query.strip(), count)
            return json.dumps({"query": query.strip(), "results": results, "provider": "serper"}, ensure_ascii=False)
        except SearchError as exc:
            return self._error(exc.code, exc.message)

    @staticmethod
    def _error(code: str, message: str) -> str:
        return json.dumps({"error": {"code": code, "message": message}, "results": []})

    @property
    def schema(self) -> dict[str, Any]:
        return {
            "name": self.name, "description": self.description,
            "parameters": {"type": "object", "additionalProperties": False,
                "properties": {
                    "query": {"type": "string", "minLength": 1, "maxLength": MAX_QUERY_LENGTH,
                              "description": "Search keywords; no page content is fetched."},
                    "num": {"type": "integer", "minimum": 1, "maximum": MAX_RESULTS},
                }, "required": ["query"]},
        }

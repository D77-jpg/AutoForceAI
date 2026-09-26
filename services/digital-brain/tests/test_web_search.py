"""H-07: real Serper web search acceptance tests; all HTTP is mocked.

Run from services/digital-brain: python -m pytest tests/test_web_search.py -q
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.tools.web_search import SerperProvider, WebSearchTool, SearchError  # noqa: E402


class FakeResponse:
    def __init__(self, status=200, data=None, *, chunks=None, headers=None):
        self.status_code = status
        self._chunks = chunks if chunks is not None else [json.dumps(data if data is not None else {}).encode()]
        self.headers = headers or {}
        self.closed = False

    def iter_content(self, chunk_size=8192):
        yield from self._chunks

    def close(self):
        self.closed = True


@pytest.fixture(autouse=True)
def _no_real_http(monkeypatch):
    """Even a missing patch in a test must never spend a real API quota."""
    monkeypatch.delenv("SERPER_API_KEY", raising=False)
    def forbidden(*args, **kwargs):
        pytest.fail("Unmocked HTTP request")
    monkeypatch.setattr(requests.Session, "post", forbidden)
    monkeypatch.setattr(requests, "post", forbidden)


@pytest.fixture
def http(monkeypatch):
    calls = []
    responses = []

    def post(*args, **kwargs):
        calls.append((args, kwargs))
        if not responses:
            pytest.fail("More HTTP requests than queued mock responses")
        result = responses.pop(0)
        if isinstance(result, BaseException):
            raise result
        return result

    monkeypatch.setattr(requests.Session, "post", post)
    monkeypatch.setattr(requests, "post", post)
    # Retry tests should run fast, without relying on elapsed wall time.
    import core.tools.web_search as search_module
    if hasattr(search_module, "time"):
        monkeypatch.setattr(search_module.time, "sleep", lambda *_: None)
    return calls, responses


def _payload(query="moon", count=1):
    return {"organic": [
        {"title": f"Title {n}", "snippet": f"Snippet {n}", "link": f"https://example.org/{n}"}
        for n in range(count)
    ]}


def _run(params):
    value = WebSearchTool().run(params)
    assert isinstance(value, str), "Tool contract requires a JSON string"
    return json.loads(value)


def test_missing_key_fails_closed_without_http_or_fake_news(monkeypatch):
    assert _run({"query": "actual headlines"})["error"]["code"] == "SEARCH_NOT_CONFIGURED"
    monkeypatch.setenv("SERPER_API_KEY", "   ")
    payload = _run({"query": "actual headlines"})
    assert payload["error"]["code"] == "SEARCH_NOT_CONFIGURED"
    assert "results" not in payload or payload["results"] == []
    assert "mock" not in json.dumps(payload).lower()


def test_real_results_have_uniform_fields_and_provider(monkeypatch, http):
    monkeypatch.setenv("SERPER_API_KEY", "test-key")
    calls, responses = http
    response = FakeResponse(data=_payload("moon", 2))
    responses.append(response)
    data = _run({"query": "moon", "num": 2})
    assert data["query"] == "moon"
    assert data["provider"] == "serper"
    assert data["results"]
    assert response.closed
    for result in data["results"]:
        assert set(result) >= {"title", "snippet", "url", "provider", "retrieved_at"}
        assert result["provider"] == "serper"
        assert result["url"].startswith("https://example.org/")
        assert result["retrieved_at"]
        assert "link" not in result
    assert len(calls) == 1


def test_requested_count_limits_returned_results(monkeypatch, http):
    monkeypatch.setenv("SERPER_API_KEY", "test-key")
    calls, responses = http
    responses.append(FakeResponse(data=_payload(count=20)))
    assert len(_run({"query": "moon", "num": 2})["results"]) == 2
    assert calls[0][1]["json"]["num"] == 2


def test_provider_endpoint_is_fixed_https_with_bounded_timeouts_and_stream(monkeypatch, http):
    monkeypatch.setenv("SERPER_API_KEY", "test-key")
    calls, responses = http
    assert _run({"query": "moon", "base_url": "http://127.0.0.1:9999/search"})["error"]["code"] == "SEARCH_INVALID_REQUEST"
    assert _run({"query": "moon", "provider": "attacker"})["error"]["code"] == "SEARCH_INVALID_REQUEST"
    assert not calls
    responses.append(FakeResponse(data=_payload()))
    data = _run({"query": "moon"})
    assert data["provider"] == "serper"
    args, kwargs = calls[0]
    url = next((value for value in args if isinstance(value, str)), kwargs.get("url"))
    assert url == "https://google.serper.dev/search"
    assert kwargs["json"]["q"] == "moon"
    assert kwargs["headers"]["X-API-KEY"] == "test-key"
    assert kwargs["stream"] is True
    assert kwargs.get("allow_redirects") is False
    assert isinstance(kwargs["timeout"], tuple) and len(kwargs["timeout"]) == 2
    assert all(0 < value <= 30 for value in kwargs["timeout"])


@pytest.mark.parametrize("params", [
    {}, {"query": None}, {"query": ""}, {"query": "   "},
    {"query": 42}, {"query": "a" * 10000},
    {"query": "x", "num": 0},
    {"query": "x", "num": -1},
    {"query": "x", "num": 10000},
    {"query": "x", "num": "lots"},
    {"query": "x", "num": True},
    {"query": "x\nwith injection"},
])
def test_invalid_parameters_fail_before_any_http(monkeypatch, params):
    monkeypatch.setenv("SERPER_API_KEY", "test-key")
    response = _run(params)
    assert isinstance(response["error"]["code"], str)
    assert not response.get("results")


def test_schema_exposes_query_and_finite_bounds():
    schema = WebSearchTool().schema["parameters"]
    props = schema["properties"]
    assert "query" in schema["required"]
    assert props["query"]["type"] == "string"
    assert 0 < props["query"]["maxLength"] <= 2000
    count = props["num"]
    assert count["type"] == "integer"
    assert 1 <= count["minimum"] <= count["maximum"] <= 100
    assert "base_url" not in props


@pytest.mark.parametrize("link", [
    "javascript:alert(1)", "data:text/html,evil", "file:///etc/passwd",
    "http://user:secret@example.org/path", "//example.org/relative", "",
])
def test_unsafe_result_urls_are_not_returned(monkeypatch, http, link):
    monkeypatch.setenv("SERPER_API_KEY", "test-key")
    _, responses = http
    responses.append(FakeResponse(data={"organic": [
        {"title": "Bad", "snippet": "bad", "link": link},
        {"title": "Good", "snippet": "ok", "link": "https://good.example/page"},
    ]}))
    results = _run({"query": "moon"})["results"]
    assert [item["url"] for item in results] == ["https://good.example/page"]


@pytest.mark.parametrize("headers,chunks", [
    ({"Content-Length": str(20_000_000)}, [b"{}"]),
    ({}, [b"{" + b"x" * 20_000_000 + b"}"]),
])
def test_response_body_size_limited_by_header_and_stream(monkeypatch, http, headers, chunks):
    monkeypatch.setenv("SERPER_API_KEY", "test-key")
    _, responses = http
    response = FakeResponse(headers=headers, chunks=chunks)
    responses.append(response)
    data = _run({"query": "moon"})
    assert data["error"]["code"]
    assert response.closed


@pytest.mark.parametrize("status", [429, 500, 503])
def test_retryable_http_statuses_retry_finitely(monkeypatch, http, status):
    monkeypatch.setenv("SERPER_API_KEY", "test-key")
    calls, responses = http
    responses.extend([FakeResponse(status=status), FakeResponse(data=_payload())])
    assert _run({"query": "moon"})["results"]
    assert len(calls) == 2
    calls.clear()
    responses.extend(FakeResponse(status=status) for _ in range(5))
    assert _run({"query": "moon"})["error"]["code"]
    assert 1 < len(calls) <= 4


@pytest.mark.parametrize("status", [400, 401, 403, 404])
def test_other_4xx_never_retry(monkeypatch, http, status):
    monkeypatch.setenv("SERPER_API_KEY", "test-key")
    calls, responses = http
    responses.append(FakeResponse(status=status))
    assert _run({"query": "moon"})["error"]["code"]
    assert len(calls) == 1


def test_malformed_provider_json_fails_closed(monkeypatch, http):
    monkeypatch.setenv("SERPER_API_KEY", "test-key")
    _, responses = http
    responses.append(FakeResponse(chunks=[b"not JSON"]))
    assert _run({"query": "moon"})["error"]["code"] == "SEARCH_INVALID_RESPONSE"


def test_timeout_is_reported_without_leaking_key(monkeypatch, http, caplog, capsys):
    secret = "SERPER_SECRET_DO_NOT_LEAK_97bd"
    monkeypatch.setenv("SERPER_API_KEY", secret)
    calls, responses = http
    responses.extend(requests.Timeout(f"request failed, key={secret}") for _ in range(5))
    result = _run({"query": "moon"})
    assert result["error"]["code"]
    assert len(calls) <= 4
    captured = capsys.readouterr()
    assert secret not in json.dumps(result)
    assert secret not in captured.out + captured.err + caplog.text


def test_provider_errors_do_not_expose_key(monkeypatch, http, caplog, capsys):
    secret = "SERPER_SECRET_DO_NOT_LEAK_97bd"
    monkeypatch.setenv("SERPER_API_KEY", secret)
    calls, responses = http
    responses.append(FakeResponse(status=401, data={"message": f"bad key: {secret}"}))
    result = _run({"query": "moon"})
    assert result["error"]["code"]
    assert len(calls) == 1
    captured = capsys.readouterr()
    assert secret not in json.dumps(result)
    assert secret not in captured.out + captured.err + caplog.text

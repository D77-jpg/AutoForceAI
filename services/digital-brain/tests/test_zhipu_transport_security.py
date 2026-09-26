"""Zhipu transport is fixed-origin and never returns vendor error secrets."""
import pytest
from core.llm import zhipu_compat
from branding_monitor.engines import zhipu_client


def test_fixed_origin_and_no_credentials_in_base_url(monkeypatch):
    seen = {}
    def fake_openai(**kwargs):
        seen.update(kwargs)
        return object()
    monkeypatch.setattr(zhipu_compat, "OpenAI", fake_openai)
    zhipu_compat.ZhipuAI(api_key="dummy")
    assert seen["api_key"] == "dummy"
    assert seen["base_url"] == "https://open.bigmodel.cn/api/paas/v4/"
    assert "dummy" not in seen["base_url"]
    assert seen["timeout"] > 0


def test_failed_vendor_request_never_reflects_secret(monkeypatch):
    class Failing:
        class chat:
            class completions:
                @staticmethod
                def create(**kwargs):
                    raise RuntimeError("vendor token=dummy-secret prompt=private")
    monkeypatch.setattr(zhipu_client, "ZhipuAI", lambda **kwargs: Failing())
    client = zhipu_client.ZhipuClient(api_key="dummy")
    with pytest.raises(RuntimeError, match="ZhipuAI request failed") as exc:
        client.query("private")
    assert "dummy-secret" not in str(exc.value)

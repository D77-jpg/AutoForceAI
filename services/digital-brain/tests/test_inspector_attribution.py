"""Inspector model provenance: isolated SQLite and fake provider HTTP responses only.

Run from services/digital-brain: venv/Scripts/python -m pytest tests/test_inspector_attribution.py -q
Never make a real model request: all SDK transport entry points are replaced before inspection.
"""
from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace as NS

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import database.models  # noqa: E402,F401  # Register the User.projects mapper.
from core.llm import runtime  # noqa: E402
from core.llm.factory import ModelFactory  # noqa: E402
from core.quality.inspector import SessionInspector  # noqa: E402
from database.base import Base  # noqa: E402
from database.shared_models import (  # noqa: E402
    BrainMessage, BrainSession, InspectionRecord, LLMModel, LLMProvider,
    Organization, QualityRule, User,
)


@pytest.fixture()
def db():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    tables = [
        Organization.__table__, User.__table__, BrainSession.__table__,
        BrainMessage.__table__, QualityRule.__table__, LLMProvider.__table__,
        LLMModel.__table__, InspectionRecord.__table__,
    ]
    Base.metadata.create_all(engine, tables=tables)
    with Session(engine) as session:
        session.add(BrainSession(id=101, title="attribution acceptance"))
        session.add(BrainMessage(session_id=101, role="user", content="请提供帮助"))
        session.add(QualityRule(name="礼貌", description="用语得体", weight=100, is_active=True))
        session.commit()
        yield session
    engine.dispose()


@pytest.fixture(autouse=True)
def no_real_network(monkeypatch):
    """Fail closed on accidental provider/cache leakage and unrelated env credentials."""
    ModelFactory._instances.clear()
    for key in ("OPENAI_API_KEY", "DASHSCOPE_API_KEY", "ZHIPUAI_API_KEY"):
        monkeypatch.delenv(key, raising=False)
    yield
    ModelFactory._instances.clear()


RESULT = '{"total_score": 89, "status": "Good", "issues": [], "suggestion": "保持礼貌"}'


def _default_model(db, *, name, provider="OpenAI"):
    owner = LLMProvider(name=provider, api_key="local-test-key", base_url="https://mock.invalid/v1")
    db.add(owner)
    db.flush()
    db.add(LLMModel(
        provider_id=owner.id, name=name, type="LLM", is_default=True, is_active=True,
    ))
    db.commit()


def _assert_saved(db, returned, *, model, provider, request_id):
    db.expire_all()
    saved = db.query(InspectionRecord).filter_by(session_id=101).one()
    assert returned.id == saved.id
    assert saved.total_score == 89
    assert saved.status == "Good"
    assert saved.model_used == model
    assert saved.model_provider == provider
    assert saved.model_request_id == request_id


def test_inspector_openai_generic_uses_response_model_not_requested_model(db, monkeypatch):
    _default_model(db, name="custom-local-judge")  # Factory selects OpenAI generic for unknown names.
    calls = []

    def fake_openai(**kwargs):
        assert kwargs["api_key"] == "local-test-key"
        def create(**params):
            calls.append(params)
            return NS(
                model="actual-judge-v2", _request_id="req-openai-01",
                choices=[NS(message=NS(content=RESULT))],
                usage=NS(prompt_tokens=12, completion_tokens=8),
            )
        return NS(chat=NS(completions=NS(create=create)))

    monkeypatch.setattr("core.llm.providers.openai_generic.OpenAI", fake_openai)
    record = SessionInspector(db).inspect(101)
    assert len(calls) == 1
    assert calls[0]["model"] == "custom-local-judge"
    assert calls[0]["messages"][-1]["role"] == "user"
    _assert_saved(db, record, model="actual-judge-v2", provider="openai_compatible", request_id="req-openai-01")


def test_inspector_qwen_uses_response_model_and_request_id(db, monkeypatch):
    _default_model(db, name="qwen-max", provider="Qwen")
    calls = []

    def fake_generation(**kwargs):
        calls.append(kwargs)
        return NS(
            status_code=200, model="qwen-actual-2026", request_id="req-qwen-02",
            output=NS(choices=[NS(message=NS(content=RESULT))]),
            usage=NS(input_tokens=12, output_tokens=8),
        )

    monkeypatch.setattr("core.llm.providers.qwen.Generation.call", fake_generation)
    record = SessionInspector(db).inspect(101)
    assert len(calls) == 1 and calls[0]["model"] == "qwen-max"
    _assert_saved(db, record, model="qwen-actual-2026", provider="qwen", request_id="req-qwen-02")


def test_inspector_zhipu_uses_response_model_and_request_id(db, monkeypatch):
    _default_model(db, name="glm-4-flash", provider="Zhipu")
    calls = []

    def fake_zhipu(**kwargs):
        assert kwargs["api_key"] == "local-test-key"
        def create(**params):
            calls.append(params)
            return NS(
                model="glm-actual-2026", request_id="req-zhipu-03",
                choices=[NS(message=NS(content=RESULT))],
                usage=NS(prompt_tokens=12, completion_tokens=8),
            )
        return NS(chat=NS(completions=NS(create=create)))

    monkeypatch.setattr("core.llm.providers.zhipu.ZhipuAI", fake_zhipu)
    record = SessionInspector(db).inspect(101)
    assert len(calls) == 1 and calls[0]["model"] == "glm-4-flash"
    _assert_saved(db, record, model="glm-actual-2026", provider="zhipu", request_id="req-zhipu-03")


@pytest.mark.parametrize("fallback,env_key,module,class_name,requested", [
    ("qwen", "DASHSCOPE_API_KEY", "branding_monitor.engines.qwen_client", "QwenClient", "qwen-max"),
    ("zhipu", "ZHIPUAI_API_KEY", "branding_monitor.engines.zhipu_client", "ZhipuClient", "glm-4-flash"),
])
def test_env_fallback_without_response_metadata_cannot_claim_requested_model(
    db, monkeypatch, fallback, env_key, module, class_name, requested,
):
    monkeypatch.setenv(env_key, "local-test-key")
    calls = []

    class FakeFallback:
        def __init__(self, *args, **kwargs):
            pass

        def query(self, prompt, **kwargs):
            calls.append((prompt, kwargs))
            return RESULT  # Legacy clients return plain text: no verified model or request ID.

    monkeypatch.setattr(f"{module}.{class_name}", FakeFallback)
    attributed = runtime.query_default_llm_with_attribution(db, "质检")
    assert len(calls) == 1
    assert attributed.content == RESULT
    assert attributed.provider == fallback
    assert attributed.model == "unknown"
    assert attributed.model != requested
    assert attributed.request_id is None
    record = SessionInspector(db).inspect(101)
    assert len(calls) == 2
    _assert_saved(db, record, model="unknown", provider=fallback, request_id=None)


@pytest.mark.parametrize("failure", ["http_error", "invalid_json"])
def test_failure_does_not_attribute_requested_model(db, monkeypatch, failure):
    _default_model(db, name="qwen-max", provider="Qwen")

    def fake_generation(**kwargs):
        if failure == "http_error":
            return NS(status_code=503, code="Unavailable", message="mock transport failed")
        return NS(
            status_code=200, model="qwen-actual", request_id="req-bad-json",
            output=NS(choices=[NS(message=NS(content="not valid json"))]),
            usage=NS(input_tokens=1, output_tokens=1),
        )

    monkeypatch.setattr("core.llm.providers.qwen.Generation.call", fake_generation)
    try:
        result = SessionInspector(db).inspect(101)
    except Exception:
        result = None  # Raising is allowed if a failure audit record survives rollback.
    db.expire_all()
    saved = db.query(InspectionRecord).filter_by(session_id=101).one()
    assert saved.status == "Failed"
    assert saved.model_used == "unknown"
    assert saved.model_provider == "unknown"
    assert saved.model_request_id is None
    if result is not None:
        assert result.id == saved.id

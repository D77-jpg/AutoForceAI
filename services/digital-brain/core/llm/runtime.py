"""Shared helpers for resolving the platform default LLM and running a chat turn."""
from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from core.llm.factory import ModelFactory
from core.llm.attribution import LLMAttribution, UNKNOWN, from_response
from database.shared_models import LLMModel


def get_default_llm_model(db: Session) -> Optional[LLMModel]:
    """
    Resolve the platform default reasoning model configured in AI 中台 → 模型纳管.
    Priority: system default > any active LLM.
    """
    model = db.query(LLMModel).filter(
        LLMModel.is_active == True, LLMModel.is_default == True  # noqa: E712
    ).first()
    if model:
        return model
    return db.query(LLMModel).filter(
        LLMModel.is_active == True, LLMModel.type == "LLM"  # noqa: E712
    ).first()


def query_default_llm_with_attribution(
    db: Session,
    prompt: str,
    *,
    system: Optional[str] = None,
    temperature: float = 0.6,
    max_tokens: int = 2500,
) -> LLMAttribution:
    """Call the configured model and attribute only the actual provider response.

    Environment fallbacks using the older string-only clients cannot prove the
    served model or request ID, so those fields remain explicitly unknown.
    """
    model = get_default_llm_model(db)
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    if model:
        kwargs = {
            "model": model.name,
            "api_key": model.api_key or (model.provider.api_key if model.provider else None),
            "base_url": model.base_url or (model.provider.base_url if model.provider else None),
        }
        kwargs = {key: value for key, value in kwargs.items() if value}
        llm = ModelFactory.get_provider(model.name, **kwargs)
        response = llm.chat(messages, temperature=temperature, max_tokens=max_tokens)
        # A configured label is not proof that the remote server used that model.
        provider = (getattr(llm, "provider_name", None) or
                    ("qwen" if llm.__class__.__name__ == "QwenLLM" else
                     "zhipu" if llm.__class__.__name__ == "ZhipuLLM" else
                     "openai_compatible" if llm.__class__.__name__ == "OpenAIGenericLLM" else UNKNOWN))
        return from_response(response, provider)

    from branding_monitor.engines.zhipu_client import ZhipuClient
    from branding_monitor.engines.qwen_client import QwenClient
    import os
    if os.getenv("DASHSCOPE_API_KEY"):
        return LLMAttribution(QwenClient().query(prompt, enable_search=False), "qwen", UNKNOWN)
    if os.getenv("ZHIPUAI_API_KEY"):
        return LLMAttribution(ZhipuClient().query(prompt, enable_search=False), "zhipu", UNKNOWN)
    # Never turn an empty, unconfigured mock into a believable inspection.
    raise RuntimeError("No configured LLM for inspection")


def query_default_llm(
    db: Session,
    prompt: str,
    *,
    system: Optional[str] = None,
    temperature: float = 0.6,
    max_tokens: int = 2500,
) -> str:
    """
    Query the platform default model via ModelFactory.
    Falls back to Zhipu / Qwen env clients, then a clearly-marked mock.
    """
    model = get_default_llm_model(db)
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    if model:
        kwargs = {
            "model": model.name,
            "api_key": model.api_key or (model.provider.api_key if model.provider else None),
            "base_url": model.base_url or (model.provider.base_url if model.provider else None),
        }
        kwargs = {k: v for k, v in kwargs.items() if v}
        print(f"[LLM] Using platform default model: {model.name}")
        llm = ModelFactory.get_provider(model.name, **kwargs)
        response = llm.chat(messages, temperature=temperature, max_tokens=max_tokens)
        return response.content or ""

    from branding_monitor.engines.zhipu_client import ZhipuClient
    from branding_monitor.engines.qwen_client import QwenClient
    import os

    if os.getenv("DASHSCOPE_API_KEY"):
        print("[LLM] No DB model; falling back to QwenClient")
        return QwenClient().query(prompt, enable_search=False)
    if os.getenv("ZHIPUAI_API_KEY"):
        print("[LLM] No DB model; falling back to ZhipuClient")
        return ZhipuClient().query(prompt, enable_search=False)

    print("[LLM] No model configured; returning mock")
    return ""

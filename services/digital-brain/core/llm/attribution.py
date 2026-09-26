"""Normalized provenance for a completed LLM request; never infer a failed call."""
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class LLMAttribution:
    content: str
    provider: str
    model: str
    request_id: Optional[str] = None


UNKNOWN = "unknown"


def from_response(response, provider: str) -> LLMAttribution:
    """Prefer identifiers returned by the actual provider response to requested names."""
    raw = getattr(response, "raw_response", None)
    output = getattr(raw, "output", None)
    name = getattr(raw, "model", None) or getattr(output, "model", None)
    request_id = (getattr(raw, "_request_id", None) or getattr(raw, "request_id", None)
                  or getattr(raw, "requestId", None))
    if isinstance(raw, dict):
        name = name or raw.get("model")
        request_id = request_id or raw.get("request_id") or raw.get("requestId")
    return LLMAttribution(
        content=getattr(response, "content", "") or "",
        provider=provider or UNKNOWN,
        model=name if isinstance(name, str) and name.strip() else UNKNOWN,
        request_id=str(request_id) if request_id else None,
    )

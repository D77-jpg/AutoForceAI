"""询盘意图识别：从客服对话中抽取结构化线索 JSON。"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from core.agents.planner import get_default_llm_model
from core.llm.factory import ModelFactory

INTENT_PROMPT = """You are a B2B foreign-trade inquiry parser.
Given a customer-service conversation, extract a JSON object with these fields:
- is_inquiry: boolean (true if the visitor shows buying intent: price, MOQ, sample, catalog, quotation, OEM)
- language: ISO code like "en" or "zh"
- name: visitor name if mentioned, else null
- company: company name if mentioned, else null
- email: email if mentioned, else null
- country: country if mentioned, else null
- phone: phone if mentioned, else null
- products: short product interest summary, else null
- intent: one of "quote" | "catalog" | "sample" | "oem" | "general" | "none"
- confidence: number 0-1

Return ONLY JSON. Conversation:
"""


def detect_language(text: str) -> str:
    cjk = len(re.findall(r"[\u4e00-\u9fff]", text or ""))
    return "zh" if cjk > 8 else "en"


def extract_email(text: str) -> Optional[str]:
    m = re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text or "")
    return m.group(0).lower() if m else None


_COUNTRY_ALIASES = {
    "germany": "Germany", "deutschland": "Germany", "german": "Germany",
    "usa": "USA", "united states": "USA", "america": "USA",
    "uk": "United Kingdom", "united kingdom": "United Kingdom", "britain": "United Kingdom",
    "china": "China", "prc": "China",
    "japan": "Japan", "korea": "South Korea", "india": "India",
    "france": "France", "italy": "Italy", "spain": "Spain",
    "canada": "Canada", "australia": "Australia", "brazil": "Brazil",
    "mexico": "Mexico", "netherlands": "Netherlands", "poland": "Poland",
    "turkey": "Turkey", "uae": "UAE", "saudi": "Saudi Arabia",
}


def extract_country(text: str) -> Optional[str]:
    t = (text or "").lower()
    for alias, name in _COUNTRY_ALIASES.items():
        if re.search(rf"\b{re.escape(alias)}\b", t):
            return name
    m = re.search(r"\bfrom\s+([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)?)\b", text or "")
    return m.group(1) if m else None


def extract_name(text: str) -> Optional[str]:
    m = re.search(
        r"(?:my name is|i am|i'm|this is)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)",
        text or "",
        re.I,
    )
    return m.group(1).strip() if m else None


def extract_products(text: str) -> Optional[str]:
    raw = text or ""
    m = re.search(
        r"(?:for|about|regarding)\s+(?:the\s+)?([A-Za-z0-9][A-Za-z0-9 \-/]{2,60}?)(?:[?.!,]|$)",
        raw,
        re.I,
    )
    if m:
        prod = re.sub(r"\s+", " ", m.group(1)).strip(" .")
        if prod.lower() not in {"you", "this", "that", "it", "us"}:
            return prod[:120]
    codes = re.findall(r"\b[A-Z]{1,4}-?\d{2,6}\b", raw)
    return ", ".join(dict.fromkeys(codes)) if codes else None


def heuristic_intent(text: str) -> Dict[str, Any]:
    t = (text or "").lower()
    keywords = {
        "quote": ["price", "quotation", "quote", "cif", "fob", "报价", "询价"],
        "catalog": ["catalog", "catalogue", "brochure", "datasheet", "目录"],
        "sample": ["sample", "样品"],
        "oem": ["oem", "odm", "private label", "定制"],
    }
    intent = "none"
    for k, words in keywords.items():
        if any(w in t for w in words):
            intent = k
            break
    is_inquiry = intent != "none" or any(w in t for w in ["moq", "lead time", "交货", "最小订"])
    return {
        "is_inquiry": is_inquiry,
        "language": detect_language(text),
        "name": extract_name(text),
        "company": None,
        "email": extract_email(text),
        "country": extract_country(text),
        "phone": None,
        "products": extract_products(text),
        "intent": intent if is_inquiry else "none",
        "confidence": 0.55 if is_inquiry else 0.2,
    }


def parse_inquiry(db: Session, messages: List[Dict[str, str]]) -> Dict[str, Any]:
    convo = "\n".join(f"{m.get('role','user')}: {m.get('content','')}" for m in messages[-12:])
    base = heuristic_intent(convo)
    model = get_default_llm_model(db)
    if not model:
        return base
    try:
        kwargs = {
            "model": model.name,
            "api_key": model.api_key or (model.provider.api_key if model.provider else None),
            "base_url": model.base_url or (model.provider.base_url if model.provider else None),
        }
        kwargs = {k: v for k, v in kwargs.items() if v}
        llm = ModelFactory.get_provider(model.name, **kwargs)
        raw = llm.chat([{"role": "user", "content": INTENT_PROMPT + convo}], temperature=0.1).content or ""
        m = re.search(r"\{[\s\S]*\}", raw)
        if not m:
            return base
        parsed = json.loads(m.group(0))
        merged = {**base, **{k: v for k, v in parsed.items() if v not in (None, "", [])}}
        if not merged.get("email"):
            merged["email"] = extract_email(convo)
        return merged
    except Exception:
        return base

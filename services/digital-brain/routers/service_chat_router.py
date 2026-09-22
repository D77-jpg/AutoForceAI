"""AI 客服：机器人配置、匿名会话（聊天插件）、会话列表、质检规则。"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from core.agents.planner import get_default_llm_model
from core.db_manager import get_shared_db
from core.dependencies import get_current_user
from core.llm.factory import ModelFactory
from core.rag.intent import detect_language, parse_inquiry
from core.rag.retriever import KnowledgeRetriever
from database.models import ChatMessage, ChatSession
from database.shared_models import Bot, KnowledgeBase, Lead, QualityRule, User
from routers.lead_router import upsert_lead

router = APIRouter(prefix="/api/v1/service", tags=["AI Customer Service"])


def _user(payload: dict, db: Session) -> User:
    user = db.query(User).filter(User.id == payload["id"]).first()
    if not user:
        raise HTTPException(401, "用户不存在")
    return user


# ---------- Bots ----------

class BotIn(BaseModel):
    name: str
    description: Optional[str] = None
    system_prompt: Optional[str] = None
    welcome_message: Optional[str] = None
    model_name: Optional[str] = None
    kb_id: Optional[int] = None
    is_active: bool = True


@router.get("/bots")
def list_bots(payload: dict = Depends(get_current_user), db: Session = Depends(get_shared_db)):
    user = _user(payload, db)
    q = db.query(Bot)
    if user.organization_id:
        q = q.filter(Bot.organization_id == user.organization_id)
    rows = q.order_by(Bot.id.desc()).all()
    return {"items": [
        {
            "id": b.id, "name": b.name, "description": b.description,
            "system_prompt": b.system_prompt, "welcome_message": b.welcome_message,
            "model_name": b.model_name, "kb_id": b.kb_id, "is_active": b.is_active,
        } for b in rows
    ]}


@router.post("/bots")
def create_bot(body: BotIn, payload: dict = Depends(get_current_user), db: Session = Depends(get_shared_db)):
    user = _user(payload, db)
    bot = Bot(
        organization_id=user.organization_id,
        name=body.name,
        description=body.description,
        system_prompt=body.system_prompt or (
            "You are a professional B2B export sales assistant. "
            "Answer in the visitor's language. Prefer English for overseas buyers. "
            "Use the knowledge base. If unsure, say you will have a human follow up."
        ),
        welcome_message=body.welcome_message or "Hello! How can I help you today?",
        model_name=body.model_name or "qwen-turbo",
        kb_id=body.kb_id,
        is_active=body.is_active,
    )
    db.add(bot)
    db.commit()
    db.refresh(bot)
    return {"id": bot.id, "name": bot.name}


@router.patch("/bots/{bot_id}")
def update_bot(bot_id: int, body: BotIn, payload: dict = Depends(get_current_user), db: Session = Depends(get_shared_db)):
    user = _user(payload, db)
    bot = db.query(Bot).filter(Bot.id == bot_id).first()
    if not bot:
        raise HTTPException(404, "机器人不存在")
    if user.organization_id and bot.organization_id != user.organization_id:
        raise HTTPException(403, "无权操作")
    for k, v in body.model_dump().items():
        setattr(bot, k, v)
    db.commit()
    return {"id": bot.id}


# ---------- Widget (anonymous) ----------

class WidgetStartIn(BaseModel):
    bot_id: Optional[int] = None
    visitor_id: Optional[str] = None
    language: Optional[str] = None


class WidgetChatIn(BaseModel):
    session_uuid: str
    message: str
    visitor_email: Optional[str] = None
    visitor_name: Optional[str] = None


def _get_bot(db: Session, bot_id: Optional[int]) -> Optional[Bot]:
    if bot_id:
        return db.query(Bot).filter(Bot.id == bot_id, Bot.is_active == True).first()  # noqa: E712
    return db.query(Bot).filter(Bot.is_active == True).order_by(Bot.id.asc()).first()


@router.post("/widget/start")
def widget_start(body: WidgetStartIn, db: Session = Depends(get_shared_db)):
    bot = _get_bot(db, body.bot_id)
    sess = ChatSession(
        session_uuid=str(uuid.uuid4()),
        bot_id=bot.id if bot else None,
        visitor_id=body.visitor_id or str(uuid.uuid4()),
        language=body.language,
        status="active",
    )
    db.add(sess)
    db.commit()
    db.refresh(sess)
    welcome = (bot.welcome_message if bot else None) or "Hello! How can I help you today?"
    db.add(ChatMessage(session_id=sess.id, role="assistant", content=welcome, meta_data={"kind": "welcome"}))
    db.commit()
    return {
        "session_uuid": sess.session_uuid,
        "welcome": welcome,
        "bot_name": bot.name if bot else "AI Assistant",
        "bot_id": bot.id if bot else None,
    }


def _reply_with_kb(db: Session, bot: Optional[Bot], user_text: str) -> str:
    lang = detect_language(user_text)
    kb_ids = []
    if bot and bot.kb_id:
        kb_ids = [bot.kb_id]
    else:
        kb_ids = [k.id for k in db.query(KnowledgeBase).filter(KnowledgeBase.is_public == True).all()]  # noqa: E712

    context = ""
    if kb_ids:
        hits = KnowledgeRetriever(db).search_multi_kb(kb_ids, user_text, top_k=4, score_threshold=0.15)
        if hits:
            context = "\n\n".join(f"[{h.get('doc_name')}] {h.get('content')}" for h in hits)

    system = (bot.system_prompt if bot else None) or (
        "You are a professional B2B export sales assistant. Answer using the knowledge context when present."
    )
    if lang == "en":
        system += " Reply in English."
    else:
        system += " Reply in the visitor's language."
    if context:
        system += "\n\nKnowledge context:\n" + context[:6000]
    else:
        system += "\nIf the knowledge base has no answer, be honest and offer a human follow-up."

    model = get_default_llm_model(db)
    if not model:
        if context:
            return ("Based on our catalog:\n" + context[:800]) if lang != "zh" else ("根据资料：\n" + context[:800])
        return "Thanks for your message. A sales representative will follow up shortly." if lang != "zh" else "感谢咨询，我们的业务员会尽快跟进。"

    kwargs = {
        "model": (bot.model_name if bot and bot.model_name else model.name),
        "api_key": model.api_key or (model.provider.api_key if model.provider else None),
        "base_url": model.base_url or (model.provider.base_url if model.provider else None),
    }
    kwargs = {k: v for k, v in kwargs.items() if v}
    llm = ModelFactory.get_provider(kwargs.get("model", model.name), **kwargs)
    resp = llm.chat([
        {"role": "system", "content": system},
        {"role": "user", "content": user_text},
    ], temperature=bot.temperature if bot else 0.4)
    return resp.content or "Thanks, we will follow up shortly."


@router.post("/widget/chat")
def widget_chat(body: WidgetChatIn, db: Session = Depends(get_shared_db)):
    sess = db.query(ChatSession).filter(ChatSession.session_uuid == body.session_uuid).first()
    if not sess:
        raise HTTPException(404, "会话不存在")
    if body.visitor_email:
        sess.visitor_email = body.visitor_email
    if body.visitor_name:
        sess.visitor_name = body.visitor_name
    sess.language = detect_language(body.message)
    db.add(ChatMessage(session_id=sess.id, role="user", content=body.message, meta_data={}))
    db.commit()

    bot = db.query(Bot).filter(Bot.id == sess.bot_id).first() if sess.bot_id else _get_bot(db, None)
    try:
        answer = _reply_with_kb(db, bot, body.message)
    except Exception as exc:
        answer = f"Sorry, the assistant is temporarily unavailable. ({exc})"

    db.add(ChatMessage(session_id=sess.id, role="assistant", content=answer, meta_data={}))
    sess.updated_at = datetime.now()
    db.commit()

    msgs = db.query(ChatMessage).filter(ChatMessage.session_id == sess.id).order_by(ChatMessage.id.asc()).all()
    parsed = parse_inquiry(db, [{"role": m.role, "content": m.content} for m in msgs])
    sess.intent = parsed
    db.commit()

    lead = None
    if parsed.get("is_inquiry"):
        org_id = bot.organization_id if bot and bot.organization_id else None
        lead_obj = upsert_lead(db, org_id, {
            "source": "Website AI Chat",
            "email": parsed.get("email") or sess.visitor_email,
            "name": parsed.get("name") or sess.visitor_name,
            "company": parsed.get("company"),
            "country": parsed.get("country"),
            "phone": parsed.get("phone"),
            "products": parsed.get("products"),
            "intent_json": parsed,
            "conversation": "\n".join(f"{m.role}: {m.content}" for m in msgs[-16:]),
            "session_uuid": sess.session_uuid,
            "language": parsed.get("language") or sess.language,
        })
        lead = {"id": lead_obj.id, "status": lead_obj.status, "email": lead_obj.email}

    return {"reply": answer, "intent": parsed, "lead": lead}


@router.get("/widget/history/{session_uuid}")
def widget_history(session_uuid: str, db: Session = Depends(get_shared_db)):
    sess = db.query(ChatSession).filter(ChatSession.session_uuid == session_uuid).first()
    if not sess:
        raise HTTPException(404, "会话不存在")
    msgs = db.query(ChatMessage).filter(ChatMessage.session_id == sess.id).order_by(ChatMessage.id.asc()).all()
    return {
        "session_uuid": sess.session_uuid,
        "status": sess.status,
        "messages": [{"role": m.role, "content": m.content, "created_at": m.created_at.isoformat() if m.created_at else None} for m in msgs],
    }


# ---------- Admin sessions / quality ----------

@router.get("/sessions")
def list_sessions(payload: dict = Depends(get_current_user), db: Session = Depends(get_shared_db)):
    _user(payload, db)
    rows = db.query(ChatSession).order_by(ChatSession.id.desc()).limit(200).all()
    return {"items": [
        {
            "id": s.id,
            "session_uuid": s.session_uuid,
            "status": s.status,
            "visitor_id": s.visitor_id,
            "visitor_email": s.visitor_email,
            "visitor_name": s.visitor_name,
            "language": s.language,
            "intent": s.intent,
            "bot_id": s.bot_id,
            "created_at": s.created_at.isoformat() if s.created_at else None,
            "updated_at": s.updated_at.isoformat() if s.updated_at else None,
        } for s in rows
    ], "total": len(rows)}


@router.get("/sessions/{session_uuid}")
def session_detail(session_uuid: str, payload: dict = Depends(get_current_user), db: Session = Depends(get_shared_db)):
    return widget_history(session_uuid, db)


@router.get("/rules")
def list_rules(payload: dict = Depends(get_current_user), db: Session = Depends(get_shared_db)):
    user = _user(payload, db)
    q = db.query(QualityRule)
    if user.organization_id:
        q = q.filter((QualityRule.organization_id == user.organization_id) | (QualityRule.organization_id == None))  # noqa: E711
    rows = q.all()
    return {"items": [
        {"id": r.id, "name": r.name, "description": r.description, "weight": r.weight, "is_active": r.is_active}
        for r in rows
    ]}


class RuleIn(BaseModel):
    name: str
    description: Optional[str] = None
    weight: float = 1.0
    is_active: bool = True


@router.post("/rules")
def create_rule(body: RuleIn, payload: dict = Depends(get_current_user), db: Session = Depends(get_shared_db)):
    user = _user(payload, db)
    rule = QualityRule(organization_id=user.organization_id, **body.model_dump())
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return {"id": rule.id}


@router.get("/stats")
def service_stats(payload: dict = Depends(get_current_user), db: Session = Depends(get_shared_db)):
    total = db.query(ChatSession).count()
    active = db.query(ChatSession).filter(ChatSession.status == "active").count()
    leads = db.query(Lead).count()
    return {"sessions": total, "active": active, "leads": leads}

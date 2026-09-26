from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, UploadFile, File, Form, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, or_
from pydantic import BaseModel
from datetime import datetime
import json
import asyncio

from core.db_manager import get_shared_db, SharedSessionLocal
from database.shared_models import User, KnowledgeBase, Organization, RAGConfig, LLMModel, BrainSession, BrainMessage
from core.dependencies import get_current_user_id
from core.rag.retriever import KnowledgeRetriever
from core.utils.file_parser import FileParser # Import Parser
# from branding_monitor.engines.zhipu_client import ZhipuClient # Deprecated in favor of generic factory
from core.llm.factory import ModelFactory 

router = APIRouter(prefix="/api/v1/brain", tags=["Enterprise Brain"])

# --- Schemas ---

class BrainChatRequest(BaseModel):
    query: str
    session_id: Optional[int] = None # Support chat sessions
    context: Optional[str] = None # Support additional file context
    kb_ids: Optional[List[int]] = None # Optional: limit to specific KBs, defaults to all
    top_k: Optional[int] = None
    temperature: Optional[float] = None
    score_threshold: Optional[float] = None
    model_name: Optional[str] = None # Support explicit model selection

class BrainSource(BaseModel):
    doc_id: int
    doc_name: str
    kb_id: int
    kb_name: Optional[str] = None # Add KB name
    is_public: bool = False # Add Public Flag
    score: float
    content_preview: str

class BrainChatResponse(BaseModel):
    session_id: int
    answer: str
    sources: List[BrainSource]
    thought_process: Optional[str] = None
    context: Optional[str] = None
    model_used: Optional[str] = None

class SessionResponse(BaseModel):
    id: int
    title: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class SessionMessageResponse(BaseModel):
    role: str
    content: str
    thought_process: Optional[str]
    citations: Optional[List[dict]]
    created_at: datetime

# --- Helpers ---

def get_active_kb_model(db: Session):
    # 1. Check for KB Default
    model = db.query(LLMModel).filter(LLMModel.is_active == True, LLMModel.is_kb_search_default == True).first()
    if model: return model
    
    # 2. Check for System Default
    model = db.query(LLMModel).filter(LLMModel.is_active == True, LLMModel.is_default == True).first()
    if model: return model
    
    # 3. Fallback (First available LLM)
    model = db.query(LLMModel).filter(LLMModel.is_active == True, LLMModel.type == 'LLM').first()
    return model

def generate_session_title(db: Session, session_id: int, query: str):
    # Background task to rename session based on first query
    try:
        session = db.query(BrainSession).filter(BrainSession.id == session_id).first()
        if session and session.title == "New Chat":
            # Simple heuristic or LLM call could go here. For speed, just truncate query.
            new_title = query[:20] + "..." if len(query) > 20 else query
            session.title = new_title
            db.commit()
    except Exception as e:
        print("Title generation failed")

# --- Endpoints ---

@router.get("/config")
def get_brain_config(db: Session = Depends(get_shared_db)):
    """Get current configuration including active model"""
    model = get_active_kb_model(db)
    return {
        "active_model": {
            "name": model.name if model else "System Default",
            "display_name": model.display_name if model else "System Default",
            "provider": model.provider.name if model and model.provider else "Custom"
        }
    }

@router.get("/sessions", response_model=List[SessionResponse])
def get_sessions(user_id: int = Depends(get_current_user_id), db: Session = Depends(get_shared_db)):
    """List user's chat sessions"""
    sessions = db.query(BrainSession).filter(
        BrainSession.user_id == user_id, 
        BrainSession.is_active == True
    ).order_by(desc(BrainSession.updated_at)).all()
    return sessions

@router.post("/sessions", response_model=SessionResponse)
def create_session(user_id: int = Depends(get_current_user_id), db: Session = Depends(get_shared_db)):
    """Create a new empty session"""
    user = db.query(User).filter(User.id == user_id).first()
    sess = BrainSession(user_id=user_id, organization_id=user.organization_id)
    db.add(sess)
    db.commit()
    db.refresh(sess)
    return sess

@router.get("/sessions/{session_id}/messages", response_model=List[SessionMessageResponse])
def get_session_messages(session_id: int, user_id: int = Depends(get_current_user_id), db: Session = Depends(get_shared_db)):
    """Get history for a session"""
    session = db.query(BrainSession).filter(BrainSession.id == session_id, BrainSession.user_id == user_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
        
    messages = db.query(BrainMessage).filter(BrainMessage.session_id == session_id).order_by(BrainMessage.created_at).all()
    
    # Transform to response format (handling citations JSON)
    result = []
    for m in messages:
        result.append({
            "role": m.role,
            "content": m.content,
            "thought_process": m.thought_process,
            "citations": m.citations, # SQLAlchemy JSON field handles this automatically?
            "created_at": m.created_at
        })
    return result

@router.delete("/sessions/{session_id}")
def delete_session(session_id: int, user_id: int = Depends(get_current_user_id), db: Session = Depends(get_shared_db)):
    session = db.query(BrainSession).filter(BrainSession.id == session_id, BrainSession.user_id == user_id).first()
    if session:
        session.is_active = False # Soft delete
        db.commit()
    return {"success": True}


@router.post("/chat/upload")
async def extract_file_content(file: UploadFile = File(...)):
    """
    Extracts text content from an uploaded file (PDF, DOCX, TXT)
    to be used as context in the chat.
    """
    try:
        content = await FileParser.parse_upload_file(file)
        # Limit content size if needed, but for now allow large contexts (LLMs handles it)
        # Maybe preview first 200 chars for UI
        preview = content[:200].replace('\n', ' ') + "..."
        return {
            "filename": file.filename,
            "content": content,
            "preview": preview,
            "size": len(content)
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail="Invalid uploaded file")

@router.post("/chat")
def brain_chat(
    request: BrainChatRequest,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_shared_db)
):
    """
    Streamed Chat Endpoint
    """
    # Do not log chat content or prompts.
    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.organization_id:
        raise HTTPException(status_code=400, detail="User context invalid")

    # 1. Session Setup
    session = None
    if request.session_id:
        session = db.query(BrainSession).filter(BrainSession.id == request.session_id, BrainSession.user_id == user_id).first()
    
    if not session:
        session = BrainSession(user_id=user_id, organization_id=user.organization_id, title=request.query[:15] + "...")
        db.add(session)
        db.commit()
        db.refresh(session)
    else:
        session.updated_at = datetime.now()
        if session.title == "New Chat":
             session.title = request.query[:15] + "..."
        db.commit()

    # Determine Target KBs
    # Logic: 
    # - If kb_ids specified in request -> Use strictly those (filtered by org)
    # - If NOT specified (General Chat) -> Use all "Public" KBs in Organization + System 
    
    target_kb_ids = []
    
    # Base query for Allowed KBs (Org or System)
    # Note: System KBs have organization_id == None
    base_kb_query = db.query(KnowledgeBase.id).filter(
        or_(
            KnowledgeBase.organization_id == user.organization_id,
            KnowledgeBase.organization_id == None
        )
    )
    
    if request.kb_ids:
        # User requested specific KBs: Validate membership
        # Ensure requested KBs belong to user's org or are system KBs
        valid_kbs = base_kb_query.filter(KnowledgeBase.id.in_(request.kb_ids)).all()
        target_kb_ids = [k.id for k in valid_kbs]
        # IDs are not logged; query scope is enforced by the organization filter.
    else:
        # Default: Search Public KBs in Organization + System Public KBs
        public_kbs = base_kb_query.filter(KnowledgeBase.is_public == True).all()
        target_kb_ids = [k.id for k in public_kbs]
        print(f"[DEBUG] General Chat -Using Public Org/System KBs: {target_kb_ids}")

    # Save User Message
    user_msg_db = BrainMessage(session_id=session.id, role="user", content=request.query)
    db.add(user_msg_db)
    db.commit()

    # Capture IDs to avoid lazy loading issues in generator
    session_id_val = session.id
    organization_id_val = user.organization_id
    user_msg_id = user_msg_db.id

    def generate():
        # Create a new session for the generator thread/context
        # The dependency-injected 'db' will be closed when the route handler returns
        gen_db = SharedSessionLocal() 
        
        # Helper to force-flush buffers in proxies by padding
        def pack_json(obj):
            s = json.dumps(obj, ensure_ascii=False)
            return s + "\n"

        try:
            # 1. Init Signal
            yield pack_json({"t": "init", "session_id": session_id_val})

            # 2. Scope & Retrieval
            yield pack_json({"t": "step", "msg": "正在识别意图..."})
            
            filter_start = datetime.now()
            
            # Use the target_kb_ids determined in the main handler (Pre-filtered for Public/Private)
            # Ensure we are using the IDs captured from the outer scope
            params_kb_ids = target_kb_ids 
            
            yield pack_json({"t": "step", "msg": f"正在检索知识库 (范围: {len(params_kb_ids)} 个库)..."})

            retriever = KnowledgeRetriever(gen_db)
            rag_config = gen_db.query(RAGConfig).filter(RAGConfig.organization_id == organization_id_val).first()
            
            top_k = request.top_k or (rag_config.top_k if rag_config else 5)
            # Relax default threshold from 0.5 to 0.35 to allow broader matching for short queries
            threshold = request.score_threshold or (rag_config.score_threshold if rag_config else 0.35)
            temperature = request.temperature or 0.7
            
            chunks = []
            try:
                if target_kb_ids:
                    chunks = retriever.search_multi_kb(
                        kb_ids=target_kb_ids,
                        query=request.query,
                        top_k=top_k, 
                        score_threshold=threshold
                    )
                yield pack_json({"t": "step", "msg": f"检索完成，找到 {len(chunks)} 条相关内容..."})
            except Exception as e:
                print("RAG retrieval failed")
                chunks = []
                yield pack_json({"t": "step", "msg": "检索服务暂时不可用，尝试通用回答..."})

            # 3. Context Build
            context_text = ""
            sources_out = []
            citations_json = []
            seen_doc_ids = set()

            # Pre-fetch KB info for tagging (optimization: do 1 query)
            unique_kb_ids = list(set([c.get("kb_id") for c in chunks if c.get("kb_id")]))
            kb_map = {}
            if unique_kb_ids:
                kb_infos = gen_db.query(KnowledgeBase).filter(KnowledgeBase.id.in_(unique_kb_ids)).all()
                for k in kb_infos:
                    kb_map[k.id] = {"name": k.name, "is_public": getattr(k, "is_public", False)}

            for idx, chunk in enumerate(chunks):
                c_text = chunk.get("content", "")
                c_doc_name = chunk.get("doc_name", "Unknown")
                c_score = chunk.get("score", 0.0)
                c_kb_id = chunk.get("kb_id", 0)
                
                kb_info = kb_map.get(c_kb_id, {"name": "Unknown", "is_public": False})
                
                # Keep context full for LLM
                context_text += f"[{idx+1}] (File: {c_doc_name}): {c_text}\n\n"
                
                # Deduplicate for Frontend Display (Sources List)
                c_doc_id = chunk.get("doc_id", 0)
                if c_doc_id not in seen_doc_ids:
                    seen_doc_ids.add(c_doc_id)
                    sources_out.append({
                        "doc_id": c_doc_id,
                        "doc_name": c_doc_name,
                        "kb_id": c_kb_id,
                        "kb_name": kb_info["name"],
                        "is_public": kb_info["is_public"],
                        "score": c_score,
                        "content_preview": c_text[:100] + "..."
                    })
                    citations_json.append({
                        "id": c_doc_id,
                        "title": c_doc_name,
                        "kb_id": c_kb_id,
                        "kb_name": kb_info["name"],
                        "is_public": kb_info["is_public"],
                        "score": c_score
                    })
            
            # Add User Uploaded Context (Priority)
            if request.context:
                context_text = f"【用户上传文档内容】:\n{request.context}\n\n" + context_text
            
            # 4. History
            history_messages = []
            past_msgs = gen_db.query(BrainMessage).filter(BrainMessage.session_id == session_id_val).order_by(desc(BrainMessage.created_at)).limit(11).all()
            past_msgs.reverse()
            for m in past_msgs:
                if m.id == user_msg_id: continue
                history_messages.append({"role": m.role, "content": m.content or ""})

            # 5. Prompting
            system_prompt = """你是一个智能企业知识助手(CKO)。你的目标是尽最大努力回答用户的问题。
原则：
1. 首先，仔细阅读提供的【上下文信息】（Context Information）。如果其中包含答案，请依据上下文回答，并使用 [1], [2] 格式引用来源。
2. 如果【上下文信息】为空，或者不包含回答问题所需的信息，请忽略上下文，**直接利用你的通用知识库进行回答**。
3. 当使用通用知识回答时，不要编造虚假的引用来源。
4. 回答要专业、简洁、有帮助。"""
            
            final_user_content = f"【上下文信息】:\n{context_text if context_text else '(无相关上下文，请使用通用知识回答)'}\n\n【用户问题】: {request.query}"
            
            # Send Meta Data incl Context
            import json as _json_alias # Avoid conflict
            full_context_debug = [{"role": "system", "content": system_prompt}] + history_messages + [{"role": "user", "content": final_user_content}]
            yield pack_json({
                "t": "meta", 
                "sources": sources_out, 
                "context": _json_alias.dumps(full_context_debug, ensure_ascii=False, indent=2)
            })

            # 6. Inference
            active_model = None
            if request.model_name:
                active_model = gen_db.query(LLMModel).filter(LLMModel.name == request.model_name, LLMModel.is_active == True).first()
                if active_model:
                     yield pack_json({"t": "step", "msg": f"使用指定模型: {active_model.display_name}..."})
            
            if not active_model:
                active_model = get_active_kb_model(gen_db)
            
            if not active_model:
                # Fallback to hard error
                yield pack_json({"t": "step", "msg": "未找到任何可用模型，请在后台配置。"})
                # yield pack_json({"t": "token", "chunk": "Error: No model available."}) # Handled by error block below
                raise Exception("No active model found")

            yield pack_json({"t": "step", "msg": f"正在调用 {active_model.display_name} 进行推理..."})
            
            # --- Generic Factory Call ---
            # Now we use the ModelFactory to handle different providers (OpenAI, DashScope, Zhipu, etc)
            
            # Get API Key (Decrypt if necessary, here assumed plain for simplicity or env var if empty)
            api_key = active_model.api_key
            if not api_key:
                # Try getting from ENV based on provider
                if active_model.provider and active_model.provider.name == "zhipu":
                     import os
                     api_key = os.getenv("ZHIPUAI_API_KEY")
                elif active_model.provider and active_model.provider.name == "dashscope":
                     import os
                     api_key = os.getenv("DASHSCOPE_API_KEY")
                     
            # Build Messages
            messages = [{"role": "system", "content": system_prompt}]
            
            # Combine Context + History + Current Query
            # Strategy: 
            # 1. System Prompt
            # 2. History (User/Assistant exchanges)
            # 3. Reference Context (as System or User instruction)
            # 4. Current User Query
            
            for m in history_messages:
                messages.append(m)

            # Insert context before the last user message or as a separate system 'context' message
            if context_text:
                context_message = f"请基于以下【参考资料】回答问题，如果资料不足以回答，请使用你的通用知识。\n\n【参考资料Start】\n{context_text}\n【参考资料End】\n"
                # Add as the second to last message (before current query) or append to current query
                # Appending to current query is safer for most models
                final_active_query = context_message + "\n\n用户问题: " + request.query
            else:
                final_active_query = request.query
                
            messages.append({"role": "user", "content": final_active_query})

            # Call Factory
            provider_args = {
                "api_key": active_model.api_key or api_key,
                "base_url": active_model.base_url,
                "context_window": active_model.context_window,
                "model": active_model.name
            }
            llm = ModelFactory.get_provider(active_model.name or "qwen", **provider_args)
            
            # --- Chat Call ---
            # Reconstruct message list for provider (System + History + User)
            messages = [{"role": "system", "content": system_prompt}]
            for m in history_messages:
                messages.append(m)
            messages.append({"role": "user", "content": final_active_query})
            
            full_answer = ""
            full_thought = ""

            # Try-Catch for Stream
            try:
                # Use stream_chat from provider
                for chunk_data in llm.chat_stream(messages, temperature=temperature):
                    # Standardize chunk data
                    
                    # Case 1: Simple String
                    if isinstance(chunk_data, str):
                        yield pack_json({"t": "token", "chunk": chunk_data})
                        full_answer += chunk_data
                        continue

                    # Case 2: Dict Response
                    if isinstance(chunk_data, dict):
                        # 2a. OpenAI Generic / DeepSeek style {type: "reasoning"|"content", content: "..."}
                        if "type" in chunk_data:
                            c_type = chunk_data["type"]
                            c_content = chunk_data.get("content", "")
                            
                            if c_type == "reasoning" or c_type == "thought":
                                yield pack_json({"t": "thought", "chunk": c_content})
                                full_thought += c_content
                            else:
                                 # Assume content
                                yield pack_json({"t": "token", "chunk": c_content})
                                full_answer += c_content
                        
                        # 2b. Legacy / Other { "content": "...", "thought": "..." }
                        else:
                             if "thought" in chunk_data and chunk_data["thought"]:
                                 yield pack_json({"t": "thought", "chunk": chunk_data["thought"]})
                                 full_thought += chunk_data["thought"]
                             if "content" in chunk_data and chunk_data["content"]:
                                 yield pack_json({"t": "token", "chunk": chunk_data["content"]})
                                 full_answer += chunk_data["content"]
            except Exception as e:
                print("Model inference failed")
                
            # Save Assistant Reply
            new_msg = BrainMessage(
                session_id=session_id_val, 
                role="assistant", 
                content=full_answer,
                thought_process=full_thought,
                citations=citations_json
            )
            # Use distinct session for save
            save_db = SharedSessionLocal()
            try:
                 save_db.add(new_msg)
                 save_db.commit()
            except Exception as e:
                 print("Message persistence failed")
            finally:
                 save_db.close()
            
            yield pack_json({"t": "done"})

        except Exception as e:
            print(f"Generator Fatal: {e}")
            import traceback
            traceback.print_exc()
            yield pack_json({"t": "error", "msg": str(e)})
        finally:
            gen_db.close()

    return StreamingResponse(generate(), media_type="text/event-stream")


# --- Title Summarization Endpoint ---
class SummaryRequest(BaseModel):
    content: str

@router.post("/summary")
async def summarize_title(request: SummaryRequest, user_id: int = Depends(get_current_user_id), db: Session = Depends(get_shared_db)):
    """Generate a short title for a given content using the active LLM."""
    content = request.content.strip().replace("\n", " ")
    if len(content) < 30:
        return {"title": content[:30]}
    active_model = get_active_kb_model(db)
    if not active_model:
        return {"title": content[:30]}
    try:
        provider_args = {
            "api_key": active_model.api_key,
            "base_url": active_model.base_url,
            "model": active_model.name
        }
        llm = ModelFactory.get_provider(active_model.type, **provider_args)
        # Prompt for title summarization
        prompt = f"请用20字以内高度概括以下内容，适合作为文档标题：\n内容：{content}\n标题："
        messages = [
            {"role": "system", "content": "你是一个擅长总结标题的AI助手。"},
            {"role": "user", "content": prompt}
        ]
        response = llm.chat(messages=messages, temperature=0.3)
        title = response.content.strip().replace("\n", " ")[:30]
        return {"title": title}
    except Exception as e:
        print(f"[SUMMARY ERROR] {e}")
        return {"title": content[:30]}

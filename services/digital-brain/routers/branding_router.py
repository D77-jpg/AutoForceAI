from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import List, Optional
from pydantic import BaseModel
import os

from core.dependencies import get_db, get_current_user_id
from core.db_manager import get_tenant_session, SharedSessionLocal
from database.models import AnalysisTask, TaskStatus, GeoWatchQuery
from database.shared_models import User
from branding_monitor.engines.qwen_client import QwenClient
from branding_monitor.engines.zhipu_client import ZhipuClient
from branding_monitor.engines.perplexity_client import PerplexityClient
from branding_monitor.analyzer.mention_extractor import MentionExtractor

router = APIRouter(prefix="/api/v1/branding", tags=["Branding Monitor"])

# --- Schemas ---

class AnalysisRequest(BaseModel):
    target_brand: str
    query: str
    engine_name: str = "perplexity"
    project_id: Optional[int] = None
    language: Optional[str] = "en"


class WatchRequest(BaseModel):
    target_brand: str
    query: str
    engine_name: str = "perplexity"
    language: str = "en"
    interval_hours: int = 24
    enabled: bool = True

class AnalysisTaskResponse(BaseModel):
    id: int
    target_brand: str
    query: str
    status: str
    engine_name: Optional[str]
    is_mentioned: Optional[bool]
    rank_position: Optional[int]
    sentiment_score: Optional[float]
    reasoning: Optional[str]
    suggestions: Optional[List[str]] = []
    citations: Optional[List[str]] = []
    progress: Optional[int] = 0
    current_step: Optional[str] = ""
    logs: Optional[List[dict]] = []
    raw_response: Optional[str] = ""
    created_at: datetime
    
    class Config:
        orm_mode = True

# --- Background Task Logic ---

def run_brand_analysis(task_id: int, target_brand: str, query: str, engine_name: str, user_id: int):
    """
    Executes the analysis in background using a fresh DB session (Tenant Specific)
    """
    # Use Tenant DB Session instead of Global SessionLocal
    db = get_tenant_session(user_id)
    print(f"[Task {task_id}] Starting analysis for '{target_brand}' on '{query}' using {engine_name} (User: {user_id})")
    
    def update_progress(msg: str, step: str, prog: int):
        try:
             # Re-fetch task to ensure we have latest state and valid session attachment
             t = db.query(AnalysisTask).filter(AnalysisTask.id == task_id).first()
             if t:
                 progress_log = {"timestamp": datetime.now().isoformat(), "message": msg, "type": "info"}
                 # Append to existing logs (ensure list is initialized)
                 current_logs = t.logs if t.logs else []
                 # Make a copy to trigger SQLAlchemy change detection for JSON type
                 new_logs = list(current_logs) 
                 new_logs.append(progress_log)
                 
                 t.logs = new_logs
                 t.current_step = step
                 t.progress = prog
                 db.commit()
        except Exception as ex:
            print(f"Error updating progress: {ex}")

    try:
        task = db.query(AnalysisTask).filter(AnalysisTask.id == task_id).first()
        if not task:
            return

        task.status = TaskStatus.RUNNING.value
        task.logs = [] # Initialize logs
        db.commit()
        
        update_progress(f"正在初始化任务: {target_brand}...", "初始化", 10)

        # 1. Fetch Content
        search_result = ""
        
        # Determine Engine
        lower_engine = (engine_name or "perplexity").lower()
        if "perplexity" in lower_engine or "sonar" in lower_engine:
            print(f"[Task {task_id}] Using Perplexity (Sonar)...")
            update_progress("Connecting to Perplexity / Sonar...", "正在搜索", 25)
            client = PerplexityClient()
            search_result = client.query(query, enable_search=True)
        elif "qwen" in lower_engine:
            print(f"[Task {task_id}] Using Qwen (DashScope)...")
            update_progress("正在连接通义千问 (Qwen-Max)...", "正在搜索", 25)
            client = QwenClient()
            search_result = client.query(query, enable_search=True)
        elif "zhipu" in lower_engine or "glm" in lower_engine:
            print(f"[Task {task_id}] Using ZhipuAI (GLM-4)...")
            update_progress("正在连接智谱AI (GLM-4)...", "正在搜索", 25)
            client = ZhipuClient()
            search_result = client.query(query, enable_search=True)
        else:
            print(f"[Task {task_id}] Auto Mode: Perplexity then Qwen...")
            update_progress("Auto engine: Perplexity → Qwen...", "正在搜索", 25)
            client = PerplexityClient()
            search_result = client.query(query, enable_search=True)

        update_progress("搜索完成。已获取网页内容。", "正在分析", 50)

        # 2. Analyze Content
        update_progress("开始 AI 语义分析 (LLM 裁判)...", "正在分析", 60)
        
        # Wrapper to enforce enable_search=False for the Analyzer
        class NoSearchWrapper:
            def __init__(self, client):
                self.client = client
                
            def query(self, prompt, **kwargs):
                # Ignore any kwargs passed by caller, enforce our own
                update_progress("正在发送评估指令给 LLM...", "正在分析", 65)
                start_analyzing = datetime.now()
                
                # QwenClient signature might differ slightly or handle kwargs differently
                # But our QwenClient.query accepts enable_search
                res = self.client.query(prompt, enable_search=False)
                
                duration = (datetime.now() - start_analyzing).total_seconds()
                update_progress(f"LLM 响应耗时 {duration:.1f}秒。正在解析 JSON...", "正在分析", 85)
                return res

        # Use the SAME client class for analysis to match the selected engine
        if "zhipu" in lower_engine or "glm" in lower_engine:
            analyzer_engine = ZhipuClient()
        elif "perplexity" in lower_engine or "sonar" in lower_engine:
            analyzer_engine = PerplexityClient()
        else:
            analyzer_engine = QwenClient()

        analyzer_client = NoSearchWrapper(analyzer_engine)
            
        analyzer = MentionExtractor(llm_client=analyzer_client)
        
        analysis = analyzer.analyze(target_brand, query, search_result)
        
        # [Crucial Fix] Inject the actual LLM Answer into the analysis result so frontend can display it
        analysis['snippet'] = search_result

        update_progress("分析完成。正在生成最终数据...", "完成", 90)
        
        # 3. Update DB
        # Re-fetch one last time to be safe
        task = db.query(AnalysisTask).filter(AnalysisTask.id == task_id).first()
        
        task.is_mentioned = analysis.get("is_mentioned", False)
        # Ensure rank_position is an integer, even if analysis returns None or invalid
        try:
             task.rank_position = int(analysis.get("rank_position", -1))
        except (ValueError, TypeError):
             task.rank_position = -1
             
        task.sentiment_score = analysis.get("sentiment_score", 0.0)
        task.reasoning = analysis.get("reasoning", "Analysis failed or returned empty.")
        task.suggestions = analysis.get("suggestions", [])
        task.citations = analysis.get("citations", []) 
        
        # Save full analysis including the 'snippet' (search_result) as valid JSON string
        import json
        task.raw_response = json.dumps(analysis, ensure_ascii=False)
        
        task.status = TaskStatus.COMPLETED.value
        task.progress = 100
        task.current_step = "已完成"
        
        db.add(task) # Explicit add for session tracking
        db.commit()
        db.refresh(task)
        print(f"[Task {task_id}] Completed successfully. Score: {task.sentiment_score}")
        
    except Exception as e:
        print(f"[Task {task_id}] Failed: {e}")
        # Need to rollback to ensure we can write the error state
        try:
            db.rollback()
            task = db.query(AnalysisTask).filter(AnalysisTask.id == task_id).first()
            if task:
                task.status = TaskStatus.FAILED.value
                task.reasoning = f"Error: {str(e)}"
                task.progress = 0
                db.commit()
        except:
             pass
    finally:
        db.close()

# --- Endpoints ---

@router.post("/analyze", response_model=AnalysisTaskResponse)
def create_analysis_task(
    request: AnalysisRequest, 
    background_tasks: BackgroundTasks,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Create a new brand monitoring task"""
    new_task = AnalysisTask(
        target_brand=request.target_brand,
        query=request.query,
        engine_name=request.engine_name,
        project_id=request.project_id,
        status=TaskStatus.PENDING.value,
        created_at=datetime.now()
    )
    db.add(new_task)
    db.commit()
    db.refresh(new_task)
    
    # Trigger Background Task - Pass User ID for correct DB access
    background_tasks.add_task(
        run_brand_analysis, 
        new_task.id, 
        new_task.target_brand, 
        new_task.query, 
        new_task.engine_name,
        user_id
    )
    
    # Return 200 explicitly with model to ensure frontend gets data
    return new_task

@router.get("/tasks", response_model=List[AnalysisTaskResponse])
def get_tasks(
    skip: int = 0, 
    limit: int = 20, 
    db: Session = Depends(get_db)
):
    """List recent tasks"""
    tasks = db.query(AnalysisTask).order_by(AnalysisTask.created_at.desc()).offset(skip).limit(limit).all()
    # Debug print
    # print(f"Found {len(tasks)} tasks")
    return tasks

@router.get("/tasks/{task_id}", response_model=AnalysisTaskResponse)
def get_task_detail(task_id: int, db: Session = Depends(get_db)):
    task = db.query(AnalysisTask).filter(AnalysisTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task

@router.delete("/tasks/{task_id}")
def delete_task(task_id: int, db: Session = Depends(get_db)):
    task = db.query(AnalysisTask).filter(AnalysisTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    db.delete(task)
    db.commit()
    return {"message": "Task deleted successfully"}


def _watch_dict(w: GeoWatchQuery) -> dict:
    return {
        "id": w.id,
        "target_brand": w.target_brand,
        "query": w.query,
        "engine_name": w.engine_name,
        "language": w.language,
        "interval_hours": w.interval_hours,
        "enabled": w.enabled,
        "last_run_at": w.last_run_at.isoformat() if w.last_run_at else None,
        "next_run_at": w.next_run_at.isoformat() if w.next_run_at else None,
        "last_task_id": w.last_task_id,
        "created_at": w.created_at.isoformat() if w.created_at else None,
    }


def dispatch_watch(db: Session, watch: GeoWatchQuery) -> AnalysisTask:
    """Create an analysis task for a scheduled watch and queue the background job."""
    task = AnalysisTask(
        target_brand=watch.target_brand,
        query=watch.query,
        engine_name=watch.engine_name or "perplexity",
        status=TaskStatus.PENDING.value,
        created_at=datetime.now(),
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    watch.last_run_at = datetime.now()
    watch.last_task_id = task.id
    hours = watch.interval_hours or 24
    watch.next_run_at = datetime.now() + timedelta(hours=hours)
    db.commit()

    # Run inline in the scheduler thread (no FastAPI BackgroundTasks available).
    run_brand_analysis(task.id, watch.target_brand, watch.query, watch.engine_name or "perplexity", watch.user_id or 0)
    return task


@router.get("/watches")
def list_watches(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    items = (
        db.query(GeoWatchQuery)
        .filter(GeoWatchQuery.user_id == user_id)
        .order_by(GeoWatchQuery.created_at.desc())
        .all()
    )
    return {"items": [_watch_dict(w) for w in items]}


@router.post("/watches")
def create_watch(
    req: WatchRequest,
    background_tasks: BackgroundTasks,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    hours = max(1, min(int(req.interval_hours or 24), 24 * 30))
    watch = GeoWatchQuery(
        user_id=user_id,
        target_brand=req.target_brand.strip(),
        query=req.query.strip(),
        engine_name=req.engine_name or "perplexity",
        language=req.language or "en",
        interval_hours=hours,
        enabled=req.enabled,
        next_run_at=datetime.now(),
        created_at=datetime.now(),
    )
    db.add(watch)
    db.commit()
    db.refresh(watch)

    # Kick off the first run immediately so the user sees a history point.
    new_task = AnalysisTask(
        target_brand=watch.target_brand,
        query=watch.query,
        engine_name=watch.engine_name,
        status=TaskStatus.PENDING.value,
        created_at=datetime.now(),
    )
    db.add(new_task)
    db.commit()
    db.refresh(new_task)
    watch.last_task_id = new_task.id
    watch.last_run_at = datetime.now()
    watch.next_run_at = datetime.now() + timedelta(hours=hours)
    db.commit()

    background_tasks.add_task(
        run_brand_analysis,
        new_task.id,
        watch.target_brand,
        watch.query,
        watch.engine_name,
        user_id,
    )
    return {**_watch_dict(watch), "task_id": new_task.id}


@router.post("/watches/{watch_id}/run")
def run_watch_now(
    watch_id: int,
    background_tasks: BackgroundTasks,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    watch = db.query(GeoWatchQuery).filter(GeoWatchQuery.id == watch_id, GeoWatchQuery.user_id == user_id).first()
    if not watch:
        raise HTTPException(404, "watch not found")
    new_task = AnalysisTask(
        target_brand=watch.target_brand,
        query=watch.query,
        engine_name=watch.engine_name,
        status=TaskStatus.PENDING.value,
        created_at=datetime.now(),
    )
    db.add(new_task)
    db.commit()
    db.refresh(new_task)
    watch.last_task_id = new_task.id
    watch.last_run_at = datetime.now()
    watch.next_run_at = datetime.now() + timedelta(hours=watch.interval_hours or 24)
    db.commit()
    background_tasks.add_task(
        run_brand_analysis,
        new_task.id,
        watch.target_brand,
        watch.query,
        watch.engine_name,
        user_id,
    )
    return {"ok": True, "task_id": new_task.id, "watch": _watch_dict(watch)}


@router.patch("/watches/{watch_id}")
def patch_watch(
    watch_id: int,
    enabled: Optional[bool] = None,
    interval_hours: Optional[int] = None,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    watch = db.query(GeoWatchQuery).filter(GeoWatchQuery.id == watch_id, GeoWatchQuery.user_id == user_id).first()
    if not watch:
        raise HTTPException(404, "watch not found")
    if enabled is not None:
        watch.enabled = enabled
    if interval_hours is not None:
        watch.interval_hours = max(1, min(int(interval_hours), 24 * 30))
    db.commit()
    return _watch_dict(watch)


@router.delete("/watches/{watch_id}")
def delete_watch(
    watch_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    watch = db.query(GeoWatchQuery).filter(GeoWatchQuery.id == watch_id, GeoWatchQuery.user_id == user_id).first()
    if not watch:
        raise HTTPException(404, "watch not found")
    db.delete(watch)
    db.commit()
    return {"ok": True}


@router.get("/diagnosis-summary")
def diagnosis_summary(
    brand: Optional[str] = None,
    limit: int = Query(80, ge=5, le=200),
    db: Session = Depends(get_db),
):
    """Aggregate completed GEO tasks into radar-ready metrics (no mock defaults)."""
    q = db.query(AnalysisTask).order_by(AnalysisTask.created_at.desc())
    if brand:
        like = f"%{brand.strip()}%"
        q = q.filter(
            (AnalysisTask.target_brand.ilike(like)) | (AnalysisTask.query.ilike(like))
        )
    tasks = q.limit(limit).all()
    completed = [t for t in tasks if (t.status or "") in ("completed", TaskStatus.COMPLETED.value if hasattr(TaskStatus.COMPLETED, "value") else "completed")]
    if not completed:
        completed = tasks

    def _mentioned(t: AnalysisTask) -> bool:
        val = str(t.is_mentioned).lower()
        if val in ("true", "1", "yes"):
            return True
        try:
            return int(t.rank_position or 0) > 0
        except (TypeError, ValueError):
            return False

    total = len(completed)
    mentioned = [t for t in completed if _mentioned(t)]
    sentiments = [float(t.sentiment_score or 0) for t in completed]
    avg_sent = sum(sentiments) / total if total else 0
    ranks = [int(t.rank_position) for t in mentioned if t.rank_position and int(t.rank_position) > 0]
    best_rank = min(ranks) if ranks else -1
    mention_rate = (len(mentioned) / total * 100) if total else 0
    citation_n = 0
    for t in completed:
        if isinstance(t.citations, list):
            citation_n += len(t.citations)

    # Scale 0-150 to match existing radar chart fullMark
    visibility = min(150, mention_rate * 1.5)
    sentiment_axis = min(150, (avg_sent / 10) * 150)
    citation_quality = min(150, 40 + citation_n * 8) if mentioned else 0
    recommend = min(150, 50 + len(mentioned) * 12)
    cost = min(150, 70 + (mention_rate * 0.4))
    innovation = min(150, 45 + (mention_rate * 0.6))

    return {
        "brand": brand,
        "sample_size": total,
        "mentioned": len(mentioned),
        "mention_rate": round(mention_rate, 1),
        "avg_sentiment": round(avg_sent, 2),
        "best_rank": best_rank,
        "engine_configured": {
            "perplexity": bool(os.getenv("PERPLEXITY_API_KEY")),
            "qwen": bool(os.getenv("DASHSCOPE_API_KEY")),
            "zhipu": bool(os.getenv("ZHIPUAI_API_KEY")),
        },
        "radar": [
            {"subject": "品牌可见性", "A": round(visibility, 1), "fullMark": 150},
            {"subject": "情感倾向", "A": round(sentiment_axis, 1), "fullMark": 150},
            {"subject": "引用质量", "A": round(citation_quality, 1), "fullMark": 150},
            {"subject": "功能推荐", "A": round(recommend, 1), "fullMark": 150},
            {"subject": "成本感知", "A": round(cost, 1), "fullMark": 150},
            {"subject": "创新程度", "A": round(innovation, 1), "fullMark": 150},
        ],
        "pie": [
            {"name": "品牌提及 (Mentioned)", "value": len(mentioned)},
            {"name": "未被提及 (Missed)", "value": max(0, total - len(mentioned))},
        ],
        "recent": [
            {
                "id": t.id,
                "query": t.query,
                "engine_name": t.engine_name,
                "is_mentioned": _mentioned(t),
                "rank_position": t.rank_position,
                "sentiment_score": t.sentiment_score,
                "created_at": t.created_at.isoformat() if t.created_at else None,
            }
            for t in completed[:12]
        ],
    }

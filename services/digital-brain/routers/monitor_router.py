from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Dict, Any
from datetime import datetime, timedelta, timezone
import platform
try:
    import psutil
except ImportError:
    psutil = None

from core.dependencies import get_db
from core.db_manager import SharedSessionLocal, get_shared_db 
# Fix: RPAJob moved to shared_models
from database.shared_models import LLMRequestLog, RPAJobStatus, LLMModel, User, InspectionRecord, BrainSession, QualityRule
from database.models import RPAJob
from core.quality.inspector import SessionInspector
from fastapi import BackgroundTasks


router = APIRouter(prefix="/api/v1/monitor", tags=["Monitoring"])

def get_shared_db_local(): # Rename to avoid conflict if already imported
    """Dependency for Shared DB (Logs)"""
    db = SharedSessionLocal()
    try:
        yield db
    finally:
        db.close()

from pydantic import BaseModel

class QualityRuleBase(BaseModel):
    name: str
    description: str
    weight: float = 1.0
    is_active: bool = True

class QualityRuleCreate(QualityRuleBase):
    pass

class QualityRuleUpdate(QualityRuleBase):
    pass

# --- Quality Rule Configuration Endpoints ---

@router.get("/inspection/rules")
def get_quality_rules(db: Session = Depends(get_shared_db)):
    """获取所有质检规则"""
    rules = db.query(QualityRule).order_by(QualityRule.id).all()
    return rules

@router.post("/inspection/rules")
def create_quality_rule(rule: QualityRuleCreate, db: Session = Depends(get_shared_db)):
    """创建新的质检规则"""
    db_rule = QualityRule(**rule.dict())
    db.add(db_rule)
    db.commit()
    db.refresh(db_rule)
    return db_rule

@router.put("/inspection/rules/{rule_id}")
def update_quality_rule(rule_id: int, rule: QualityRuleUpdate, db: Session = Depends(get_shared_db)):
    """更新质检规则"""
    db_rule = db.query(QualityRule).filter(QualityRule.id == rule_id).first()
    if not db_rule:
        return {"error": "Rule not found"}
    
    for key, value in rule.dict().items():
        setattr(db_rule, key, value)
    
    db.commit()
    db.refresh(db_rule)
    return db_rule

@router.delete("/inspection/rules/{rule_id}")
def delete_quality_rule(rule_id: int, db: Session = Depends(get_shared_db)):
    """删除质检规则"""
    db_rule = db.query(QualityRule).filter(QualityRule.id == rule_id).first()
    if not db_rule:
        return {"error": "Rule not found"}
    
    db.delete(db_rule)
    db.commit()
    return {"status": "success", "message": "Rule deleted"}

# --- Quality Inspection Endpoints ---

@router.get("/inspection/stats")
def get_inspection_stats(db: Session = Depends(get_shared_db)):
    """Get summarized quality metrics for dashboard"""
    # 1. KPI Cards
    total_records = db.query(InspectionRecord).count()
    if total_records == 0:
        return {"avg_score": 0, "issue_count": 0, "critical_count": 0}
        
    avg_score = db.query(func.avg(InspectionRecord.total_score)).scalar() or 0
    critical_count = db.query(InspectionRecord).filter(InspectionRecord.status == "Critical").count()
    
    # 2. Issues Breakdown (Need to parse JSON, simplify for now by counting records with issues)
    # Ideally should flatten the JSON array
    # For MVP, we return simple stats
    
    return {
        "avg_score": round(avg_score, 1),
        "total_inspections": total_records,
        "critical_sessions": critical_count,
    }

@router.post("/inspection/{session_id}")
def trigger_inspection(session_id: int, background_tasks: BackgroundTasks, db: Session = Depends(get_shared_db)):
    """Manually trigger an AI inspection for a session"""
    session = db.query(BrainSession).filter(BrainSession.id == session_id).first()
    if not session:
        return {"error": "Session not found"}
    
    inspector = SessionInspector(db)
    # Run in background to avoid blocking
    background_tasks.add_task(inspector.inspect, session_id)
    
    return {"status": "queued", "message": f"Inspection started for Session {session_id}"}


@router.get("/inspection/records")
def get_inspection_records(limit: int = 50, db: Session = Depends(get_shared_db)):
    """Get list of recent inspections with session details"""
    records = db.query(
            InspectionRecord, 
            User.nickname,
            BrainSession.title, 
            BrainSession.created_at.label("session_time")
        )\
        .join(BrainSession, InspectionRecord.session_id == BrainSession.id)\
        .outerjoin(User, BrainSession.user_id == User.id)\
        .order_by(InspectionRecord.created_at.desc())\
        .limit(limit)\
        .all()
    
    result = []
    for r, nickname, title, s_time in records:
        result.append({
            "id": r.id,
            "session_id": r.session_id,
            "user_id": r.session_id, # Keep for ID ref
            "user_nickname": nickname or f"User_{r.session_id}",
            "topic": title,
            "score": r.total_score,
            "status": r.status,
            "time": s_time,
            "issues": r.issues,
            "suggestion": r.suggestion,
            "issues_count": len(r.issues) if r.issues else 0
        })
    return result

@router.get("/system")
def get_system_status(db: Session = Depends(get_shared_db)):
    """Get System Health & Resource Usage"""
    
    # System Info
    try:
        cpu_percent = psutil.cpu_percent(interval=None) if psutil else None
        memory = psutil.virtual_memory() if psutil else None
    except Exception:
        cpu_percent, memory = None, None
    
    # DB Counts
    def safe_count(query):
        try:
            return query.count()
        except Exception:
            db.rollback()
            return None

    active_models = safe_count(db.query(LLMModel).filter(LLMModel.is_active == True))
    active_users = safe_count(db.query(User).filter(User.is_active == True))
    queued_jobs = safe_count(db.query(RPAJob).filter(RPAJob.status == "queued"))
    
    return {
        "status": "healthy" if cpu_percent is not None and all(value is not None for value in (active_models, active_users, queued_jobs)) else "partial",
        "cpu_usage": cpu_percent,
        "memory_usage": {
            "total": memory.total if memory else None,
            "used": memory.used if memory else None,
            "percent": memory.percent if memory else None
        },
        "system_info": {
            "platform": platform.system(),
            "release": platform.release(),
            "python_version": platform.python_version()
        },
        "resources": {
            "active_models": active_models,
            "active_users": active_users,
            "queued_jobs": queued_jobs
        }
    }

@router.get("/rpa/stats")
def get_rpa_stats(db: Session = Depends(get_shared_db)): # Use shared_db for RPAJob now
    """Get RPA Job counts by status"""
    # Group by status
    stats = db.query(RPAJob.status, func.count(RPAJob.id)).group_by(RPAJob.status).all()
    result = {k: 0 for k in ["queued", "claimed", "running", "success", "completed", "failed"]}
    
    # Map ENUM to Frontend keys if they differ, otherwise just use as is
    for status, count in stats:
        result[str(status)] = count
        
    # Get recent failures
    failed_jobs = db.query(RPAJob).filter(RPAJob.status == "failed").order_by(RPAJob.created_at.desc()).limit(5).all()
    
    return {
        "counts": result,
        "recent_failures": [
            {"id": j.id, "platform": j.platform, "msg": "RPA task failed", "time": j.created_at}
            for j in failed_jobs
        ]
    }

@router.get("/llm/usage")
def get_llm_usage(days: int = Query(7, ge=1, le=366), db: Session = Depends(get_shared_db)):
    """Return the last `days` UTC calendar dates, including today and empty dates.

    Existing database timestamps are timezone-naive; they are interpreted as UTC.
    Only independently verified persisted prices contribute to cost_usd; if
    any call has unknown cost, the bucket remains null. No price is guessed.
    """
    today = datetime.now(timezone.utc).date()
    first_day = today - timedelta(days=days - 1)
    start = datetime.combine(first_day, datetime.min.time())
    end = datetime.combine(today + timedelta(days=1), datetime.min.time())

    daily_stats = {
        (first_day + timedelta(days=offset)).isoformat(): {
            "date": (first_day + timedelta(days=offset)).isoformat(),
            "tokens": 0, "calls": 0, "success": 0, "failure": 0,
            "cost_usd": None,
        }
        for offset in range(days)
    }
    provider_stats = {}
    summary = {"total_tokens": 0, "total_calls": 0, "success": 0,
               "failure": 0, "cost_usd": None}

    # Half-open boundaries keep midnight in exactly one UTC calendar bucket.
    # DateTime columns store naive timestamps; avoid dialect-specific date_trunc/strftime.
    logs = db.query(LLMRequestLog).filter(
        LLMRequestLog.created_at >= start, LLMRequestLog.created_at < end
    ).all()
    for log in logs:
        timestamp = log.created_at
        day = (timestamp.replace(tzinfo=timezone.utc) if timestamp.tzinfo is None
               else timestamp.astimezone(timezone.utc)).date().isoformat()
        stats = daily_stats[day]
        tokens = log.total_tokens or 0
        outcome = "success" if log.status == "success" else "failure"
        stats["tokens"] += tokens
        if log.cost_usd is not None and stats["cost_usd"] is not None:
            stats["cost_usd"] += log.cost_usd
        stats["calls"] += 1
        stats[outcome] += 1
        provider = log.provider or "unknown"
        provider_stats[provider] = provider_stats.get(provider, 0) + tokens
        summary["total_tokens"] += tokens
        summary["total_calls"] += 1
        summary[outcome] += 1

    return {"summary": summary, "daily_trend": list(daily_stats.values()),
            "by_provider": provider_stats}

@router.get("/llm/logs")
def get_recent_logs(limit: int = Query(50, ge=1, le=200), db: Session = Depends(get_shared_db)):
    rows = db.query(LLMRequestLog).order_by(LLMRequestLog.created_at.desc()).limit(limit).all()
    return [{"id": row.id, "created_at": row.created_at, "provider": row.provider,
             "model": row.model, "input_tokens": row.input_tokens,
             "output_tokens": row.output_tokens, "total_tokens": row.total_tokens,
             "latency_ms": row.latency_ms, "status": row.status,
             "error_category": row.error_category, "cost_usd": row.cost_usd}
            for row in rows]

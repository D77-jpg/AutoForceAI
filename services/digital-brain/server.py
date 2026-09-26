import os
import json
import time
import uuid
import uvicorn
from contextlib import asynccontextmanager
from hmac import compare_digest
from datetime import datetime
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional, List
from dotenv import load_dotenv

# Database Models (Tenant Specific models are imported for Type Hints, but not Init)
from database.models import AnalysisTask, TaskStatus, ContentAsset

# SaaS New Architecture Imports
from database.shared_models import SharedBase, RPAJobStatus
from database.models import RPAJob
from core.db_manager import SHARED_ENGINE, SharedSessionLocal, get_shared_db, init_shared_db
from routers import auth_router, monitor_router, bot_router, branding_router, content_router, agent_router, platform_router, storage_router, brain_router, export_router, admin_router
from routers import kb_router, service_chat_router, lead_router, marketing_router, crm_integration_router, quotation_router, alert_router
from core.dependencies import get_db, get_current_user_id
from core.config import settings
from core.security_cors import allowed_origins
from core.security_rate_limit import enforce_rate_limit
from fastapi.staticfiles import StaticFiles

# --- Missing Imports Added ---
from branding_monitor.engines.zhipu_client import ZhipuClient
from branding_monitor.engines.qwen_client import QwenClient
from branding_monitor.analyzer.mention_extractor import MentionExtractor

# AI Platforms (Refactored)
# from core.llm.factory import ModelFactory
from core.llm.monitor import CostMonitor
from branding_monitor.engines.perplexity_client import MockPerplexityClient # Keep Mock for now or refactor later
from branding_monitor.analyzer.mention_extractor import MentionExtractor

# 加载环境变量
load_dotenv()

# Lifecycle Manager 
@asynccontextmanager
async def lifespan(app: FastAPI):
    print(">>> [System] Digital Brain Service Starting - DeepSeek DB Support Enabled <<<")
    # Initialize Shared Database (Users)
    init_shared_db()
    
    print("[OK] Connected to Digital Employee Shared Database")
    try:
        from core.geo_scheduler import start as start_geo_scheduler
        start_geo_scheduler(interval_seconds=int(os.getenv("GEO_SCHEDULER_INTERVAL", "60")))
    except Exception:
        print("[Warn] GEO scheduler not started")
    # Retention is bounded and only removes resolved incidents. Never let
    # retention failure prevent the main service from starting.
    try:
        from core.alerts import cleanup_resolved, validate_notifications_disabled
        validate_notifications_disabled()
        with SharedSessionLocal() as cleanup_db:
            cleanup_resolved(cleanup_db)
            cleanup_db.commit()
    except ValueError:
        raise  # Unsafe notification configuration must fail closed at startup.
    except Exception:
        import logging
        logging.getLogger("autoforce.alerts").warning("Alert retention cleanup unavailable")
    # CRM Outbox 投递器（阶段 2 Wave C）：租约抢占 + 退避 + 死信
    try:
        from core.crm.dispatcher import start_dispatcher
        start_dispatcher()
    except Exception:
        print("[Warn] CRM dispatcher not started")
    yield
    try:
        from core.crm.dispatcher import stop_dispatcher
        stop_dispatcher()
    except Exception:
        pass
    try:
        from core.geo_scheduler import stop as stop_geo_scheduler
        stop_geo_scheduler()
    except Exception:
        pass

app = FastAPI(title="Digital Employee SaaS API", version="2.0.0", lifespan=lifespan)

@app.middleware("http")
async def request_metadata_log(request: Request, call_next):
    """Log only safe request metadata, never headers, URL query or request body."""
    request_id = str(uuid.uuid4())
    start = time.monotonic()
    route = "unmatched"
    status = 500
    try:
        denied = enforce_rate_limit(request)
        response = denied if denied is not None else await call_next(request)
        status = response.status_code
        matched = request.scope.get("route")
        route = getattr(matched, "path", "unmatched")
        response.headers["X-Request-ID"] = request_id
        return response
    finally:
        import logging
        logging.getLogger("autoforce.api").info(json.dumps({
            "request_id": request_id, "route": route, "status": status,
            "latency_ms": round((time.monotonic() - start) * 1000, 2),
            # Only trusted auth dependencies can resolve organization; do not
            # infer it from caller-controlled headers, params or unverified JWT.
            "organization": getattr(request.state, "organization_id", None),
        }, separators=(",", ":")))

# Add CORS Middleware - CRITICAL for Direct Browser Access & Streaming
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files for uploads
# Make sure directory exists
if not os.path.exists("storage/uploads"):
    os.makedirs("storage/uploads")
app.mount("/uploads", StaticFiles(directory="storage/uploads"), name="uploads")

# Chat widget (embeddable JS for independent sites)
_WIDGET_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "apps", "chat-widget"))
if os.path.isdir(_WIDGET_DIR):
    app.mount("/widget", StaticFiles(directory=_WIDGET_DIR), name="chat-widget")

from fastapi.exceptions import RequestValidationError
from starlette.requests import Request
from fastapi.responses import JSONResponse

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    # Validation errors can include submitted passwords/tokens in `input`.
    # Never print them or echo them to clients.
    return JSONResponse(
        status_code=422,
        content={"detail": "Invalid request data"},
    )

from routers import solution_router, ppt_template_router

# Include Routers
app.include_router(auth_router.router)
app.include_router(ppt_template_router.router)
app.include_router(monitor_router.router)
app.include_router(alert_router.router)
app.include_router(kb_router.router)
app.include_router(bot_router.router)
app.include_router(storage_router.router)
app.include_router(content_router.router)
# app.include_router(chat_router.router) # Excluded
app.include_router(branding_router.router)
app.include_router(agent_router.router)
app.include_router(platform_router.router)
app.include_router(brain_router.router)
app.include_router(export_router.router)
app.include_router(service_chat_router.router)
app.include_router(lead_router.router)
app.include_router(crm_integration_router.router)
app.include_router(quotation_router.router)
app.include_router(marketing_router.router)
app.include_router(solution_router.router)
app.include_router(admin_router.router)

# Lightweight health check
@app.get("/health")
def health():
    return {"status": "ok"}


# Debug jobs endpoint (bypass routers) to quickly verify DB visibility
@app.get("/debug/jobs")
def debug_jobs(limit: int = 20, db: Session = Depends(get_shared_db)):
    jobs = db.query(RPAJob).order_by(RPAJob.created_at.desc()).limit(limit).all()
    print(f"[DEBUG] Queried {len(jobs)} jobs: {[j.id for j in jobs]}")
    return [
        {
            "id": job.id,
            "platform": job.platform,
            "job_type": job.job_type,
            "status": job.status,
            "created_at": job.created_at.isoformat(),
            "payload": job.payload
        }
        for job in jobs
    ]

class PublishRequest(BaseModel):
    platform: str
    title: str
    content: str

# RPA Trigger View Endpoint
# Support both paths to handle different client configurations and legacy links
@app.get("/rpa/trigger-view")
@app.get("/api/v1/rpa/trigger-view")
def trigger_view(
    url: str, 
    platform: str = "xiaohongshu", 
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_shared_db)
):
    # Create a transient high-priority job for RPA to open the browser
    # This job is purely for viewing/debugging
    job = RPAJob(
        user_id=user_id,
        platform=platform,
        job_type="view_browser",
        status="queued",
        payload={
            "url": url, 
            "action": "view_only"
        }
    )
    db.add(job)
    db.commit()
    
    return {
        "msg": "已发送指令给 RPA 机器人。请查看 RPA 机器人的屏幕窗口。", 
        "target_url": url,
        "job_id": job.id
    }

# Forced Reload Trigger
print("[INFO] Server Routers Loaded - V2")

# 配置 CORS
# app.add_middleware(
#    CORSMiddleware,
#    allow_origins=["*"],  # 生产环境请修改为前端的实际域名
#    allow_credentials=True,
#    allow_methods=["*"],
#    allow_headers=["*"],
# )

# NOTE: The local get_db() has been replaced by core.dependencies.get_db
# which supports Multi-Tenancy (Physical Isolation).


# --- Pydantic Models (请求/响应结构) ---

class MonitorRequest(BaseModel):
    brand_name: str
    query: str
    engine: str = "auto" # auto, zhipu, qwen, mock

class AnalysisResponse(BaseModel):
    task_id: int
    status: str
    message: str

# --- 核心逻辑 ---


def generate_optimization_suggestions(result: dict, query: str) -> List[str]:
    """
    根据分析结果生成 GEO 优化建议
    """
    suggestions = []
    
    # 场景 1: 完全未提及
    if not result.get("is_mentioned"):
        suggestions.append(f"🔴 **必须增加品牌曝光**: 您的品牌完全未出现在搜索结果中。建议在排名靠前的竞争对手出现的页面（如 {', '.join(result.get('citations', [])[:3])}）投放内容。")
        suggestions.append(f"📝 **优化内容结构**: 在官网创建一篇标题为 '{query}' 的博客文章，并使用 H2/H3 标题清晰罗列产品优势。")
        suggestions.append("📊 **添加对比表格**: 在着陆页增加与竞品的参数对比表，AI 极易抓取表格数据。")
        
    # 场景 2: 提及但排名低
    elif result.get("rank_position", -1) > 3:
        suggestions.append("📉 **提升排名**: 尝试修改页面 Meta Description，强调'2026最新'、'性价比'等 AI 高频抓取的关键词。")
        suggestions.append("🔗 **增加权威外链**: 寻找高权重的行业媒体进行报道，提高域名的 Authority。")
    
    # 场景 3: 情感分低
    if result.get("sentiment_score", 0) < 6:
        suggestions.append("❤️ **情感修复**: AI 正在引用负面评价。请排查 Trustpilot 或 Reddit 上的差评并进行公关回复。")

    suggestions.append("🤖 **Schema 标记**: 确保官网首页包含 'Product' 和 'FAQPage' 的 JSON-LD 结构化数据。")
    
    return suggestions

# --- 集成层: 第三方 API 适配器 ---
import requests

class PlatformConnector:
    """
    负责与第三方发布平台进行 API 通信
    """
    
    @staticmethod
    def push_to_wordpress(title: str, content: str):
        """
        示例：通过 REST API 推送到 WordPress (Direct Mode)
        """
        from core.wordpress import publish_post
        print(f"   [Connect] 连接到 WordPress API...")
        return publish_post(title, content, status="draft")

    @staticmethod
    def trigger_rpa_agent(platform: str, content: str):
        """
        示例：调用内部 RPA 服务或第三方矩阵管理平台 (RPA Bridge Mode)
        针对知乎/小红书等无开放 API 的平台
        """
        rpa_service_url = os.getenv("RPA_SERVICE_URL", "http://localhost:9000/api/task")
        print(f"   [Connect] 唤醒 RPA 机器人代理: 目标平台 {platform}...")
        
        # 模拟发送指令给 RPA 集群
        # payload = {
        #    "action": "post_article",
        #    "platform": platform,
        #    "data": {"content": content, "images": []}
        # }
        # requests.post(rpa_service_url, json=payload)
        
        return {"job_id": "job_zh_8821", "queue_position": 2, "estimated_time": "30s"}

# --- Tasks ---

def perform_analysis_task(task_id: int, request: MonitorRequest):
    """
    后台任务：执行 AI 搜索与分析，并更新数据库
    """
    print(f"[Task] 开始处理任务 #{task_id}")
    
    db = SessionLocal()
    # 使用 AnalysisTask
    task = db.query(AnalysisTask).filter(AnalysisTask.id == task_id).first()
    
    def update_progress(progress: int, step: str, info: str = None):
        try:
            task.progress = progress
            task.current_step = step
            if info:
                # Copied lists to ensure SQLAlchemy detects changes
                current_logs = list(task.logs) if task.logs else []
                current_logs.append({
                    "timestamp": datetime.now().isoformat(),
                    "message": info,
                    "type": "info"
                })
                task.logs = current_logs
            db.commit()
        except Exception as e:
            print("Update progress failed")

    try:
        task.status = TaskStatus.RUNNING.value
        update_progress(5, "初始化任务", f"开始处理任务: {request.brand_name}")

        # 1. 选择引擎
        engine_client = None
        engine_name = "Mock"
        
        update_progress(10, "选择 AI 引擎", "正在根据配置选择合适的 AI 引擎...")
        
        # 优先检测 Key
        zhipu_key = os.getenv("ZHIPUAI_API_KEY")
        dash_key = os.getenv("DASHSCOPE_API_KEY")
        
        if request.engine == "zhipu" or (request.engine == "auto" and zhipu_key):
            # engine_client = ModelFactory.get_provider("zhipu")
            engine_client = None # ModelFactory disabled
            engine_name = "ZhipuGLM-4"
        elif request.engine == "qwen" or (request.engine == "auto" and dash_key):
            # engine_client = ModelFactory.get_provider("qwen")
            engine_client = None # ModelFactory disabled
            engine_name = "QwenMax"
        else:
            engine_client = MockPerplexityClient()

        # 2. 获取 AI 回答
        update_progress(20, "AI 搜索中", f"使用引擎: {engine_name} 进行搜索...")
        print(f"   [Engine] 使用引擎: {engine_name}")
        
        # Check if it's new Middle Platform LLM or Legacy Mock
        if hasattr(engine_client, 'chat'):
            start_t = datetime.now()
            llm_resp = engine_client.chat(
                messages=[{"role": "user", "content": request.query}],
                enable_search=True
            )
            ai_response = llm_resp.content
            
            # Log Search Usage
            if llm_resp.usage:
                CostMonitor.log_request(
                    provider=getattr(engine_client, 'provider_name', None) or 'unknown',
                    model=getattr(llm_resp, 'model_name', None) or 'unknown',
                    input_tokens=llm_resp.usage.get('input_tokens',0),
                    output_tokens=llm_resp.usage.get('output_tokens',0),
                    latency_ms=int((datetime.now() - start_t).total_seconds() * 1000),
                    status="success"
                )
        else:
            ai_response = engine_client.query(request.query)
        
        update_progress(50, "分析 AI 回答", "获得搜索结果，正在进行内容分析...")
        
        # 3. 分析回答
        print(f"   [Analyzer] 开始分析...")
        analyzer = MentionExtractor(llm_client=engine_client)
        result = analyzer.analyze(request.brand_name, request.query, ai_response)
        
        update_progress(70, "生成建议", "正在基于分析结果生成优化建议...")
        
        # 生成建议
        advice_list = generate_optimization_suggestions(result, request.query)

        update_progress(90, "保存结果", "正在保存最终结果...")

        # 4. 更新数据库
        task.engine_name = engine_name
        task.raw_response = ai_response
        task.is_mentioned = result.get("is_mentioned", False)
        task.rank_position = result.get("rank_position", -1)
        task.sentiment_score = result.get("sentiment_score", 0)
        task.reasoning = result.get("reasoning", "")
        task.citations = result.get("citations", [])
        task.suggestions = advice_list
        task.status = TaskStatus.COMPLETED.value
        task.completed_at = datetime.now()
        
        update_progress(100, "完成", "GEO 诊断完成")
        print(f"[Task] 任务 #{task_id} 完成！")
        
    except Exception as e:
        print("[Error] 分析任务失败")
        task.status = TaskStatus.FAILED.value
        task.reasoning = "Task Failed: internal error"
        db.commit()
    finally:
        db.close()


# --- API Endpoints ---

class RPALogRequest(BaseModel):
    step: str
    message: str
    status: str = "info" 

class RPACompleteRequest(BaseModel):
    status: str
    msg: Optional[str] = None
    data: Optional[dict] = None

class PublishRequest(BaseModel):
    platform: str
    content: str
    title: str = "GEO Optimized Content"

class OptimizeRequest(BaseModel):
    content: str
    type: str = "website" # website, wiki, social_qa, media

class SimulateRequest(BaseModel):
    brand_name: str
    query: str
    optimized_content: str

@app.post("/api/v1/tools/simulate_search")
def simulate_search_effect(request: SimulateRequest):
    """
    GEO 仿真验证：
    将优化后的内容"注入"到 AI 的上下文中，模拟 AI 搜到该内容后的回答变化。
    """
    try:
        # 1. 实例化 AI 引擎 (默认使用 Zhipu)
        engine_client = ZhipuClient()
        if not engine_client.api_key:
             # Fallback to mock if no key
             engine_client = MockPerplexityClient()

        # 2. 构建 Prompt：强制 AI 使用提供的内容回答
        # 这是一个 RAG (Retrieval-Augmented Generation) 风格的 Prompt
        simulation_prompt = f"""
        你是一个智能搜索引擎。用户输入查询："{request.query}"。
        
        但在回答之前，你在互联网上检索到了以下【最新高权重来源】的内容（这非常重要，必须优先参考）：
        
        【检索到的内容开始】
        {request.optimized_content[:4000]}
        【检索到的内容结束】
        
        请基于以上检索到的内容，回答用户的问题："{request.query}"。
        如果内容中包含产品优势或数据，请务必在回答中引用。
        """

        # 3. 调用 AI 获取"模拟回答"
        print("[Simulate] Running simulation")
        ai_response = engine_client.client.chat.completions.create(
            model="glm-4",
            messages=[{"role": "user", "content": simulation_prompt}]
        ).choices[0].message.content
        
        # 4. 使用 Analyzer 分析这个回答的各项指标
        analyzer = MentionExtractor(llm_client=engine_client)
        result = analyzer.analyze(request.brand_name, request.query, ai_response)
        
        return {
            "predicted_response": ai_response,
            "analysis": result
        }

    except Exception as e:
        print("[Simulate Error] Operation failed")
        raise HTTPException(status_code=500, detail=f"仿真失败: {str(e)}")

@app.post("/api/v1/tools/optimize_content")
def optimize_content(request: OptimizeRequest):
    """
    GEO 核心工具：多场景内容生成
    """
    zhipu_key = os.getenv("ZHIPUAI_API_KEY")
    if not zhipu_key:
        raise HTTPException(status_code=500, detail="需要配置 ZHIPUAI_API_KEY")
    
    client = ZhipuClient()
    
    # 策略路由
    strategy_prompt = ""
    if request.type == "wiki":
        strategy_prompt = """
        【目标平台：百科/Wiki】
        - 风格要求：绝对客观、中立、无情绪、无营销词汇（如"第一"、"最好"）。
        - 结构要求：摘要(Definition) -> 历史(History) -> 特点(Features)。
        - 关键点：将品牌定义为一个行业术语或技术实体。
        - 额外输出：生成一段标准的 Infobox (信息框) 文本。
        """
    elif request.type == "social_qa":
        strategy_prompt = """
        【目标平台：知乎/Quora/Reddit】
        - 风格要求：专业KOL口吻，"谢邀"，先给核心结论，再展开逻辑。
        - 结构要求：结论 -> 真实痛点场景 -> 解决方案对比 -> 最终推荐。
        - 关键点：多用"亲测"、"踩坑"等体验类词汇，AI 认为这类信息具有高独特性。
        - 额外输出：无 JSON-LD，但输出 3-5 个适合该内容的"提问标题"。
        """
    elif request.type == "media":
        strategy_prompt = """
        【目标平台：新闻媒体/PR】
        - 风格要求：新闻报道风格，第三人称。
        - 结构要求：倒金字塔结构（最重要信息在第一段）。
        - 关键点：强调"行业首发"、"数据增长"、"战略合作"等事实。
        """
    else: # website
        strategy_prompt = """
        【目标平台：品牌官网】
        - 风格要求：直接答案 (Direct Answer)，营销与信息并重。
        - 额外输出：生成 Schema.org JSON-LD 代码。
        """

    prompt = f"""
    你是一个 GEO 专家。请将以下原始内容，改写为适合【{request.type}】平台发布的内容，以最大化被 AI 收录的概率。
    
    {strategy_prompt}
    
    原始内容:
    {request.content[:2000]}
    
    请输出两部分，用 "|||GEO_SPLIT|||" 分隔：
    第一部分：优化后的正文
    第二部分：附带代码或额外元数据 (JSON-LD 或 Infobox 或 推荐标题)
    """
    
    try:
        # 调用 GLM-4 生成
        response = client.client.chat.completions.create(
            model="glm-4",
            messages=[{"role": "user", "content": prompt}]
        )
        full_text = response.choices[0].message.content
        
        # 分割结果
        parts = full_text.split("|||GEO_SPLIT|||")
        optimized_text = parts[0].strip()
        json_ld = parts[1].strip() if len(parts) > 1 else ""
        
        # Fallback: 如果只有 JSON 或分割失败导致正文为空，但总文本不为空
        if not optimized_text and full_text.strip():
            # 简单策略：如果没找到分隔符，或者分隔符在最前面
            if "|||GEO_SPLIT|||" not in full_text:
                optimized_text = full_text.strip()
            # 如果分隔符在最前面，说明全是 JSON LD? 
            # 这种情况比较少见，通常 GLM-4 还是比较听话的
        
        # 清洗一下 json_ld 如果包含 markdown 标记
        json_ld = json_ld.replace("```json", "").replace("```html", "").replace("```", "").strip()
        
        return {
            "optimized_content": optimized_text,
            "json_ld_snippet": json_ld
        }
    except Exception as e:
        print("[Optimize Error] Operation failed") # Add logging
        raise HTTPException(status_code=500, detail=f"Generation Error: {str(e)}")


class PublishRequest(BaseModel):
    platform: str
    content: str
    title: str = "GEO Optimized Content"

class RPACompleteRequest(BaseModel):
    status: str
    msg: Optional[str] = None
    data: Optional[dict] = None

class RPALogRequest(BaseModel):
    step: str
    message: str
    status: str = "info" # info, success, warning, error, pending

# --- RPA 任务管理 (Database Backend) ---

def require_worker_key(candidate: Optional[str]) -> None:
    """No worker endpoint may accept a missing/empty configured secret."""
    expected = settings.worker_secret
    if not expected or not candidate or not compare_digest(candidate, expected):
        raise HTTPException(status_code=401, detail="Invalid Worker Key")


@app.post("/api/v1/rpa/tasks/{task_id}/log")
def append_rpa_log(
    task_id: int, 
    request: RPALogRequest, 
    x_worker_key: str = Header(None, alias="X-Worker-Key"),
    db: Session = Depends(get_shared_db)
):
    """
    RPA 机器人专用接口：实时汇报执行步骤
    """
    require_worker_key(x_worker_key)

    import traceback
    try:
        job = db.query(RPAJob).filter(RPAJob.id == task_id).first()
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        # Python timestamp
        import time
        entry = {
             "timestamp": time.time(),
             "step": request.step,
             "message": request.message,
             "status": request.status
        }
        
        # Safe JSON handling
        logs = job.execution_logs
        if logs is None:
            logs = []
        elif isinstance(logs, str):
            # Should not happen in proper JSON column, but defensiveness for SQLite
            import json
            try:
                logs = json.loads(logs)
            except:
                logs = []
        
        # Ensure it's a list
        if not isinstance(logs, list):
            logs = [logs] if logs else []

        logs.append(entry)
        
        job.execution_logs = logs
        
        from datetime import datetime
        job.updated_at = datetime.now()
        
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(job, "execution_logs")
        
        db.commit()
        return {"status": "logged"}
    except Exception as e:
        print("[RPA Log Error] Failed to append log")
        raise HTTPException(status_code=500, detail="Unable to append worker log")

@app.post("/api/v1/rpa/tasks/{task_id}/retry")
def retry_rpa_task(
    task_id: int, 
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_shared_db)
):
    """
    重试失败的 RPA 任务
    """
    job = db.query(RPAJob).filter(RPAJob.id == task_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Reset state
    job.status = RPAJobStatus.QUEUED.value
    job.retry_count = (job.retry_count or 0) + 1
    job.result_log = f"Retrying... (Attempt {job.retry_count})"
    job.worker_id = None
    job.completed_at = None
    
    # Log the retry action
    from datetime import datetime
    import time
    
    entry = {
         "timestamp": time.time(),
         "step": "System",
         "message": f"Manual Retry triggered. Attempt #{job.retry_count}",
         "status": "warning"
    }
    
    # Handle existing logs
    logs = job.execution_logs
    if not isinstance(logs, list):
        logs = []
    logs.append(entry)
    
    job.execution_logs = logs
    job.updated_at = datetime.now()
    
    from sqlalchemy.orm.attributes import flag_modified
    flag_modified(job, "execution_logs")
    
    db.commit()
    return {"status": "queued", "msg": "Task re-queued successfully"}


@app.post("/api/v1/rpa/tasks/{task_id}/cancel")
def cancel_rpa_task(
    task_id: int, 
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_shared_db)
):
    """
    手动取消/停止任务
    """
    job = db.query(RPAJob).filter(RPAJob.id == task_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job.status = RPAJobStatus.FAILED.value
    job.result_log = "用户手动停止任务"
    
    from datetime import datetime
    job.completed_at = datetime.now()
    job.updated_at = datetime.now()

    db.commit()
    return {"status": "cancelled", "msg": "Task marked as failed."}

from core.dependencies import get_current_user_id

@app.delete("/api/v1/rpa/tasks/{task_id}")
def delete_rpa_task(task_id: int, user_id: int = Depends(get_current_user_id), db: Session = Depends(get_shared_db)):
    """
    删除任务记录 (Global Job Queue)
    """
    job = db.query(RPAJob).filter(RPAJob.id == task_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
        
    # Check permission: allow if owner, or if job has no owner, or if user is admin/enterprise_admin
    if job.user_id is not None and job.user_id != user_id:
         # Check if current user is admin
         from database.shared_models import User, UserRole
         current_user = db.query(User).filter(User.id == user_id).first()
         if not current_user or current_user.role not in (UserRole.ADMIN.value, UserRole.ENTERPRISE_ADMIN.value):
             raise HTTPException(status_code=403, detail="Not authorized to delete this job")

    db.delete(job)
    db.commit()
    return {"status": "success", "msg": "Task deleted"}

@app.get("/api/v1/rpa/tasks/pop")
def pop_rpa_task(
    x_worker_key: str = Header(None, alias="X-Worker-Key"),
    db: Session = Depends(get_shared_db)
):
    """
    RPA 机器人专用接口：获取一个待处理任务 (Global Queue in Shared DB)
    Requires X-Worker-Key header.
    """
    require_worker_key(x_worker_key)
        
    # PRIORITY 1: Check for Real-time "View" requests (view_browser)
    # These should jump the queue immediately so the user doesn't wait.
    job = db.query(RPAJob).filter(
        RPAJob.status == RPAJobStatus.QUEUED.value,
        RPAJob.job_type == "view_browser"
    ).order_by(RPAJob.created_at.asc()).first()
    
    # PRIORITY 2: Normal FIFO Queue
    if not job:
        job = db.query(RPAJob).filter(RPAJob.status == RPAJobStatus.QUEUED.value).order_by(RPAJob.created_at.asc()).first()
    
    if job:
        # 标记为被领取
        job.status = RPAJobStatus.CLAIMED.value
        db.commit()
        db.refresh(job)
        
        # 构造返回给 Worker 的 payload
        # Merge basic fields with payload fields to ensure flexibility
        task_data = {
            "id": job.id,
            "platform": job.platform,
            "job_type": job.job_type,
            "user_id": job.user_id,
            **job.payload # Spread payload (title, content, url, action, etc.)
        }
        return task_data
    return None

@app.post("/api/v1/rpa/tasks/{task_id}/complete")
def complete_rpa_task(
    task_id: int, 
    request: RPACompleteRequest, 
    x_worker_key: str = Header(None, alias="X-Worker-Key"),
    db: Session = Depends(get_shared_db)
):
    """
    RPA 机器人专用接口：回传任务结果
    """
    require_worker_key(x_worker_key)

    job = db.query(RPAJob).filter(RPAJob.id == task_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
        
    if request.status not in ("success", "failed"):
        raise HTTPException(status_code=422, detail="Invalid task status")
    previous_status = job.status
    job.status = request.status
    
    # Store URL in message or execution log if available
    final_msg = request.msg
    if request.data and request.data.get("url"):
        final_msg = f"{final_msg} |||LINK:{request.data.get('url')}|||"
        
    job.result_log = final_msg
    job.completed_at = datetime.now()
    if previous_status != request.status:
        from core.alerts import record_rpa_job_outcome
        record_rpa_job_outcome(db, job, failed=request.status == "failed")
    db.commit()
    
    print(f"[RPA Callback] 任务 {task_id} 完成. 状态: {request.status}")
    return {"status": "ok"}

@app.get("/api/v1/rpa/jobs")
def get_rpa_jobs(
    limit: int = 20,
    offset: int = 0,
    job_type: Optional[str] = None,
    exclude_job_type: Optional[str] = None,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_shared_db)
):
    """
    Web Console: 获取 RPA 任务列表 (Filtered by User)
    Returns a dict: { items: [...], total: N }
    Supports pagination via `limit` and `offset`.
    """
    # print(f"[DIAG] GET /api/v1/rpa/jobs called - user_id={user_id} limit={limit} offset={offset}")
    # Allow admins to see all tasks (including ownerless). Regular users see only their own tasks.
    from database.shared_models import User, UserRole
    current_user = db.query(User).filter(User.id == user_id).first()
    if current_user and current_user.role in (UserRole.ADMIN.value, UserRole.ENTERPRISE_ADMIN.value):
        query = db.query(RPAJob)
    else:
        # Regular users: return ONLY their own tasks (SaaS Isolation)
        query = db.query(RPAJob).filter(RPAJob.user_id == user_id)

    # Apply filters
    if job_type:
        query = query.filter(RPAJob.job_type == job_type)
    if exclude_job_type:
        query = query.filter(RPAJob.job_type != exclude_job_type)

    total = query.count()
    jobs = query.order_by(RPAJob.created_at.desc()).offset(offset).limit(limit).all()
    return {"items": jobs, "total": total}


@app.get("/api/v1/rpa/tasks/{task_id}")
def get_rpa_task(
    task_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_shared_db)
):
    """
    获取单条 RPA 任务详情 (含 execution_logs)
    """
    job = db.query(RPAJob).filter(RPAJob.id == task_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # 权限校验：允许创建者查看；若任务无 owner 则允许；或者允许管理员查看
    # print(f"[DIAG] GET /api/v1/rpa/tasks/{task_id} called - user_id={user_id} job_user_id={job.user_id}")
    if job.user_id != user_id:
        from database.shared_models import User, UserRole
        current_user = db.query(User).filter(User.id == user_id).first()
        if job.user_id is not None:
            if not current_user or current_user.role not in (UserRole.ADMIN.value, UserRole.ENTERPRISE_ADMIN.value):
                raise HTTPException(status_code=403, detail="Not authorized to view this job")

    return job

class RPAJobUpdate(BaseModel):
    title: str
    content: str
@app.put("/api/v1/rpa/tasks/{task_id}")
def update_rpa_task(
    task_id: int, 
    request: RPAJobUpdate, 
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_shared_db)
):
    """
    修改 RPA 任务内容 (Global Queue)
    """
    job = db.query(RPAJob).filter(RPAJob.id == task_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job.user_id is not None and job.user_id != user_id:
        from database.shared_models import User, UserRole
        current_user = db.query(User).filter(User.id == user_id).first()
        if not current_user or current_user.role not in (UserRole.ADMIN.value, UserRole.ENTERPRISE_ADMIN.value):
            raise HTTPException(status_code=403, detail="Not authorized to edit this job")
    
    current_payload = job.payload or {}
    current_payload['title'] = request.title
    current_payload['content'] = request.content
    job.payload = current_payload
    
    from sqlalchemy.orm.attributes import flag_modified
    flag_modified(job, "payload")
    
    db.commit()
    return {"status": "success", "msg": "Task updated"}

@app.post("/api/v1/tools/publish")
def publish_content_to_platform(
    request: PublishRequest, 
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_shared_db)
):
    """
    发布内容到外部平台 (集成 WordPress API 和 RPA Bridge)
    """
    import time
    print("[Publish] Task requested")
    
    try:
        if request.platform == 'website':
            # 模式 1: 标准 API 直连 (WordPress, CMS)
             # ... (Keep existing logic for website) ...
            result = PlatformConnector.push_to_wordpress(request.title, request.content)
            time.sleep(1) 
            return {
                "status": "success", 
                "platform": "WordPress (API)", 
                "msg": f"发布成功！文章 ID: {result['id']} (状态: Draft)。可前往后台预览。"
            }
        
        elif request.platform in ['social_qa', 'media', 'wiki', 'redbook', 'tiktok', 'wechat', 'linkedin', 'x', 'twitter', 'wordpress']:
            # 模式 2: RPA 任务派发 (入库)
            
            new_job = RPAJob(
                user_id=user_id,
                platform=request.platform,
                job_type="publish",
                payload={
                    "title": request.title,
                    "content": request.content
                },
                status=RPAJobStatus.QUEUED.value,
                result_log="Waiting for worker..."
            )
            db.add(new_job)
            db.commit()
            db.refresh(new_job)
            
            return {
                "status": "success", 
                "platform": "RPA Robot", 
                "msg": f"任务已创建，等待机器人认领。任务ID: {new_job.id}"
            }
            
        else:
            return {"status": "manual_required", "msg": f"{request.platform} 暂未配置 API 连接器，内容已复制。"}
            
    except Exception as e:
        print("[Publish Error] Operation failed")
        return {"status": "error", "msg": f"API 连接超时或认证失败: {str(e)}"}


@app.post("/api/v1/monitor/start", response_model=AnalysisResponse)
def start_monitor_task(request: MonitorRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """
    创建一个新的 GEO 监测任务 (异步执行)
    """
    # 1. 创建初始记录
    new_task = AnalysisTask(
        target_brand=request.brand_name,
        query=request.query,
        engine_name="Pending",
        status=TaskStatus.PENDING.value,
        is_mentioned=False,
        rank_position=-1,
        sentiment_score=0,
        reasoning="Processing...",
        raw_response=""
    )
    db.add(new_task)
    db.commit()
    db.refresh(new_task)
    
    # 2. 放入后台队列
    background_tasks.add_task(perform_analysis_task, new_task.id, request)
    
    return {
        "task_id": new_task.id,
        "status": "queued",
        "message": "监测任务已创建，正在后台运行。"
    }

@app.get("/api/v1/monitor/history")
def get_history(limit: int = 10, db: Session = Depends(get_db)):
    """
    获取历史分析记录
    """
    tasks = db.query(AnalysisTask).order_by(AnalysisTask.created_at.desc()).limit(limit).all()
    return tasks 




if __name__ == "__main__":
    print("=== REGISTERED ROUTES ===")
    for route in app.routes:
        if hasattr(route, "methods"):
            print(f"[ROUTE] {route.path} {route.methods}")
    print("=========================")

    port = int(os.getenv("PORT", 8010))
    # Disable reload to avoid signal/subprocess issues in this environment
    uvicorn.run("server:app", host="0.0.0.0", port=port, reload=False)


from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from typing import List, Optional
import os
import json
import re
from sqlalchemy.orm import Session

from core.db_manager import get_shared_db
from database.shared_models import RPAJobStatus
from database.models import RPAJob


from branding_monitor.engines.zhipu_client import ZhipuClient
from branding_monitor.engines.qwen_client import QwenClient

router = APIRouter(prefix="/content", tags=["Content Factory"])

class ContentGenerationRequest(BaseModel):
    topic: str
    platform: str
    tone: str
    key_points: Optional[str] = ""

class ContentGenerationResponse(BaseModel):
    title: str
    body: str
    tags: List[str]
    image_url: Optional[str] = None

class PublishRequest(BaseModel):
    platform: str
    title: str
    content: str

def clean_json_string(text: str) -> str:
    """Helper to extract JSON from LLM response"""
    # Remove markdown code blocks
    text = re.sub(r'```json\s*', '', text)
    text = re.sub(r'```\s*', '', text)
    # Find start and end brackets
    start = text.find('{')
    end = text.rfind('}') + 1
    if start != -1 and end != -1:
        return text[start:end]
    return text.strip()

@router.post("/generate", response_model=ContentGenerationResponse)
async def generate_content(request: ContentGenerationRequest):
    # 1. Select Engine
    zhipu_key = os.getenv("ZHIPUAI_API_KEY")
    dash_key = os.getenv("DASHSCOPE_API_KEY")
    client = None
    
    # Priority: DashScope (Qwen) > ZhipuAI
    if dash_key:
        print(f"[INFO] Using Content Engine: Qwen (DashScope)")
        client = QwenClient()
    elif zhipu_key:
        print(f"[INFO] Using Content Engine: ZhipuAI")
        client = ZhipuClient()
    
    # 2. Build Prompt
    prompt = f"""
    Act as an expert Social Media Content Creator (Chief Content Officer).
    
    Task: Create a high-performing post for {request.platform}.
    Topic: {request.topic}
    Tone: {request.tone}
    Key Selling Points: {request.key_points}
    
    Requirements:
    1. Title: Catchy, viral hook.
    2. Body: Engaging, well-formatted (use emojis), addressing the pain points or interests.
    3. Tags: 3-5 relevant hashtags.
    4. Language: Use English if the topic/platform is LinkedIn, WordPress, X/Twitter, SEO blog, or otherwise clearly overseas; otherwise Simplified Chinese.

    RESPONSE FORMAT:
    You MUST output ONLY valid JSON. Structure:
    {{
        "title": "...",
        "body": "...",
        "tags": ["tag1", "tag2"]
    }}
    """
    
    if client:
        try:
            # Enable search to get latest context if needed, though for pure creative writing it might be optional.
            # Let's keep it enabled as the user UI suggests "Scanning trends"
            raw_response = client.query(prompt, enable_search=True) 
            
            clean_json = clean_json_string(raw_response)
            # strict=False allows control characters (like newlines) inside strings
            data = json.loads(clean_json, strict=False)
            
            # 3. Generate Image (Multimodal)
            image_url = None
            if hasattr(client, 'generate_image'):
                image_prompt = f"Highly aesthetic, viral social media image for topic: {data.get('title', request.topic)}. Style: High quality photography, 4k."
                try:
                    image_url = client.generate_image(prompt=image_prompt)
                except Exception as img_err:
                    print(f"[!] Image Gen Error: {img_err}")

            return ContentGenerationResponse(
                title=data.get("title", f"关于 {request.topic}"),
                body=data.get("body", raw_response),
                tags=data.get("tags", []),
                image_url=image_url
            )
        except Exception as e:
            print(f"[!] Content Gen Error: {e}")
            # Fallthrough to mock
            return ContentGenerationResponse(
                title=f"Error: {str(e)}",
                body="生成失败",
                tags=[]
            )
            
    # Mock Response (Fallback if no client or init failed)
    return ContentGenerationResponse(
        title=f"🚀 {request.topic}: 核心解析",
        body=f"【系统提示】: 由于未配置 API Key 或调用失败，这是模拟生成的文案。\n\n关于 {request.topic} 的主要观点：\n{request.key_points}\n\n请检查服务端日志或 .env 配置。",
        tags=["模拟数据", "请配置API", request.platform],
        image_url=None
    )

from core.dependencies import get_current_user_id

@router.post("/publish")
async def publish_content(
    request: PublishRequest, 
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_shared_db)
):
    # Create RPA Job for distribution
    new_job = RPAJob(
        user_id=user_id,
        platform=request.platform,
        job_type="publish_content",
        status=RPAJobStatus.QUEUED.value,
        payload={
            "title": request.title,
            "content": request.content
        }
    )
    db.add(new_job)
    db.commit()
    db.refresh(new_job)
    
    print(f"[PUBLISH] Created Job ID: {new_job.id} | Platform: {request.platform} | Title: {request.title}")
    
    return {
        "msg": "已加入分发队列", 
        "status": "queued", 
        "platform": request.platform,
        "job_id": new_job.id
    }


# 查询分发任务列表
@router.get("/jobs")
async def get_distribution_jobs(limit: int = Query(20, ge=1, le=100), db: Session = Depends(get_shared_db)):
    jobs = db.query(RPAJob).order_by(RPAJob.created_at.desc()).limit(limit).all()
    # 可根据需要筛选 job_type/publish_content
    return [
        {
            "id": job.id,
            "platform": job.platform,
            "job_type": job.job_type,
            "status": job.status,
            "result_log": job.result_log,
            "execution_logs": job.execution_logs,
            "created_at": job.created_at,
            "payload": job.payload
        }
        for job in jobs
    ]

# Image Generation via Aliyun Wanx
try:
    from dashscope import ImageSynthesis
    import dashscope
    from http import HTTPStatus
except ImportError:
    pass

class ImageGenRequest(BaseModel):
    prompt: str
    resolution: Optional[str] = "1024*1024" # 1024*1024, 720*1280, 1280*720

@router.post("/generate-image")
async def generate_image(req: ImageGenRequest):
    dash_key = os.getenv("DASHSCOPE_API_KEY") 
    
    if not dash_key:
         raise HTTPException(status_code=500, detail="Server Configuration Error: Missing DASHSCOPE_API_KEY")

    try:
        import dashscope
        dashscope.api_key = dash_key
        
        print(f"[IMAGE] Generatng with Wanx: {req.prompt}")
        rsp = dashscope.ImageSynthesis.call(
            model="wanx-v1",
            prompt=req.prompt,
            n=1,
            size=req.resolution
        )
        
        if rsp.status_code == 200: # HTTPStatus.OK
            img_url = rsp.output.results[0].url
            return {"success": True, "url": img_url}
        else:
            return {"success": False, "error": rsp.message, "code": rsp.code}
            
    except Exception as e:
        print(f"[IMAGE] Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


"""外贸获客引擎：英文内容 / 文生图 / 海外发布 / 转化漏斗。"""
from __future__ import annotations

import json
import os
import re
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from core.db_manager import get_shared_db
from core.dependencies import get_current_user_id
from core.llm.runtime import query_default_llm
from core.marketing_images import IMAGE_ROOT, generate_image_url, store_image
from core.wordpress import publish_post as wp_publish, status as wp_status, test_connection as wp_test
from database.models import AnalysisTask, MarketingContent, RPAJob
from database.shared_models import Lead, RPAJobStatus

router = APIRouter(prefix="/api/v1/marketing", tags=["Marketing Acquisition"])

TEXT_TYPES = {
    "product_article": {
        "label": "Product Feature Article",
        "system": "You are a B2B industrial copywriter writing for overseas buyers.",
        "instruction": (
            "Write a 500-700 word English product feature article. "
            "Use H2 subheadings, concrete specs (MOQ, lead time, certifications if given), "
            "and a closing CTA inviting RFQs. No Chinese."
        ),
        "min_words": 400,
    },
    "linkedin_post": {
        "label": "LinkedIn Post",
        "system": "You are a LinkedIn thought-leadership ghostwriter for a Chinese manufacturer selling overseas.",
        "instruction": (
            "Write a LinkedIn post (180-280 words) with a strong hook in the first line, "
            "2-4 short paragraphs, and 4-6 relevant hashtags. Professional, not salesy. No Chinese."
        ),
        "min_words": 120,
    },
    "seo_blog": {
        "label": "SEO Blog",
        "system": "You are an SEO content strategist specializing in B2B manufacturing keywords.",
        "instruction": (
            "Write an 800-1000 word English SEO blog post. Include: a compelling title, "
            "an intro that answers search intent, H2/H3 structure, a comparison or spec table in markdown, "
            "FAQ section (3 questions), and a CTA. Target long-tail buyer keywords. No Chinese."
        ),
        "min_words": 700,
    },
    "outreach_email": {
        "label": "Outreach Email",
        "system": "You are a veteran B2B export salesperson writing cold outreach.",
        "instruction": (
            "Write a short English outreach email: subject line, greeting, 120-180 word body, "
            "one specific ask (catalog / quote / 15-min call), professional sign-off. "
            "Mention the recipient's likely use-case. No Chinese."
        ),
        "min_words": 80,
    },
}

IMAGE_PRESETS = {
    "product_scene": "photorealistic product-in-use scene, factory or industrial setting, 4k, no text overlay",
    "banner": "clean B2B website hero banner, wide 16:9, professional lighting, subtle brand-safe composition, no text",
    "social": "square social-media visual for LinkedIn, modern industrial aesthetic, high contrast, no text overlay",
}


def _extract_json(text: str) -> dict:
    text = re.sub(r"```json\s*", "", text or "")
    text = re.sub(r"```\s*", "", text)
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return json.loads(text[start : end + 1], strict=False)
    raise ValueError("No JSON object in model output")


def _word_count(text: str) -> int:
    return len(re.findall(r"[A-Za-z0-9']+", text or ""))


class TextGenRequest(BaseModel):
    content_type: str = Field(..., description="product_article | linkedin_post | seo_blog | outreach_email")
    product_name: str
    selling_points: str = ""
    audience: Optional[str] = "overseas B2B buyers / importers"
    language: str = "en"
    save: bool = True


class ImageGenRequest(BaseModel):
    prompt: Optional[str] = None
    product_name: Optional[str] = None
    preset: str = "product_scene"  # product_scene | banner | social
    resolution: Optional[str] = "1024*1024"
    save: bool = True


class TextEditRequest(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    body: str = Field(min_length=1, max_length=50000)

    @field_validator('title', 'body')
    @classmethod
    def nonblank(cls, value):
        if not value.strip():
            raise ValueError('内容不能为空')
        return value.strip()


class PublishRequest(BaseModel):
    platform: str  # linkedin | wordpress | x | twitter | website
    title: str
    content: str
    content_id: Optional[int] = None
    image_url: Optional[str] = None
    wp_status: str = "draft"


@router.post("/text/generate")
def generate_text(
    req: TextGenRequest,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_shared_db),
):
    kind = (req.content_type or "").strip()
    if kind not in TEXT_TYPES:
        raise HTTPException(400, f"content_type must be one of {list(TEXT_TYPES)}")

    spec = TEXT_TYPES[kind]
    prompt = (
        f"Product: {req.product_name}\n"
        f"Audience: {req.audience}\n"
        f"Selling points / specs:\n{req.selling_points or '(not provided)'}\n"
        f"Language: {req.language}\n\n"
        f"{spec['instruction']}\n\n"
        "Return ONLY valid JSON with keys: title, body, tags (array of strings)"
        + (", subject" if kind == "outreach_email" else "")
        + "."
        + f"\nThe body field alone must contain at least {spec['min_words']} English words. "
          "Count words, not tokens; exclude title, tags and subject from this count. "
          "Develop each requested section fully. For missing specifications, discuss buyer checks "
          "and questions to confirm instead of inventing product facts."
    )
    try:
        # Accumulate a complete stream within the provider's bounded deadline.
        # Buffered gateway calls may time out twice before the page can respond.
        # DeepSeek defaults to thinking mode, which shares the output token budget.
        # This bounded final-copy task needs the budget for the complete article.
        raw = query_default_llm(db, prompt, system=spec["system"], temperature=0.7,
                                max_tokens=3500, stream=True, thinking=False)
    except Exception:
        raise HTTPException(502, "文字模型调用失败，请检查模型配置后重试") from None
    data = None
    if raw:
        try:
            data = _extract_json(raw)
        except Exception:
            data = {"title": req.product_name, "body": raw, "tags": [kind], "subject": None}

    if (not isinstance(data, dict) or not isinstance(data.get("body"), str)
            or _word_count(data["body"]) < spec["min_words"]):
        raise HTTPException(502, "模型没有返回符合所选类型长度要求的内容，请重试；本次未保存")

    title = data.get("title") or req.product_name
    body = data.get("body") or ""
    tags = data.get("tags") or []
    if not isinstance(tags, list) or not all(isinstance(tag, str) for tag in tags):
        tags = []
    extra = {"subject": data.get("subject"), "mock": False}

    record = None
    if req.save:
        record = MarketingContent(
            user_id=user_id,
            content_type=kind,
            product_name=req.product_name,
            selling_points=req.selling_points,
            language=req.language,
            title=title,
            body=body,
            tags=tags,
            extra=extra,
        )
        db.add(record)
        db.commit()
        db.refresh(record)

    return {
        "id": record.id if record else None,
        "content_type": kind,
        "title": title,
        "body": body,
        "tags": tags,
        "subject": extra.get("subject"),
        "word_count": _word_count(body),
        "mock": extra.get("mock", False),
        "created_at": record.created_at.isoformat() if record else datetime.now().isoformat(),
    }


@router.get("/text")
def list_text(
    content_type: Optional[str] = None,
    limit: int = Query(30, ge=1, le=100),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_shared_db),
):
    q = db.query(MarketingContent).filter(MarketingContent.user_id == user_id)
    q = q.filter(MarketingContent.content_type != "image")
    if content_type:
        q = q.filter(MarketingContent.content_type == content_type)
    items = q.order_by(MarketingContent.created_at.desc()).limit(limit).all()
    return {"items": [_content_dict(c) for c in items]}


@router.get("/text/{content_id}")
def get_text(
    content_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_shared_db),
):
    item = db.query(MarketingContent).filter(MarketingContent.id == content_id, MarketingContent.user_id == user_id).first()
    if not item:
        raise HTTPException(404, "content not found")
    return _content_dict(item)


@router.patch("/text/{content_id}")
def update_text(content_id: int, body: TextEditRequest, user_id: int = Depends(get_current_user_id), db: Session = Depends(get_shared_db)):
    record = db.query(MarketingContent).filter(
        MarketingContent.id == content_id, MarketingContent.user_id == user_id,
        MarketingContent.content_type != "image",
    ).first()
    if not record:
        raise HTTPException(404, "内容不存在")
    record.title, record.body = body.title, body.body
    db.commit()
    db.refresh(record)
    return _content_dict(record)


@router.post("/images/generate")
def generate_image(
    req: ImageGenRequest,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_shared_db),
):
    preset = IMAGE_PRESETS.get(req.preset, IMAGE_PRESETS["product_scene"])
    prompt = req.prompt or f"{req.product_name or 'industrial product'}, {preset}"
    url = generate_image_url(prompt, req.resolution or "1024*1024")

    record = None
    if req.save:
        path = store_image(url)
        record = MarketingContent(
            user_id=user_id,
            content_type="image",
            product_name=req.product_name,
            title=req.product_name or req.preset,
            body=prompt,
            image_url=None,
            prompt=prompt,
            extra={"preset": req.preset, "mock": False, "image_file": path.name},
        )
        try:
            db.add(record)
            db.flush()
            url = f"/api/v1/marketing/images/{record.id}/file"
            record.image_url = url
            db.commit()
            db.refresh(record)
        except Exception:
            db.rollback()
            path.unlink(missing_ok=True)
            raise HTTPException(500, "图片记录保存失败，请重试") from None

    return {
        "id": record.id if record else None,
        "url": url,
        "prompt": prompt,
        "preset": req.preset,
        "mock": False,
        "created_at": record.created_at.isoformat() if record else datetime.now().isoformat(),
    }


@router.get("/images")
def list_images(
    limit: int = Query(24, ge=1, le=100),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_shared_db),
):
    items = (
        db.query(MarketingContent)
        .filter(MarketingContent.user_id == user_id, MarketingContent.content_type == "image")
        .order_by(MarketingContent.created_at.desc())
        .limit(limit)
        .all()
    )
    return {"items": [_content_dict(c) for c in items]}


@router.get("/images/{content_id}/file")
def image_file(content_id: int, user_id: int = Depends(get_current_user_id), db: Session = Depends(get_shared_db)):
    record = db.query(MarketingContent).filter(
        MarketingContent.id == content_id, MarketingContent.user_id == user_id,
        MarketingContent.content_type == "image",
    ).first()
    if not record:
        raise HTTPException(404, "图片不存在")
    filename = (record.extra or {}).get("image_file")
    if not isinstance(filename, str) or not re.fullmatch(r"[a-f0-9]{32}\.(png|jpg|webp)", filename):
        raise HTTPException(404, "该历史图片没有本地文件，请重新生成")
    path = (IMAGE_ROOT / filename).resolve()
    if not path.is_relative_to(IMAGE_ROOT.resolve()) or not path.is_file():
        raise HTTPException(404, "图片文件不存在")
    return FileResponse(path, headers={"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"})


@router.post("/publish")
def publish(
    req: PublishRequest,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_shared_db),
):
    platform = (req.platform or "").lower().strip()
    if platform in ("twitter",):
        platform = "x"
    if platform == "website":
        raise HTTPException(503, "自建独立站尚未接入，请先提供站点代码与发布接口")
    if platform == "wp":
        platform = "wordpress"

    payload = {
        "title": req.title,
        "content": req.content,
        "image_url": req.image_url,
        "content_id": req.content_id,
    }

    if platform == "wordpress":
        try:
            result = wp_publish(req.title, req.content, status=req.wp_status)
        except Exception as exc:
            raise HTTPException(502, str(exc))
        if result.get("mode") != "live":
            raise HTTPException(503, "WordPress 尚未配置，本次未发布")
        job = RPAJob(
            user_id=user_id,
            platform="wordpress",
            job_type="publish",
            payload={**payload, "wp": result},
            status=RPAJobStatus.SUCCESS.value if result.get("mode") == "live" else RPAJobStatus.SUCCESS.value,
            result_log=f"{result.get('msg')} |||LINK:{result.get('link')}|||",
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        return {
            "status": "success",
            "platform": "wordpress",
            "mode": result.get("mode"),
            "job_id": job.id,
            "link": result.get("link"),
            "msg": result.get("msg"),
        }

    if platform not in ("linkedin", "x", "wordpress"):
        raise HTTPException(400, "platform must be linkedin | wordpress | x")

    job = RPAJob(
        user_id=user_id,
        platform=platform,
        job_type="publish",
        payload=payload,
        status=RPAJobStatus.QUEUED.value,
        result_log="Waiting for worker...",
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return {
        "status": "queued",
        "platform": platform,
        "job_id": job.id,
        "msg": f"任务已入队，等待 RPA Worker 认领。任务 ID: {job.id}",
    }


@router.get("/wordpress/status")
def wordpress_status():
    return wp_status()


@router.post("/wordpress/test")
def wordpress_test():
    return wp_test()


@router.get("/funnel")
def funnel(
    days: int = Query(30, ge=1, le=365),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_shared_db),
):
    since = datetime.now() - timedelta(days=days)
    contents = (
        db.query(MarketingContent)
        .filter(MarketingContent.user_id == user_id, MarketingContent.created_at >= since)
        .all()
    )
    jobs = (
        db.query(RPAJob)
        .filter(RPAJob.user_id == user_id, RPAJob.created_at >= since)
        .all()
    )
    tasks = (
        db.query(AnalysisTask)
        .filter(AnalysisTask.created_at >= since)
        .all()
    )
    leads = db.query(Lead).filter(Lead.created_at >= since).all()

    text_n = len([c for c in contents if c.content_type != "image"])
    image_n = len([c for c in contents if c.content_type == "image"])
    published = [j for j in jobs if j.job_type in ("publish", "publish_content")]
    success = [j for j in published if j.status == RPAJobStatus.SUCCESS.value]
    overseas = [j for j in published if (j.platform or "").lower() in ("linkedin", "wordpress", "x", "twitter", "website")]
    mentioned = [t for t in tasks if t.is_mentioned]
    inquiry_leads = [l for l in leads if (l.source or "").lower().find("chat") >= 0 or l.status in ("new", "contacted", "converted")]

    by_platform = {}
    for j in published:
        p = (j.platform or "unknown").lower()
        by_platform.setdefault(p, {"total": 0, "success": 0, "failed": 0, "queued": 0})
        by_platform[p]["total"] += 1
        if j.status == "success":
            by_platform[p]["success"] += 1
        elif j.status == "failed":
            by_platform[p]["failed"] += 1
        else:
            by_platform[p]["queued"] += 1

    daily = {}
    for c in contents:
        key = c.created_at.strftime("%m-%d") if c.created_at else "?"
        daily.setdefault(key, {"date": key, "content": 0, "publish": 0, "mentions": 0, "leads": 0})
        daily[key]["content"] += 1
    for j in published:
        key = j.created_at.strftime("%m-%d") if j.created_at else "?"
        daily.setdefault(key, {"date": key, "content": 0, "publish": 0, "mentions": 0, "leads": 0})
        daily[key]["publish"] += 1
    for t in mentioned:
        key = t.created_at.strftime("%m-%d") if t.created_at else "?"
        daily.setdefault(key, {"date": key, "content": 0, "publish": 0, "mentions": 0, "leads": 0})
        daily[key]["mentions"] += 1
    for l in leads:
        key = l.created_at.strftime("%m-%d") if l.created_at else "?"
        daily.setdefault(key, {"date": key, "content": 0, "publish": 0, "mentions": 0, "leads": 0})
        daily[key]["leads"] += 1

    recent_jobs = sorted(published, key=lambda j: j.created_at or datetime.min, reverse=True)[:12]
    recent_leads = sorted(leads, key=lambda l: l.created_at or datetime.min, reverse=True)[:8]

    return {
        "window_days": days,
        "steps": [
            {"key": "content", "label": "内容产出", "value": text_n, "hint": f"{image_n} 张配图"},
            {"key": "publish", "label": "海外发布", "value": len(success), "hint": f"{len(published)} 个任务 / {len(overseas)} 海外渠道"},
            {"key": "exposure", "label": "GEO 曝光", "value": len(mentioned), "hint": f"{len(tasks)} 次监测"},
            {"key": "leads", "label": "本地询盘", "value": len(leads), "hint": f"{len(inquiry_leads)} 来自接待渠道"},
            {"key": "crm", "label": "CRM 归因", "value": None, "hint": "待阶段 2 启动后补齐"},
        ],
        "by_platform": by_platform,
        "trend": sorted(daily.values(), key=lambda x: x["date"])[-14:],
        "recent_jobs": [
            {
                "id": j.id,
                "platform": j.platform,
                "status": j.status,
                "title": (j.payload or {}).get("title"),
                "created_at": j.created_at.isoformat() if j.created_at else None,
                "result_log": (j.result_log or "")[:240],
            }
            for j in recent_jobs
        ],
        "recent_leads": [
            {
                "id": l.id,
                "source": l.source,
                "email": l.email,
                "company": l.company,
                "products": l.products,
                "status": l.status,
                "created_at": l.created_at.isoformat() if l.created_at else None,
            }
            for l in recent_leads
        ],
        "kpis": {
            "content": text_n,
            "images": image_n,
            "jobs": len(published),
            "success_rate": round(100 * len(success) / len(published), 1) if published else 0,
            "mentions": len(mentioned),
            "mention_rate": round(100 * len(mentioned) / len(tasks), 1) if tasks else 0,
            "leads": len(leads),
        },
    }


def _content_dict(c: MarketingContent) -> dict:
    return {
        "id": c.id,
        "content_type": c.content_type,
        "product_name": c.product_name,
        "title": c.title,
        "body": c.body,
        "word_count": _word_count(c.body),
        "subject": (c.extra or {}).get("subject"),
        "mock": (c.extra or {}).get("mock", False),
        "tags": c.tags or [],
        "image_url": c.image_url,
        "prompt": c.prompt,
        "extra": c.extra or {},
        "created_at": c.created_at.isoformat() if c.created_at else None,
    }

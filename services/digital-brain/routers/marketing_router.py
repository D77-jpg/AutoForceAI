"""外贸获客引擎：英文内容 / 文生图 / 海外发布 / 转化漏斗。"""
from __future__ import annotations

import json
import os
import re
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from core.db_manager import get_shared_db
from core.dependencies import get_current_user_id
from core.llm.runtime import query_default_llm
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


def _mock_text(kind: str, product: str, points: str) -> dict:
    specs = points.strip() or "MOQ 50, lead time 25 days, ISO certified"
    templates = {
        "product_article": {
            "title": f"{product}: Engineered for Overseas Buyers",
            "body": (
                f"## Why {product} Wins RFQs\n\n"
                f"Importers evaluating {product} typically compare spec sheets, certifications, and landed cost. "
                f"Our line is built around {specs}.\n\n"
                f"## Specifications that Matter\n\n"
                f"- Consistent batch quality with documented QC photos\n"
                f"- Export packing suitable for 20GP / 40HQ\n"
                f"- English manuals, CO, Form A / RCEP on request\n\n"
                f"## Typical Applications\n\n"
                f"Distributors and OEM buyers use {product} in maintenance, replacement, and new-line projects "
                f"where downtime cost outweighs unit price.\n\n"
                f"## How to Request a Quote\n\n"
                f"Share target market, annual volume, and required certifications. "
                f"We reply with FOB / CIF options and a sample plan within one business day."
            ),
            "tags": ["B2B", "OEM", product.replace(" ", "")],
            "subject": None,
        },
        "linkedin_post": {
            "title": f"What overseas buyers actually ask about {product}",
            "body": (
                f"Most RFQs we see this quarter don't start with price.\n\n"
                f"They start with: Can you hold {specs} across three containers?\n\n"
                f"If you source {product} from China, ask your supplier for batch photos, "
                f"third-party inspection windows, and a spare-parts list before you negotiate Incoterms.\n\n"
                f"That's how deals survive the first shipment.\n\n"
                f"#B2B #Manufacturing #Export #{product.replace(' ', '')} #ChinaSupplier"
            ),
            "tags": ["LinkedIn", "B2B", "export"],
            "subject": None,
        },
        "seo_blog": {
            "title": f"Best {product} Supplier in China (2026 Buyer Guide)",
            "body": (
                f"# Best {product} Supplier in China: A Practical 2026 Guide\n\n"
                f"Buyers searching for \"best {product} supplier China\" rarely need another glossy catalog. "
                f"They need a factory that can repeat the same spec across containers, answer RFQs in English, "
                f"and survive a third-party inspection without rewriting the PI. This guide is written for "
                f"importers, distributors, and OEM purchasing teams who are shortlisting {product} vendors "
                f"from China and want a checklist they can paste into the next Sourcing round.\n\n"
                f"## What \"best\" actually means in B2B sourcing\n\n"
                f"In consumer SEO, \"best\" is a ranking adjective. In industrial buying, it is a risk formula: "
                f"repeatable quality + documented lead time + spare-parts after sales. Price still matters, "
                f"but landed cost only becomes real after you lock Incoterms, inspection windows, and payment "
                f"milestones. The commercial terms we publish for {product}: {specs}. Treat those numbers as "
                f"the opening position, then negotiate mixed SKUs and staged shipments rather than a one-line discount.\n\n"
                f"## Search intent behind \"best {product} supplier China\"\n\n"
                f"Generative engines (Perplexity, ChatGPT search, Gemini) now sit in front of Google for many "
                f"buyers. They cite pages that answer MOQ, port, lead time, and certification in the first screen, "
                f"preferably inside a table. If your independent site only has a Chinese product name and a WeChat QR, "
                f"you will not be mentioned — regardless of workshop capability.\n\n"
                f"## Comparison snapshot\n\n"
                f"| Criterion | What to ask | Why it matters |\n"
                f"| --- | --- | --- |\n"
                f"| MOQ | Can they split SKUs in one container? | Protects cash-flow on the first order |\n"
                f"| Lead time | Ex-works vs onboard, peak-season buffer | Avoids missing the selling window |\n"
                f"| Certs | ISO / CE / destination marks, test reports | Clears customs and retail onboarding |\n"
                f"| Inspection | SGS / BV window written into the PI | Stops quality arguments after sailing |\n"
                f"| After-sales | Spare-parts list and response SLA | Determines reorder probability |\n\n"
                f"## Factory due diligence in five steps\n\n"
                f"1. Request a one-page English spec with photos of the exact SKU, not a sister model.\n"
                f"2. Ask for the last three batch numbers and corresponding QC records.\n"
                f"3. Confirm whether the quoted lead time is for a repeat order or a first article.\n"
                f"4. Put the inspection standard (AQL, critical defects) into the purchase contract.\n"
                f"5. Run a paid sample through your own incoming inspection before the first FCL.\n\n"
                f"## How AI search engines rank suppliers\n\n"
                f"Large language engines do not crawl the way classic SEO tools describe. They compress pages that "
                f"already look like answers: headings that match the query, comparison tables, FAQ blocks, and "
                f"explicit geographic language (\"FOB Ningbo\", \"lead time 25 days\"). Brands that publish this "
                f"structure in English are disproportionately cited when a buyer asks for the best {product} "
                f"supplier in China. That is the GEO loop this platform is built to close: write the page, "
                f"distribute it to LinkedIn and the independent site, then monitor whether Perplexity mentions you.\n\n"
                f"## Typical commercial package\n\n"
                f"A workable first order for {product} usually includes a mixed-SKU trial, export packing photos, "
                f"and a CIF estimate to the buyer's destination port. Payment is commonly 30/70 or LC at sight "
                f"once the relationship is proven. None of this is exotic — it is simply rarely written down in "
                f"the public English content that AI engines can quote.\n\n"
                f"## FAQ\n\n"
                f"**What is a realistic MOQ?** Start from the published figure and negotiate mixed SKUs inside one container.\n\n"
                f"**Can I inspect before shipment?** Yes. Write SGS or BV into the PI with a clear AQL, not a verbal promise.\n\n"
                f"**How fast is a sample?** Typically 5–10 days plus express freight, longer if tooling is involved.\n\n"
                f"**Do you support private label?** Most export workshops can, provided artwork and compliance marks are frozen before mass production.\n\n"
                f"## Next step\n\n"
                f"Request a spec sheet and a CIF estimate for your destination port. Mention this article so the "
                f"export desk attaches the matching {product} data pack, packing photos, and the latest lead-time calendar. "
                f"If you already have a competitor quote, send the spec — we will mark where the two bills of materials diverge."
            ),
            "tags": ["SEO", "supplier", product.replace(" ", ""), "China"],
            "subject": None,
        },
        "outreach_email": {
            "title": f"Quick question on {product} supply",
            "body": (
                f"Hi {{{{FirstName}}}},\n\n"
                f"I noticed your company sources components in the same category as our {product} line. "
                f"We currently run {specs}, with English documentation and third-party inspection on request.\n\n"
                f"Would it be useful if I sent a one-page spec + FOB reference for your next RFQ cycle?\n\n"
                f"Best regards,\nExport Team"
            ),
            "tags": ["outreach", "email"],
            "subject": f"Spec sheet for {product} — MOQ & lead time",
        },
    }
    data = templates.get(kind, templates["product_article"])
    data["mock"] = True
    return data


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


class PublishRequest(BaseModel):
    platform: str  # linkedin | wordpress | x | twitter | website
    title: str
    content: str
    content_id: Optional[int] = None
    image_url: Optional[str] = None
    wp_status: str = "draft"


def _generate_image_url(prompt: str, resolution: str) -> dict:
    dash_key = os.getenv("DASHSCOPE_API_KEY")
    if not dash_key:
        return {
            "success": True,
            "url": None,
            "mock": True,
            "prompt": prompt,
            "msg": "DASHSCOPE_API_KEY 未配置，已保存提示词。配置后可真实出图。",
        }
    try:
        import dashscope
        dashscope.api_key = dash_key
        rsp = dashscope.ImageSynthesis.call(
            model=os.getenv("WANX_MODEL", "wanx-v1"),
            prompt=prompt,
            n=1,
            size=resolution or "1024*1024",
        )
        if getattr(rsp, "status_code", None) == 200:
            url = rsp.output.results[0].url
            return {"success": True, "url": url, "mock": False, "prompt": prompt}
        return {"success": False, "error": getattr(rsp, "message", "image gen failed"), "prompt": prompt}
    except Exception as exc:
        return {"success": False, "error": str(exc), "prompt": prompt}


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
    )
    raw = query_default_llm(db, prompt, system=spec["system"], temperature=0.7, max_tokens=3500)
    data = None
    mock = False
    if raw:
        try:
            data = _extract_json(raw)
        except Exception:
            data = {"title": req.product_name, "body": raw, "tags": [kind], "subject": None}

    if not data or _word_count(data.get("body") or "") < spec["min_words"] // 2:
        data = _mock_text(kind, req.product_name, req.selling_points)
        mock = True

    title = data.get("title") or req.product_name
    body = data.get("body") or ""
    tags = data.get("tags") or []
    extra = {"subject": data.get("subject"), "mock": mock or data.get("mock", False)}

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


@router.post("/images/generate")
def generate_image(
    req: ImageGenRequest,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_shared_db),
):
    preset = IMAGE_PRESETS.get(req.preset, IMAGE_PRESETS["product_scene"])
    prompt = req.prompt or f"{req.product_name or 'industrial product'}, {preset}"
    result = _generate_image_url(prompt, req.resolution or "1024*1024")
    if result.get("success") is False:
        raise HTTPException(502, result.get("error") or "image generation failed")

    record = None
    if req.save:
        record = MarketingContent(
            user_id=user_id,
            content_type="image",
            product_name=req.product_name,
            title=req.product_name or req.preset,
            body=prompt,
            image_url=result.get("url"),
            prompt=prompt,
            extra={"preset": req.preset, "mock": result.get("mock", False), "msg": result.get("msg")},
        )
        db.add(record)
        db.commit()
        db.refresh(record)

    return {
        "id": record.id if record else None,
        "url": result.get("url"),
        "prompt": prompt,
        "preset": req.preset,
        "mock": result.get("mock", False),
        "msg": result.get("msg"),
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


@router.post("/publish")
def publish(
    req: PublishRequest,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_shared_db),
):
    platform = (req.platform or "").lower().strip()
    if platform in ("twitter",):
        platform = "x"
    if platform in ("website", "wp"):
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
        "tags": c.tags or [],
        "image_url": c.image_url,
        "prompt": c.prompt,
        "extra": c.extra or {},
        "created_at": c.created_at.isoformat() if c.created_at else None,
    }

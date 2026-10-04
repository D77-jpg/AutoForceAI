"""Bounded Beijing Wanx generation and durable private image storage."""
from __future__ import annotations

import os
from pathlib import Path
import re
import time
from urllib.parse import urlsplit
import uuid

import requests
from fastapi import HTTPException

IMAGE_ROOT = Path("storage/marketing-images")
BASE_URL = "https://dashscope.aliyuncs.com/api/v1"
MAX_IMAGE_BYTES = 20 * 1024 * 1024


def _check_response(response):
    if response.status_code != 200:
        if response.status_code in (401, 403):
            raise HTTPException(502, "百炼鉴权失败，请检查北京地域密钥及模型权限")
        if response.status_code == 429:
            raise HTTPException(502, "百炼额度或调用频率受限，请检查额度后重试")
        raise HTTPException(502, "百炼图片服务调用失败，请检查模型权限后重试")
    return response.json()


def generate_image_url(prompt: str, resolution: str) -> str:
    key = os.getenv("DASHSCOPE_API_KEY")
    if not key:
        raise HTTPException(503, "尚未配置百炼图片服务，请先配置北京地域密钥")
    try:
        with requests.Session() as client:
            headers = {"Authorization": f"Bearer {key}", "X-DashScope-Async": "enable"}
            task = _check_response(client.post(
                f"{BASE_URL}/services/aigc/text2image/image-synthesis",
                headers=headers,
                json={"model": os.getenv("WANX_MODEL") or "wanx2.1-t2i-turbo",
                      "input": {"prompt": prompt},
                      "parameters": {"size": resolution, "n": 1}},
                timeout=(5, 30), allow_redirects=False,
            ))
            task_id = task.get("output", {}).get("task_id", "")
            if not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", task_id):
                raise HTTPException(502, "图片服务没有返回有效任务")
            deadline = time.monotonic() + 180
            while time.monotonic() < deadline:
                result = _check_response(client.get(
                    f"{BASE_URL}/tasks/{task_id}", headers=headers,
                    timeout=(5, 15), allow_redirects=False,
                ))
                output = result.get("output", {})
                state = output.get("task_status")
                if state == "SUCCEEDED":
                    results = output.get("results") or []
                    url = results[0].get("url") if results else None
                    if not isinstance(url, str) or not url:
                        raise HTTPException(502, "图片服务返回空结果")
                    return url
                if state not in ("PENDING", "RUNNING"):
                    raise HTTPException(502, "图片生成未完成，请检查提示词或模型权限后重试")
                time.sleep(2)
            raise HTTPException(504, "图片任务等待超时，请稍后检查服务状态；本次未保存成功记录")
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(502, "图片服务连接失败，请检查网络和北京地域配置") from None


def store_image(url: str) -> Path:
    """Download only vendor CDN results, without forwarding API credentials."""
    parsed = urlsplit(url)
    host = parsed.hostname or ""
    if (parsed.scheme != "https" or parsed.username or parsed.password
            or parsed.port not in (None, 443)
            or not any(host.endswith(suffix) for suffix in (".aliyuncs.com", ".alicdn.com"))):
        raise HTTPException(502, "图片服务返回了不支持的文件地址")
    target = None
    try:
        with requests.get(url, stream=True, timeout=(5, 30), allow_redirects=False) as response:
            if response.status_code != 200:
                raise HTTPException(502, "生成图片下载失败，未保存成功记录")
            chunks = bytearray()
            for chunk in response.iter_content(64 * 1024):
                chunks.extend(chunk)
                if len(chunks) > MAX_IMAGE_BYTES:
                    raise HTTPException(502, "生成图片超过文件大小限制")
            data = bytes(chunks)
            if data.startswith(b"\x89PNG\r\n\x1a\n"):
                extension = ".png"
            elif data.startswith(b"\xff\xd8\xff"):
                extension = ".jpg"
            elif data.startswith(b"RIFF") and data[8:12] == b"WEBP":
                extension = ".webp"
            else:
                raise HTTPException(502, "生成结果不是可用的图片文件")
            IMAGE_ROOT.mkdir(parents=True, exist_ok=True)
            target = IMAGE_ROOT / (uuid.uuid4().hex + extension)
            target.write_bytes(data)
            return target
    except HTTPException:
        raise
    except Exception:
        if target:
            target.unlink(missing_ok=True)
        raise HTTPException(502, "生成图片保存失败，未保存成功记录") from None

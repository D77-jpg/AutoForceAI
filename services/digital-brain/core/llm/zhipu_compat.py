"""Zhipu GLM OpenAI-compatible transport; no vulnerable Zhipu SDK/JWT dependency.

Only the fixed vendor HTTPS endpoint is allowed. Never forward arbitrary origins,
credentials, prompts or vendor error text into application logs/exceptions.
"""
import os
from openai import OpenAI

ZHIPU_BASE_URL = "https://open.bigmodel.cn/api/paas/v4/"


def ZhipuAI(*, api_key: str | None = None):
    """Compatibility constructor for our two historical Zhipu call sites."""
    secret = api_key or os.getenv("ZHIPUAI_API_KEY")
    if not secret:
        raise ValueError("Zhipu credentials are not configured")
    return OpenAI(api_key=secret, base_url=ZHIPU_BASE_URL, timeout=30.0, max_retries=1)

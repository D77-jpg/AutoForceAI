import os
from openai import OpenAI
from typing import List, Dict, Any
from time import monotonic
from ..base import BaseLLM, LLMResponse

class OpenAIGenericLLM(BaseLLM):
    """
    通用 OpenAI 协议适配器
    支持: OpenAI (GPT), DeepSeek, Moonshot (Kimi), LocalAI, vLLM 等
    """
    def __init__(self, api_key: str = None, base_url: str = None, **kwargs):
        super().__init__(api_key, **kwargs)
        
        # 1. API Key
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        
        # 2. Base URL (关键：用于适配 DeepSeek / Moonshot 等第三方)
        # 优先使用传入参数，其次读取环境变量，最后默认为 OpenAI官方
        self.base_url = base_url or os.getenv("OPENAI_BASE_URL")
        
        if not self.api_key:
            # pass or log warning
            pass
            
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            timeout=60,
            max_retries=1,
        )
        self.default_model = kwargs.get("model", "gpt-3.5-turbo")

    def chat(self, messages: List[Dict[str, str]], **kwargs) -> LLMResponse:
        model = kwargs.get("model", self.default_model)
        temperature = kwargs.get("temperature", 0.7)
        max_tokens = kwargs.get("max_tokens", 2000)

        # Standard OpenAI parameters
        params = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }

        try:
            if kwargs.get('stream'):
                # Longer structured outputs can exceed the gateway's buffered
                # response wait. Accumulate actual deltas, with a total deadline.
                parts = []
                last = None
                usage = None
                completed = False
                deadline = monotonic() + 85
                # A stalled read can take at most another 30s; no hidden retry
                # may outlive the presentation UI's 120s request limit.
                client = self.client.with_options(timeout=30, max_retries=0)
                with client.chat.completions.create(**params, stream=True) as chunks:
                    for chunk in chunks:
                        if monotonic() > deadline:
                            raise TimeoutError('Model generation deadline exceeded')
                        last = chunk
                        if getattr(chunk, 'usage', None):
                            usage = chunk.usage
                        if not chunk.choices:
                            continue
                        choice = chunk.choices[0]
                        if choice.delta.content:
                            parts.append(choice.delta.content)
                        if choice.finish_reason:
                            if choice.finish_reason != 'stop':
                                raise ValueError('Model output was incomplete')
                            completed = True
                if not completed or not parts:
                    raise ValueError('Model stream ended without a complete output')
                return LLMResponse(
                    content=''.join(parts), raw_response=last, model_name=model,
                    usage={'input_tokens': usage.prompt_tokens, 'output_tokens': usage.completion_tokens} if usage else {},
                )
            response = self.client.chat.completions.create(**params)
            
            content = response.choices[0].message.content
            
            return LLMResponse(
                content=content,
                raw_response=response,
                model_name=model,
                usage={
                    "input_tokens": response.usage.prompt_tokens if response.usage else 0,
                    "output_tokens": response.usage.completion_tokens if response.usage else 0
                }
            )
        except Exception as e:
            raise Exception(f"OpenAI Generic Error ({model} @ {self.base_url}): {str(e)}")

    def chat_stream(self, messages: List[Dict[str, str]], **kwargs):
        model = kwargs.get("model", self.default_model)
        
        # DeepSeek specific handling: standard is <think> in content, 
        # but some proxys use reasoning_content. We check both.
        
        stream = self.client.chat.completions.create(
            model=model,
            messages=messages,
            stream=True,
            temperature=kwargs.get("temperature", 0.7),
            max_tokens=kwargs.get("max_tokens", 2500),
        )
        for chunk in stream:
            delta = chunk.choices[0].delta
            
            # 1. Check for explicit reasoning_content (DeepSeek R1 / Azure DeepSeek)
            # Accessing via getattr to avoid error if attribute missing in SDK type
            r_content = getattr(delta, "reasoning_content", None)
            # Some SDKs put extra fields in model_extra
            if r_content is None and hasattr(delta, "model_extra") and delta.model_extra:
                r_content = delta.model_extra.get("reasoning_content")

            if r_content:
                yield {"type": "reasoning", "content": r_content}
                
            # 2. Standard Content
            if delta.content is not None:
                yield {"type": "content", "content": delta.content}

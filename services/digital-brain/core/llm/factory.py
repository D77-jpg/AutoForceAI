from typing import Dict, Type, Optional
from hashlib import sha256
from .base import BaseLLM, ModelType
from .providers.qwen import QwenLLM
from .providers.zhipu import ZhipuLLM
from .providers.openai_generic import OpenAIGenericLLM

class ModelFactory:
    _registry: Dict[str, Type[BaseLLM]] = {}
    _instances: Dict[str, BaseLLM] = {}

    @classmethod
    def register(cls, model_type: str, provider_cls: Type[BaseLLM]):
        cls._registry[model_type] = provider_cls

    @classmethod
    def get_provider(cls, model_type: str, **kwargs) -> BaseLLM:
        """
        Factory method to get or create a provider instance
        """
        model_type = model_type.lower()
        
        # Normalization
        if "qwen" in model_type:
            provider_key = "qwen"
            provider_cls = QwenLLM
        elif "glm" in model_type or "zhipu" in model_type:
            provider_key = "zhipu"
            provider_cls = ZhipuLLM
        elif "gpt" in model_type or "openai" in model_type:
            provider_key = "openai"
            provider_cls = OpenAIGenericLLM
        elif "deepseek" in model_type:
             # DeepSeek uses OpenAI Protocol
            provider_key = "deepseek"
            provider_cls = OpenAIGenericLLM
            # Inject deepseek specific config if not present
            if "base_url" not in kwargs:
                kwargs["base_url"] = "https://api.deepseek.com/v1"
            if "api_key" not in kwargs:
                 # Try specific env var first
                 from os import getenv
                 kwargs["api_key"] = getenv("DEEPSEEK_API_KEY") 
        else:
             # Fallback to OpenAI Generic for unknown types
             provider_key = "openai_generic"
             provider_cls = OpenAIGenericLLM
        
        # The same model name may point to different endpoints/credentials after
        # reconfiguration. Fingerprint config for cache identity without exposing keys.
        identity = repr((provider_key, sorted(kwargs.items())))
        cache_key = sha256(identity.encode("utf-8")).hexdigest()
        
        if cache_key not in cls._instances:
            cls._instances[cache_key] = provider_cls(**kwargs)
            
        return cls._instances[cache_key]

# Pre-register known providers
ModelFactory.register("qwen", QwenLLM)
ModelFactory.register("zhipu", ZhipuLLM)
ModelFactory.register("openai", OpenAIGenericLLM)
ModelFactory.register("deepseek", OpenAIGenericLLM)

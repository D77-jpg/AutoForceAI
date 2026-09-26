import os
from core.llm.zhipu_compat import ZhipuAI
from typing import List, Dict, Any
from ..base import BaseLLM, LLMResponse

class ZhipuLLM(BaseLLM):
    def __init__(self, api_key: str = None, **kwargs):
        super().__init__(api_key, **kwargs)
        self.api_key = api_key or os.getenv("ZHIPUAI_API_KEY")
        if self.api_key:
            self.client = ZhipuAI(api_key=self.api_key)
        else:
            self.client = None
        
        raw_model = kwargs.get("model", "glm-4")
        # Sanitize model name (remove zhipu- prefix if accidentally passed)
        if raw_model.startswith("zhipu-"):
            raw_model = raw_model.replace("zhipu-", "")
        self.default_model = raw_model

    def chat(self, messages: List[Any], **kwargs) -> LLMResponse:
        if not self.client:
            raise ValueError("ZhipuAI Client not initialized (Missing API Key)")

        # Convert Pydantic models to dicts if necessary
        formatted_messages = []
        for m in messages:
            if hasattr(m, 'model_dump'):
                formatted_messages.append(m.model_dump())
            elif hasattr(m, 'dict'):
                formatted_messages.append(m.dict())
            else:
                formatted_messages.append(m)

        model = kwargs.get("model", self.default_model)
        enable_search = kwargs.get("enable_search", False)
        
        tools = None
        if enable_search and formatted_messages:
            # Extract last user prompt for search query
            last_msg = formatted_messages[-1]
            if isinstance(last_msg, dict):
               last_content = last_msg.get('content', '')
               tools = [{
                   "type": "web_search",
                   "web_search": {
                       "enable": True,
                       "search_query": last_content 
                   }
               }]

        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=formatted_messages,
                tools=tools
            )
            
            return LLMResponse(
                content=response.choices[0].message.content,
                raw_response=response,
                model_name=model,
                usage={
                    "input_tokens": response.usage.prompt_tokens,
                    "output_tokens": response.usage.completion_tokens
                }
            )
        except Exception:
            raise RuntimeError("ZhipuAI request failed") from None

    def chat_stream(self, messages: List[Dict[str, str]], **kwargs):
        print(f"[ZhipuLLM] chat_stream called. Client exists: {self.client is not None}")
        if not self.client:
             raise ValueError("ZhipuAI Client not initialized")
             
        # Format messages
        formatted_messages = []
        for m in messages:
            if hasattr(m, 'model_dump'):
                formatted_messages.append(m.model_dump())
            elif hasattr(m, 'dict'):
                formatted_messages.append(m.dict())
            else:
                formatted_messages.append(m)
                
        model = kwargs.get("model", self.default_model)
        # Ensure model is sanitized again just in case kwargs override it with dirty name
        if model.startswith("zhipu-"):
            model = model.replace("zhipu-", "")

        print(f"[ZhipuLLM] Calling API with model={model}, stream=True")
        
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=formatted_messages,
                stream=True
            )
            
            print("[ZhipuLLM] API call returned, iterating response...")
            count = 0
            for chunk in response:
                count += 1
                # print(f"[ZhipuLLM] Raw Chunk: {chunk}")
                if chunk.choices and chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    # print(f"[ZhipuLLM] Yielding: {content}")
                    yield content
            print(f"[ZhipuLLM] Stream finished. Chunks processed: {count}")
                    
        except Exception:
            print("[ZhipuLLM] Stream failed")
            yield "[Error: model request failed]"

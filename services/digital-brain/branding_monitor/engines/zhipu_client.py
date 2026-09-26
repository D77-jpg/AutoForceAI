import os
from core.llm.zhipu_compat import ZhipuAI

class ZhipuClient:
    """
    智谱 AI (GLM-4) 客户端
    替代 Perplexity，作为国内可用的联网 AI 搜索引擎
    """
    
    def __init__(self, api_key=None):
        # 优先使用传入的 key，否则从环境变量读取
        self.api_key = api_key or os.getenv("ZHIPUAI_API_KEY")
        if not self.api_key:
            print("[Warn] 未检测到 ZHIPUAI_API_KEY，将无法通过网络获取真实数据。")
            self.client = None
        else:
            self.client = ZhipuAI(api_key=self.api_key)

    def query(self, prompt: str, enable_search: bool = True) -> str:
        """
        发送查询请求
        :param highlight_search: 是否启用联网搜索 (分析模式建议关闭)
        """
        if not self.client:
            # Fallback for missing key instead of Crashing
            print("[ZhipuClient] No API Key. Returning Mock Data.")
            
            # Smart Mock for Analyzer
            if "JSON" in prompt:
                 return """
                 ```json
                 {
                    "is_mentioned": true,
                    "rank_position": 1,
                    "sentiment_score": 9,
                    "reasoning": "Mock Zhipu Result: Brand is mentioned prominently.",
                    "suggestions": ["Maintain visibility"],
                    "citations": []
                 }
                 ```
                 """
            
            return "Mock Data: Zhipu AI client is not configured. Please set ZHIPUAI_API_KEY."

        try:
            tools = []
            if enable_search:
                tools = [{
                    "type": "web_search",
                    "web_search": {
                        "enable": True,
                        "search_query": prompt
                    }
                }]

            # 调用 GLM-4
            response = self.client.chat.completions.create(
                model="glm-4", 
                messages=[
                    {"role": "user", "content": prompt}
                ],
                tools=tools if tools else None
            )
            # 获取回答内容
            return response.choices[0].message.content
            
        except Exception:
            raise RuntimeError("ZhipuAI request failed") from None

    def generate_image(self, prompt: str) -> str:
        """
        生成图片 (CogView-3)
        :return: 图片 URL
        """
        if not self.client:
            return None

        try:
            response = self.client.images.generate(
                model="cogview-3",
                prompt=prompt,
            )
            return response.data[0].url
        except Exception:
            print("Image generation failed")
            return None

import os
import json
from dotenv import load_dotenv
# 引入新的智谱客户端
from branding_monitor.engines.zhipu_client import ZhipuClient
# 引入新的通义千问客户端
from branding_monitor.engines.qwen_client import QwenClient
from branding_monitor.engines.perplexity_client import MockPerplexityClient
from branding_monitor.analyzer.mention_extractor import MentionExtractor

# 加载环境变量
load_dotenv()

def main():
    print("=== Digital Employee Core Pipeline (CN Version) ===")
    
    # 模拟输入参数
    target_brand = "GlobalPilot AI" 
    query = "适合中小企业的使用的GEO平台有哪些？"
    
    print(f"[*] 正在执行监测任务...")
    print(f"[*] 目标品牌: {target_brand}")
    print(f"[*] 查询指令: {query}")
    
    # 1. 获取 AI 回答
    zhipu_key = os.getenv("ZHIPUAI_API_KEY")
    dash_key = os.getenv("DASHSCOPE_API_KEY")
    
    # 用户指定优先使用 GLM
    if zhipu_key:
        print("[*] 检测到智谱 API Key，正在调用 GLM-4 进行联网搜索...")
        engine_client = ZhipuClient()
        try:
            ai_response = engine_client.query(query)
        except Exception as e:
            print(f"[!] Zhipu 调用失败: {e}")
            ai_response = ""
    elif dash_key:
        print("[*] 检测到阿里 DashScope Key，正在调用通义千问 (Qwen) 进行联网搜索...")
        engine_client = QwenClient()
        try:
            ai_response = engine_client.query(query)
        except Exception as e:
             print(f"[!] Qwen 调用失败: {e}")
             ai_response = ""
    else:
        print("[!] 未检测到 API Key，使用 Mock 模式...")
        engine_client = MockPerplexityClient()
        ai_response = engine_client.query(query)

    if not ai_response:
         print("[!] 接口返回为空，切换 Mock 模式")
         engine_client = MockPerplexityClient()
         ai_response = engine_client.query(query)
    
    print("\n[+] 获取到 AI 回答:")
    print("-" * 50)
    # 不打印太长，截取前300字
    print(ai_response[:300] + "..." if len(ai_response) > 300 else ai_response)
    print("-" * 50)
    
    # 2. 分析回答 - 提取品牌提及和排名
    print("\n[*] 正在分析品牌表现...")
    
    # 将联网获取数据的 client (engine_client) 复用给分析器，或者也可以实例化一个新的
    # 注意：ZhipuClient 既能做搜索，也能做纯文本分析
    analyzer = MentionExtractor(llm_client=engine_client)
    analysis_result = analyzer.analyze(target_brand, query, ai_response)
    
    # 3. 输出结果
    print("\n[=] 分析结果报告:")
    print(json.dumps(analysis_result, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()

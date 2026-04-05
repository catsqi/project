import sys
import os

# 添加项目根目录到 Python 路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

import time
from app.core.config import settings
from openai import OpenAI

def test_deepseek_latency():
    print(f"--- DeepSeek Latency & Throughput Test (Streaming) ---")
    print(f"Model: {settings.deepseek_model}")
    print(f"Base URL: {settings.deepseek_base_url}")
    
    client = OpenAI(
        api_key=settings.deepseek_api_key,
        base_url=settings.deepseek_base_url
    )
    
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Write a 200-word story about a robot learning to feel."}
    ]
    
    print("\n[1] Starting request...")
    start_time = time.time()
    
    try:
        # 使用流式输出以测量 TTFT
        stream = client.chat.completions.create(
            model=settings.deepseek_model,
            messages=messages,
            temperature=0.5,
            stream=True
        )
        
        ttft = None
        full_content = ""
        token_count = 0
        
        print("[2] Waiting for first token...", end="", flush=True)
        
        for chunk in stream:
            if ttft is None:
                ttft = time.time() - start_time
                print(f" DONE (TTFT: {ttft:.4f}s)")
                print("[3] Receiving tokens: ", end="", flush=True)
            
            if chunk.choices and chunk.choices[0].delta.content:
                content = chunk.choices[0].delta.content
                full_content += content
                token_count += 1 
        
        end_time = time.time()
        total_time = end_time - start_time
        generation_time = end_time - (start_time + ttft)
        
        print(f"\n\n--- Performance Metrics ---")
        print(f"Time to First Token (TTFT): {ttft:.4f}s (网络往返 + 模型首字耗时)")
        print(f"Total Generation Time:      {generation_time:.4f}s (模型全量生成耗时)")
        print(f"Total Request Time:         {total_time:.4f}s")
        print(f"Estimated Tokens/sec:       {token_count / generation_time if generation_time > 0 else 0:.2f} t/s")
        print("-" * 40)
        
    except Exception as e:
        print(f"\n❌ Error during DeepSeek latency test: {e}")

if __name__ == "__main__":
    test_deepseek_latency()

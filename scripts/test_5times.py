import sys
import os

# 添加项目根目录到 Python 路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

import time
from app.core.config import settings
from openai import OpenAI

def test_deepseek_latency():
    print(f"\n--- DeepSeek Latency Test ---")
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
    
    print("[1] Starting request...")
    start_time = time.time()
    
    try:
        stream = client.chat.completions.create(
            model=settings.deepseek_model,
            messages=messages,
            temperature=0.5,
            stream=True
        )
        
        ttft = None
        token_count = 0
        
        for chunk in stream:
            if ttft is None:
                ttft = time.time() - start_time
            if chunk.choices and chunk.choices[0].delta.content:
                token_count += 1
        
        end_time = time.time()
        total_time = end_time - start_time
        generation_time = total_time - ttft
        
        tps = token_count / generation_time if generation_time > 0 else 0
        
        print(f"TTFT: {ttft:.4f}s | Total: {total_time:.4f}s | Tokens: {token_count} | TPS: {tps:.2f}")
        return ttft, total_time, token_count, tps
        
    except Exception as e:
        print(f"Error: {e}")
        return None, None, None, None

if __name__ == "__main__":
    print("=" * 50)
    print("DeepSeek API Latency Test - 5 Runs")
    print("=" * 50)
    
    results = []
    for i in range(1, 6):
        print(f"\n[Run {i}/5]")
        result = test_deepseek_latency()
        if result[0]:
            results.append(result)
        time.sleep(1)  # 避免请求过快
    
    print("\n" + "=" * 50)
    print("Summary:")
    print("=" * 50)
    if results:
        ttfts = [r[0] for r in results]
        totals = [r[1] for r in results]
        tps_list = [r[3] for r in results]
        print(f"TTFT   - Avg: {sum(ttfts)/len(ttfts):.4f}s  Min: {min(ttfts):.4f}s  Max: {max(ttfts):.4f}s")
        print(f"Total  - Avg: {sum(totals)/len(totals):.4f}s  Min: {min(totals):.4f}s  Max: {max(totals):.4f}s")
        print(f"TPS    - Avg: {sum(tps_list)/len(tps_list):.2f}  Min: {min(tps_list):.2f}  Max: {max(tps_list):.2f}")

import time
import os
from app.core.config import settings
from groq import Groq

def test_groq_latency():
    print(f"--- Groq Latency & Throughput Test (Streaming) ---")
    print(f"Model: {settings.groq_model}")
    
    client = Groq(api_key=settings.groq_api_key)
    
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Write a 200-word story about a robot learning to feel."}
    ]
    
    print("\n[1] Starting request...")
    start_time = time.time()
    
    try:
        # 使用流式输出以测量 TTFT
        stream = client.chat.completions.create(
            model=settings.groq_model,
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
            
            content = chunk.choices[0].delta.content
            if content:
                full_content += content
                token_count += 1 # 估算 token 数 (粗略)
                # print(".", end="", flush=True) # 每收到一个块打个点
        
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
        print(f"\n❌ Error during Groq latency test: {e}")

if __name__ == "__main__":
    test_groq_latency()

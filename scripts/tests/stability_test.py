import time
import statistics
import os
import sys

# Ensure app is in path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from app.core.config import settings
from app.core.llm import GroqClient, DeepSeekClient

def run_bench(client, model_name, provider_name, n=5):
    print(f"\n⚡️ 开始测试 {provider_name} ({model_name}) - 共 {n} 次...")
    
    ttfts = []
    tps_list = []
    totals = []
    
    messages = [{"role": "user", "content": "Tell me a short 50-word story about space."}]
    
    for i in range(n):
        print(f"  测试 [{i+1}/{n}]...", end="", flush=True)
        start_time = time.time()
        try:
            # Streaming to get TTFT
            stream = client.chat_completion(
                messages=messages,
                temperature=0.5,
                stream=True
            )
            
            ttft = None
            token_count = 0
            for chunk in stream:
                if ttft is None:
                    ttft = time.time() - start_time
                if hasattr(chunk.choices[0], 'delta') and chunk.choices[0].delta.content:
                    token_count += 1
                    
            end_time = time.time()
            total_time = end_time - start_time
            gen_time = end_time - (start_time + ttft)
            tps = token_count / gen_time if gen_time > 0 else 0
            
            ttfts.append(ttft)
            tps_list.append(tps)
            totals.append(total_time)
            print(f" 完成 (TTFT: {ttft:.3f}s, TPS: {tps:.1f})")
            
        except Exception as e:
            print(f" ❌ 失败: {e}")
            
    if not ttfts:
        return None
        
    return {
        "ttft_avg": statistics.mean(ttfts),
        "ttft_std": statistics.stdev(ttfts) if len(ttfts) > 1 else 0,
        "ttft_min": min(ttfts),
        "ttft_max": max(ttfts),
        "tps_avg": statistics.mean(tps_list),
        "total_avg": statistics.mean(totals)
    }

def print_stats(name, stats):
    if not stats:
        print(f"\n--- {name} 测试失败 ---")
        return
    print(f"\n📊 --- {name} 统计结果 ---")
    print(f"  首字延迟 (TTFT):")
    print(f"    - 平均值: {stats['ttft_avg']:.4f}s")
    print(f"    - 标准差: {stats['ttft_std']:.4f}s (越小越稳定)")
    print(f"    - 范围:   [{stats['ttft_min']:.3f}s ~ {stats['ttft_max']:.3f}s]")
    print(f"  生成速度 (TPS): {stats['tps_avg']:.2f} t/s")
    print(f"  单次完整响应平均时间: {stats['total_avg']:.2f}s")

if __name__ == "__main__":
    import sys
    target = sys.argv[1].lower() if len(sys.argv) > 1 else "both"
    
    if target == "groq" or target == "both":
        groq_stats = run_bench(GroqClient(), settings.groq_model, "Groq")
        print_stats("Groq (LPU 引擎)", groq_stats)
        
    if target == "deepseek" or target == "both":
        ds_stats = run_bench(DeepSeekClient(), settings.deepseek_model, "DeepSeek")
        print_stats("DeepSeek (直连)", ds_stats)

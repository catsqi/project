import asyncio
import numpy as np
import torch
import io
import base64
from scipy.io import wavfile
from fastrtc import AsyncAudioVideoStreamHandler, Stream, wait_for_item
from zai import ZhipuAiClient
from dotenv import load_dotenv
import os

# 1. 环境加载
load_dotenv()
GLM_4_VOICE_API_KEY = os.getenv("GLM_4_VOICE_API_KEY")
client = ZhipuAiClient(api_key=GLM_4_VOICE_API_KEY)

# ==========================================
# 2. Silero VAD 模型初始化 (保持本地加载)
# ==========================================
model, utils = torch.hub.load(
    repo_or_dir='D:/ai_models/silero',
    model='silero_vad',
    source='local',
    trust_repo=True
)
(get_speech_timestamps, _, _, _, _) = utils


# ==========================================
# 3. 极速流式 AI 逻辑
# ==========================================
async def run_glm_voice_streaming(audio_data: np.ndarray, sample_rate: int, output_queue: asyncio.Queue):
    """
    核心优化：流式处理。AI 边说，我们边往队列里塞音频片。
    """
    try:
        # 快速转换音频为字节
        byte_io = io.BytesIO()
        wavfile.write(byte_io, sample_rate, audio_data)
        base64_voice = base64.b64encode(byte_io.getvalue()).decode('utf-8')

        print("[AI] 正在流式生成...")

        # 优化点 1: 开启 stream=True，并增加 system 限制回答长度降低延迟
        response = client.chat.completions.create(
            model="glm-4-voice",
            messages=[
                {
                    "role": "system",
                    "content": "你是一个AI面试官。请尽量精简，每次仅用一两句话回答或反问，避免长篇大论，以实现极低延迟交流。"
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_audio",
                            "input_audio": {"data": base64_voice, "format": "wav"}
                        }
                    ]
                }
            ],
            stream=True  # 开启流式
        )

        # ✨ 优化点 2: 迭代获取音频分片
        for chunk in response:
            delta = chunk.choices[0].delta
            if hasattr(delta, 'audio') and delta.audio:
                audio_chunk_b64 = delta.audio.get('data')
                if audio_chunk_b64:
                    # 直接 base64 解码并转为 numpy (比 librosa 快 10 倍以上)
                    raw_audio_bytes = base64.b64decode(audio_chunk_b64)
                    # 智谱返回的是 24k 采样率, 16bit PCM
                    audio_np = np.frombuffer(raw_audio_bytes, dtype=np.int16)

                    # ✨ 优化点 3: 立即塞入播放队列
                    await output_queue.put(audio_np)

        print("[AI] 传输完成")
    except Exception as e:
        print(f"流式调用失败: {e}")


# ==========================================
# 4. 优化后的处理器
# ==========================================
class HighSpeedVADHandler(AsyncAudioVideoStreamHandler):
    def __init__(self):
        super().__init__("mono", output_sample_rate=24000, input_sample_rate=16000)
        self.audio_buffer = []
        self.output_queue = asyncio.Queue()
        self.is_speaking = False
        self.is_ai_thinking = False
        self.silence_duration = 0
        self.frame_size = 512
        self.threshold = 0.5

    async def receive(self, frame: tuple[int, np.ndarray]):
        if self.is_ai_thinking:
            return

        _, audio_data = frame
        audio_data = audio_data.squeeze()
        audio_float32 = audio_data.astype(np.float32) / 32768.0

        for i in range(0, len(audio_float32), self.frame_size):
            chunk = audio_float32[i: i + self.frame_size]
            if len(chunk) < self.frame_size: break

            with torch.no_grad():
                speech_prob = model(torch.from_numpy(chunk), 16000).item()

            if speech_prob > self.threshold:
                if not self.is_speaking:
                    self.is_speaking = True
                    print("\n[VAD] 听...")
                self.audio_buffer.append(audio_data[i: i + self.frame_size])
                self.silence_duration = 0
            else:
                if self.is_speaking:
                    self.audio_buffer.append(audio_data[i: i + self.frame_size])
                    self.silence_duration += 1
                    # ✨ 优化点 4: 缩短静音判断时延。降低到 15 次约等于 0.45 秒，反应更灵敏
                    if self.silence_duration > 15:
                        self.is_speaking = False
                        print("[VAD] 说完了，连线中...")
                        full_audio = np.concatenate(self.audio_buffer)
                        self.audio_buffer = []
                        self.is_ai_thinking = True

                        # 开启异步流式处理任务
                        asyncio.create_task(self._process_stream(full_audio))

    async def _process_stream(self, audio_data):
        try:
            # 传入 output_queue，实现边推理边入队
            await run_glm_voice_streaming(audio_data, self.input_sample_rate, self.output_queue)

            # 等待队列中的音频播完（防止 AI 还没说完就开始听）
            # 这里的等待时间会随着 emit 动态调整，为了演示稳定，我们等一下队列清空
            while not self.output_queue.empty():
                await asyncio.sleep(0.1)
        finally:
            self.is_ai_thinking = False
            print("[System] 恢复监听。")

    async def emit(self):
        # 只要队列里有音频片，立刻吐给前端播放
        array = await wait_for_item(self.output_queue, 0.01)
        if array is not None:
            return (self.output_sample_rate, array)
        return None

    async def video_receive(self, frame: np.ndarray):
        pass

    async def video_emit(self) -> np.ndarray:
        return None

    def copy(self):
        return HighSpeedVADHandler()


# ==========================================
# 5. 启动
# ==========================================
stream = Stream(handler=HighSpeedVADHandler(), modality="audio", mode="send-receive")

if __name__ == "__main__":
    print("极速流式版 AI 面试官已就绪...")
    stream.ui.launch()
import asyncio
import numpy as np
import webrtcvad
from fastrtc import AsyncAudioVideoStreamHandler, Stream, wait_for_item
from faster_whisper import WhisperModel
import os
import wave
import base64
from zai import ZhipuAiClient




# ==========================================
# 1. 模型初始化 (针对 CPU 优化)
# ==========================================
model_path = "base"

print("正在加载 ASR 模型，请稍候...")
asr_model = WhisperModel(
    model_path,
    device="cpu",
    compute_type="int8",
    cpu_threads=4,
    download_root="./models"
)


def my_asr(audio_np: np.ndarray) -> str:
    try:
        # 归一化处理
        audio_float32 = audio_np.astype(np.float32) / 32768.0   # 16bit音频，每个采样点占16位， 2的15次是32768，除一下就归一化至（-1,1）
        segments, _ = asr_model.transcribe(audio_float32, beam_size=1, language=None)
        text = "".join([segment.text for segment in segments])
        return text.strip()
    except Exception as e:
        print(f"ASR 识别出错: {e}")
        return ""


# ==========================================
# 2. 核心 AI 业务逻辑
# ==========================================
async def run_ai_pipeline(audio_data: np.ndarray):
    text = await asyncio.to_thread(my_asr, audio_data)   # 使用 asyncio.to_thread 将耗时的 CPU 计算扔到后台线程
    if text:
        print(f"【面试者说】：{text}")

    # 这里未来可以接入 LLM 和 TTS
    # 模拟返回 1 秒 24k 采样率的空音频
    return np.zeros((24000,), dtype=np.int16)


# ==========================================
# 3. 补全后的 PrecisionVADHandler
# ==========================================
class PrecisionVADHandler(AsyncAudioVideoStreamHandler):
    def __init__(self):
        # 输入 16k 采样率，输出 24k 采样率
        super().__init__("mono", output_sample_rate=24000, input_sample_rate=16000)
        self.vad = webrtcvad.Vad(3)
        self.audio_buffer = []
        self.output_queue = asyncio.Queue()
        self.is_speaking = False
        self.silence_duration = 0
        self.frame_size = 320

    # --- 音频接收与处理 ---
    async def receive(self, frame: tuple[int, np.ndarray]):
        _, audio_data = frame
        audio_data = audio_data.squeeze()

        for i in range(0, len(audio_data), self.frame_size):
            chunk = audio_data[i: i + self.frame_size]
            if len(chunk) < self.frame_size:
                break

            is_speech = self.vad.is_speech(chunk.tobytes(), self.input_sample_rate)

            if is_speech:
                if not self.is_speaking:
                    self.is_speaking = True
                    print("\n[VAD] 正在听...")
                self.audio_buffer.append(chunk)
                self.silence_duration = 0
            else:
                if self.is_speaking:
                    self.audio_buffer.append(chunk)
                    self.silence_duration += 1
                    # 约 1 秒静音断句
                    if self.silence_duration > 50:
                        self.is_speaking = False
                        print("[VAD] 说话结束")
                        full_audio = np.concatenate(self.audio_buffer)
                        self.audio_buffer = []
                        asyncio.create_task(self._process_and_queue(full_audio))

    async def _process_and_queue(self, audio_data):
        try:
            audio_out = await run_ai_pipeline(audio_data)
            if audio_out is not None:
                await self.output_queue.put(audio_out)
        except Exception as e:
            print(f"AI Pipeline 报错: {e}")

    # --- 音频发送 ---
    async def emit(self):
        array = await wait_for_item(self.output_queue, 0.01)
        if array is not None:
            return (self.output_sample_rate, array)
        return None

    # ==========================================
    # ✨ 新增：补全视频接口（解决 TypeError）
    # ==========================================
    async def video_receive(self, frame: np.ndarray):
        """接收并处理面试者的视频帧（未来可在此做表情识别）"""
        # 目前仅作占位，不做处理
        pass

    async def video_emit(self) -> np.ndarray:
        """发送视频帧给面试者（未来可在此发送数字人画面）"""
        # 返回 None 表示暂不发送视频内容
        return None

    def copy(self):
        return PrecisionVADHandler()


# ==========================================
# 4. 启动
# ==========================================
stream = Stream(
    handler=PrecisionVADHandler(),
    # 如果以后想看到摄像头画面，请改为 "audio-video"
    modality="audio-video",
    mode="send-receive",

)

if __name__ == "__main__":
    # 使用 Python 3.11 运行此脚本
    stream.ui.launch()
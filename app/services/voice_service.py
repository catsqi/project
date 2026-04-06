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
# 2. 全局状态与资源
# ==========================================
model, utils = torch.hub.load(
    repo_or_dir='D:/ai_models/silero',
    model='silero_vad',
    source='local',
    trust_repo=True
)
(get_speech_timestamps, _, _, _, _) = utils

class ConversationState:
    def __init__(self):
        self.messages = [
            {
                "role": "system",
                "content": "你是一个严厉的AI面试官，名为Karen。请尽量精简，每次仅用一两句话回答或反问，避免长篇大论，以极低延迟交流。务必根据上下文追问细节。"
            }
        ]
        self.is_processing = False
        self.active_handler = None  # Reference to the current WebRTC handler instance

global_state = ConversationState()


# ==========================================
# 3. 统一多模态处理逻辑
# ==========================================
async def process_interaction_stream(input_type: str, content: any, output_queue: asyncio.Queue = None):
    """
    统一流式处理来自语音 (WebRTC) 或文字 (API) 的输入。
    """
    if global_state.is_processing:
        print("[System] 正在处理中，忽略新请求。")
        yield {"error": "Processing in progress"}
        return

    global_state.is_processing = True

    try:
        # 处理输入并追加历史记录
        if input_type == 'audio':
            audio_data, sample_rate = content
            byte_io = io.BytesIO()
            wavfile.write(byte_io, sample_rate, audio_data)
            base64_voice = base64.b64encode(byte_io.getvalue()).decode('utf-8')
            
            global_state.messages.append({
                "role": "user",
                "content": [{"type": "input_audio", "input_audio": {"data": base64_voice, "format": "wav"}}]
            })
            print("\n[AI] 接收到语音输入，开始生成...")
            
        elif input_type == 'text':
            global_state.messages.append({
                "role": "user",
                "content": [{"type": "text", "text": content}]
            })
            print(f"\n[AI] 接收到文本输入: '{content}'，开始生成...")
            
            # 尝试寻找活跃的 WebRTC 处理器的队列进行语音辅助播报
            if output_queue is None:
                if global_state.active_handler is not None:
                    output_queue = global_state.active_handler.output_queue
                    print(f"[System] 识别到活跃 WebRTC 通道，文本输入将同步推送到通道。")
                else:
                    print(f"[System] 注意：当前 WebRTC 未连接，音频将仅通过 API 流返回。")

        # 滑动窗口：System Prompt 永远保留，只发送最近 6 条消息（3 轮对话）给模型
        # 这样无论面试多少轮，发送给模型的 Token 数始终固定，时延不会随轮次增大
        WINDOW_SIZE = 6
        system_prompt = global_state.messages[:1]          # 始终包含 System Prompt
        recent_history = global_state.messages[-WINDOW_SIZE:]  # 最近 6 条对话
        # 防止 system_prompt 被重复包含
        if recent_history and recent_history[0].get("role") == "system":
            messages_to_send = recent_history
        else:
            messages_to_send = system_prompt + recent_history

        response_iter = await asyncio.to_thread(
            client.chat.completions.create,
            model="glm-4-voice",
            messages=messages_to_send,
            stream=True
        )

        full_text_response = ""
        current_audio_id = None
        
        # 定义一个“哨兵”对象，用于非阻塞地探测同步迭代器的结束
        sentinel = object()

        # 解析流式响应（非阻塞型迭代）
        while True:
            try:
                # 在后台线程获取下一个分片。如果结束，返回哨兵对象而不是抛出异常
                chunk = await asyncio.to_thread(next, response_iter, sentinel)
                if chunk is sentinel:
                    break
            except Exception as e:
                print(f"[Error] 获取分片失败: {e}")
                break

            delta = chunk.choices[0].delta
            text_chunk = ""
            audio_chunk_b64 = None

            # 1. 提取文字
            if hasattr(delta, 'content') and delta.content:
                text_chunk = delta.content
                full_text_response += text_chunk
                print(text_chunk, end="", flush=True)

            # 2. 提取音频
            if hasattr(delta, 'audio') and delta.audio:
                # 记录 ID（主线程中操作，安全）
                if current_audio_id is None:
                    if isinstance(delta.audio, dict):
                        current_audio_id = delta.audio.get('id')
                    else:
                        current_audio_id = getattr(delta.audio, 'id', None)
                
                # 提取 Base64
                if isinstance(delta.audio, str):
                    audio_chunk_b64 = delta.audio
                elif isinstance(delta.audio, dict):
                    audio_chunk_b64 = delta.audio.get('data')
                else:
                    audio_chunk_b64 = getattr(delta.audio, 'data', None)
                
                # 同步推送到 WebRTC 通道队列（主线程操作）
                if audio_chunk_b64 and output_queue is not None:
                    raw_audio_bytes = base64.b64decode(audio_chunk_b64)
                    audio_np = np.frombuffer(raw_audio_bytes, dtype=np.int16)
                    await output_queue.put(audio_np)
            
            # 实时发送到 API（SSE/Stream）
            if text_chunk or audio_chunk_b64:
                yield {
                    "text": text_chunk,
                    "audio": audio_chunk_b64,
                    "audio_id": current_audio_id
                }
            
            # 让出控制权，确保其他异步任务（如 WebRTC 包传输）有机会执行
            await asyncio.sleep(0)

        print(f"\n[AI] 传输完成。")
        
        # 将回答追加到历史记录
        assistant_msg = {"role": "assistant", "content": full_text_response}
        if current_audio_id:
            assistant_msg["audio"] = {"id": current_audio_id}
        global_state.messages.append(assistant_msg)
        
    except Exception as e:
        import traceback
        print(f"\n[Error] 流式交互失败:")
        traceback.print_exc()
        yield {"error": str(e)}
    finally:
        global_state.is_processing = False

async def process_interaction(input_type: str, content: any, output_queue: asyncio.Queue = None):
    """
    非流式封装，用于兼容 VAD。
    """
    full_text = ""
    async for chunk in process_interaction_stream(input_type, content, output_queue):
        if "text" in chunk:
            full_text += chunk["text"]
    return full_text


# ==========================================
# 4. 优化后的 VAD 处理器
# ==========================================
class HighSpeedVADHandler(AsyncAudioVideoStreamHandler):
    def __init__(self):
        super().__init__("mono", output_sample_rate=24000, input_sample_rate=16000)
        self.audio_buffer = []
        self.output_queue = asyncio.Queue()
        self.is_speaking_user = False
        self.silence_duration = 0
        self.frame_size = 512
        self.threshold = 0.5
        
        # 注册自身为活跃处理器，以便文本接口能找到播放队列
        global_state.active_handler = self

    async def receive(self, frame: tuple[int, np.ndarray]):
        # 如果系统正在处理上一个请求，或者正在播放音频，暂时忽略新的语音输入
        if global_state.is_processing or not self.output_queue.empty():
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
                if not self.is_speaking_user:
                    self.is_speaking_user = True
                    print("\n[VAD] 听...")
                self.audio_buffer.append(audio_data[i: i + self.frame_size])
                self.silence_duration = 0
            else:
                if self.is_speaking_user:
                    self.audio_buffer.append(audio_data[i: i + self.frame_size])
                    self.silence_duration += 1
                    
                    if self.silence_duration > 15:
                        self.is_speaking_user = False
                        print("[VAD] 说话结束，处理中...")
                        full_audio = np.concatenate(self.audio_buffer)
                        self.audio_buffer = []
                        
                        # 交给统一调度器处理
                        asyncio.create_task(self._process_stream(full_audio))

    async def _process_stream(self, audio_data):
        # 必须等待音频全部消耗完，才能开启下一轮监听
        await process_interaction('audio', (audio_data, self.input_sample_rate), self.output_queue)
        while not self.output_queue.empty():
            await asyncio.sleep(0.1)

    async def emit(self):
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
# 5. 组装路由
# ==========================================
stream = Stream(handler=HighSpeedVADHandler(), modality="audio", mode="send-receive")

if __name__ == "__main__":
    print("多模态交互 AI 面试官已就绪...")
    stream.ui.launch()
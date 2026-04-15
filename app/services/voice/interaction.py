from __future__ import annotations

import asyncio
import base64
import io
import json
from typing import Any, Callable

import numpy as np
from scipy.io import wavfile

from .glm_client import start_voice_stream
from .state import global_state


def _maybe_get_webrtc_output_queue(output_queue: asyncio.Queue | None) -> asyncio.Queue | None:
    """
    如果调用者没有提供输出队列，尝试使用活跃的 WebRTC 处理器，
    但仅在数据通道实际连接时才使用。
    """
    if output_queue is not None:
        return output_queue
    handler = global_state.active_handler
    if handler is None:
        return None

    # fastrtc 在 WebRTC 数据通道可用时会设置 `handler.channel`。
    # 之前的代码只检查 `handler is not None`，但这在真正的 WebRTC 连接建立前也为真，
    # 导致音频被推入一个永远不会被消费的队列（并且从 API 响应中被抑制）。
    if getattr(handler, "channel", None) is None:
        return None

    return handler.output_queue


async def process_interaction_stream(
    input_type: str,
    content: Any,
    output_queue: asyncio.Queue | None = None,
    user_transcript: str | None = None,
    *,
    manage_processing_state: bool = True,
    skip_history: bool = False,
):
    """
    统一流式处理来自语音 (WebRTC) 或文本 (API) 的输入。

    manage_processing_state:
      - True (默认): 此函数管理 `global_state.is_processing`。
      - False: 调用者管理 `global_state.is_processing`，此函数不会阻塞自己
        也不会在 finally 中翻转标志（由 VAD 管道使用，需要持有锁直到音频播放完成）。

    skip_history:
      - False (默认): 用户消息会写入 global_state.messages（持久化）。
      - True: 用户消息仅用于本次 API 请求，不写入历史记录（幽灵消息/静默轮次）。
        用于系统级触发词，如 "继续"，避免污染真实对话上下文。
    """
    if manage_processing_state and global_state.is_processing:
        print("[System] 正在处理中，忽略新请求。")
        yield {"error": "Processing in progress"}
        return

    if manage_processing_state:
        global_state.is_processing = True

    try:
        # 1. 拷贝当前真实的对话历史，用于构建本次 API 请求
        api_messages = list(global_state.messages)

        # 2. 处理输入：构建用户消息，加入本次请求，选择性持久化
        if input_type == "audio":
            audio_data, sample_rate = content
            byte_io = io.BytesIO()
            wavfile.write(byte_io, sample_rate, audio_data)
            base64_voice = base64.b64encode(byte_io.getvalue()).decode("utf-8")

            user_content = [{"type": "input_audio", "input_audio": {"data": base64_voice, "format": "wav"}}]
            if user_transcript:
                user_content.append({"type": "text", "text": f"(用户语音转录: {user_transcript})"})

            user_msg = {"role": "user", "content": user_content}
            api_messages.append(user_msg)  # 加入本次请求
            
            # 音频输入通常不跳过历史，但保持一致性
            if not skip_history:
                global_state.messages.append(user_msg)
            
            print(f"\n[AI] 语音输入，开始生成.. (持久化: {not skip_history})")

        elif input_type == "text":
            user_msg = {"role": "user", "content": [{"type": "text", "text": content}]}
            api_messages.append(user_msg)  # 无论是否跳过，都要加入本次请求！
            
            if not skip_history:
                global_state.messages.append(user_msg)  # 只有持久化才写全局
            
            print(f"\n[AI] 文本输入: '{content}' (持久化: {not skip_history})")

            output_queue = _maybe_get_webrtc_output_queue(output_queue)

        # 3. 滑动窗口：对 api_messages 做切片，而非 global_state.messages
        WINDOW_SIZE = 8
        system_prompt = api_messages[:1]
        recent_history = api_messages[-WINDOW_SIZE:]
        if recent_history and recent_history[0].get("role") == "system":
            messages_to_send = recent_history
        else:
            messages_to_send = system_prompt + recent_history

        response_iter = await asyncio.to_thread(start_voice_stream, messages_to_send)

        full_text_response = ""
        current_audio_id = None
        sentinel = object()

        while True:
            try:
                chunk = await asyncio.to_thread(next, response_iter, sentinel)
                if chunk is sentinel:
                    break
            except Exception as e:
                print(f"[Error] 获取分片失败: {e}")
                break

            delta = chunk.choices[0].delta
            text_chunk = ""
            audio_chunk_b64 = None

            # 1. 文本
            if hasattr(delta, "content") and delta.content:
                text_chunk = delta.content
                full_text_response += text_chunk

            # 2. 音频
            if hasattr(delta, "audio") and delta.audio:
                if current_audio_id is None:
                    if isinstance(delta.audio, dict):
                        current_audio_id = delta.audio.get("id")
                    else:
                        current_audio_id = getattr(delta.audio, "id", None)

                if isinstance(delta.audio, str):
                    audio_chunk_b64 = delta.audio
                elif isinstance(delta.audio, dict):
                    audio_chunk_b64 = delta.audio.get("data")
                else:
                    audio_chunk_b64 = getattr(delta.audio, "data", None)

                # WebRTC 播放优先：推到队列后，API 侧不再返回 base64 音频，避免重复
                if audio_chunk_b64 and output_queue is not None:
                    raw_audio_bytes = base64.b64decode(audio_chunk_b64)
                    
                    # 处理 WAV 头：如果数据以 RIFF 开头，需要剥离 WAV 头
                    if raw_audio_bytes[:4] == b'RIFF':
                        # 找到 'data' 子块的位置
                        idx = raw_audio_bytes.find(b'data')
                        if idx != -1 and idx + 8 < len(raw_audio_bytes):
                            data_start = idx + 8  # data 子块后4字节是长度，之后是 PCM
                            raw_audio_bytes = raw_audio_bytes[data_start:]
                            print(f"[Audio] 剥离 WAV 头，剩余 {len(raw_audio_bytes)} 字节 PCM")
                    
                    audio_np = np.frombuffer(raw_audio_bytes, dtype=np.int16)
                    await output_queue.put(audio_np)
                    audio_chunk_b64 = None

            if text_chunk or audio_chunk_b64:
                yield {
                    "type": "ai_text",
                    "text": text_chunk,
                    "audio": audio_chunk_b64,
                    "audio_id": current_audio_id,
                }

            await asyncio.sleep(0)

        # 统一消息格式：assistant 消息也使用数组格式，与 user 消息一致
        assistant_content = [{"type": "text", "text": full_text_response}]
        assistant_msg = {"role": "assistant", "content": assistant_content}
        if current_audio_id:
            assistant_msg["audio"] = {"id": current_audio_id}
        global_state.messages.append(assistant_msg)
        print(f"[AI] 回复完成: '{full_text_response[:50]}...' " if len(full_text_response) > 50 else f"[AI] 回复完成: '{full_text_response}'")

    except Exception as e:
        print(f"\n[Error] {e}")
        yield {"error": str(e)}
    finally:
        if manage_processing_state:
            global_state.is_processing = False


async def process_interaction(
    input_type: str,
    content: Any,
    output_queue: asyncio.Queue | None = None,
    on_text_chunk: Callable[[str], Any] | None = None,
    user_transcript: str | None = None,
    *,
    manage_processing_state: bool = True,
    skip_history: bool = False,
):
    """
    非流式封装，用于兼容 VAD。支持 on_text_chunk 回调实时推送文本。
    
    skip_history: 透传给 process_interaction_stream，用于幽灵消息。
    """
    full_text = ""
    async for chunk in process_interaction_stream(
        input_type,
        content,
        output_queue,
        user_transcript=user_transcript,
        manage_processing_state=manage_processing_state,
        skip_history=skip_history,
    ):
        if "text" in chunk and chunk["text"]:
            text_piece = chunk["text"]
            full_text += text_piece
            if on_text_chunk:
                if asyncio.iscoroutinefunction(on_text_chunk):
                    await on_text_chunk(text_piece)  # type: ignore[misc]
                else:
                    on_text_chunk(text_piece)
    return full_text


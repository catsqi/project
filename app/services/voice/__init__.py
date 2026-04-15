"""
语音服务模块 (WebRTC + LLM + ASR)。

本包将原有的单体 `app.services.voice_service` 拆分为更小的文件，
同时保持运行时行为不变。
"""

from .state import ConversationState, global_state
from .interaction import process_interaction, process_interaction_stream
from .stream import stream

__all__ = [
    "ConversationState",
    "global_state",
    "process_interaction",
    "process_interaction_stream",
    "stream",
]


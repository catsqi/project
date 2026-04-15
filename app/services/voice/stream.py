from __future__ import annotations

from fastrtc import Stream

from .vad_handler import HighSpeedVADHandler

# 组装 WebRTC 端点。
stream = Stream(handler=HighSpeedVADHandler(), modality="audio", mode="send-receive")


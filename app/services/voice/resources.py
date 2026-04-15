from __future__ import annotations

import torch
from faster_whisper import WhisperModel

from .config import SILERO_REPO_DIR, WHISPER_MODEL_PATH, USE_SENSEVOICE, SENSEVOICE_MODEL_PATH

# ------------------------------------------
# 语音活动检测 (Silero VAD)
# ------------------------------------------
model, utils = torch.hub.load(
    repo_or_dir=SILERO_REPO_DIR,
    model="silero_vad",
    source="local",
    trust_repo=True,
)
# utils 包含多个工具函数，但当前只使用了模型本身

# ------------------------------------------
# 自动语音识别 (ASR)
# ------------------------------------------
if USE_SENSEVOICE:
    # 使用 SenseVoice（中文最优）
    print(f"[System] 正在加载 SenseVoice 模型: {SENSEVOICE_MODEL_PATH}")
    from funasr import AutoModel
    
    sensevoice_model = AutoModel(
        model=SENSEVOICE_MODEL_PATH,
        trust_remote_code=True,
        disable_update=True,
        device="cuda:0" if torch.cuda.is_available() else "cpu",
    )
    whisper_model = None
    print("[System] SenseVoice 模型加载完成。")
else:
    # 使用 Whisper
    print(f"[System] 正在加载 Whisper 模型: {WHISPER_MODEL_PATH}")
    whisper_model = WhisperModel(WHISPER_MODEL_PATH, device="auto", compute_type="int8")
    sensevoice_model = None
    print("[System] Whisper 模型加载完成。")


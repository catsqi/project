from __future__ import annotations

import os

from dotenv import load_dotenv

# 为语音服务加载环境变量
load_dotenv()

GLM_4_VOICE_API_KEY = os.getenv("GLM_4_VOICE_API_KEY")

# 保持默认值与原始实现一致
GLM_MODEL = os.getenv("GLM_4_VOICE_MODEL", "glm-4-voice")
GLM_VOICE_NAME = os.getenv("GLM_4_VOICE_NAME", "charissa")

# 本地模型路径。默认值保持现有行为。
SILERO_REPO_DIR = os.getenv("SILERO_REPO_DIR", "D:/ai_models/silero")

# ASR 模型选择：
# 选项 1: Whisper small (75-80% 准确率)
# 选项 2: Whisper medium (85-90% 准确率)
# 选项 3: SenseVoice (92-96% 准确率，推荐) ← 当前使用
USE_SENSEVOICE = os.getenv("USE_SENSEVOICE", "true").lower() == "true"

# SenseVoice 模型路径（中文最优）
SENSEVOICE_MODEL_PATH = os.getenv(
    "SENSEVOICE_MODEL_PATH",
    r"D:/ai_models/SenseVoice/iic/SenseVoiceSmall",
)

# Whisper 模型路径（备选）
WHISPER_MODEL_PATH = os.getenv(
    "WHISPER_MODEL_PATH",
    r"d:\大三作业\大三下作业\project\app\services\models\models--Systran--faster-whisper-small\snapshots\c8c53c06e7b6892e1e46d6f46658e8e8a3f4f0e7",
)


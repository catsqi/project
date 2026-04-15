from __future__ import annotations

from zhipuai import ZhipuAI

from .config import GLM_4_VOICE_API_KEY, GLM_MODEL, GLM_VOICE_NAME

client = ZhipuAI(api_key=GLM_4_VOICE_API_KEY)


def start_voice_stream(messages: list[dict]) -> object:
    """
    启动流式补全调用并返回迭代器形式的响应。

    注意：返回对象故意类型为 `object`，以避免依赖特定的 SDK 类型
    （上游库之前曾更改过其类型定义）。
    """
    return client.chat.completions.create(
        model=GLM_MODEL,
        messages=messages,
        stream=True,
        extra_body={"voice": GLM_VOICE_NAME},  # 固定音色，避免受语音输入影响产生变音
    )


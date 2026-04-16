from __future__ import annotations

from zhipuai import ZhipuAI

from .config import GLM_4_VOICE_API_KEY, GLM_MODEL, GLM_VOICE_NAME

client = ZhipuAI(api_key=GLM_4_VOICE_API_KEY)


def start_voice_stream(messages: list[dict], max_tokens: int | None = None) -> object:
    """
    启动流式补全调用并返回迭代器形式的响应。
    """
    params = {
        "model": GLM_MODEL,
        "messages": messages,
        "stream": True,
        "extra_body": {"voice": GLM_VOICE_NAME},
    }
    if max_tokens:
        params["max_tokens"] = max_tokens
        
    return client.chat.completions.create(**params)


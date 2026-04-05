from typing import Any
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.core.llm import llm_client

router = APIRouter(prefix="/interview", tags=["interview"])

class ChatRequest(BaseModel):
    message: str
    history: list[dict[str, str]] = []

@router.post("/chat/stream", summary="Stream chat response from LLM")
async def chat_stream(request: ChatRequest):
    """
    流式生成大模型回复，并保持低延迟。
    """
    messages = [
        {"role": "system", "content": "你是一位专业的AI面试官。请根据面试者的回答进行追问或评价。保持简洁、专业且具有启发性。"},
    ]
    # 合并历史记录
    for msg in request.history:
        messages.append(msg)
    
    messages.append({"role": "user", "content": request.message})

    async def generate():
        # 获取流式输出 (注意: llm_client.chat_completion 返回的是同步生成器)
        response = llm_client.chat_completion(
            messages=messages,
            stream=True,
            temperature=0.7
        )
        
        for chunk in response:
            if chunk.choices and chunk.choices[0].delta.content:
                content = chunk.choices[0].delta.content
                yield content

    return StreamingResponse(generate(), media_type="text/plain")

@router.get("/placeholder", summary="Reserved interview route")
async def interview_placeholder() -> dict[str, str]:
    return {"message": "Interview module is reserved for future implementation."}

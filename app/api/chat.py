"""对话交互路由"""
import json

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.services.voice.interaction import process_interaction_stream
from app.services.voice.state import global_state
from app.services.interview.preparation_service import get_opening_from_cache

router = APIRouter(prefix="/api/chat", tags=["对话交互"])


class TextInput(BaseModel):
    text: str


class SyncTranscriptRequest(BaseModel):
    text: str


class StartInterviewRequest(BaseModel):
    candidate_id: str


@router.post("/reset")
async def reset_chat():
    """重置对话历史"""
    global_state.reset()
    return {"status": "reset_ok"}


@router.post("/start_interview")
async def start_interview(request: StartInterviewRequest):
    """开始面试，设置候选人ID"""
    global_state.candidate_id = request.candidate_id
    print(f"[System] 面试开始，候选人ID: {request.candidate_id[:8]}...")
    return {"status": "ok", "candidate_id": request.candidate_id}


@router.post("/sync_transcript")
async def sync_transcript(request: SyncTranscriptRequest):
    """同步语音转录"""
    transcript = request.text
    if transcript and global_state.messages:
        # 倒序查找最近的一条用户消息进行补录
        for i in range(len(global_state.messages) - 1, -1, -1):
            msg = global_state.messages[i]
            if msg["role"] == "user":
                content = msg["content"]
                if isinstance(content, list):
                    # 检查是否已经包含了转录文字（避免重复）
                    has_text = any(
                        c.get("type") == "text"
                        and "用户语音转录" in c.get("text", "")
                        for c in content
                    )
                    if not has_text:
                        content.append(
                            {
                                "type": "text",
                                "text": f"(用户语音转录: {transcript})",
                            }
                        )
                        print(f"[System] 已同步同步转录文本到历史记录: {transcript}")
                break
    return {"status": "sync_ok"}


@router.post("/text")
async def chat_text(input_data: TextInput):
    """文本对话（流式响应）"""

    async def generate():
        async for chunk in process_interaction_stream(
            input_type="text", content=input_data.text
        ):
            yield json.dumps(chunk, ensure_ascii=False) + "\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@router.get("/opening")
async def get_opening():
    """获取预生成的开场白"""
    candidate_id = global_state.candidate_id
    
    if not candidate_id:
        return {"status": "no_candidate", "message": "未设置候选人ID"}
    
    opening = get_opening_from_cache(candidate_id)
    
    if not opening:
        return {"status": "not_ready", "message": "开场白准备中，请稍后再试"}
    
    return {
        "status": "ready",
        "opening_text": opening["opening_text"],
        "opening_audio": opening.get("opening_audio"),
        "first_topic": opening["first_topic"],
        "questions": opening["questions"]
    }

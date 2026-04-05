import os

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.api import api_router
from app.core.config import settings
from app.services.voice_service import stream, process_interaction

class TextInput(BaseModel):
    text: str

def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # 1. 跨域配置
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 2. 健康检查
    @app.get("/health", tags=["system"], summary="Health check")
    async def health_check() -> dict[str, str]:
        return {"status": "ok", "app": settings.app_name}

    # 3. 业务 API
    app.include_router(api_router, prefix=settings.api_prefix)

    # 4. 静态文件挂载
    static_dir = os.path.join(os.path.dirname(__file__), "static")
    os.makedirs(static_dir, exist_ok=True)
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

    @app.get("/", include_in_schema=False)
    async def index() -> FileResponse:
        return FileResponse(os.path.join(static_dir, "fastrtc_test.html"))

    # 4.5. FastRTC ICE Configuration Endpoint
    @app.get("/voice/webrtc/config")
    async def get_webrtc_config():
        """提供与 Stream 相同的 ICE 配置给前端"""
        return {
            "iceServers": [
                {"urls": "stun:stun.l.google.com:19302"},
                {"urls": "stun:stun1.l.google.com:19302"},
            ]
        }

    # 4.6. Text Input Multimodal Endpoint (Streaming)
    @app.post("/api/chat/text", tags=["multimodal"], summary="Text Input with streaming response")
    async def text_chat(input_data: TextInput):
        """
        接收普通文本输入，交由全局 Voice Service 处理。
        通过 StreamingResponse 实时返还文字和音频分片。
        """
        from app.services.voice_service import process_interaction_stream
        import json

        async def generate():
            async for chunk in process_interaction_stream(input_type='text', content=input_data.text):
                # 以换行符分隔的 JSON 流，方便前端解析
                yield json.dumps(chunk, ensure_ascii=False) + "\n"

        from fastapi.responses import StreamingResponse
        return StreamingResponse(
            generate(), 
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
                "Connection": "keep-alive",
            }
        )

    # 5. 【关键】挂载 FastRTC 语音流（放在最后）
    print(">>> [DEBUG] Mounting FastRTC Stream at /voice ...")
    stream.mount(app, path="/voice")

    print(">>> [DEBUG] Registered routes:")
    for route in app.routes:
        methods = getattr(route, "methods", None)
        methods_text = ",".join(sorted(methods)) if methods else "MOUNT"
        print(f"    {methods_text:20s} {route.path}")
    
    return app

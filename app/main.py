import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.services.voice_service import stream
from app.api.resume import router as resume_router
from app.api.chat import router as chat_router


def create_app() -> FastAPI:
    app = FastAPI(
        title="AI Interview Platform",
        version="0.1.0",
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
        return {"status": "ok", "app": "AI Interview Platform"}
    
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

    # 5. 注册 API 路由
    app.include_router(resume_router)
    app.include_router(chat_router)

    # 6. 【关键】挂载 FastRTC 语音流（放在最后）
    print(">>> [DEBUG] Mounting FastRTC Stream at /voice ...")
    stream.mount(app, path="/voice")

    print(">>> [DEBUG] Registered routes:")
    for route in app.routes:
        methods = getattr(route, "methods", None)
        methods_text = ",".join(sorted(methods)) if methods else "MOUNT"
        print(f"    {methods_text:20s} {route.path}")

    return app

from app import create_app

app = create_app()

if __name__ == "__main__":
    import os
    import uvicorn
    # 直接运行 app 实例，提高稳定性
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(app, host=host, port=port)

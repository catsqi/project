from fastapi import APIRouter

from app.api.interview import router as interview_router

api_router = APIRouter()
api_router.include_router(interview_router)

__all__ = ["api_router"]

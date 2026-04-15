"""简历上传与管理路由"""
from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel
from app.services.resume_service import upload_and_parse, confirm_and_store

router = APIRouter(prefix="/api/resume", tags=["简历管理"])


class ConfirmRequest(BaseModel):
    candidate_id: str
    resume: dict


@router.post("/upload")
async def upload_resume(file: UploadFile = File(...)):
    """上传简历文件并解析"""
    result = await upload_and_parse(file)
    return result


@router.post("/confirm")
async def confirm_resume(request: ConfirmRequest):
    """确认简历并存入知识库"""
    result = await confirm_and_store(request.candidate_id, request.resume)
    return result

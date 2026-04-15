"""统一简历服务 - 编排文件上传、解析、知识库入库的完整流程"""

import uuid
import asyncio
from fastapi import UploadFile, HTTPException
from app.services.file_parser import extract_text
from app.services.llm_service import extract_resume_to_json
from app.services.knowledge_service import build_candidate_knowledge_base
from app.services.interview.preparation_service import get_preparation_service
from app.models.resume_schema import ComplexResume
from app.core.database import db

# 临时缓存解析结果（candidate_id -> resume），供确认步骤使用
_resume_cache: dict[str, dict] = {}


async def upload_and_parse(file: UploadFile) -> dict:
    """
    上传文件 → 提取文本 → LLM解析为结构化简历
    
    返回: {
        "candidate_id": "uuid-string",
        "resume": { ComplexResume 的 dict 形式 }
    }
    """
    try:
        # 1. 调用 file_parser.extract_text() 提取文本
        raw_text = await extract_text(file)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"文本提取失败: {str(e)}"
        )
    
    try:
        # 2. 调用 llm_service.extract_resume_to_json() 解析为 ComplexResume
        resume = await extract_resume_to_json(raw_text)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"简历解析失败，LLM 处理出错: {str(e)}"
        )
    
    # 3. 生成 candidate_id (uuid4)
    candidate_id = str(uuid.uuid4())
    
    # 4. 将结果缓存到 _resume_cache
    _resume_cache[candidate_id] = resume.model_dump()
    
    # 5. 返回 candidate_id + resume dict
    return {
        "candidate_id": candidate_id,
        "resume": resume.model_dump()
    }


async def confirm_and_store(candidate_id: str, resume_data: dict) -> dict:
    """
    确认简历 → 写入 candidates 表 → 构建知识库
    
    参数:
        candidate_id: 候选人ID
        resume_data: ComplexResume 的 dict 格式
    返回: {
        "candidate_id": str,
        "candidate_name": str,
        "message": "简历已确认，知识库构建完成"
    }
    """
    # 1. 将 resume_data 解析为 ComplexResume 对象（用 Pydantic 验证）
    try:
        resume = ComplexResume(**resume_data)
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"简历数据格式无效: {str(e)}"
        )
    
    # 2. 使用数据库连接，向 candidates 表插入记录
    try:
        insert_sql = """
            INSERT INTO candidates (candidate_id, candidate_name)
            VALUES (:candidate_id, :candidate_name)
        """
        await db.async_execute(insert_sql, {
            "candidate_id": candidate_id,
            "candidate_name": resume.candidate_name
        })
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"候选人信息写入数据库失败: {str(e)}"
        )
    
    # 3. 调用 knowledge_service.build_candidate_knowledge_base 构建知识库
    try:
        inserted_count = await build_candidate_knowledge_base(candidate_id, resume)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"知识库构建失败: {str(e)}"
        )
    
    # 4. 【新增】后台异步准备面试（生成开场白）
    # 使用 asyncio.create_task 不阻塞响应
    try:
        preparation_service = get_preparation_service()
        asyncio.create_task(
            preparation_service.prepare_interview(candidate_id, resume_data)
        )
        print(f"[ResumeService] 面试准备任务已启动: {candidate_id[:8]}...")
    except Exception as e:
        print(f"[ResumeService-Warning] 面试准备任务启动失败: {e}")
        # 不阻断主流程
    
    # 5. 从 _resume_cache 中清除该条目
    if candidate_id in _resume_cache:
        del _resume_cache[candidate_id]
    
    # 6. 返回成功信息
    return {
        "candidate_id": candidate_id,
        "candidate_name": resume.candidate_name,
        "message": f"简历已确认，知识库构建完成，共插入 {inserted_count} 条切片"
    }

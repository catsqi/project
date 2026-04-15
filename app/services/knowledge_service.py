import json
import uuid
import os
from openai import AsyncOpenAI
from app.core.database import db
from app.models.resume_schema import ComplexResume

# 1. 读取向量模型专属配置（这里用的是 OpenAI 的向量模型）
EMBEDDING_API_KEY = os.getenv("DASHSCOPE_API_KEY")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
EMBEDDING_BASE_URL = os.getenv("EMBEDDING_BASE_URL","https://dashscope.aliyuncs.com/compatible-mode/v1")
# 2. 初始化向量生成的专属客户端 (注意这里不加 base_url，默认去 OpenAI)
vector_client = AsyncOpenAI(
    api_key=EMBEDDING_API_KEY,
    base_url=EMBEDDING_BASE_URL  # ← 添加这行
)

async def generate_embedding(text: str) -> list[float]:
    response = await vector_client.embeddings.create(
        input=text,
        model=EMBEDDING_MODEL
    )
    return response.data[0].embedding


async def build_candidate_knowledge_base(candidate_id: str, resume: ComplexResume):
    name = resume.candidate_name
    inserted_count = 0

    # 1. 切割全局切片
    global_text = f"[{name}的全局概览]：{resume.global_profile.summary}。技术栈：{', '.join(resume.global_profile.all_technical_skills)}。"
    global_meta = {
        "chunk_type": "global_summary",
        "skills": resume.global_profile.all_technical_skills
    }
    await _insert_chunk(candidate_id, global_text, global_meta)
    inserted_count += 1

    # 2. 循环切割项目切片
    for proj in resume.projects:
        proj_text = f"[{name}的项目经历] 在{proj.time_period}担任【{proj.project_name}】的{proj.role}。描述：{proj.description}。"
        if proj.star_extraction:
            proj_text += f" 背景任务：{proj.star_extraction.situation_task}。行动结果：{proj.star_extraction.action_result}。"

        proj_meta = {
            "chunk_type": "project_detail",
            "project_name": proj.project_name,
            "skills": proj.project_specific_skills  # 完美隔离技术栈
        }
        await _insert_chunk(candidate_id, proj_text, proj_meta)
        inserted_count += 1

    return inserted_count


async def _insert_chunk(candidate_id: str, content: str, metadata: dict):
    # 转向量
    vector = await generate_embedding(content)

    # 入库 (原生 SQL 配合 pgvector)
    sql = """
        INSERT INTO resume_chunks (chunk_id, candidate_id, chunk_category, content, metadata, embedding)
        VALUES (:id, :cid, :cat, :cnt, :meta, :emb)
    """
    await db.async_execute(sql, {
        "id": str(uuid.uuid4()),
        "cid": candidate_id,
        "cat": metadata.get("chunk_type"),
        "cnt": content,
        "meta": json.dumps(metadata, ensure_ascii=False),
        "emb": str(vector)
    })
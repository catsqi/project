import json
import os
import logging

from dotenv import load_dotenv
from openai import AsyncOpenAI
from app.models.resume_schema import ComplexResume

load_dotenv()

# 初始化 logger
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# 1. 读取正确的环境变量
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

# 2. 初始化 DeepSeek 专属客户端
client = AsyncOpenAI(
    api_key=DEEPSEEK_API_KEY,
    base_url=DEEPSEEK_BASE_URL
)

SYSTEM_PROMPT = """
你是一个专业的 HR 数据解析引擎。请提取用户简历，并严格输出合法的 JSON 格式。
【提取准则】
1. 技能解耦：必须区分"全局技能"和"单个项目专属技能(project_specific_skills)"。
2. STAR法则：项目经历必须尝试提取 situation_task 和 action_result。
3. 如果无数据请填空字符串 "" 或空数组 []，绝不捏造。
4. 所有字段必须存在，即使为空也要返回空数组 [] 或空字符串 ""。

输出必须严格符合以下 JSON 结构：
{
  "candidate_name": "姓名",
  "global_profile": {
    "summary": "个人总结概述",
    "all_technical_skills": ["技能1", "技能2"],
    "all_behavioral_tags": ["标签1", "标签2"]
  },
  "projects": [
    {
      "project_id": "p1",
      "project_name": "项目名称",
      "role": "角色",
      "time_period": "时间段",
      "description": "项目描述",
      "project_specific_skills": ["项目专属技能"],
      "project_specific_behavioral": ["项目行为标签"],
      "star_extraction": {
        "situation_task": "情境与任务",
        "action_result": "行动与结果"
      }
    }
  ]
}

注意：all_behavioral_tags 是必须的字段，即使没有也要返回空数组 []。
"""

async def extract_resume_to_json(raw_text: str) -> ComplexResume:
    """调用大模型，输出结构化 Pydantic 对象"""
    logger.info(f"[LLM解析] 开始调用 API - 模型: {DEEPSEEK_MODEL}, 文本长度: {len(raw_text)}")
    
    try:
        response = await client.chat.completions.create(
            model=DEEPSEEK_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"请解析以下简历:\n{raw_text}"}
            ],
            response_format={"type": "json_object"},
            temperature=0.1
        )
        logger.info(f"[LLM解析] API 调用成功, response id: {response.id}")
    except Exception as e:
        logger.error(f"[LLM解析] API 调用失败: {type(e).__name__}: {str(e)}", exc_info=True)
        raise
    
    # 提取响应内容
    try:
        content = response.choices[0].message.content
        logger.info(f"[LLM解析] 返回内容长度: {len(content) if content else 0}")
        logger.debug(f"[LLM解析] 返回内容前200字符: {content[:200] if content else 'None'}")
    except Exception as e:
        logger.error(f"[LLM解析] 提取响应内容失败: {type(e).__name__}: {str(e)}", exc_info=True)
        raise
    
    # JSON 解析
    try:
        json_data = json.loads(content)
        logger.info(f"[LLM解析] JSON 解析成功, keys: {list(json_data.keys())}")
    except json.JSONDecodeError as e:
        logger.error(f"[LLM解析] JSON 解析失败: {str(e)}", exc_info=True)
        logger.error(f"[LLM解析] 原始内容: {content}")
        raise
    
    # 字段补全：确保关键字段存在
    try:
        # 确保根节点字段存在
        json_data.setdefault("candidate_name", "")
        json_data.setdefault("projects", [])
        
        # 确保 global_profile 存在且有默认值
        if "global_profile" not in json_data or not isinstance(json_data["global_profile"], dict):
            json_data["global_profile"] = {}
        gp = json_data["global_profile"]
        gp.setdefault("summary", "")
        gp.setdefault("all_technical_skills", [])
        gp.setdefault("all_behavioral_tags", [])
        
        # 确保每个项目都有必需的字段
        for idx, project in enumerate(json_data.get("projects", [])):
            if not isinstance(project, dict):
                continue
            project.setdefault("project_id", f"p{idx+1}")
            project.setdefault("project_name", "")
            project.setdefault("role", "")
            project.setdefault("time_period", "")
            project.setdefault("description", "")
            project.setdefault("project_specific_skills", [])
            project.setdefault("project_specific_behavioral", [])
            # star_extraction 可选，但如果存在则确保字段完整
            if "star_extraction" in project and isinstance(project["star_extraction"], dict):
                se = project["star_extraction"]
                se.setdefault("situation_task", "")
                se.setdefault("action_result", "")
        
        logger.info(f"[LLM解析] 字段补全完成")
    except Exception as e:
        logger.warning(f"[LLM解析] 字段补全时出错: {type(e).__name__}: {str(e)}")
    
    # Pydantic 验证
    try:
        resume = ComplexResume(**json_data)
        logger.info(f"[LLM解析] Pydantic 验证成功, 候选人: {resume.candidate_name}")
        return resume
    except Exception as e:
        logger.error(f"[LLM解析] Pydantic 验证失败: {type(e).__name__}: {str(e)}", exc_info=True)
        logger.error(f"[LLM解析] JSON 数据: {json_data}")
        raise
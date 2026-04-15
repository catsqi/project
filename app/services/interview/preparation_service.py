"""
面试准备服务

职责：
- 在简历确认阶段预生成面试开场白
- 分析简历内容，检索相关题库
- 调用 DeepSeek 生成 InterviewGuidance
- 调用 GLM 生成个性化开场白语音

使用场景：
用户在确认页面点击"开始面试"后，后台异步执行：
1. 分析简历提取考核点
2. 检索 javabackend 题库
3. DeepSeek 决策第一个问题
4. GLM 生成开场白（含语音）
5. 缓存结果供面试页面直接使用
"""

import os
import json
import wave
import io
import base64
from typing import Dict, Optional, List
from openai import AsyncOpenAI
from dotenv import load_dotenv

from app.services.pg_retriever import get_retriever
from .models import InterviewGuidance, ActionType
import sys
from pathlib import Path
from app.services.voice.glm_client import start_voice_stream
from app.services.voice.config import GLM_MODEL
import asyncio

load_dotenv()

# 全局缓存：candidate_id -> 开场白数据
_opening_cache: Dict[str, Dict] = {}


class InterviewPreparationService:
    """面试准备服务 - 预生成开场白"""
    
    def __init__(self):
        # DeepSeek 客户端（用于决策）
        self.decision_client = AsyncOpenAI(
            api_key=os.getenv("DEEPSEEK_API_KEY"),
            base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
        )
        self.decision_model = os.getenv("CONTROLLER_MODEL", "deepseek-chat")
        
        # 检索器
        self.retriever = get_retriever()
        
        print("[Preparation] 面试准备服务初始化完成")
    
    @staticmethod
    def _pcm_to_wav_base64(pcm_base64_chunks: List[str], sample_rate: int = 24000, channels: int = 1, sample_width: int = 2) -> str:
        """
        将多个 PCM/WAV base64 数据片段合并转换为标准 WAV
        
        关键：先解码所有 chunks 为原始 PCM 字节，拼接后再统一加 WAV 头
        如果 chunks 已经是 WAV 格式，会先剥离 WAV 头
        """
        try:
            # 1. 解码所有 chunks 为 PCM 字节并拼接
            all_pcm_bytes = b''
            for i, chunk_b64 in enumerate(pcm_base64_chunks):
                chunk_bytes = base64.b64decode(chunk_b64)
                
                # 检查是否包含 WAV 头（RIFF标志）
                if chunk_bytes[:4] == b'RIFF':
                    # 包含 WAV 头，需要剥离
                    # WAV 文件结构：RIFF header (12字节) + fmt chunk + data chunk
                    # 找到 'data' 子块的位置
                    idx = chunk_bytes.find(b'data')
                    if idx != -1 and idx + 8 < len(chunk_bytes):
                        # data 子块后4字节是数据长度，之后才是真正的 PCM 数据
                        data_start = idx + 8
                        all_pcm_bytes += chunk_bytes[data_start:]
                        print(f"[Preparation-DEBUG] Chunk {i}: 剥离 WAV 头，提取 {len(chunk_bytes) - data_start} 字节 PCM")
                    else:
                        # 找不到 data 子块，直接使用
                        all_pcm_bytes += chunk_bytes
                        print(f"[Preparation-DEBUG] Chunk {i}: 无法剥离 WAV 头，使用原始数据 {len(chunk_bytes)} 字节")
                else:
                    # 纯 PCM 数据，直接使用
                    all_pcm_bytes += chunk_bytes
                    print(f"[Preparation-DEBUG] Chunk {i}: 纯 PCM 数据 {len(chunk_bytes)} 字节")
            
            print(f"[Preparation-DEBUG] 合并后总 PCM 数据: {len(all_pcm_bytes)} 字节")
            
            # 2. 创建统一的 WAV 文件
            wav_buffer = io.BytesIO()
            with wave.open(wav_buffer, 'wb') as wav_file:
                wav_file.setnchannels(channels)
                wav_file.setsampwidth(sample_width)
                wav_file.setframerate(sample_rate)
                wav_file.writeframes(all_pcm_bytes)
            
            # 3. 获取 WAV 数据并编码为 base64
            wav_buffer.seek(0)
            wav_data = wav_buffer.read()
            result_b64 = base64.b64encode(wav_data).decode('utf-8')
            print(f"[Preparation-DEBUG] 生成 WAV: {len(wav_data)} 字节 -> Base64: {len(result_b64)} 字符")
            return result_b64
            
        except Exception as e:
            print(f"[Preparation-Error] PCM 转 WAV 失败: {e}")
            # 降级：返回第一个 chunk
            return pcm_base64_chunks[0] if pcm_base64_chunks else ""
    
    async def prepare_interview(self, candidate_id: str, resume_data: Dict) -> Dict:
        """
        准备面试：分析简历 → 检索题库 → 生成开场白
        
        参数：
        - candidate_id: 候选人ID
        - resume_data: 简历结构化数据
        
        返回：
        {
            "candidate_id": str,
            "opening_text": str,      # 开场白文本
            "opening_audio": str,     # 开场白音频(base64)
            "first_topic": str,       # 第一个考核点
            "questions": List[Dict],  # 相关题目
            "guidance": Dict          # InterviewGuidance
        }
        """
        print(f"\n[Preparation] 开始为候选人 {candidate_id[:8]}... 准备面试")
        
        # 1. 提取简历关键信息
        candidate_name = resume_data.get("candidate_name", "候选人")
        skills = self._extract_skills(resume_data)
        projects = resume_data.get("projects", [])
        
        print(f"[Preparation] 提取到技能: {skills[:5]}...")
        print(f"[Preparation] 项目数量: {len(projects)}")
        
        # 2. 根据技能检索题库
        questions = await self._retrieve_questions_for_skills(skills)
        print(f"[Preparation] 检索到 {len(questions)} 道相关题目")
        
        # 3. DeepSeek 决策第一个考核点
        guidance = await self._decide_first_topic(candidate_name, skills, projects, questions)
        print(f"[Preparation] DeepSeek 决策: {guidance['target_topic']}")
        
        # 4. GLM 生成个性化开场白（含语音）
        opening = await self._generate_opening(candidate_name, guidance, projects)
        print(f"[Preparation] 开场白生成完成 ({len(opening['text'])} 字符)")
        
        # 5. 组装结果
        result = {
            "candidate_id": candidate_id,
            "opening_text": opening["text"],
            "opening_audio": opening.get("audio"),  # 可能为None
            "first_topic": guidance["target_topic"],
            "questions": questions[:3],  # 只保留前3题
            "guidance": guidance
        }
        
        # 6. 缓存结果
        _opening_cache[candidate_id] = result
        print(f"[Preparation] 面试准备完成，已缓存")
        
        return result
    
    def _extract_skills(self, resume_data: Dict) -> List[str]:
        """从简历提取技能列表"""
        skills = []
        
        # 全局技能
        global_skills = resume_data.get("global_profile", {}).get("all_technical_skills", [])
        skills.extend(global_skills)
        
        # 项目技能
        for proj in resume_data.get("projects", []):
            proj_skills = proj.get("project_specific_skills", [])
            skills.extend(proj_skills)
        
        # 去重并返回
        return list(dict.fromkeys(skills))  # 保持顺序去重
    
    async def _retrieve_questions_for_skills(self, skills: List[str]) -> List[Dict]:
        """根据技能列表检索相关题目"""
        all_questions = []
        seen_ids = set()
        
        # 对每个技能检索题目
        for skill in skills[:5]:  # 最多前5个技能
            try:
                questions = await self.retriever.search_questions(skill, limit=3)
                for q in questions:
                    if q.get("id") not in seen_ids:
                        all_questions.append(q)
                        seen_ids.add(q.get("id"))
            except Exception as e:
                print(f"[Preparation-Warning] 检索技能 '{skill}' 失败: {e}")
        
        # 按相似度排序
        all_questions.sort(key=lambda x: x.get("similarity", 0), reverse=True)
        return all_questions
    
    async def _decide_first_topic(
        self, 
        candidate_name: str, 
        skills: List[str], 
        projects: List[Dict],
        questions: List[Dict]
    ) -> Dict:
        """
        使用 DeepSeek 决策第一个考核点
        
        简化版：不生成完整的 InterviewGuidance，只决定考什么
        """
        # 构建 Prompt
        project_names = [p.get("project_name", "") for p in projects[:2]]
        question_previews = [f"[{q.get('category')}] {q.get('question', '')[:40]}..." for q in questions[:5]]
        
        prompt = f"""请分析以下候选人简历，决定面试的第一个考核点。

候选人：{candidate_name}
技能列表：{', '.join(skills[:10])}
主要项目：{', '.join(project_names)}

相关题库题目：
{chr(10).join(question_previews)}

请输出 JSON 格式决策：
{{
    "target_topic": "要考核的技术点（从技能中选择最核心的）",
    "question_focus": "核心要了解什么",
    "suggested_angle": "提问角度（原理/实践/优化/场景）",
    "context_hints": ["结合简历的提示1", "结合简历的提示2"],
    "selected_question_id": "选用的题库ID（从上面选择最相关的）",
    "reason": "选择理由"
}}"""
        
        try:
            response = await self.decision_client.chat.completions.create(
                model=self.decision_model,
                messages=[
                    {"role": "system", "content": "你是技术面试官，负责决定面试策略。输出JSON格式。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            
            # 查找选用的题目原文
            selected_question = None
            selected_id = result.get("selected_question_id")
            for q in questions:
                if q.get("id") == selected_id:
                    selected_question = q.get("question")
                    break
            
            return {
                "action": "transition",
                "target_topic": result.get("target_topic", skills[0] if skills else "Java基础"),
                "question_focus": result.get("question_focus", "了解技术经验"),
                "suggested_angle": result.get("suggested_angle", "实践"),
                "context_hints": result.get("context_hints", []),
                "question_bank_id": selected_id,
                "question_bank_text": selected_question,
                "reason": result.get("reason", "")
            }
            
        except Exception as e:
            print(f"[Preparation-Error] DeepSeek 决策失败: {e}")
            # 降级：使用第一个技能
            return {
                "action": "transition",
                "target_topic": skills[0] if skills else "Java基础",
                "question_focus": f"了解{skills[0] if skills else 'Java'}的使用经验",
                "suggested_angle": "实践",
                "context_hints": ["从简历中提取的核心技能"],
                "question_bank_id": questions[0].get("id") if questions else None,
                "question_bank_text": questions[0].get("question") if questions else None,
                "reason": "DeepSeek 失败，使用默认策略"
            }

    async def _generate_opening(self, candidate_name: str, guidance: Dict, projects: List[Dict]) -> Dict:
        """
        使用 GLM-4-Voice 生成个性化开场白（文本 + 语音）
        
        返回：{"text": str, "audio": str|None}  # audio 为 base64 编码
        """
        # 构建 Prompt
        project_info = ""
        if projects:
            proj = projects[0]
            project_info = f"主要项目：{proj.get('project_name', '')}，使用技术：{', '.join(proj.get('project_specific_skills', []))}"
        
        first_topic = guidance["target_topic"]
        first_question = guidance.get("question_bank_text", "")  # DeepSeek 选定的具体题目
        
        # GLM-4-Voice 消息格式：system用字符串，user用数组
        messages = [
            {
                "role": "system",
                "content": "你是AI面试官Karen，语气友好专业。你正在开始一场真实的面试对话，请直接以面试官身份说话，不要描述或解释你在做什么。"
            },
            {
                "role": "user",
                "content": [{
                    "type": "text",
                    "text": f"""请以AI面试官Karen的身份，直接向候选人说出面试的开场白。

候选人姓名：{candidate_name}
简历亮点：{project_info}
本次面试要考核的第一个技术点：{first_topic}
准备提出的第一个问题：{first_question}

要求：
1. 以面试官Karen的身份直接说话，就像正在面对候选人一样
2. 先简单自我介绍（"你好，我是Karen，今天的面试官"）
3. 简要提及已阅读简历，对候选人的项目经验表示认可
4. 直接提出第一个具体问题（使用上面的"准备提出的第一个问题"），要求候选人现在回答
5. 语气友好专业，简洁明了（4-5句话）
6. 不要加任何前缀如"这是生成的开场白"等
7. 不要问"是否符合要求"或"是否需要调整"之类的话
8. 你是真正的面试官，不是AI助手

请直接输出你要对候选人说的话，只输出说话内容，不要有任何额外说明或解释。"""
                }]
            }
        ]
        
        try:
            # 使用同步客户端（在线程池中运行）
            response_iter = await asyncio.to_thread(start_voice_stream, messages)
            
            full_text = ""
            audio_chunks = []
            current_audio_id = None
            sentinel = object()
            
            # 处理流式响应
            while True:
                try:
                    chunk = await asyncio.to_thread(next, response_iter, sentinel)
                    if chunk is sentinel:
                        break
                except Exception as e:
                    print(f"[Preparation-Error] 获取分片失败: {e}")
                    break
                
                delta = chunk.choices[0].delta
                
                # 1. 提取文本
                if hasattr(delta, "content") and delta.content:
                    full_text += delta.content
                
                # 2. 提取音频
                if hasattr(delta, "audio") and delta.audio:
                    # 获取音频 ID
                    if current_audio_id is None:
                        if isinstance(delta.audio, dict):
                            current_audio_id = delta.audio.get("id")
                        else:
                            current_audio_id = getattr(delta.audio, "id", None)
                        print(f"[Preparation-DEBUG] 音频流开始，ID: {current_audio_id}")

                    # 获取音频数据
                    audio_data = None
                    if isinstance(delta.audio, str):
                        audio_data = delta.audio
                    elif isinstance(delta.audio, dict):
                        audio_data = delta.audio.get("data")
                    else:
                        audio_data = getattr(delta.audio, "data", None)

                    if audio_data:
                        chunk_idx = len(audio_chunks)
                        # 检查是否包含 WAV 头 (RIFF 标志)
                        is_wav = False
                        try:
                            decoded = base64.b64decode(audio_data[:20])  # 解码前20个字符看头部
                            if decoded[:4] == b'RIFF':
                                is_wav = True
                        except:
                            pass
                        print(f"[Preparation-DEBUG] Chunk {chunk_idx}: {len(audio_data)} chars, is_wav={is_wav}, head={audio_data[:30]}...")
                        audio_chunks.append(audio_data)

            # 拼接音频数据
            full_audio_b64 = None
            if audio_chunks:
                print(f"[Preparation-DEBUG] 共收到 {len(audio_chunks)} 个音频 chunks")
                # GLM-4-Voice 返回的是多个带 WAV 头的片段，需要剥离后重新打包
                full_audio_b64 = self._pcm_to_wav_base64(audio_chunks, sample_rate=24000)
                print(f"[Preparation] 开场白语音生成成功 (WAV: {len(full_audio_b64)} chars)")
            
            return {
                "text": full_text.strip(),
                "audio": full_audio_b64
            }
            
        except Exception as e:
            print(f"[Preparation-Error] GLM 生成开场白失败: {e}")
            # 降级：使用模板
            default_opening = f"你好{candidate_name}，我是Karen。我已经仔细阅读了你的简历，看到你有不错的技术背景。那我们先从{first_topic}开始聊聊吧，你能简单介绍一下你在这方面的经验吗？"
            return {
                "text": default_opening,
                "audio": None
            }


def get_opening_from_cache(candidate_id: str) -> Optional[Dict]:
    """从缓存获取开场白"""
    return _opening_cache.get(candidate_id)


def clear_opening_cache(candidate_id: str):
    """清除缓存"""
    if candidate_id in _opening_cache:
        del _opening_cache[candidate_id]


# 全局单例
_preparation_service: Optional[InterviewPreparationService] = None


def get_preparation_service() -> InterviewPreparationService:
    """获取准备服务单例"""
    global _preparation_service
    if _preparation_service is None:
        _preparation_service = InterviewPreparationService()
    return _preparation_service

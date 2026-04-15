"""
InterviewController - AI 面试大脑控制器（精简组装版）

职责：
- 组装各个子模块
- 提供统一的决策入口
- 协调检索 → 分析 → 决策 → 状态更新 全流程

**重要变化：**
- 不再生成台词！只生成 InterviewGuidance（思路指令）
- GLM-4-Voice 根据思路自己组织话术

使用示例：
    controller = InterviewController()
    controller.load_candidate(resume_json)
    
    guidance = await controller.decide_next_action(user_input)
    # guidance 包含思路指令，交给 GLM 组织话术
"""

from typing import Dict, List

from .models import InterviewGuidance
from .state_manager import InterviewStateManager
from .quality_analyzer import AnswerQualityAnalyzer
from .decision_engine import DecisionEngine

# 引入检索器
from app.services.pg_retriever import get_retriever


class InterviewController:
    """
    AI 面试大脑控制器 - 组装器模式
    
    将复杂功能拆分为：
    - StateManager: 状态管理
    - QualityAnalyzer: 质量分析
    - DecisionEngine: 决策引擎
    - Retriever: 题目检索（外部）
    - ResumeRetriever: 简历知识库检索（新增）
    """
    
    def __init__(self, max_depth_per_topic: int = 3):
        print("[Controller] 初始化 InterviewController...")
        
        # 子模块
        self.state = InterviewStateManager(max_depth_per_topic)
        self.analyzer = AnswerQualityAnalyzer()
        self.engine = DecisionEngine(self.state)
        self.retriever = get_retriever()
        
        # 新增：候选人ID（用于简历知识库检索）
        self.candidate_id: str = None
        self.resume_context: str = ""  # 缓存当前简历上下文
        
        print("[Controller] 初始化完成")
    
    def load_candidate(self, resume_json: Dict, candidate_id: str = None):
        """加载候选人简历
        
        参数：
        - resume_json: 简历结构化数据
        - candidate_id: 候选人ID（用于简历知识库检索）
        """
        self.state.load_candidate(resume_json)
        self.candidate_id = candidate_id
        if candidate_id:
            print(f"[Controller] 候选人ID已设置: {candidate_id[:8]}...")
    
    def load_candidate_with_id(self, candidate_id: str):
        """仅通过 candidate_id 加载候选人（从数据库检索简历切片）
        
        用于语音面试流程，从 resume_chunks 表获取简历信息
        """
        self.candidate_id = candidate_id
        print(f"[Controller] 通过ID加载候选人: {candidate_id[:8]}...")
        
        # 从数据库获取候选人的简历切片，提取技能作为考核点
        # 这里简化处理：后续在 _retrieve_resume_context 中动态检索
    
    async def decide_next_action(self, user_input: str) -> InterviewGuidance:
        """
        【核心入口】每次用户回答后调用
        
        完整流程：
        1. 分析回答质量
        2. 检索简历上下文（新增）
        3. 检索相关题目
        4. 做出决策（生成 InterviewGuidance 思路指令）
        5. 更新状态
        6. 返回思路指令给 GLM
        
        **注意：不生成台词！GLM 根据思路自己组织话术**
        """
        print(f"\n[Controller] 收到回答: {user_input[:60]}...")
        
        # 步骤 1: 分析质量
        quality = self.analyzer.analyze(user_input)
        print(f"[Controller] 质量评估: {quality.value}")
        
        # 步骤 2: 检索简历上下文（新增）
        await self._retrieve_resume_context(user_input)
        
        # 步骤 3: 检索题目
        questions = await self._retrieve_questions(user_input)
        print(f"[Controller] 检索到 {len(questions)} 道相关题目")
        
        # 步骤 4: 做出决策（传入简历上下文）
        guidance = await self.engine.make_decision(
            user_input, quality, questions, self.resume_context
        )
        print(f"[Controller] 决策: {guidance.action.value}")
        print(f"[Controller] 考核点: {guidance.target_topic}")
        print(f"[Controller] 问题焦点: {guidance.question_focus[:60]}...")
        
        # 步骤 5: 更新状态
        self.state.update(guidance)
        
        # 步骤 6: 返回思路指令
        print(f"[Controller] 思路指令已生成，交给 GLM 组织话术")
        return guidance
    
    async def _retrieve_resume_context(self, query: str):
        """
        检索简历上下文（新增方法）
        
        策略：
        1. 优先按用户回答内容检索简历
        2. 如果无结果，按当前考核点检索
        3. 缓存到 self.resume_context 供后续使用
        """
        if not self.candidate_id:
            self.resume_context = ""
            return
        
        current_topic = self.state.get_current_topic()
        topic_name = current_topic.topic if current_topic else None
        
        # 1. 先按用户回答检索
        self.resume_context = await self.retriever.get_resume_context(
            candidate_id=self.candidate_id,
            topic=query,
            max_chunks=2
        )
        
        # 2. 如果无结果，按当前考核点检索（兜底）
        if not self.resume_context and topic_name:
            self.resume_context = await self.retriever.get_resume_context(
                candidate_id=self.candidate_id,
                topic=topic_name,
                max_chunks=2
            )
        
        if self.resume_context:
            print(f"[Controller] 简历上下文已加载 ({len(self.resume_context)} 字符)")
    
    async def _retrieve_questions(self, query: str, limit: int = 3) -> List[Dict]:
        """
        检索相关题目
        
        策略：
        1. 先按用户回答检索（可能提到新关键词）
        2. 如果没结果，按当前话题检索（保底）
        3. 过滤已使用和相似度阈值
        """
        # 1. 按用户回答检索
        all_questions = await self.retriever.search_questions(query, limit=limit * 2)
        
        # 2. 如果没结果，按当前话题检索
        if not all_questions:
            current_topic = self.state.get_current_topic()
            if current_topic:
                all_questions = await self.retriever.search_questions(
                    current_topic.topic,
                    limit=limit * 2
                )
        
        # 3. 过滤：未使用 + 相似度>0.5（从0.6降低，避免有效题目被过滤）
        filtered = []
        for q in all_questions:
            q_id = q.get('id')
            similarity = q.get('similarity', 0)
            
            if not self.state.is_question_used(q_id) and similarity > 0.5:
                filtered.append(q)
                if len(filtered) >= limit:
                    break
        
        return filtered
    
    def get_summary(self) -> Dict:
        """获取面试摘要"""
        return self.state.get_summary()

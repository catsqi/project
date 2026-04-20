"""
InterviewController - AI 面试大脑控制器（三阶段版）

职责：
- 组装各个子模块
- 提供统一的决策入口
- 按阶段协调检索策略

面试流程：项目A → 项目B → 技术题1 → 技术题2 → 行为题 → 结束
"""

from typing import Dict, List

from .models import InterviewGuidance, AnswerQuality, InterviewPhase
from .state_manager import InterviewStateManager, PHASE_LABELS
from .quality_analyzer import AnswerQualityAnalyzer
from .decision_engine import DecisionEngine

# 引入检索器
from app.services.pg_retriever import get_retriever

# 行为题默认检索词（当 behavioral_topics 只有占位符时使用）
BEHAVIORAL_SEARCH_QUERIES = [
    "遇到最大的挑战 如何解决",
    "团队冲突 如何处理",
    "项目遇到困难 如何克服",
    "和同事意见不合怎么办",
    "压力最大的时刻",
]


class InterviewController:
    """AI 面试大脑控制器 - 三阶段版"""
    
    def __init__(self, max_projects: int = 2, max_technical: int = 2, max_behavioral: int = 1):
        print("[Controller] 初始化 InterviewController...")
        
        self.state = InterviewStateManager(max_projects, max_technical, max_behavioral)
        self.analyzer = AnswerQualityAnalyzer()
        self.engine = DecisionEngine(self.state)
        self.retriever = get_retriever()
        
        self.candidate_id: str = None
        self.resume_context: str = ""
        
        print(f"[Controller] 初始化完成（项目≤{max_projects}, 技术≤{max_technical}, 行为≤{max_behavioral}）")
    
    def load_candidate(self, resume_json: Dict, candidate_id: str = None):
        """加载候选人简历"""
        self.state.load_candidate(resume_json)
        self.candidate_id = candidate_id
        if candidate_id:
            print(f"[Controller] 候选人ID已设置: {candidate_id[:8]}...")
    
    def load_candidate_with_id(self, candidate_id: str):
        """仅通过 candidate_id 加载候选人"""
        self.candidate_id = candidate_id
        print(f"[Controller] 通过ID加载候选人: {candidate_id[:8]}...")
    
    async def decide_next_action(self, user_input: str) -> InterviewGuidance:
        """【核心入口】每次用户回答后调用"""
        current_phase = self.state.get_current_phase()
        print(f"\n[Controller] 收到回答: {user_input[:60]}... [阶段: {PHASE_LABELS.get(current_phase)}]")
        
        # 步骤 1: 分析质量
        try:
            quality, quality_reason = self.analyzer.analyze(user_input)
            quality = quality or AnswerQuality.ADEQUATE
        except Exception:
            quality, quality_reason = AnswerQuality.ADEQUATE, "分析异常"
        print(f"[Controller] 质量评估: {quality.value}（{quality_reason}）")
        
        # 步骤 2: 按阶段检索上下文
        await self._retrieve_context_by_phase(user_input)
        
        # 步骤 3: 按阶段检索题目
        questions = await self._retrieve_questions_by_phase(user_input)
        print(f"[Controller] 检索到 {len(questions)} 道相关题目")
        
        # 步骤 4: 决策
        guidance = await self.engine.make_decision(
            user_input, quality, questions, self.resume_context, quality_reason
        )
        print(f"[Controller] 决策: {guidance.action.value} | 阶段: {guidance.phase.value}")
        print(f"[Controller] 考核点: {guidance.target_topic}")
        if guidance.phase_transition_hint:
            print(f"[Controller] 阶段切换提示: {guidance.phase_transition_hint}")
        
        # 步骤 5: 更新状态
        self.state.update(guidance, user_answer=user_input)
        
        return guidance
    
    async def _retrieve_context_by_phase(self, query: str):
        """按阶段检索上下文"""
        current_phase = self.state.get_current_phase()
        
        if current_phase == InterviewPhase.PROJECTS:
            # 项目阶段：检索简历上下文
            await self._retrieve_resume_context_dual(query)
        elif current_phase == InterviewPhase.TECHNICAL:
            # 技术阶段：不需要简历上下文，靠题库
            self.resume_context = ""
        elif current_phase == InterviewPhase.BEHAVIORAL:
            # 行为阶段：不需要简历上下文
            self.resume_context = ""
        else:
            self.resume_context = ""
    
    async def _retrieve_resume_context_dual(self, query: str):
        """检索简历上下文（仅项目阶段使用）"""
        if not self.candidate_id:
            self.resume_context = ""
            return
        
        current_topic = self.state.get_current_topic()
        topic_name = current_topic.topic if current_topic else None
        current_depth = current_topic.depth if current_topic else 0
        max_depth = self.state.get_max_depth()
        
        context_parts = []
        
        # 当前考核点的上下文
        current_context = await self.retriever.get_resume_context(
            candidate_id=self.candidate_id,
            topic=query if query else topic_name,
            max_chunks=2
        )
        
        if not current_context and topic_name and query:
            current_context = await self.retriever.get_resume_context(
                candidate_id=self.candidate_id,
                topic=topic_name,
                max_chunks=2
            )
        
        if current_context:
            context_parts.append(f"【当前考核点：{topic_name}】\n{current_context}")
            print(f"[Controller] 当前考核点简历上下文已加载 ({len(current_context)} 字符)")
        
        # 预加载下一个考核点
        should_preload = (
            current_depth >= max_depth - 1
            and not self.state.is_last_topic_overall()
        )
        
        if should_preload:
            next_topic_info = self.state.get_next_topic_info()
            if next_topic_info:
                next_topic_name = next_topic_info.topic
                next_topic_source = next_topic_info.source
                print(f"[Controller] 预加载下一个考核点: {next_topic_name} (来源: {next_topic_source})")
                
                next_context = await self.retriever.get_resume_context(
                    candidate_id=self.candidate_id,
                    topic=next_topic_name,
                    max_chunks=2
                )
                
                if next_context:
                    context_parts.append(f"【下一个考核点：{next_topic_name} (来源: {next_topic_source})】\n{next_context}")
        
        self.resume_context = "\n\n".join(context_parts) if context_parts else ""
    
    async def _retrieve_questions_by_phase(self, query: str, limit: int = 3) -> List[Dict]:
        """按阶段检索题目"""
        current_phase = self.state.get_current_phase()
        
        if current_phase == InterviewPhase.PROJECTS:
            # 项目阶段：检索技术题作为备选
            return await self._retrieve_questions(query, question_type="tech", limit=limit)
        
        elif current_phase == InterviewPhase.TECHNICAL:
            # 技术阶段：用当前技能标签检索技术题
            current_topic = self.state.get_current_topic()
            search_query = current_topic.topic if current_topic else query
            return await self._retrieve_questions(search_query, question_type="tech", limit=limit)
        
        elif current_phase == InterviewPhase.BEHAVIORAL:
            # 行为阶段：检索行为题
            return await self._retrieve_behavioral_questions(limit=limit)
        
        return []
    
    async def _retrieve_questions(self, query: str, question_type: str = None, limit: int = 3) -> List[Dict]:
        """检索相关题目（通用方法）"""
        # 1. 按查询检索
        all_questions = await self.retriever.search_questions(
            query, category=question_type, limit=limit * 2
        )
        
        # 2. 如果没结果，按当前话题检索
        if not all_questions:
            current_topic = self.state.get_current_topic()
            if current_topic:
                all_questions = await self.retriever.search_questions(
                    current_topic.topic, category=question_type, limit=limit * 2
                )
        
        # 3. 过滤：未使用 + 相似度>0.5
        filtered = []
        for q in all_questions:
            q_id = q.get('id')
            similarity = q.get('similarity', 0)
            if not self.state.is_question_used(q_id) and similarity > 0.5:
                filtered.append(q)
                if len(filtered) >= limit:
                    break
        
        return filtered
    
    async def _retrieve_behavioral_questions(self, limit: int = 3) -> List[Dict]:
        """检索行为题（使用多个查询词兜底）"""
        all_questions = []
        seen_ids = set()
        
        for search_query in BEHAVIORAL_SEARCH_QUERIES:
            questions = await self.retriever.search_questions(
                search_query, category="behavioral", limit=3
            )
            for q in questions:
                if q.get('id') not in seen_ids and not self.state.is_question_used(q.get('id')):
                    all_questions.append(q)
                    seen_ids.add(q.get('id'))
        
        # 按相似度排序
        all_questions.sort(key=lambda x: x.get("similarity", 0), reverse=True)
        return all_questions[:limit]
    
    def get_summary(self) -> Dict:
        """获取面试摘要"""
        return self.state.get_summary()

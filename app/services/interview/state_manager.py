"""
面试状态管理器

职责：
- 管理面试进度（三阶段状态机：项目→技术→行为→结束）
- 从简历提取考核点，按阶段分队列管理
- 阶段差异化深度限制
- 状态持久化和查询
"""

from typing import List, Dict, Optional, Set
from .models import TopicInfo, InterviewGuidance, ActionType, InterviewPhase

# 阶段顺序
PHASE_ORDER = [InterviewPhase.PROJECTS, InterviewPhase.TECHNICAL, InterviewPhase.BEHAVIORAL]

# 各阶段深度限制
PHASE_DEPTH_LIMITS = {
    InterviewPhase.PROJECTS: 3,     # 项目阶段可深入追问
    InterviewPhase.TECHNICAL: 2,    # 技术题答完就换
    InterviewPhase.BEHAVIORAL: 1,   # 行为题浅问即可
}

# 阶段中文标签（用于 Prompt 注入）
PHASE_LABELS = {
    InterviewPhase.PROJECTS: "项目经验考核",
    InterviewPhase.TECHNICAL: "技术题库考核",
    InterviewPhase.BEHAVIORAL: "行为面试",
    InterviewPhase.CLOSING: "面试结束",
}

# 阶段切换提示（用于 GLM 过渡语）
PHASE_TRANSITION_HINTS = {
    (InterviewPhase.PROJECTS, InterviewPhase.TECHNICAL): "项目经验聊得差不多了，接下来我们考几道技术题",
    (InterviewPhase.TECHNICAL, InterviewPhase.BEHAVIORAL): "技术方面了解得差不多了，最后聊一个行为面试的问题",
    (InterviewPhase.BEHAVIORAL, InterviewPhase.CLOSING): "面试已经全部完成，感谢你的参与",
}


class InterviewStateManager:
    """面试状态管理器（三阶段状态机）"""
    
    def __init__(self, max_projects: int = 2, max_technical: int = 2, max_behavioral: int = 1):
        # 各阶段话题数量限制
        self.max_projects = max_projects
        self.max_technical = max_technical
        self.max_behavioral = max_behavioral
        
        # 状态机
        self.current_phase = InterviewPhase.PROJECTS
        self.current_topic_index = 0       # 当前阶段内的游标
        
        # 三阶段独立队列
        self.project_topics: List[TopicInfo] = []
        self.technical_topics: List[TopicInfo] = []
        self.behavioral_topics: List[TopicInfo] = []
        
        # 兼容旧接口：resume_topics 扁平视图
        self.resume_topics: List[TopicInfo] = []
        
        # 题库防重复
        self.current_question_bank: List[Dict] = []
        self.used_question_ids: Set[str] = set()
        
        # 历史记录
        self.history: List[Dict] = []
    
    # ==================== 加载候选人 ====================
    
    def load_candidate(self, resume_json: Dict):
        """加载候选人简历，按阶段提取考核点"""
        self.project_topics, self.technical_topics, self.behavioral_topics = \
            self._extract_resume_topics(resume_json)
        
        self.current_phase = InterviewPhase.PROJECTS
        self.current_topic_index = 0
        
        # 构建扁平视图（兼容旧代码）
        self.resume_topics = self.project_topics + self.technical_topics + self.behavioral_topics
        
        total = len(self.resume_topics)
        print(f"[State] 提取考核点: 项目{len(self.project_topics)}个, "
              f"技术{len(self.technical_topics)}个, 行为{len(self.behavioral_topics)}个 (共{total}个)")
    
    def _extract_resume_topics(self, resume: Dict):
        """从简历提取考核点，按阶段分队列"""
        seen = set()
        project_topics = []
        technical_topics = []
        behavioral_topics = []
        
        # === 1. 项目技能 → project_topics ===
        project_count = 0
        for proj in resume.get("projects", []):
            if project_count >= self.max_projects:
                break
            
            proj_name = proj.get("project_name", "未知项目")
            for skill in proj.get("project_specific_skills", []):
                skill_lower = skill.lower()
                if skill_lower not in seen:
                    project_topics.append(TopicInfo(
                        topic=skill,
                        source=f"项目:{proj_name}",
                        priority=8,
                        phase=InterviewPhase.PROJECTS
                    ))
                    seen.add(skill_lower)
            
            project_count += 1
        
        # === 2. 全局技能 → technical_topics ===
        skill_count = 0
        for skill in resume.get("global_profile", {}).get("all_technical_skills", []):
            if skill_count >= self.max_technical:
                break
            
            skill_lower = skill.lower()
            if skill_lower not in seen:
                technical_topics.append(TopicInfo(
                    topic=skill,
                    source="简历技能",
                    priority=5,
                    phase=InterviewPhase.TECHNICAL
                ))
                seen.add(skill_lower)
                skill_count += 1
        
        # === 3. 行为题占位 → behavioral_topics ===
        for i in range(self.max_behavioral):
            behavioral_topics.append(TopicInfo(
                topic="行为面试题",
                source="行为题库",
                priority=3,
                phase=InterviewPhase.BEHAVIORAL
            ))
        
        return project_topics, technical_topics, behavioral_topics
    
    # ==================== 当前阶段话题列表 ====================
    
    def _get_current_topics(self) -> List[TopicInfo]:
        """获取当前阶段的话题列表"""
        return {
            InterviewPhase.PROJECTS: self.project_topics,
            InterviewPhase.TECHNICAL: self.technical_topics,
            InterviewPhase.BEHAVIORAL: self.behavioral_topics,
        }.get(self.current_phase, [])
    
    # ==================== 话题访问 ====================
    
    def get_current_topic(self) -> Optional[TopicInfo]:
        """获取当前考核点"""
        topics = self._get_current_topics()
        if 0 <= self.current_topic_index < len(topics):
            return topics[self.current_topic_index]
        return None
    
    def get_next_topic(self) -> str:
        """获取下一个考核点名称（安全）"""
        info = self.get_next_topic_info()
        return info.topic if info else "其他技术点"
    
    def get_next_topic_info(self) -> Optional[TopicInfo]:
        """获取下一个考核点的完整信息（先阶段内，再下一阶段）"""
        topics = self._get_current_topics()
        
        # 阶段内下一个
        next_idx = self.current_topic_index + 1
        if next_idx < len(topics):
            return topics[next_idx]
        
        # 跨阶段下一个
        next_phase = self._get_next_phase()
        if next_phase:
            next_topics = {
                InterviewPhase.PROJECTS: self.project_topics,
                InterviewPhase.TECHNICAL: self.technical_topics,
                InterviewPhase.BEHAVIORAL: self.behavioral_topics,
            }.get(next_phase, [])
            if next_topics:
                return next_topics[0]
        
        return None
    
    def get_current_phase(self) -> InterviewPhase:
        """获取当前面试阶段"""
        return self.current_phase
    
    def get_current_phase_label(self) -> str:
        """获取当前阶段中文标签"""
        return PHASE_LABELS.get(self.current_phase, "未知阶段")
    
    def is_last_topic(self) -> bool:
        """检查当前是否是阶段内最后一个考核点（兼容旧接口）"""
        return self.is_last_topic_in_phase()
    
    def is_last_topic_in_phase(self) -> bool:
        """检查当前是否是阶段内最后一个考核点"""
        topics = self._get_current_topics()
        return self.current_topic_index >= len(topics) - 1
    
    def is_last_topic_overall(self) -> bool:
        """检查当前是否是整个面试最后一个考核点"""
        if self.current_phase != InterviewPhase.BEHAVIORAL:
            return False
        topics = self._get_current_topics()
        return self.current_topic_index >= len(topics) - 1
    
    def is_interview_complete(self) -> bool:
        """检查面试是否已完成"""
        return self.current_phase == InterviewPhase.CLOSING
    
    # ==================== 深度限制 ====================
    
    def get_max_depth(self) -> int:
        """获取当前阶段的深度上限"""
        return PHASE_DEPTH_LIMITS.get(self.current_phase, 2)
    
    # 兼容旧代码：max_depth 属性
    @property
    def max_depth(self) -> int:
        return self.get_max_depth()
    
    def is_depth_limit_reached(self) -> bool:
        """检查当前话题是否达到深度上限"""
        topic = self.get_current_topic()
        if topic:
            return topic.depth >= self.get_max_depth()
        return False
    
    # ==================== 状态更新 ====================
    
    def update(self, guidance: InterviewGuidance, user_answer: str = ""):
        """根据思路指令更新状态"""
        current_topic = self.get_current_topic()
        
        if guidance.action == ActionType.TRANSITION:
            # 重置当前话题深度
            if current_topic:
                current_topic.depth = 0
            
            # 阶段内游标 +1
            self.current_topic_index += 1
            self.current_question_bank = []
            
            # 检查是否需要跨阶段
            topics = self._get_current_topics()
            if self.current_topic_index >= len(topics):
                self._advance_phase()
            else:
                # 阶段内切换
                new_topic = self.get_current_topic()
                if new_topic:
                    new_topic.depth = 0
                    new_topic.asked_count += 1
        
        elif guidance.action == ActionType.NEXT_QUESTION:
            if current_topic:
                current_topic.depth += 1
                current_topic.asked_count += 1
        
        elif guidance.action == ActionType.FOLLOW_UP:
            if current_topic:
                current_topic.depth += 1
        
        elif guidance.action == ActionType.END:
            if current_topic:
                current_topic.depth = 0
            self.current_phase = InterviewPhase.CLOSING
        
        # 记录历史
        self.history.append({
            "action": guidance.action.value,
            "topic": guidance.target_topic,
            "phase": self.current_phase.value,
            "focus": guidance.question_focus[:80],
            "user_answer": user_answer
        })
    
    # ==================== 阶段切换 ====================
    
    def _get_next_phase(self) -> Optional[InterviewPhase]:
        """获取下一个阶段"""
        try:
            current_idx = PHASE_ORDER.index(self.current_phase)
            if current_idx + 1 < len(PHASE_ORDER):
                return PHASE_ORDER[current_idx + 1]
        except ValueError:
            pass
        return None
    
    def _advance_phase(self):
        """切换到下一个阶段"""
        old_phase = self.current_phase
        next_phase = self._get_next_phase()
        
        if next_phase:
            self.current_phase = next_phase
            self.current_topic_index = 0
            print(f"[State] 阶段切换: {PHASE_LABELS[old_phase]} → {PHASE_LABELS[next_phase]}")
            
            # 初始化新阶段的第一个话题
            new_topic = self.get_current_topic()
            if new_topic:
                new_topic.depth = 0
                new_topic.asked_count += 1
        else:
            self.current_phase = InterviewPhase.CLOSING
            print(f"[State] 面试结束")
    
    def get_phase_transition_hint(self) -> Optional[str]:
        """获取阶段切换提示语（供 GLM 使用）"""
        next_phase = self._get_next_phase()
        if next_phase:
            return PHASE_TRANSITION_HINTS.get((self.current_phase, next_phase))
        return None
    
    # ==================== 题库防重复 ====================
    
    def mark_question_used(self, question_id: str):
        """标记题目已使用"""
        if question_id:
            self.used_question_ids.add(question_id)
    
    def is_question_used(self, question_id: str) -> bool:
        """检查题目是否已使用"""
        return question_id in self.used_question_ids
    
    # ==================== 摘要 ====================
    
    def get_summary(self) -> Dict:
        """获取面试摘要"""
        total = len(self.project_topics) + len(self.technical_topics) + len(self.behavioral_topics)
        return {
            "current_phase": self.current_phase.value,
            "total_topics": total,
            "project_topics": len(self.project_topics),
            "technical_topics": len(self.technical_topics),
            "behavioral_topics": len(self.behavioral_topics),
            "total_questions": len(self.used_question_ids),
            "history": self.history
        }

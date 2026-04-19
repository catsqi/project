"""
面试状态管理器

职责：
- 管理面试进度（当前话题、深度、历史）
- 从简历提取考核点（支持演示模式限制）
- 状态持久化和查询
"""

from typing import List, Dict, Optional, Set
from .models import TopicInfo, InterviewGuidance, ActionType


class InterviewStateManager:
    """面试状态管理器"""
    
    def __init__(self, max_depth_per_topic: int = 3, max_projects: int = None, max_skills: int = None):
        self.max_depth = max_depth_per_topic
        self.max_projects = max_projects  # 演示模式：限制项目数量
        self.max_skills = max_skills      # 演示模式：限制技能数量
        
        # 面试进度
        self.phase = "technical"           # technical/behavioral/closing
        self.current_topic_index = 0       # 当前考核点游标
        
        # 数据
        self.resume_topics: List[TopicInfo] = []      # 简历考核点队列
        self.current_question_bank: List[Dict] = []   # 当前话题的候选题目
        self.used_question_ids: Set[str] = set()      # 防重复
        
        # 历史记录
        self.history: List[Dict] = []
    
    def load_candidate(self, resume_json: Dict):
        """加载候选人简历，提取考核点（支持演示模式限制）"""
        self.resume_topics = self._extract_resume_topics(resume_json)
        
        if self.resume_topics:
            print(f"[State] 提取 {len(self.resume_topics)} 个考核点（演示模式: 项目≤{self.max_projects}, 技能≤{self.max_skills}）")
        else:
            print("[State] 警告：未提取到考核点")
    
    def _extract_resume_topics(self, resume: Dict) -> List[TopicInfo]:
        """从简历提取考核点，按优先级排序（支持演示模式限制）"""
        topics = []
        seen = set()
        project_count = 0
        
        # 1. 项目实战技能（高优先级）
        for proj in resume.get("projects", []):
            # 演示模式：限制项目数量
            if self.max_projects is not None and project_count >= self.max_projects:
                break
                
            proj_name = proj.get("project_name", "未知项目")
            for skill in proj.get("project_specific_skills", []):
                skill_lower = skill.lower()
                if skill_lower not in seen:
                    topics.append(TopicInfo(
                        topic=skill,
                        source=f"项目:{proj_name}",
                        priority=8
                    ))
                    seen.add(skill_lower)
            
            project_count += 1
        
        # 2. 全局技能（中优先级）
        skill_count = 0
        for skill in resume.get("global_profile", {}).get("all_technical_skills", []):
            # 演示模式：限制技能数量
            if self.max_skills is not None and skill_count >= self.max_skills:
                break
                
            skill_lower = skill.lower()
            if skill_lower not in seen:
                topics.append(TopicInfo(
                    topic=skill,
                    source="简历技能",
                    priority=5
                ))
                seen.add(skill_lower)
                skill_count += 1
        
        # 按优先级排序
        topics.sort(key=lambda x: x.priority, reverse=True)
        return topics
    
    def get_current_topic(self) -> Optional[TopicInfo]:
        """获取当前考核点"""
        if 0 <= self.current_topic_index < len(self.resume_topics):
            return self.resume_topics[self.current_topic_index]
        return None
    
    def get_next_topic(self) -> str:
        """获取下一个考核点名称（安全）"""
        next_idx = self.current_topic_index + 1
        if next_idx < len(self.resume_topics):
            return self.resume_topics[next_idx].topic
        return "其他技术点"
    
    def get_next_topic_info(self) -> Optional[TopicInfo]:
        """获取下一个考核点的完整信息（用于简历检索和决策）"""
        next_idx = self.current_topic_index + 1
        if next_idx < len(self.resume_topics):
            return self.resume_topics[next_idx]
        return None
    
    def is_last_topic(self) -> bool:
        """检查当前是否是最后一个考核点"""
        return self.current_topic_index >= len(self.resume_topics) - 1
    
    def is_interview_complete(self) -> bool:
        """检查面试是否已完成（所有考核点已覆盖）"""
        return self.current_topic_index >= len(self.resume_topics)
    
    def update(self, guidance: InterviewGuidance, user_answer: str = ""):
        """根据思路指令更新状态"""
        current_topic = self.get_current_topic()
        
        if guidance.action == ActionType.TRANSITION:
            # 切换话题：重置深度，移动游标，清空题库
            if current_topic:
                current_topic.depth = 0
            
            self.current_topic_index += 1
            self.current_question_bank = []
            
            # 更新新话题
            new_topic = self.get_current_topic()
            if new_topic:
                new_topic.depth = 0  # 新话题初始深度为0（还没问问题）
                new_topic.asked_count += 1

        elif guidance.action == ActionType.NEXT_QUESTION:
            # 同话题新题：重置深度
            if current_topic:
                current_topic.depth += 1
                current_topic.asked_count += 1
                
        elif guidance.action == ActionType.FOLLOW_UP:
            # 追问：深度+1
            if current_topic:
                current_topic.depth += 1
        
        elif guidance.action == ActionType.END:
            # 结束面试：标记为完成状态
            if current_topic:
                current_topic.depth = 0
            self.current_topic_index = len(self.resume_topics)  # 标记所有考核点已完成
        
        # 记录历史
        self.history.append({
            "action": guidance.action.value,
            "topic": guidance.target_topic,
            "focus": guidance.question_focus[:80],
            "user_answer": user_answer
        })
    
    def is_depth_limit_reached(self) -> bool:
        """检查当前话题是否达到深度上限"""
        topic = self.get_current_topic()
        if topic:
            return topic.depth >= self.max_depth
        return False
    
    def mark_question_used(self, question_id: str):
        """标记题目已使用"""
        if question_id:
            self.used_question_ids.add(question_id)
    
    def is_question_used(self, question_id: str) -> bool:
        """检查题目是否已使用"""
        return question_id in self.used_question_ids
    
    def get_summary(self) -> Dict:
        """获取面试摘要"""
        return {
            "total_topics": len(self.resume_topics),
            "covered_topics": self.current_topic_index + 1,
            "total_questions": len(self.used_question_ids),
            "history": self.history
        }

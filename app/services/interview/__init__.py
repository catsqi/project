"""
AI 面试控制器模块

使用示例：
    from app.services.interview import InterviewController
    
    controller = InterviewController()
    controller.load_candidate(resume_json)
    
    guidance = await controller.decide_next_action(user_input)
    # guidance 是 InterviewGuidance（思路指令），交给 GLM 组织话术
"""

# 导入模型
from .models import InterviewGuidance, ActionType, AnswerQuality, TopicInfo, InterviewPhase

# 保持兼容性：Instruction 是 InterviewGuidance 的别名
Instruction = InterviewGuidance

# 延迟导入 Controller（避免循环依赖）
def get_interview_controller():
    """获取 InterviewController 实例"""
    from .interview_controller import InterviewController
    return InterviewController()

__all__ = [
    "InterviewGuidance",
    "Instruction",  # 别名，兼容旧代码
    "ActionType",
    "AnswerQuality",
    "TopicInfo",
    "InterviewPhase",
    "get_interview_controller"
]

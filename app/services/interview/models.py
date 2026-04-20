"""
数据模型定义
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import List, Dict, Optional


class ActionType(str, Enum):
    """决策动作类型"""
    FOLLOW_UP = "follow_up"         # 追问：深入当前回答
    NEXT_QUESTION = "next_question" # 下一题：同话题的新问题
    TRANSITION = "transition"       # 切换：换到下一个考核点
    END = "end"                     # 结束：面试完成


class AnswerQuality(str, Enum):
    """回答质量评估"""
    EXCELLENT = "excellent"   # 优秀：深入、有细节、有数据
    ADEQUATE = "adequate"     # 合格：有基本理解
    VAGUE = "vague"           # 模糊：太笼统、太短
    EVASIVE = "evasive"       # 逃避：说不会/忘了/不清楚
    IRRELEVANT = "irrelevant" # 跑题：答非所问


class InterviewPhase(str, Enum):
    """面试阶段"""
    PROJECTS = "projects"       # 项目经验考核
    TECHNICAL = "technical"     # 技术题库考核
    BEHAVIORAL = "behavioral"   # 行为面试
    CLOSING = "closing"         # 结束阶段


@dataclass
class TopicInfo:
    """考核点信息"""
    topic: str           # 技术点名称，如"Redis分布式锁"
    source: str          # 来源：项目A/简历技能
    priority: int        # 优先级：8=高（项目经验），5=中（技能列表）
    phase: InterviewPhase = InterviewPhase.PROJECTS  # 归属阶段
    asked_count: int = 0 # 已问次数
    depth: int = 0       # 当前深度


@dataclass
class InterviewGuidance:
    """
    DeepSeek 给 GLM-4-Voice 的"思路指令"
    
    【核心】不是台词！是指导 GLM 怎么问的要点
    GLM 根据这些思路，结合原始音频，自然组织话术
    """
    action: ActionType                   # 动作类型
    target_topic: str                    # 要考核的技术点
    question_focus: str                  # 问题焦点/核心要了解什么
    context_hints: List[str] = field(default_factory=list)  # 上下文提示（简历相关点、之前回答线索）
    depth_level: int = 1                 # 深度级别：1=基础，2=深入，3=挑战
    suggested_angle: str = "实践"         # 建议角度：原理/实践/优化/对比/场景/故障
    
    # 阶段信息
    phase: InterviewPhase = InterviewPhase.PROJECTS  # 当前面试阶段
    phase_transition_hint: Optional[str] = None      # 阶段切换提示，如"项目考核完成，开始技术题"
    
    # 可选约束
    must_use_bank_question: bool = False # 是否必须用题库原题
    question_bank_id: Optional[str] = None  # 题库ID（如果很匹配）
    question_bank_text: Optional[str] = None  # 题库原文（供GLM参考）
    
    # 参考表达（不是台词！是示例）
    example_approach: Optional[str] = None  # 建议的提问方式
    
    # 追踪信息
    brain_intent: str = ""               # 决策意图（日志用）
    expected_keywords: List[str] = field(default_factory=list)  # 期望用户回答包含的关键词


# 为了保持兼容性，保留 Instruction 作为别名（但内部使用 InterviewGuidance）
Instruction = InterviewGuidance

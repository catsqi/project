"""
决策引擎

职责：
- 根据回答质量决策下一步动作
- 生成"思路指令"（InterviewGuidance）给 GLM
- **不生成台词！** GLM 根据思路自己组织话术
- 协调 DeepSeek 进行复杂决策
"""

import asyncio
import json
import os
import re
from typing import List, Dict, Optional
from openai import AsyncOpenAI
from dotenv import load_dotenv

from .models import InterviewGuidance, ActionType, AnswerQuality, TopicInfo
from .state_manager import InterviewStateManager

load_dotenv()


class DecisionEngine:
    """决策引擎"""
    
    # 避免网络波动导致非必要降级
    DEEPSEEK_TIMEOUT = 15.0
    
    def __init__(self, state_manager: InterviewStateManager):
        self.state = state_manager
        
        # DeepSeek 客户端
        self.client = AsyncOpenAI(
            api_key=os.getenv("DEEPSEEK_API_KEY"),
            base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
        )
        self.model = os.getenv("CONTROLLER_MODEL", "deepseek-chat")
    
    async def make_decision(
        self,
        user_input: str,
        quality: AnswerQuality,
        questions: List[Dict],
        resume_context: str = ""  # 新增：简历上下文
    ) -> InterviewGuidance:
        """
        做出决策，生成 InterviewGuidance（思路指令）
        
        **全部走 DeepSeek 进行智能判断**
        
        参数：
        - user_input: 用户回答
        - quality: 回答质量
        - questions: 候选题目列表
        - resume_context: 简历上下文（新增）
        """
        # 缓存简历上下文和用户输入供后续使用
        self._resume_context = resume_context
        self._user_input = user_input
        
        current_topic = self.state.get_current_topic()
        # 改进：使用有意义的默认值（多层兜底推断）
        topic_name = current_topic.topic if current_topic else self._infer_topic_fallback(questions)
        
        # 所有情况都走 DeepSeek 智能决策
        return await self._handle_normal(user_input, questions, topic_name, quality)
    
    def _handle_evasive(self, user_input: str, questions: List[Dict]) -> InterviewGuidance:
        """处理逃避回答 - 生成思路，不生成台词"""
        next_topic = self.state.get_next_topic()
        
        if questions:
            q = questions[0]
            self.state.mark_question_used(q.get('id'))
            return InterviewGuidance(
                action=ActionType.TRANSITION,
                target_topic=next_topic,
                question_focus=f"了解候选人在{next_topic}方面的经验",
                context_hints=["用户表示不会当前技术", "需要温和过渡", "避免尴尬"],
                depth_level=1,
                suggested_angle="实践",
                must_use_bank_question=True,
                question_bank_id=q.get('id'),
                question_bank_text=q.get('question'),
                example_approach="先安抚，再自然过渡到新问题",
                brain_intent=f"用户不会，切换到{next_topic}，选用题库"
            )
        else:
            return InterviewGuidance(
                action=ActionType.TRANSITION,
                target_topic=next_topic,
                question_focus=f"了解{next_topic}的使用经验",
                context_hints=["用户表示不会", "无题库可用", "兜底提问"],
                depth_level=1,
                suggested_angle="实践",
                example_approach="温和过渡，开放式提问",
                brain_intent="用户不会，无题库，兜底切换"
            )
    
    def _handle_vague(self, topic_name: str) -> InterviewGuidance:
        """处理模糊回答 - 生成思路，不生成台词"""
        return InterviewGuidance(
            action=ActionType.FOLLOW_UP,
            target_topic=topic_name,
            question_focus="要求结合具体业务场景或实际案例详细说明",
            context_hints=["用户回答太笼统", "需要引导具体化", "挖掘实际经验"],
            depth_level=2,
            suggested_angle="场景",
            example_approach="引导用户举具体例子",
            brain_intent="回答太笼统，要求具体案例",
            expected_keywords=["场景", "问题", "方案", "结果"]
        )
    
    async def _handle_excellent_and_switch(self, questions: List[Dict]) -> InterviewGuidance:
        """优秀回答，表扬并切换 - 生成思路，不生成台词"""
        next_topic = self.state.get_next_topic()
        
        if questions:
            q = questions[0]
            self.state.mark_question_used(q.get('id'))
            return InterviewGuidance(
                action=ActionType.TRANSITION,
                target_topic=next_topic,
                question_focus=f"考核{next_topic}，从题库选一道题",
                context_hints=["用户回答优秀", "当前话题已充分", "需要表扬后切换"],
                depth_level=1,
                suggested_angle="实践",
                must_use_bank_question=True,
                question_bank_id=q.get('id'),
                question_bank_text=q.get('question'),
                example_approach="先认可表扬，再自然过渡到新问题",
                brain_intent=f"当前话题已充分，切换到{next_topic}"
            )
        else:
            return InterviewGuidance(
                action=ActionType.TRANSITION,
                target_topic=next_topic,
                question_focus=f"了解{next_topic}的经验",
                context_hints=["用户回答优秀", "无题库", "兜底提问"],
                depth_level=1,
                suggested_angle="实践",
                example_approach="表扬后开放式提问",
                brain_intent="当前话题已充分，无题库，兜底切换"
            )
    
    async def _handle_depth_limit(self, questions: List[Dict]) -> InterviewGuidance:
        """深度达上限，强制切换 - 生成思路，不生成台词"""
        next_topic = self.state.get_next_topic()
        
        if questions:
            q = questions[0]
            self.state.mark_question_used(q.get('id'))
            return InterviewGuidance(
                action=ActionType.TRANSITION,
                target_topic=next_topic,
                question_focus=f"切换到{next_topic}进行考核",
                context_hints=["当前话题深度已达上限", "需要强制切换", "自然过渡"],
                depth_level=1,
                suggested_angle="实践",
                must_use_bank_question=True,
                question_bank_id=q.get('id'),
                question_bank_text=q.get('question'),
                example_approach="简洁结束当前话题，直接引入新问题",
                brain_intent=f"深度达上限，强制切换到{next_topic}"
            )
        else:
            return InterviewGuidance(
                action=ActionType.TRANSITION,
                target_topic=next_topic,
                question_focus=f"了解{next_topic}",
                context_hints=["深度达上限", "无题库", "兜底切换"],
                depth_level=1,
                suggested_angle="实践",
                example_approach="简洁过渡",
                brain_intent="深度达上限，兜底切换"
            )
    
    def _handle_follow_up(self, user_input: str, topic_name: str) -> InterviewGuidance:
        """追问处理 - 生成思路，不生成台词"""
        return InterviewGuidance(
            action=ActionType.FOLLOW_UP,
            target_topic=topic_name,
            question_focus="深入挖掘技术细节，如性能优化、异常处理、架构设计等",
            context_hints=["需要继续深入", "挖掘细节", "考察深度"],
            depth_level=2,
            suggested_angle="优化",
            example_approach="基于用户回答追问具体实现细节",
            brain_intent="继续深入挖掘",
            expected_keywords=["性能", "优化", "异常", "问题", "架构", "设计"]
        )
    
    async def _handle_normal(
        self,
        user_input: str,
        questions: List[Dict],
        topic_name: str,
        quality: AnswerQuality = None  # 新增 quality 参数
    ) -> InterviewGuidance:
        """正常流程：用 DeepSeek 生成思路指令，代码层兜底校验"""
        
        prompt = self._build_prompt(user_input, questions, quality)
        
        try:
            # 使用配置的超时时间（15秒）
            response = await asyncio.wait_for(
                self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": self._get_system_prompt()},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.3,
                    response_format={"type": "json_object"}
                ),
                timeout=self.DEEPSEEK_TIMEOUT
            )
            
            # 稳健的 JSON 解析
            data = self._safe_parse_json(response.choices[0].message.content)
            
            # 代码层强制兜底校验
            data = self._validate_and_correct_decision(data, topic_name)
            
            return self._parse_response(data, questions)
            
        except asyncio.TimeoutError:
            print(f"[DecisionEngine] DeepSeek 超时（{self.DEEPSEEK_TIMEOUT}s），使用降级策略")
            return self._fallback_decision(topic_name, questions, "DeepSeek 超时", user_input)
        except Exception as e:
            print(f"[DecisionEngine] DeepSeek 失败: {e}")
            return self._fallback_decision(topic_name, questions, str(e), user_input)
    
    def _safe_parse_json(self, content: str) -> Dict:
        """稳健的 JSON 解析，处理各种格式问题"""
        try:
            # 先尝试直接解析
            return json.loads(content)
        except json.JSONDecodeError:
            # 尝试提取 JSON 块（处理 Markdown 标记）
            json_match = re.search(r'\{[\s\S]*\}', content)
            if json_match:
                try:
                    return json.loads(json_match.group())
                except:
                    pass
            # 返回空字典，后续使用默认值
            return {}
    
    def _validate_and_correct_decision(self, data: Dict, topic_name: str) -> Dict:
        """代码层强制兜底校验"""
        current_topic = self.state.get_current_topic()
        current_depth = current_topic.depth if current_topic else 0
        
        # 强制校验 1: 深度上限检查
        if current_depth >= self.state.max_depth:
            print(f"[DecisionEngine] 强制切换: 深度已达上限 {current_depth}/{self.state.max_depth}")
            data['action'] = 'transition'
            data['brain_intent'] = data.get('brain_intent', '') + ' [代码强制: 深度达上限]'
        
        # 强制校验 2: 死循环检测（同一话题追问次数过多）
        if data.get('action') == 'follow_up' and current_depth >= 3:
            print(f"[DecisionEngine] 强制切换: 防止死循环")
            data['action'] = 'transition'
            data['brain_intent'] = data.get('brain_intent', '') + ' [代码强制: 防止死循环]'
        
        # 强制校验 3: 必填字段默认值
        data.setdefault('action', 'next_question')
        data.setdefault('target_topic', topic_name)
        data.setdefault('question_focus', f'了解{topic_name}的使用经验')
        data.setdefault('context_hints', [])
        data.setdefault('depth_level', 1)
        data.setdefault('suggested_angle', '实践')
        
        return data
    
    def _fallback_decision(
        self, 
        topic_name: str, 
        questions: List[Dict], 
        reason: str, 
        user_input: str = ""
    ) -> InterviewGuidance:
        """
        降级决策：DeepSeek 失败时的多层兜底方案
        
        兜底优先级：
        1. 题库问题 → 使用题库问题作为焦点
        2. 简历上下文 → 提取关键词生成焦点
        3. 用户回答 → 基于回答推断追问方向
        4. 默认兜底 → 使用语义明确的默认值
        """
        q = questions[0] if questions else None
        
        # === 第一层：确定有意义的考核点名称 ===
        effective_topic = self._determine_effective_topic(topic_name, q)
        
        # === 第二层：确定问题焦点 ===
        if q and q.get('question'):
            # 有题库问题：使用题库原文
            self.state.mark_question_used(q.get('id'))
            question_focus = q['question']
            question_text = q['question']
            must_use_bank = True
        elif hasattr(self, '_resume_context') and self._resume_context:
            # 有简历上下文：生成基于简历的焦点
            question_focus = f"结合你的项目经验，请谈谈{effective_topic}的实际应用场景"
            question_text = None
            must_use_bank = False
        elif user_input:
            # 有用户回答：生成自然追问
            question_focus = "针对刚才的回答，追问一个相关的技术细节或实践经验"
            question_text = None
            must_use_bank = False
        else:
            # 最终兜底：语义明确的默认提示
            question_focus = f"请分享你在{effective_topic}方面的实际经验"
            question_text = None
            must_use_bank = False
        
        
        return InterviewGuidance(
            action=ActionType.NEXT_QUESTION,
            target_topic=effective_topic,
            question_focus=question_focus,
            context_hints=[
                f"降级模式: {reason}",
                "DeepSeek决策失败，使用多层兜底策略",
                f"考核点来源: {effective_topic}"
            ],
            depth_level=1,
            suggested_angle="实践",
            must_use_bank_question=must_use_bank,
            question_bank_id=q.get('id') if q else None,
            question_bank_text=question_text,
            example_approach="自然地提出问题，引导候选人分享具体经验",
            brain_intent=f"DeepSeek降级({reason})，使用{'题库' if q else '兜底'}策略"
        )
    
    def _determine_effective_topic(self, topic_name: str, question: Dict = None) -> str:
        """
        确定有效的考核点名称（多层兜底）
        
        禁止返回无业务含义的硬编码字符串如"这个技术"
        """
        # 第一优先级：当前话题有效
        if topic_name and topic_name not in ["这个技术", "当前技术", "技术问题"]:
            return topic_name
        
        # 第二优先级：从题库问题推断
        if question and question.get('question'):
            inferred = self._infer_topic_from_question(question['question'])
            if inferred != "技术能力":
                return inferred
        
        # 第三优先级：从简历上下文提取
        if hasattr(self, '_resume_context') and self._resume_context:
            extracted = self._extract_topic_from_resume(self._resume_context)
            if extracted != "技术能力":
                return extracted
        
        # 第四优先级：从用户回答推断
        if hasattr(self, '_user_input') and self._user_input:
            inferred = self._infer_topic_from_question(self._user_input)
            if inferred != "技术能力":
                return inferred
        
        # 最终兜底：语义明确的默认值
        return "技术能力"
    
    def _infer_topic_from_question(self, text: str) -> str:
        """从文本推断考核点关键词"""
        if not text:
            return "技术能力"
        
        # 技术关键词映射
        topic_keywords = {
            # Java生态
            'redis': 'Redis',
            'mysql': 'MySQL',
            'java': 'Java',
            'spring': 'Spring',
            'jvm': 'JVM',
            'thread': '多线程',
            '线程': '多线程',
            '并发': '并发编程',
            '锁': '分布式锁',
            'collection': '集合框架',
            '集合': 'Java集合',
            # 数据库
            'mongodb': 'MongoDB',
            'mongo': 'MongoDB',
            'database': '数据库',
            '索引': '数据库索引',
            '事务': '事务管理',
            # 架构
            'microservice': '微服务',
            '微服务': '微服务',
            '分布式': '分布式系统',
            '架构': '系统架构',
            # 其他
            'docker': 'Docker',
            'k8s': 'Kubernetes',
            'kafka': 'Kafka',
            'mq': '消息队列',
        }
        
        text_lower = text.lower()
        for keyword, topic in topic_keywords.items():
            if keyword in text_lower:
                return topic
        
        return "技术能力"
    
    
    def _extract_topic_from_resume(self, resume_context: str) -> str:
        """从简历上下文提取考核点关键词"""
        if not resume_context or len(resume_context) < 10:
            return "技术能力"
        
        # 使用关键词推断
        inferred = self._infer_topic_from_question(resume_context)
        if inferred != "技术能力":
            return inferred
        
        # 无法推断时，截取关键片段
        return resume_context[:20].replace('\n', ' ') + "..."
    
    
    def _infer_topic_fallback(self, questions: List[Dict]) -> str:
        """初始化时的考核点推断（当 current_topic 为 None 时）"""
        if questions and questions[0].get('question'):
            return self._infer_topic_from_question(questions[0]['question'])
        return "技术能力"
    
    def _build_prompt(self, user_input: str, questions: List[Dict], quality: AnswerQuality = None) -> str:
        """构建 Prompt（注入短期记忆、质量评估、简历上下文）"""
        current_topic = self.state.get_current_topic()
        topic_name = current_topic.topic if current_topic else "当前技术"
        
        # 获取最近 2-3 轮对话历史
        recent_history = self._get_recent_history(3)
        
        formatted = []
        for q in questions:
            q_id = q.get('id', 'N/A')
            sim = q.get('similarity', 0)
            text = q.get('question', '')
            formatted.append(f"[ID:{q_id}] [相关度:{sim:.2f}] {text}")
        
        state = {
            "当前考核点": topic_name,
            "当前深度": f"{current_topic.depth if current_topic else 0}/{self.state.max_depth}",
            "用户回答": user_input,
            "回答质量": quality.value if quality else "unknown",
            "最近对话历史": recent_history,
            "候选题目": formatted,
            "简历上下文": getattr(self, '_resume_context', '')
        }
        
        return f"请根据以下状态输出 JSON 决策：\n{json.dumps(state, ensure_ascii=False, indent=2)}"
    
    def _get_recent_history(self, rounds: int = 3) -> List[Dict]:
        """获取最近 N 轮对话历史"""
        history = []
        # 从 state.history 获取历史记录
        if hasattr(self.state, 'history') and self.state.history:
            recent = self.state.history[-rounds:] if len(self.state.history) > rounds else self.state.history
            for item in recent:
                history.append({
                    "考核点": item.get('topic', '未知'),
                    "动作": item.get('action', '未知'),
                    "问题焦点": item.get('focus', '')[:50]
                })
        return history
    
    def _get_system_prompt(self) -> str:
        """系统 Prompt - DeepSeek 处理所有情况，带防死循环和情绪感知"""
        return """你是技术面试官的"决策大脑"。

【任务】
分析候选人回答和对话历史，智能决定下一步考核策略，输出"思路指令"给语音模型。

**重要：不生成台词！只输出思路要点，让GLM自己组织话术**

【输入信息】
- 当前考核点：正在考核的技术主题
- 当前深度：当前话题的追问深度（注意：不能超过max_depth）
- 用户回答：候选人的回答内容
- 回答质量：excellent/good/vague/evasive/empty
- 最近对话历史：最近2-3轮的考核点和动作（用于检测死循环）
- 候选题目：从题库检索到的相关题目
- 简历上下文：候选人的项目经历（如果有）

【核心决策规则】

1. **防死循环检测（最高优先级）**
   - 如果当前深度 >= max_depth，必须输出 `transition` 切换话题
   - 如果同一话题已经追问 >= 3 次，建议输出 `transition` 或 `next_question`
   - 绝不要在同一话题上无限追问！

2. **根据质量智能决策**
   - EXCELLENT: 深度足够则切换，否则继续深挖亮点
   - GOOD: 从候选题目选一道更深入的问题
   - VAGUE: 追问要求具体案例，但注意深度上限
   - EVASIVE: 温和切换，不要追问（候选人可能真不会）
   - EMPTY: 可能是ASR错误，建议重新提问或澄清

3. **情绪与节奏感知**
   - 如果连续两次 EVASIVE，候选人可能受挫，切换到简单话题缓解压力
   - 如果用户表现出困惑，可以输出 `follow_up` 附带澄清意图

4. **简历上下文智能使用**
   - 结合候选人真实项目经历提问
   - 在 context_hints 中引用具体项目名和技术点

【输出格式 - 严格JSON】
{
    "action": "follow_up|next_question|transition",
    "target_topic": "要考核的技术点",
    "question_focus": "核心要了解什么（给GLM的提示）",
    "context_hints": ["简历相关点", "质量评估依据", "死循环检测提示"],
    "depth_level": 1-3,
    "suggested_angle": "原理/实践/优化/对比/场景/故障",
    "must_use_bank_question": true/false,
    "selected_question_id": "题库ID或null",
    "example_approach": "建议的提问方式（不是台词！）",
    "brain_intent": "决策理由（必须包含质量判断和深度考虑）"
}

【重要约束】
- 必须考虑当前深度和max_depth，绝不能超限
- 必须参考最近对话历史，避免重复追问同一话题
- 如果检测到ASR错误（回答无意义），在brain_intent中注明"""
    
    def _parse_response(self, data: Dict, questions: List[Dict]) -> InterviewGuidance:
        """解析响应 - 生成 InterviewGuidance（思路指令）"""
        action = ActionType(data.get("action", "next_question"))
        selected_id = data.get("selected_question_id")
        must_use_bank = data.get("must_use_bank_question", False)
        
        # 查找题库原文
        question_text = None
        if selected_id:
            for q in questions:
                if q.get('id') == selected_id:
                    self.state.mark_question_used(selected_id)
                    question_text = q.get('question')
                    break
        
        return InterviewGuidance(
            action=action,
            target_topic=data.get("target_topic", "技术问题"),
            question_focus=data.get("question_focus", "了解技术经验"),
            context_hints=data.get("context_hints", []),
            depth_level=data.get("depth_level", 1),
            suggested_angle=data.get("suggested_angle", "实践"),
            must_use_bank_question=must_use_bank,
            question_bank_id=selected_id,
            question_bank_text=question_text,
            example_approach=data.get("example_approach"),
            brain_intent=data.get("brain_intent", "DeepSeek决策"),
            expected_keywords=data.get("expected_keywords", [])
        )

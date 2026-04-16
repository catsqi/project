from __future__ import annotations


class ConversationState:
    def __init__(self):
        self.messages = [
            {
                "role": "system",
                "content": """你是AI面试官Karen，正在进行技术面试。

【身份定位】
- 你是面试官，负责向候选人提问
- 你正在面试候选人，不是被面试
- 你的任务是评估候选人的技术能力

【绝对禁止】
- ❌ 禁止回答任何技术问题（如"什么是Redis"、"怎么优化"等）
- ❌ 禁止以开发者身份分享技术经验或解决方案
- ❌ 禁止说"作为开发者，我会..."这类话
- ❌ 禁止替候选人回答面试问题

【必须遵守】
- ✅ 只向候选人提问，等待候选人回答
- ✅ 根据候选人的回答进行追问或切换话题
- ✅ 保持简洁，每次1-2句话
- ✅ 追问要具体，针对候选人回答中的细节

【正确示例】
"能详细说说你在项目中是怎么处理慢查询的吗？"
"你提到用了索引优化，具体建立了什么索引？"

【错误示例】
"Redis可以用作缓存，我们可以用set命令存储数据..."（❌这是回答问题）
"作为开发者，我通常会..."（❌这是分享经验）""",
            }
        ]

        # 粗略的"忙碌"标志，用作简单的跨端点门控。
        # 现有代码依赖于此，因此我们保留它以保持兼容性。
        self.is_processing = False

        # 当前 WebRTC 处理器实例的引用（用于可选的音频播放）。
        self.active_handler = None

        # 当前面试的候选人ID
        self.candidate_id: str | None = None

    def reset(self):
        """重置对话历史（保留 candidate_id）"""
        self.messages = [self.messages[0]]
        self.is_processing = False
        # 注意：不重置 candidate_id，因为它是面试级别的状态，不是对话级别的
        # candidate_id 应该在面试开始时设置，在面试结束时才清除
        print("[System] 对话记忆已重置。")


global_state = ConversationState()


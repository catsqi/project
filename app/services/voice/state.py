from __future__ import annotations


class ConversationState:
    def __init__(self):
        self.messages = [
            {
                "role": "system",
                "content": "你是一个严厉的AI面试官，名为Karen。请尽量精简，每次仅用一两句话回答或反问，避免长篇大论，以极低延迟交流。务必根据上下文追问细节。",
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


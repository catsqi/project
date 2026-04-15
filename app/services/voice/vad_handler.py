from __future__ import annotations

import asyncio
import io
import json
import time
import traceback
from contextlib import asynccontextmanager

import numpy as np
import soundfile as sf
import torch
from fastrtc import AsyncAudioVideoStreamHandler, wait_for_item

from .interaction import process_interaction, process_interaction_stream
from .resources import model, whisper_model, sensevoice_model
from .state import global_state
from .config import USE_SENSEVOICE

# 导入 Interview 模块
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from app.services.interview import InterviewGuidance, ActionType


@asynccontextmanager
async def temporary_system_prompt_modifier(modifier_func):
    """
    临时修改 System Prompt 的上下文管理器
    
    使用方式：
    async with temporary_system_prompt_modifier(lambda p: p + "额外内容"):
        await process_interaction(...)
    """
    original = global_state.messages[0].copy()
    try:
        # 应用修改函数
        modified_content = modifier_func(original["content"])
        global_state.messages[0] = {"role": "system", "content": modified_content}
        yield
    finally:
        # 确保恢复
        global_state.messages[0] = original


class HighSpeedVADHandler(AsyncAudioVideoStreamHandler):
    def __init__(self):
        super().__init__("mono", output_sample_rate=24000, input_sample_rate=16000)
        self.audio_buffer: list[np.ndarray] = []
        self.output_queue: asyncio.Queue = asyncio.Queue()
        self.is_speaking_user = False
        self.silence_duration = 0
        self.frame_size = 512
        self.threshold = 0.7  # 提高阈值，滤除环境底噪

        # VAD 稳定性参数
        self.speech_counter = 0
        self.activation_count = 5  # 连续 5 帧(约160ms) 才激活
        self.pre_speech_buffer: list[np.ndarray] = []
        self.last_process_time = 0.0
        self.cooldown_period = 1.0

        # 注册为活跃处理器（注意：只有 channel 不为 None 才代表真正连上 WebRTC）
        global_state.active_handler = self
        
        # 初始化 InterviewController（延迟加载，避免启动时失败）
        self._interview_controller = None
        self._current_guidance = None

    async def receive(self, frame: tuple[int, np.ndarray]):
        current_time = time.time()

        # 严格的三重防护：处理中、有音频输出、冷却期
        if global_state.is_processing:
            # AI正在处理或播放中，完全静默
            self.silence_duration = 0
            self.is_speaking_user = False
            self.audio_buffer = []
            self.pre_speech_buffer = []
            return

        if not self.output_queue.empty():
            # 还有音频在队列中等待播放
            self.silence_duration = 0
            return

        if current_time - self.last_process_time < self.cooldown_period:
            # 冷却期内，防止回声触发
            self.silence_duration = 0
            return

        _, audio_data = frame
        audio_data = audio_data.squeeze()
        audio_float32 = audio_data.astype(np.float32) / 32768.0

        for i in range(0, len(audio_float32), self.frame_size):
            chunk = audio_float32[i : i + self.frame_size]
            if len(chunk) < self.frame_size:
                break

            with torch.no_grad():
                speech_prob = model(torch.from_numpy(chunk), 16000).item()

            if speech_prob > self.threshold:
                if not self.is_speaking_user:
                    self.speech_counter += 1
                    self.pre_speech_buffer.append(audio_data[i : i + self.frame_size])
                    if self.speech_counter >= self.activation_count:
                        self.is_speaking_user = True
                        print("\n[VAD] 听..")
                        self.audio_buffer.extend(self.pre_speech_buffer)
                        self.pre_speech_buffer = []
                        self.speech_counter = 0
                else:
                    self.audio_buffer.append(audio_data[i : i + self.frame_size])
                    self.silence_duration = 0
            else:
                if self.is_speaking_user:
                    self.audio_buffer.append(audio_data[i : i + self.frame_size])
                    self.silence_duration += 1

                    if self.silence_duration > 20:
                        self.is_speaking_user = False
                        full_audio = np.concatenate(self.audio_buffer)
                        self.audio_buffer = []
                        self.silence_duration = 0

                        # 总时长不足 600ms 的直接丢弃
                        if len(full_audio) < 9600:
                            print("[VAD] 忽略过短或疑似噪音的片段。")
                            continue

                        print("[VAD] 说话结束，解析指令..")
                        asyncio.create_task(self._process_stream(full_audio))
                else:
                    self.speech_counter = max(0, self.speech_counter - 1)
                    if len(self.pre_speech_buffer) > 10:
                        self.pre_speech_buffer.pop(0)

    async def _process_stream(self, audio_data: np.ndarray):
    

        async def send_transcript(text: str):
            if not text or not text.strip():
                return
            try:
                print(f"[ASR] 识别结果: '{text}'")
                if hasattr(self, "channel") and self.channel is not None:
                    self.channel.send(json.dumps({"type": "user_transcript", "text": text}))
            except Exception as e:
                print(f"[ASR-Error] 发送失败: {e}")

        async def send_ai_text(text: str):
            try:
                if hasattr(self, "channel") and self.channel is not None:
                    self.channel.send(json.dumps({"type": "ai_text", "text": text}))
                preview = text[:30] + '...' if len(text) > 30 else text
                print(f"[AI-Text] 发送成功: '{preview}'")
            except Exception as e:
                print(f"[AI-Text-Error] 发送失败: {e}")
                import traceback
                traceback.print_exc()

        print("[VAD] 开始处理...")

        def run_asr_sync():
            """执行语音识别（同步版本，在线程池中运行）"""
            # 音频预处理：归一化到 float32
            audio_f32 = audio_data.astype(np.float32) / 32768.0

            # 音量归一化：提升低音量音频的识别率
            rms = np.sqrt(np.mean(audio_f32**2))
            if rms > 0.001:  # 避免除以零
                target_rms = 0.3  # 目标音量
                audio_f32 = audio_f32 * (target_rms / rms)
                audio_f32 = np.clip(audio_f32, -1.0, 1.0)  # 防止溢出
            
            transcript = ""
            
            if USE_SENSEVOICE:
                # 使用 SenseVoice 识别（中文最优）
                if sensevoice_model is None:
                    print("[ASR-Error] SenseVoice 模型未加载！检查 resources.py 是否正确初始化")
                    return ""

                try:
                    # SenseVoice 识别 - 直接传入 numpy 数组和采样率
                    result = sensevoice_model.generate(
                        input=audio_f32,
                        fs=16000,  # 指定采样率
                        cache={},
                        language="auto",  # 自动检测语言
                        use_itn=True,     # 使用逆文本标准化
                        batch_size_s=60,
                    )

                    if result and len(result) > 0:
                        transcript = result[0].get("text", "") if isinstance(result[0], dict) else str(result[0])
                        print(f"[ASR] SenseVoice 原始结果: '{transcript}'")
                    else:
                        transcript = ""
                        print("[ASR-Warning] SenseVoice 返回空结果")

                    # 移除 SenseVoice 的情感标签等额外信息
                    # 格式: <|zh|><|ANGRY|><|Speech|><|withitn|>实际内容
                    if transcript and "<|" in transcript:
                        # 找到最后一个 |> 之后的内容
                        if "|>" in transcript:
                            transcript = transcript.split("|>")[-1].strip()
                        print(f"[ASR] 清理后结果: '{transcript}'")

                except Exception as e:
                    print(f"[ASR-Error] SenseVoice 识别失败: {e}")
                    transcript = ""
            else:
                # 使用 Whisper 识别（备选方案）
                if whisper_model is None:
                    print("[ASR-Error] Whisper 模型未加载！检查 resources.py 是否正确初始化")
                    return ""
                    
                try:
                    print("[ASR] 使用 Whisper 识别...")
                    segments, info = whisper_model.transcribe(
                        audio_f32,
                        language="zh",              # 指定中文语言
                        beam_size=5,                # 集束搜索大小
                        temperature=0.0,            # 降低随机性，提高稳定性
                        no_speech_threshold=0.6,    # 无语音阈值
                        condition_on_previous_text=True,  # 利用上下文
                        initial_prompt="以下是中文语音识别，请准确识别专业术语和常见词汇。",  # 提示词
                    )
                    segments_list = list(segments)  # 转换生成器为列表
                    print(f"[ASR] Whisper 返回 {len(segments_list)} 个片段")
                    transcript = "".join([s.text for s in segments_list])
                    print(f"[ASR] Whisper 最终结果: '{transcript}'")
                except Exception as e:
                    print(f"[ASR-Error] Whisper 识别失败: {e}")
                    traceback.print_exc()
                    transcript = ""
            
            return transcript

        async def run_asr():
            """异步包装，在线程池中执行同步 ASR"""
            try:
                # 在线程池中执行同步 ASR，避免阻塞事件循环
                transcript = await asyncio.to_thread(run_asr_sync)

                if transcript and transcript.strip():
                    print(f"[ASR] 识别成功: '{transcript}'")
                    await send_transcript(transcript)
                    return transcript
                else:
                    print("[ASR-Warning] 识别结果为空")
                    return ""
            except Exception as e:
                print(f"[ASR-Error] {e}")
                return ""

        # ========== 开始智能流式处理 ==========
        print("[VAD] ========== 开始智能流式处理 ==========")
        global_state.is_processing = True

        try:
            # 启动 ASR 后台任务
            asr_task = asyncio.create_task(run_asr())
            
            # ========== 阶段一：GLM 简短（扩展）回应（使用上下文管理器）==========
            def short_response_modifier(original_prompt: str) -> str:
                """引导 GLM 进行充分的回应缓冲，为后台争取更多时间"""
                return original_prompt + """
                
【切换到：过渡反馈模式 - 当前阶段禁止提问！】
此刻用户（候选人）刚刚回答完问题，你的任务只有一个：给予肯定和反馈。
⚠️ 关键：你的提问工作将在下一阶段进行，现在还不是提问的时候！

你当前的身份：面试官（评价者，不是被面试者）
你的当前任务：针对候选人刚才的回答，给出专业的肯定和评价。

📝 必须遵循的结构（共3-4句话，全部以句号结尾）：
第1句：肯定开场。提炼候选人提到的1个核心点并复述。（例："听到你分享了关于慢查询优化的实践经验，很有价值。"）
第2句：专业评价。从面试官视角评价这个回答的质量。（例："这种从发现问题到建立索引的思路，体现了系统性的问题解决能力。"）
第3句：收尾陈述。用肯定性陈述结束，不要留悬念。（例："这是很扎实的技术积累。"）

🚫🚫🚫 绝对禁止事项（违反将导致面试流程错误）：
- ❌ 禁止使用任何疑问号（？）
- ❌ 禁止提出任何问题（包括"能详细说说吗"、"是怎么做的？"等）
- ❌ 禁止使用"接下来"、"然后"等推进性词汇
- ❌ 禁止以"我作为开发者"的口吻分享个人经验
- ❌ 禁止引导候选人继续回答（那是下一阶段的事）

✅ 正确示例：
"听到你分享了后端核心开发中解决慢查询问题的经验。通过建立索引来优化查询性能，这是一个很实际的方案。这种发现问题、定位瓶颈、建立索引的思路体现了不错的工程能力。"

❌ 错误示例（绝对禁止）：
"听到你分享了慢查询优化的经验。那你们是怎么发现问题的呢？有没有使用什么工具？"
                                                    ↑ 这里的问号是错误的！"""

            # 使用上下文管理器：临时修改 System Prompt，确保恢复
            async with temporary_system_prompt_modifier(short_response_modifier):
                print("[VAD-阶段一] GLM生成过渡反馈...")
                await process_interaction(
                    "audio",
                    (audio_data, self.input_sample_rate),
                    self.output_queue,
                    on_text_chunk=send_ai_text,
                    manage_processing_state=False,
                    skip_history=True,  # 阅后即焚：不写入全局历史，避免污染
                )
            
            print("[VAD] System Prompt已恢复")
            # ========== 阶段一结束 ==========

            # 等待 ASR 完成
            user_transcript = await asr_task
            
            if not user_transcript:
                print("[VAD-Warning] ASR为空")
                await self._sync_transcript_to_memory("")
            else:
                print(f"[VAD] ASR完成: '{user_transcript[:50]}...'")
                await self._sync_transcript_to_memory(user_transcript)
                
                # DeepSeek 思考
                guidance = await self._call_deepseek(user_transcript)
                
                if guidance:
                    self._current_guidance = guidance
                    print("[VAD] GLM继续输出完整问题...")
                    await self._continue_with_guidance(guidance, send_ai_text)
                else:
                    print("[VAD-Warning] 使用默认追问")
                    await self._continue_default(send_ai_text)

            # 等待音频播放完成
            print("[VAD] 等待音频播放...")
            while not self.output_queue.empty():
                await asyncio.sleep(0.1)
            
            await asyncio.sleep(1.0)
            self.last_process_time = time.time()
            print("[VAD] ========== 处理完成 ==========")

            # 通知前端本轮交互生成完全结束，可以重置气泡绑定
            try:
                if hasattr(self, "channel") and self.channel is not None:
                    self.channel.send(json.dumps({"type": "ai_text_end"}))
            except Exception as e:
                pass
            
        finally:
            global_state.is_processing = False

    def _get_interview_controller(self):
        """获取 InterviewController（延迟初始化）"""
        if self._interview_controller is None:
            try:
                from app.services.interview.interview_controller import InterviewController
                self._interview_controller = InterviewController()
                print("[VAD] InterviewController 初始化成功")
                
                # 如果有候选人ID，加载候选人数据
                if global_state.candidate_id:
                    self._interview_controller.load_candidate_with_id(global_state.candidate_id)
                    print(f"[VAD] 候选人数据已加载: {global_state.candidate_id[:8]}...")
            except Exception as e:
                print(f"[VAD-Error] InterviewController 初始化失败: {e}")
                self._interview_controller = None
        return self._interview_controller

    async def _call_deepseek(self, transcript: str) -> InterviewGuidance | None:
        """
        调用 DeepSeek 生成 InterviewGuidance
        
        这是 ASR → DeepSeek 的关键连接！
        """
        controller = self._get_interview_controller()
        if controller is None:
            print("[VAD-Error] InterviewController 不可用，跳过 DeepSeek 调用")
            return None
        
        try:
            print(f"[VAD] 调用 DeepSeek 分析: '{transcript[:50]}...'")
            
            guidance = await controller.decide_next_action(transcript)
            
            print(f"[VAD] DeepSeek 决策完成: {guidance.action.value}")
            print(f"[VAD] 考核点: {guidance.target_topic}")
            print(f"[VAD] 问题焦点: {guidance.question_focus[:60]}...")
            
            return guidance
            
        except Exception as e:
            print(f"[VAD-Error] DeepSeek 调用失败: {e}")
            import traceback
            traceback.print_exc()
            return None

    async def _continue_with_guidance(self, guidance: InterviewGuidance, send_ai_text):
        """
        阶段三：GLM 根据 Guidance 输出正式问题（零污染版本）
        
        核心设计：
        - Guidance 通过 System Prompt 注入，不进入历史记录
        - 使用上下文管理器确保异常安全
        - 历史记录中只有真实的对话内容
        """
        # 构建 Guidance 文本
        hints = "\n".join([f"- {h}" for h in guidance.context_hints]) if guidance.context_hints else ""
        bank_ref = f"\n参考题库：{guidance.question_bank_text}" if guidance.must_use_bank_question else ""
        
        def modify_prompt(original_prompt: str) -> str:
            """修改函数：追加 Guidance 要求"""
            return original_prompt + f"""
            
【当前面试问题要求】
考核点：{guidance.target_topic}
问题焦点：{guidance.question_focus}
建议角度：{guidance.suggested_angle}
{hints}{bank_ref}

⚠️ 角色提醒：你是面试官，正在面试候选人。请基于以上要求，以面试官的身份自然地提出下一个面试问题。保持口语化、简洁、专业。

🚫 禁止：不要回答面试问题，不要以求职者身份分享经验，只提出问题。"""

        print(f"[VAD] Guidance注入: {guidance.action.value} | {guidance.target_topic}")

        # 使用上下文管理器：临时修改 System Prompt，确保恢复
        async with temporary_system_prompt_modifier(modify_prompt):
            # 触发 GLM 继续生成（幽灵消息：触发词不写入历史记录）
            await process_interaction(
                "text",
                "请根据以上给出的最新焦点和指导，自然地向候选人提出下一个面试问题。",  # 避免过短的触发词导致模型幻觉生成滴滴声
                self.output_queue,
                on_text_chunk=send_ai_text,
                manage_processing_state=False,
                skip_history=True,  # 关键：不污染历史记录
            )

        print("[VAD] 正式问题输出完成")

    async def _continue_default(self, send_ai_text):
        """
        DeepSeek 失败时的默认追问
        
        触发条件：
        - DeepSeek API 调用失败
        - 返回的 guidance 为 None
        - 网络超时等异常
        
        设计原则：
        - 简单通用，适用于任何场景
        - 不暴露系统错误
        - 给用户继续表达的机会
        """
        default_text = "能再详细说说吗？"
        
        print("[VAD] 使用默认追问")
        
        await process_interaction(
            "text",
            default_text,
            self.output_queue,
            on_text_chunk=send_ai_text,
            manage_processing_state=False,
        )

    async def _sync_transcript_to_memory(self, user_transcript: str):
        """
        同步 ASR 文本到后端记忆
        
        操作逻辑：
        阶段一已使用 skip_history=True，音频消息未写入历史。
        此处直接将 ASR 转录文本作为全新的 user 消息追加到历史中，
        确保对话历史的完整性和准确性。
        """
        if not user_transcript:
            return
        
        # 直接追加全新的 user 消息（不再查找和修改旧消息）
        global_state.messages.append(
            {"role": "user", "content": [{"type": "text", "text": user_transcript}]}
        )
        print(f"[VAD] ASR转录已同步到记忆: '{user_transcript[:50]}...'")

    async def emit(self):
        array = await wait_for_item(self.output_queue, 0.01)
        if array is not None:
            print(f"[Emit] 发送音频到前端: {len(array)} 采样点, 队列剩余: {self.output_queue.qsize()}")
            return (self.output_sample_rate, array)
        # 每隔一段时间打印一次状态，避免刷屏
        if not hasattr(self, '_emit_log_counter'):
            self._emit_log_counter = 0
        self._emit_log_counter += 1
        if self._emit_log_counter % 100 == 0:  # 每100次打印一次
            print(f"[Emit] 队列为空，等待音频数据... (计数: {self._emit_log_counter})")
        return None

    async def video_receive(self, frame: np.ndarray):
        pass

    async def video_emit(self) -> np.ndarray | None:
        return None

    def copy(self):
        return HighSpeedVADHandler()


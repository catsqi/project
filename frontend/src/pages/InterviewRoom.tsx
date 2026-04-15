import React, { useState, useEffect, useRef } from 'react';
import { Text } from '../components/ui/Text';
import { Progress } from '../components/ui/Progress';
import { useNavigate, useLocation } from 'react-router-dom';
import { DigitalInterviewer } from '../components/ui/DigitalInterviewer';
import { InteractionBar } from '../components/ui/InteractionBar';
import { useWebRTCStore } from '../store/webrtcStore';

const InterviewRoom: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { candidateId, jobTitle } = location.state || {};
  
  // 从全局 store 获取 WebRTC 状态
  const { 
    isConnected, 
    isConnecting,
    pc, 
    localStream, 
    remoteAudioStream,
    dataChannel,
    isAISpeaking,
    setAISpeaking,
    addToQueue,
    disconnect 
  } = useWebRTCStore();
  
  const [messages, setMessages] = useState<{id: number, sender: 'ai'|'user', text: string}[]>([
    { id: 1, sender: 'ai', text: 'HELLO. I AM READY. SHALL WE BEGIN?' }
  ]);
  const [progress, setProgress] = useState(0);
  const [aiState, setAiState] = useState<'idle' | 'listening' | 'thinking' | 'speaking'>('idle');
  const [isVoiceActive, setIsVoiceActive] = useState(false);

  const audioRemoteRef = useRef<HTMLAudioElement | null>(null);
  const voiceAiMsgIdRef = useRef<number | null>(null);
  const endRef = useRef<HTMLDivElement>(null);
  const hasPlayedOpeningRef = useRef(false);
  const initLock = useRef(false); // 防止 React 18 严格模式双重渲染
  const isBusinessReadyRef = useRef(false); // 标记业务初始化（start_interview）是否完成

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // ==========================================
  // Effect 1: 业务状态初始化 (严格串行)
  // 职责: 清理后端记忆，注册当前面试者
  // ==========================================
  useEffect(() => {
    if (!candidateId) return;
    if (initLock.current) return;
    initLock.current = true;

    const initializeInterview = async () => {
      try {
        console.log("[Frontend] 步骤1: 正在重置后端上下文记忆...");
        await fetch("/api/chat/reset", { method: "POST" });
        console.log("[Frontend] 步骤1 完成: 后端状态已重置");

        console.log(`[Frontend] 步骤2: 正在注册候选人ID [${candidateId}]...`);
        await fetch("/api/chat/start_interview", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ candidate_id: candidateId })
        });
        console.log("[Frontend] 步骤2 完成: 候选人ID注册成功");

        // 标记业务初始化完成
        isBusinessReadyRef.current = true;

        // === 自动连接 WebRTC ===
        if (!isConnected) {
          console.log("[Frontend] 业务初始化完成，自动尝试建立 WebRTC 连接");
          const { connect } = useWebRTCStore.getState();
          await connect();
          setIsVoiceActive(true);
          setAiState('listening');
        } else if (!hasPlayedOpeningRef.current) {
          // 如果 WebRTC 已经连接，立即播放开场白
          hasPlayedOpeningRef.current = true;
          fetchAndPlayOpening();
        }
      } catch (error) {
        console.error("[Frontend] 面试系统初始化严重失败:", error);
      }
    };

    initializeInterview();

    return () => {
      // 【关键修复】使用 getState() 直接获取，避免作为依赖项触发重连
      useWebRTCStore.getState().disconnect();
    };
  }, [candidateId]);  // 【关键修复】只依赖 candidateId，不包含 disconnect

  // 监听 WebRTC 连接状态，连接成功后播放开场白
  useEffect(() => {
    // 必须同时满足 WebRTC 连接成功 + 业务初始化完成
    if (isConnected && isBusinessReadyRef.current && !hasPlayedOpeningRef.current) {
      hasPlayedOpeningRef.current = true;
      fetchAndPlayOpening();
    }
  }, [isConnected]);

  // 监听 AI 说话状态
  useEffect(() => {
    if (isAISpeaking) {
      setAiState('speaking');
    } else {
      setAiState(isVoiceActive ? 'listening' : 'idle');
    }
  }, [isAISpeaking, isVoiceActive]);

  // 当 AI 发声时自动堵住耳朵（物理切断麦克风波形发送），防止声音循环被误认为用户发言
  useEffect(() => {
    if (localStream) {
      localStream.getAudioTracks().forEach(track => {
        track.enabled = isVoiceActive && !isAISpeaking;
      });
      console.log(`[Frontend] 麦克风轨道状态已切换: ${isVoiceActive && !isAISpeaking ? '开启接收' : '被堵住（防回音过滤）'}`);
    }
  }, [localStream, isVoiceActive, isAISpeaking]);

  // 设置数据通道监听器
  useEffect(() => {
    if (!dataChannel) return;

    dataChannel.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        
        // 1. 处理用户语音转录
        if (data.type === 'user_transcript') {
          // 如果 AI 正在说话，忽略用户输入（防止打断）
          if (useWebRTCStore.getState().isAISpeaking) {
            console.log('[Frontend] AI 正在说话，忽略用户输入:', data.text);
            return;
          }
          
          console.log('[Frontend] 收到用户转录:', data.text);
          setMessages(prev => {
            const exists = prev.some(m => m.sender === 'user' && m.text === data.text);
            if (exists) return prev;
            
            const userMsg = { id: Date.now() + Math.random(), sender: 'user' as const, text: data.text };
            return [...prev, userMsg];
          });
        }
        // 2. 处理 AI 文字
        else if (data.type === 'ai_text') {
          console.log('[Frontend] 收到 AI 文本:', data.text?.substring(0, 20) + '...');
          
          // 只有在第一次收到文字时，才将状态切换为 speaking，以此在 UI 上触发堵麦逻辑
          if (!useWebRTCStore.getState().isAISpeaking) {
            setAISpeaking(true);
          }

          // 核心修复：严禁在 setMessages 的 updater(prev => ...) 箭头函数里改变 ref 的值！
          // 在 React 18 的 Strict Mode 下，updater 会被执行两次，导致第二遍执行时判断跳过创建从而丢失气泡！
          if (voiceAiMsgIdRef.current === null) {
            const newId = Date.now() + Math.random();
            voiceAiMsgIdRef.current = newId;
            setMessages(prev => [...prev, { id: newId, sender: 'ai', text: data.text }]);
          } else {
            const activeId = voiceAiMsgIdRef.current;
            setMessages(prev => prev.map(m => 
              m.id === activeId 
                ? { ...m, text: m.text + (data.text || "") } 
                : m
            ));
          }
        }
        // 3. 处理流结束信号
        else if (data.type === 'ai_text_end') {
          voiceAiMsgIdRef.current = null;
          console.log('[Frontend] 一轮对话结束，重置对话指针');
          
          // 此处代表这轮 AI 回复的文字以及最后排队的音频包已经全部播放完毕，释放麦克风
          setAISpeaking(false);
        }
      } catch (e) {
        console.error("DataChannel error:", e);
      }
    };
  }, [dataChannel, setAISpeaking]);

  // 监听远程音频流并播放
  useEffect(() => {
    if (!remoteAudioStream || !audioRemoteRef.current) {
      console.log('[WebRTC-Audio] 等待音频流... remoteAudioStream:', !!remoteAudioStream, 'audioRemoteRef:', !!audioRemoteRef.current);
      return;
    }
    
    console.log('[WebRTC-Audio] 检测到 remoteAudioStream 变化，开始播放');
    audioRemoteRef.current.srcObject = remoteAudioStream;
    audioRemoteRef.current.play().then(() => {
      console.log('[WebRTC-Audio] 🔊 audio.play() 成功！');
    }).catch((e) => {
      console.error('[WebRTC-Audio] ❌ audio.play() 失败:', e.name, e.message);
    });
  }, [remoteAudioStream]);

  // 获取并播放预生成的开场白
  const fetchAndPlayOpening = async () => {
    try {
      const response = await fetch('/api/chat/opening');
      const data = await response.json();

      if (data.status === 'ready' && data.opening_text) {
        console.log('[Frontend] 开场白已获取:', data.opening_text);

        // 显示开场白消息
        const openingMsgId = Date.now() + Math.random();
        setMessages(prev => [...prev, {
          id: openingMsgId,
          sender: 'ai',
          text: data.opening_text
        }]);

        // 如果有预生成的音频，播放它
        if (data.opening_audio) {
          // 只有在真正开始播放音频时才设置 isAISpeaking
          setAISpeaking(true);
          addToQueue(data.opening_audio);
        } else {
          // 没有预生成音频，通过文本通道让GLM生成
          const triggerRes = await fetch('/api/chat/text', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text: data.opening_text })
          });

          if (triggerRes.ok && triggerRes.body) {
            const reader = triggerRes.body.getReader();
            const decoder = new TextDecoder();
            let partialLine = '';
            let hasReceivedAudio = false;

            while (true) {
              const { value, done } = await reader.read();
              if (done) break;

              const chunkText = decoder.decode(value, { stream: true });
              const lines = (partialLine + chunkText).split('\n');
              partialLine = lines.pop() || '';

              for (const line of lines) {
                if (!line.trim()) continue;
                try {
                  const chunk = JSON.parse(line);
                  if (chunk.audio) {
                    // 第一次收到音频时设置 isAISpeaking
                    if (!hasReceivedAudio) {
                      hasReceivedAudio = true;
                      setAISpeaking(true);
                    }
                    addToQueue(chunk.audio);
                  }
                } catch (e) {
                  console.warn('Parse opening chunk failed', e);
                }
              }
            }

            // 如果没有收到任何音频，解锁 VAD
            if (!hasReceivedAudio) {
              setAISpeaking(false);
            }
          } else {
            // 请求失败，解锁 VAD
            setAISpeaking(false);
          }
        }
      } else if (data.status === 'not_ready') {
        console.log('[Frontend] 开场白准备中，稍后重试...');
        setTimeout(fetchAndPlayOpening, 3000);
      } else {
        console.log('[Frontend] 无开场白:', data.message);
      }
    } catch (err) {
      console.error('[Frontend] 获取开场白失败:', err);
      // 确保出错时解锁 VAD
      setAISpeaking(false);
    }
  };

  const handleTextSubmit = async (text: string) => {
    // 如果 AI 正在说话，不允许发送
    if (isAISpeaking) {
      console.log('[Frontend] AI 正在说话，请稍后再试');
      return;
    }
    
    const userMsgId = Date.now() + Math.random();
    setMessages(prev => [...prev, { id: userMsgId, sender: 'user', text }]);
    setAiState('thinking');
    
    try {
      const res = await fetch("/api/chat/text", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text })
      });
      
      if (!res.ok) throw new Error("Text processing failed");
      if (!res.body) throw new Error("No response body");

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      
      const aiMsgId = userMsgId + 1;
      setMessages(prev => [...prev, { id: aiMsgId, sender: 'ai', text: "" }]);
      let fullAiText = "";
      let partialLine = "";

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        const chunkText = decoder.decode(value, { stream: true });
        const lines = (partialLine + chunkText).split("\n");
        partialLine = lines.pop() || "";

        for (const line of lines) {
          if (!line.trim()) continue;
          try {
            const data = JSON.parse(line);
            
            if (data.text) {
              const text = data.text;
              fullAiText += text;
              setMessages(prev => prev.map(m => m.id === aiMsgId ? { ...m, text: fullAiText } : m));
            }

            if (data.audio) {
              addToQueue(data.audio);
            }

          } catch (e) {
            console.warn("Parse chunk failed", e);
          }
        }
      }

      setProgress(p => Math.min(100, p + 15));
    } catch (err: any) {
      console.error("Text Submit Error:", err);
      setMessages(prev => [...prev, { id: Date.now() + Math.random(), sender: 'ai', text: `ERROR: ${err.message}` }]);
      setAiState('idle');
    }
  };


  const toggleMic = async () => {
    if (isVoiceActive) {
      disconnect();
      setIsVoiceActive(false);
      setAiState('idle');
      voiceAiMsgIdRef.current = null;
      setMessages(prev => [...prev, { id: Date.now() + Math.random(), sender: 'ai', text: 'VOICE COMMUNICATION TERMINATED.' }]);
    } else {
      setIsVoiceActive(true);
      setAiState('listening');
      voiceAiMsgIdRef.current = null;
      
      // 如果还没有连接，在这里连接
      if (!isConnected) {
        try {
          const { connect } = useWebRTCStore.getState();
          await connect();
        } catch(err: any) {
          console.error("WebRTC Error:", err);
          setIsVoiceActive(false);
          setAiState('idle');
        }
      }
    }
  };

  return (
    <div className="h-screen text-black flex flex-col p-6 md:p-8 w-full max-w-[1600px] mx-auto overflow-hidden">
      <audio ref={audioRemoteRef} autoPlay playsInline hidden></audio>
      
      {/* 连接状态指示器 */}
      {isConnecting && (
        <div className="fixed top-4 left-1/2 transform -translate-x-1/2 bg-blue-500 text-white px-4 py-2 rounded-full z-50">
          正在连接语音服务...
        </div>
      )}
      
      {/* Header Info */}
      <header className="flex-none flex justify-between items-center mb-6 border-b border-black pb-4">
        <div>
          <Text variant="h3">INTERVIEW T-001</Text>
          <Text variant="caption" className="text-gray-500 mt-1">
            {jobTitle ? jobTitle : 'FRONTEND ENGINEERING // SENIOR'}
          </Text>
        </div>
        <div className="text-right">
          <Text variant="caption" className="block text-gray-500 mb-1">STATUS</Text>
          <div className={`px-4 py-1 inline-block uppercase text-xs tracking-widest font-bold ${aiState === 'listening' ? 'bg-neon-green text-black' : 'bg-black text-white'}`}>
            {aiState}
          </div>
        </div>
      </header>

      {/* Main Area: 2-Column Layout */}
      <main className="flex-1 flex flex-col md:flex-row gap-8 min-h-0">
        
        {/* Left Column: Digital Interviewer */}
        <section className="flex-1 flex flex-col md:w-1/2 min-h-0 bg-gray-50">
          <DigitalInterviewer isSpeaking={aiState === 'speaking'} />
        </section>

        {/* Right Column: Chat Console & Interaction */}
        <section className="flex-1 flex flex-col md:w-1/2 min-h-0">
          
          {/* Progress */}
          <div className="flex-none mb-6">
            <div className="flex justify-between mb-2">
              <Text variant="caption">PROGRESS</Text>
              <Text variant="caption">{progress}%</Text>
            </div>
            <Progress value={progress} color="neon" />
          </div>

          {/* Chat History Flow */}
          <div className="flex-1 overflow-y-auto pr-4 space-y-8 pb-4 custom-scrollbar">
            {messages.map(msg => (
              <div key={msg.id} className={`flex flex-col ${msg.sender === 'user' ? 'items-end' : 'items-start'}`}>
                {msg.sender === 'user' ? (
                   <Text variant="caption" className="mb-2 text-gray-400">YOU</Text>
                ) : (
                   <Text variant="caption" className="mb-2 text-neon-green font-bold">KAREN.AI</Text>
                )}
                <div className={`max-w-[85%] ${msg.sender === 'user' ? 'bg-black text-white p-5' : 'bg-white border-2 border-neon-green shadow-[4px_4px_0px_#000000] p-5'}`}>
                  <Text variant="p" className={msg.sender === 'user' ? 'text-white' : 'text-black'}>
                    {msg.text}
                  </Text>
                </div>
              </div>
            ))}
            <div ref={endRef} />
          </div>

          {/* Interaction Bar */}
          <div className="flex-none pt-4 border-t border-black mt-2">
            <InteractionBar 
              isRecording={isVoiceActive} 
              onToggleMic={toggleMic} 
              onSubmitText={handleTextSubmit}
              onModeChange={(isTyping) => {
                  if (localStream) {
                      localStream.getAudioTracks().forEach((track: MediaStreamTrack) => {
                          track.enabled = !isTyping;
                      });
                  }
                  if (isTyping) {
                      setAiState('idle');
                  } else if (isVoiceActive) {
                      setAiState('listening');
                  }
              }}
              aiState={aiState}
              disabled={isAISpeaking}
            />
          </div>
        </section>

      </main>
    </div>
  );
};

export default InterviewRoom;

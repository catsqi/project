import React, { useState, useEffect, useRef } from 'react';
import { Text } from '../components/ReactBits/Text';
import { Progress } from '../components/ReactBits/Progress';
import { useNavigate } from 'react-router-dom';
import { DigitalInterviewer } from '../components/ReactBits/DigitalInterviewer';
import { InteractionBar } from '../components/ReactBits/InteractionBar';

const InterviewRoom: React.FC = () => {
  const navigate = useNavigate();
  const [messages, setMessages] = useState<{id: number, sender: 'ai'|'user', text: string}[]>([
    { id: 1, sender: 'ai', text: 'HELLO. I AM READY. SHALL WE BEGIN?' }
  ]);
  const [progress, setProgress] = useState(0);
  const [aiState, setAiState] = useState<'idle' | 'listening' | 'thinking' | 'speaking'>('idle');
  const [isVoiceActive, setIsVoiceActive] = useState(false);

  const pcRef = useRef<RTCPeerConnection | null>(null);
  const localStreamRef = useRef<MediaStream | null>(null);
  const audioRemoteRef = useRef<HTMLAudioElement | null>(null);
  const recognitionRef = useRef<any>(null);
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Audio Queue Management
  const audioQueueRef = useRef<string[]>([]);
  const isPlayingRef = useRef<boolean>(false);

  const playNextInQueue = () => {
    if (audioQueueRef.current.length === 0) {
      isPlayingRef.current = false;
      setAiState('idle'); // Back to idle after all audio finished
      return;
    }

    isPlayingRef.current = true;
    setAiState('speaking');
    const b64 = audioQueueRef.current.shift();
    const audio = new Audio("data:audio/wav;base64," + b64);
    audio.onended = playNextInQueue;
    audio.play().catch(e => {
        console.error("Audio playback error:", e);
        playNextInQueue(); // Skip on error
    });
  };

  const handleTextSubmit = async (text: string) => {
    const userMsgId = Date.now();
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
        partialLine = lines.pop() || ""; // The last element is the incomplete line

        for (const line of lines) {
          if (!line.trim()) continue;
          try {
            const data = JSON.parse(line);
            
            if (data.text) {
              fullAiText += data.text;
              setMessages(prev => prev.map(m => m.id === aiMsgId ? { ...m, text: fullAiText } : m));
            }

            if (data.audio) {
              audioQueueRef.current.push(data.audio);
              if (!isPlayingRef.current) {
                playNextInQueue();
              }
            }

          } catch (e) {
            console.warn("Parse chunk failed", e);
          }
        }
      }

      setProgress(p => Math.min(100, p + 15));
    } catch (err: any) {
      console.error("Text Submit Error:", err);
      setMessages(prev => [...prev, { id: Date.now(), sender: 'ai', text: `ERROR: ${err.message}` }]);
      setAiState('idle');
    }
  };

  const setupLocalSpeechRecognition = () => {
    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (SpeechRecognition) {
      const recognition = new SpeechRecognition();
      recognition.continuous = true;
      recognition.interimResults = true;
      recognition.lang = 'zh-CN';
      
      recognition.onresult = (event: any) => {
        let finalTranscript = '';
        for (let i = event.resultIndex; i < event.results.length; ++i) {
          if (event.results[i].isFinal) finalTranscript += event.results[i][0].transcript;
        }
        if (finalTranscript) {
          setMessages(prev => [...prev, { id: Date.now(), sender: 'user', text: finalTranscript }]);
          setAiState('thinking'); 
        }
      };
      recognition.start();
      return recognition;
    }
    return null;
  };

  const toggleMic = async () => {
    if (isVoiceActive) {
      if (pcRef.current) pcRef.current.close();
      if (localStreamRef.current) localStreamRef.current.getTracks().forEach(t => t.stop());
      if (recognitionRef.current) recognitionRef.current.stop();
      setIsVoiceActive(false);
      setAiState('idle');
      setMessages(prev => [...prev, { id: Date.now(), sender: 'ai', text: 'VOICE COMMUNICATION TERMINATED.' }]);
    } else {
      setIsVoiceActive(true);
      setAiState('listening');
      
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ 
            audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true } 
        });
        localStreamRef.current = stream;
        
        recognitionRef.current = setupLocalSpeechRecognition();

        const iceConfig = { iceServers: [{ urls: "stun:stun.l.google.com:19302" }] };
        const pc = new RTCPeerConnection(iceConfig);
        pcRef.current = pc;
        const webrtcId = Math.random().toString(36).slice(2);

        stream.getTracks().forEach(track => pc.addTrack(track, stream));

        pc.ontrack = (event) => {
            if (audioRemoteRef.current) {
                audioRemoteRef.current.srcObject = event.streams[0];
                audioRemoteRef.current.play();
                
                const audioCtx = new (window.AudioContext || (window as any).webkitAudioContext)();
                const source = audioCtx.createMediaStreamSource(event.streams[0]);
                const analyser = audioCtx.createAnalyser();
                source.connect(analyser);
                analyser.fftSize = 256;
                const bufferLength = analyser.frequencyBinCount;
                const dataArray = new Uint8Array(bufferLength);
                
                const checkAudioVolume = () => {
                   if (!pcRef.current) return;
                   analyser.getByteFrequencyData(dataArray);
                   let sum = 0;
                   for(let i=0; i<bufferLength; i++) { sum += dataArray[i]; }
                   const average = sum / bufferLength;
                   
                   if (average > 5) setAiState('speaking');
                   else setAiState(prev => prev === 'speaking' ? 'listening' : prev);
                   requestAnimationFrame(checkAudioVolume);
                };
                checkAudioVolume();
            }
        };

        const dc = pc.createDataChannel("chat");
        const offer = await pc.createOffer();
        await pc.setLocalDescription(offer);

        const response = await fetch("/voice/webrtc/offer", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ sdp: offer.sdp, type: offer.type, webrtc_id: webrtcId })
        });

        if (!response.ok) throw new Error("Offer failed");
        
        const answer = await response.json();
        // 修复竞争条件：如果用户在握手期间又点了"关闭"，连接会已经是 closed 状态
        // 此时不能再设置 RemoteDescription，否则会报错
        if (pc.signalingState !== 'closed') {
            await pc.setRemoteDescription(answer);
        }
        
      } catch(err: any) {
          console.error("WebRTC Error:", err);
          setIsVoiceActive(false);
          setAiState('idle');
      }
    }
  };

  return (
    <div className="h-screen text-black flex flex-col p-6 md:p-8 w-full max-w-[1600px] mx-auto overflow-hidden">
      <audio ref={audioRemoteRef} autoPlay playsInline hidden></audio>
      
      {/* Header Info */}
      <header className="flex-none flex justify-between items-center mb-6 border-b border-black pb-4">
        <div>
          <Text variant="h3">INTERVIEW T-001</Text>
          <Text variant="caption" className="text-gray-500 mt-1">FRONTEND ENGINEERING // SENIOR</Text>
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
              aiState={aiState}
            />
          </div>
        </section>

      </main>
    </div>
  );
};

export default InterviewRoom;

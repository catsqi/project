import { useState, useRef, useEffect } from 'react';
import './App.css';
import Avatar from './components/Avatar';
import ChatBox from './components/ChatBox';

function App() {
  const [isListening, setIsListening] = useState(false);
  const [messages, setMessages] = useState([
    { id: 1, sender: 'ai', text: '你好，我是你的AI面试官。我已经准备就绪。' }
  ]);
  const [aiState, setAiState] = useState('idle'); // 'idle', 'listening', 'thinking', 'speaking'
  
  const pcRef = useRef(null);
  const localStreamRef = useRef(null);
  const audioRemoteRef = useRef(null);

  // Fallback local speech recognition for visual effects (since backend is audio-to-audio natively)
  const setupLocalSpeechRecognition = () => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (SpeechRecognition) {
      const recognition = new SpeechRecognition();
      recognition.continuous = true;
      recognition.interimResults = true;
      recognition.lang = 'zh-CN';
      
      recognition.onresult = (event) => {
        let interimTranscript = '';
        let finalTranscript = '';
        for (let i = event.resultIndex; i < event.results.length; ++i) {
          if (event.results[i].isFinal) finalTranscript += event.results[i][0].transcript;
          else interimTranscript += event.results[i][0].transcript;
        }
        if (finalTranscript) {
          setMessages(prev => [...prev, { id: Date.now(), sender: 'user', text: finalTranscript }]);
          setAiState('thinking'); // Visually shift to thinking when user finishes a sentence
        }
      };
      recognition.start();
      return recognition;
    }
    return null;
  };

  const recognitionRef = useRef(null);

  const toggleMic = async () => {
    if (isListening) {
      if (pcRef.current) pcRef.current.close();
      if (localStreamRef.current) localStreamRef.current.getTracks().forEach(t => t.stop());
      if (recognitionRef.current) recognitionRef.current.stop();
      setIsListening(false);
      setAiState('idle');
      setMessages(prev => [...prev, { id: Date.now(), sender: 'ai', text: '通信已断开。' }]);
    } else {
      setIsListening(true);
      setAiState('listening');
      
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ 
            audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true } 
        });
        localStreamRef.current = stream;
        
        // Start Local Speech Recognition just for UI Subtitles!
        recognitionRef.current = setupLocalSpeechRecognition();

        let iceConfig = { iceServers: [{ urls: "stun:stun.l.google.com:19302" }] };
        const pc = new RTCPeerConnection(iceConfig);
        pcRef.current = pc;
        const webrtcId = Math.random().toString(36).slice(2);

        stream.getTracks().forEach(track => pc.addTrack(track, stream));

        pc.ontrack = (event) => {
            console.log("Got remote audio track");
            if (audioRemoteRef.current) {
                audioRemoteRef.current.srcObject = event.streams[0];
                audioRemoteRef.current.play();
                
                // Volume Analyzer to detect when AI is actually talking
                const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
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
                   
                   // If audio is playing smoothly
                   if (average > 5) {
                       setAiState('speaking');
                   } else {
                       // If silent but still connected, fallback to listening
                       setAiState(prev => prev === 'speaking' ? 'listening' : prev);
                   }
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
        await pc.setRemoteDescription(answer);
        
      } catch(err) {
          console.error("WebRTC Error:", err);
          setIsListening(false);
          setAiState('idle');
          setMessages(prev => [...prev, { id: Date.now(), sender: 'ai', text: `连接失败: ${err.message}` }]);
      }
    }
  };

  return (
    <div className="app-container">
      <audio ref={audioRemoteRef} autoPlay playsInline hidden></audio>
      <header className="app-header">
        <h1 className="logo">AI EXAMINER // 面试系统</h1>
        <div className={`status-badge ${aiState}`}>
          {aiState === 'idle' ? 'STANDBY' : aiState.toUpperCase()}
        </div>
      </header>
      
      <main className="main-content">
        <div className="avatar-section">
          <Avatar state={aiState} />
        </div>
        <div className="chat-section">
          <ChatBox messages={messages} aiState={aiState} />
        </div>
      </main>

      <footer className="controls-container">
        <button 
          className={`mic-btn ${isListening ? 'active' : ''}`} 
          onClick={toggleMic}
        >
          {isListening ? '⏹ 结束连接' : '🎙️ 开始对话'}
        </button>
      </footer>
    </div>
  );
}

export default App;

import { create } from 'zustand';

interface WebRTCState {
  // 连接状态
  isConnected: boolean;
  isConnecting: boolean;
  error: string | null;
  
  // WebRTC 实例
  pc: RTCPeerConnection | null;
  localStream: MediaStream | null;
  
  // 远程音频流（用于播放 AI 语音）
  remoteAudioStream: MediaStream | null;
  
  // AI 说话锁（防止开场白被打断）
  isAISpeaking: boolean;
  setAISpeaking: (speaking: boolean) => void;
  
  // 连接管理
  connect: () => Promise<void>;
  disconnect: () => void;
  
  // 数据通道（用于接收转录和AI回复）
  dataChannel: RTCDataChannel | null;
  
  // 音频播放队列
  audioQueue: string[];
  isPlaying: boolean;
  addToQueue: (audioBase64: string) => void;
  playNext: () => void;
}

export const useWebRTCStore = create<WebRTCState>((set, get) => ({
  isConnected: false,
  isConnecting: false,
  error: null,
  pc: null,
  localStream: null,
  remoteAudioStream: null,
  dataChannel: null,
  isAISpeaking: false,
  audioQueue: [],
  isPlaying: false,

  setAISpeaking: (speaking) => set({ isAISpeaking: speaking }),

  connect: async () => {
    const state = get();

    // 【修复】如果存在旧连接，先断开并等待清理完成
    if (state.pc || state.isConnecting) {
      console.log('[WebRTC] 检测到旧连接，先断开...');
      state.disconnect();
      await new Promise(resolve => setTimeout(resolve, 200));
    }

    set({ isConnecting: true, error: null });

    try {
      // 1. 获取麦克风权限
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true }
      });
      
      // 2. 创建 RTCPeerConnection
      const iceConfig = { iceServers: [{ urls: "stun:stun.l.google.com:19302" }] };
      const pc = new RTCPeerConnection(iceConfig);
      
      // 【关键修复】在创建连接后立即设置 ontrack 监听器，避免错过事件
      pc.ontrack = (event) => {
        console.log('[WebRTC-Audio] 收到远程轨道:', event.track.kind, 'streams:', event.streams.length);
        if (event.track.kind === 'audio' && event.streams[0]) {
          set({ remoteAudioStream: event.streams[0] });
          console.log('[WebRTC-Audio] 音频流已保存到 store');
        }
      };
      
      // 3. 添加本地音频轨道
      stream.getTracks().forEach(track => pc.addTrack(track, stream));
      
      // 4. 创建数据通道
      const dc = pc.createDataChannel("chat");
      
      // 5. 监听连接状态
      pc.onconnectionstatechange = () => {
        console.log('[WebRTC] Connection state:', pc.connectionState);
        if (pc.connectionState === 'connected') {
          set({ isConnected: true, isConnecting: false });
        } else if (pc.connectionState === 'failed' || pc.connectionState === 'closed') {
          set({ isConnected: false, isConnecting: false });
        }
      };
      
      // 6. 创建并发送 Offer
      const offer = await pc.createOffer();
      await pc.setLocalDescription(offer);
      
      const webrtcId = Math.random().toString(36).slice(2);
      const response = await fetch("/voice/webrtc/offer", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ sdp: offer.sdp, type: offer.type, webrtc_id: webrtcId })
      });
      
      if (!response.ok) throw new Error("Offer failed");
      
      const answer = await response.json();
      if (pc.signalingState !== 'closed') {
        await pc.setRemoteDescription(answer);
      }
      
      set({ 
        pc, 
        localStream: stream, 
        dataChannel: dc,
        isConnected: true,
        isConnecting: false 
      });
      
    } catch (err: any) {
      console.error("WebRTC Connect Error:", err);
      set({ error: err.message, isConnecting: false, isConnected: false });
      throw err;
    }
  },

  disconnect: () => {
    const { pc, localStream } = get();
    console.log('[WebRTC] 断开连接...');

    if (pc) {
      // 先关闭数据通道
      if (pc.signalingState !== 'closed') {
        pc.close();
      }
    }
    if (localStream) {
      localStream.getTracks().forEach(t => t.stop());
    }

    set({
      pc: null,
      localStream: null,
      remoteAudioStream: null,
      dataChannel: null,
      isConnected: false,
      isConnecting: false,
      isAISpeaking: false,
      audioQueue: [],
      isPlaying: false
    });
  },

  addToQueue: (audioBase64) => {
    const { audioQueue, isPlaying } = get();
    set({ audioQueue: [...audioQueue, audioBase64] });
    if (!isPlaying) {
      get().playNext();
    }
  },

  playNext: () => {
    const { audioQueue } = get();
    if (audioQueue.length === 0) {
      console.log('[Audio] 播放队列已空，停止播放');
      set({ isPlaying: false, isAISpeaking: false });
      return;
    }

    set({ isPlaying: true, isAISpeaking: true });
    let b64 = audioQueue[0];
    set(state => ({ audioQueue: state.audioQueue.slice(1) }));

    // 清理 base64 数据
    b64 = b64.replace(/[\s\n\r]/g, '');

    console.log('[Audio-DEBUG] 开始播放音频, base64长度:', b64.length);
    console.log('[Audio-DEBUG] 前50字符:', b64.substring(0, 50));
    console.log('[Audio-DEBUG] 是否以UklGR开头(WAV标志):', b64.startsWith('UklGR'));

    const audio = new Audio("data:audio/wav;base64," + b64);

    audio.onloadedmetadata = () => {
      console.log('[Audio-DEBUG] 音频元数据加载完成, 时长:', audio.duration, '秒');
    };

    audio.onended = () => {
      console.log('[Audio] 音频播放结束');
      get().playNext();
    };

    audio.onerror = (e) => {
      console.error('[Audio-Error] 播放错误:', e);
      console.error('[Audio-Error] 错误代码:', audio.error?.code, '消息:', audio.error?.message);
      get().playNext();
    };

    audio.play().catch(e => {
      console.error('[Audio-Error] 播放失败:', e);
      get().playNext();
    });
  }
}));

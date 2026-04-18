import { useEffect, useRef, useState } from 'react';

interface UseAudioLevelOptions {
  threshold?: number;      // 音量阈值 (0-255)
  smoothing?: number;      // 平滑系数 (0-1)
  interval?: number;       // 检测间隔 (ms)
}

export function useAudioLevel(
  stream: MediaStream | null,
  options: UseAudioLevelOptions = {}
) {
  const {
    threshold = 10,        // 默认阈值
    smoothing = 0.8,       // 平滑系数
    interval = 50          // 50ms 检测一次
  } = options;

  const [isSpeaking, setIsSpeaking] = useState(false);
  const [volume, setVolume] = useState(0);
  
  const audioContextRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const sourceRef = useRef<MediaStreamAudioSourceNode | null>(null);
  const intervalRef = useRef<number | null>(null);
  const smoothedVolumeRef = useRef(0);

  useEffect(() => {
    if (!stream) {
      setIsSpeaking(false);
      setVolume(0);
      return;
    }

    // 创建音频上下文
    const audioContext = new (window.AudioContext || (window as any).webkitAudioContext)();
    audioContextRef.current = audioContext;

    // 创建分析器
    const analyser = audioContext.createAnalyser();
    analyser.fftSize = 256;  // 采样点数
    analyser.smoothingTimeConstant = 0.3;
    analyserRef.current = analyser;

    // 连接音频源
    const source = audioContext.createMediaStreamSource(stream);
    source.connect(analyser);
    sourceRef.current = source;

    // 音量检测循环
    const dataArray = new Uint8Array(analyser.frequencyBinCount);
    
    const detectVolume = () => {
      analyser.getByteFrequencyData(dataArray);
      
      // 计算平均音量
      const avgVolume = dataArray.reduce((a, b) => a + b) / dataArray.length;
      
      // 平滑处理
      smoothedVolumeRef.current = 
        smoothing * smoothedVolumeRef.current + 
        (1 - smoothing) * avgVolume;
      
      const finalVolume = Math.round(smoothedVolumeRef.current);
      setVolume(finalVolume);
      setIsSpeaking(finalVolume > threshold);
    };

    // 启动检测
    intervalRef.current = window.setInterval(detectVolume, interval);

    // 清理函数
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
      source.disconnect();
      analyser.disconnect();
      audioContext.close();
    };
  }, [stream, threshold, smoothing, interval]);

  return { isSpeaking, volume };
}

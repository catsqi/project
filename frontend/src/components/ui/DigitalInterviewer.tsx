import React, { useEffect, useState } from 'react';
import { motion } from 'framer-motion';

interface DigitalInterviewerProps {
  isSpeaking: boolean;
  volume?: number;  // 新增：音量参数 (0-255)
}

export const DigitalInterviewer: React.FC<DigitalInterviewerProps> = ({ 
  isSpeaking,
  volume = 0  // 默认 0
}) => {
  const [blink, setBlink] = useState(false);

  // Random blink logic
  useEffect(() => {
    const blinkInterval = setInterval(() => {
      setBlink(true);
      setTimeout(() => setBlink(false), 150);
    }, Math.random() * 4000 + 2000); // Blink every 2-6 seconds
    return () => clearInterval(blinkInterval);
  }, []);

  // Generate mouth wave segments
  const numSegments = 12;
  
  // 根据音量计算嘴型开合程度 (0-1)
  const mouthOpenness = Math.min(volume / 100, 1);

  return (
    <div className="relative w-full h-full min-h-[400px] md:min-h-[600px] bg-black border border-black overflow-hidden flex flex-col justify-center items-center font-mono">
      {/* Abstract Face Container */}
      <div className="relative w-64 h-80 flex flex-col items-center justify-center">
        
        {/* Head/Face Outline (Abstract) */}
        <motion.div 
          className="absolute inset-0 border-2 border-white/10 rounded-[40%_40%_50%_50%]"
          animate={{ scale: isSpeaking ? 1.02 : 1 }}
          transition={{ duration: 0.5, repeat: Infinity, repeatType: 'reverse' }}
        />

        {/* Eyes Area */}
        <div className="flex gap-12 mt-8">
          {/* Left Eye */}
          <div className="w-12 h-4 relative flex justify-center items-center">
            <motion.div 
              className="w-12 h-2 bg-neon-green rounded-full shadow-[0_0_15px_#CCFF00]"
              animate={{ 
                height: blink ? 0 : (isSpeaking ? 10 : 4),
                opacity: blink ? 0 : 1
              }}
              transition={{ duration: blink ? 0.05 : 0.2 }}
            />
          </div>
          {/* Right Eye */}
          <div className="w-12 h-4 relative flex justify-center items-center">
            <motion.div 
              className="w-12 h-2 bg-neon-green rounded-full shadow-[0_0_15px_#CCFF00]"
              animate={{ 
                height: blink ? 0 : (isSpeaking ? 10 : 4),
                opacity: blink ? 0 : 1
              }}
              transition={{ duration: blink ? 0.05 : 0.2 }}
            />
          </div>
        </div>

        {/* Nose abstract line */}
        <div className="w-[2px] h-12 bg-white/20 mt-8 rounded-full" />

        {/* Mouth Area (Waveform) - 根据音量动态调整 */}
        <div className="mt-12 flex items-center justify-center gap-1 h-12">
          {Array.from({ length: numSegments }).map((_, i) => {
            // Create a curve so center bars are taller
            const centerDist = Math.abs(i - numSegments / 2);
            const scaleBase = 1 - (centerDist / (numSegments / 2));
            
            // 基础高度 + 音量影响
            const baseHeight = 4;
            const maxHeight = 8 + (scaleBase * 24);
            const currentHeight = isSpeaking 
              ? baseHeight + (maxHeight - baseHeight) * mouthOpenness * (0.5 + Math.random() * 0.5)
              : baseHeight;

            return (
              <motion.div
                key={i}
                className="w-1.5 bg-neon-green rounded-full shadow-[0_0_10px_#CCFF00]"
                animate={{
                  height: currentHeight
                }}
                transition={{
                  duration: 0.05,  // 快速响应
                  ease: "linear"
                }}
              />
            );
          })}
        </div>
      </div>

      {/* Futuristic Scanline Overlay */}
      <div className="absolute inset-0 pointer-events-none opacity-10 bg-[linear-gradient(rgba(255,255,255,0)_50%,rgba(0,0,0,1)_50%)] bg-[length:100%_4px]" />

      {/* Top Left Label */}
      <div className="absolute top-4 left-4 flex items-center gap-2">
        <div className={`w-2 h-2 rounded-full animate-pulse ${isSpeaking ? 'bg-neon-green' : 'bg-gray-500'}`} />
        <span className="text-neon-green text-xs font-bold tracking-widest">SYS.AI.{isSpeaking ? 'SPEAKING' : 'LISTENING'}</span>
      </div>

      {/* Video Overlay Placeholder (Bottom Right) */}
      <div className="absolute bottom-4 right-4 w-40 md:w-56 aspect-[16/9] bg-white/10 border border-white/20 backdrop-blur-sm flex justify-center items-center">
        <span className="text-white/40 text-[10px] uppercase font-bold tracking-widest">Camera Feed</span>
      </div>
    </div>
  );
};

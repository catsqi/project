import React, { useEffect, useState, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

interface DigitalInterviewerProps {
  isSpeaking: boolean;
  volume?: number;  // 0-255
}

// 粒子组件：用于说话时的能量溢出效果
const Particle: React.FC<{ i: number; power: number }> = ({ i, power }) => {
  const angle = (i / 12) * Math.PI * 2;
  return (
    <motion.div
      className="absolute w-1 h-1 bg-neon-green rounded-full shadow-[0_0_8px_#CCFF00]"
      initial={{ x: 0, y: 0, opacity: 0 }}
      animate={{ 
        x: Math.cos(angle) * (50 + Math.random() * 100 * power),
        y: Math.sin(angle) * (50 + Math.random() * 100 * power),
        opacity: [0, 1, 0],
        scale: [0, 1.5, 0]
      }}
      transition={{ 
        duration: 0.8 + Math.random() * 0.5, 
        repeat: Infinity,
        repeatDelay: Math.random() * 0.2
      }}
    />
  );
};

export const DigitalInterviewer: React.FC<DigitalInterviewerProps> = ({ 
  isSpeaking,
  volume = 0 
}) => {
  const [blink, setBlink] = useState(false);
  
  useEffect(() => {
    const blinkInterval = setInterval(() => {
      setBlink(true);
      setTimeout(() => setBlink(false), 200);
    }, Math.random() * 5000 + 3000);
    return () => clearInterval(blinkInterval);
  }, []);

  // 灵敏度增强：将音量映射到 0-1.5 的强度范围
  const power = Math.min(volume / 80, 1.5); 

  const dataBars = useMemo(() => Array.from({ length: 20 }).map(() => Math.random()), []);

  return (
    <div className="relative w-full h-full min-h-[400px] md:min-h-[600px] bg-[#051001]/10 bg-[#000] overflow-hidden flex flex-col justify-center items-center font-mono select-none">
      
      {/* 1. 背景层：说话时背景会有轻微闪烁/脉冲 */}
      <motion.div 
        className="absolute inset-0 opacity-20 pointer-events-none"
        animate={{ opacity: isSpeaking ? [0.1, 0.3 * power, 0.1] : 0.1 }}
        transition={{ duration: 0.2, repeat: isSpeaking ? Infinity : 0 }}
      >
        <div className="absolute inset-0 bg-[linear-gradient(rgba(204,255,0,0.05)_1px,transparent_1px),linear-gradient(90deg,rgba(204,255,0,0.05)_1px,transparent_1px)] bg-[size:40px_40px]" />
      </motion.div>

      <motion.div 
        className="absolute inset-0 bg-neon-green/5 pointer-events-none"
        animate={{ opacity: isSpeaking ? (0.05 + 0.1 * power) : 0 }}
      />

      {/* 2. 中心核心容器 */}
      <div className="relative w-96 h-96 flex items-center justify-center">
        
        {/* 说话时的外散射光晕 (非常明显的效果) */}
        <AnimatePresence>
          {isSpeaking && (
            <motion.div 
              initial={{ scale: 0.8, opacity: 0 }}
              animate={{ 
                scale: 1 + 0.5 * power, 
                opacity: 0.4 * power,
              }}
              exit={{ opacity: 0 }}
              className="absolute w-80 h-80 rounded-full bg-neon-green/20 blur-[80px]"
            />
          )}
        </AnimatePresence>

        {/* 旋转圆环：说话时加速旋转 */}
        <motion.div 
          className="absolute w-72 h-72 border-2 border-dashed border-neon-green/30 rounded-full"
          animate={{ rotate: 360 }}
          transition={{ duration: isSpeaking ? 5 : 20, repeat: Infinity, ease: "linear" }}
        />
        <motion.div 
          className="absolute w-64 h-64 border-2 border-neon-green/10 rounded-full"
          animate={{ scale: isSpeaking ? [1, 1.1, 1] : [1, 1.05, 1], rotate: -360 }}
          transition={{ 
            scale: { duration: isSpeaking ? 0.4 : 3, repeat: Infinity },
            rotate: { duration: 25, repeat: Infinity, ease: "linear" }
          }}
        />

        {/* 粒子放射层 */}
        {isSpeaking && (
          <div className="absolute inset-0 pointer-events-none">
            {Array.from({ length: 12 }).map((_, i) => (
              <Particle key={i} i={i} power={power} />
            ))}
          </div>
        )}

        {/* 圆形波形层 (加粗加长) */}
        <div className="absolute inset-0 flex items-center justify-center">
          <svg className="w-full h-full rotate-[-90deg] drop-shadow-lg">
            {Array.from({ length: 72 }).map((_, i) => {
              const rotation = (i / 72) * 360;
              const height = isSpeaking 
                ? 8 + (Math.random() * 60 * power) 
                : 4 + (Math.random() * 4);
              
              return (
                <motion.rect
                  key={i}
                  x="50%"
                  y="50%"
                  width={isSpeaking ? "3" : "2"}
                  height={height}
                  fill={isSpeaking ? "#CCFF00" : "#CCFF0033"}
                  className="origin-center"
                  style={{
                    transform: `rotate(${rotation}deg) translateY(-110px)`,
                    filter: isSpeaking ? `drop-shadow(0 0 ${4 * power}px #CCFF00)` : 'none'
                  }}
                  animate={{ height }}
                  transition={{ duration: 0.08 }}
                />
              );
            })}
          </svg>
        </div>

        {/* 实体核心 (核心震动感调弱) */}
        <motion.div 
          className="relative w-40 h-40"
          animate={{ x: isSpeaking ? [0, -0.5, 0.5, 0] : 0 }}
          transition={{ duration: 0.2, repeat: isSpeaking ? Infinity : 0 }}
        >
          <motion.div 
            className="absolute inset-0 rounded-full bg-neon-green/20 blur-2xl"
            animate={{ scale: isSpeaking ? [1, 1.3, 1] : [1, 1.2, 1] }}
            transition={{ duration: isSpeaking ? 0.4 : 2, repeat: Infinity }}
          />
          
          <motion.div 
            className="absolute inset-4 rounded-full border-4 border-neon-green bg-black flex items-center justify-center shadow-[0_0_40px_rgba(204,255,0,0.6)]"
            style={{ zIndex: 10 }}
            animate={{ 
              scale: isSpeaking ? [1, 1.05, 1] : 1,
              boxShadow: isSpeaking 
                ? [`0 0 30px rgba(204,255,0,0.4)`, `0 0 50px rgba(204,255,0,0.7)`, `0 0 30px rgba(204,255,0,0.4)`] 
                : `0 0 30px rgba(204,255,0,0.4)`
            }}
            transition={{ duration: 0.4, repeat: Infinity }}
          >
            <div className="flex gap-4">
              <motion.div 
                className="w-8 h-2 bg-neon-green rounded-full shadow-[0_0_10px_#CCFF00]"
                animate={{ 
                  height: blink ? 0 : (isSpeaking ? 10 : 3),
                  opacity: blink ? 0 : 1
                }}
              />
              <motion.div 
                className="w-8 h-2 bg-neon-green rounded-full shadow-[0_0_10px_#CCFF00]"
                animate={{ 
                  height: blink ? 0 : (isSpeaking ? 10 : 3),
                  opacity: blink ? 0 : 1
                }}
              />
            </div>
          </motion.div>
        </motion.div>
      </div>

      {/* 装饰与状态 */}
      <div className="absolute top-6 left-6 flex flex-col gap-1">
        <div className="flex items-center gap-2">
          <div className={`w-2 h-2 rounded-full ${isSpeaking ? 'bg-white animate-ping' : 'bg-gray-700'}`} />
          <span className={`text-xs font-bold tracking-[0.2em] uppercase ${isSpeaking ? 'text-white' : 'text-neon-green'}`}>
            {isSpeaking ? 'STATUS: TRANSMITTING_DATA' : 'STATUS: SYSTEM_IDLE'}
          </span>
        </div>
        <div className="h-[1px] w-full bg-neon-green/30" />
        <div className="text-[9px] text-gray-500 font-mono">ENCRYPTION: AES-256-GCM</div>
      </div>



      <div className="absolute inset-0 pointer-events-none shadow-[inset_0_0_150px_rgba(0,0,0,0.9)]" />
    </div>
  );
};

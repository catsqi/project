import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Mic, ArrowRight, X } from 'lucide-react';

interface InteractionBarProps {
  isRecording: boolean;
  onToggleMic: () => void;
  onSubmitText: (text: string) => void;
  onModeChange?: (isTyping: boolean) => void;
  aiState: 'idle' | 'listening' | 'thinking' | 'speaking';
  disabled?: boolean;
}

export const InteractionBar: React.FC<InteractionBarProps> = ({ 
  isRecording, 
  onToggleMic, 
  onSubmitText,
  onModeChange,
  aiState,
  disabled = false
}) => {
  const [isTypingMode, setIsTypingMode] = useState(false);
  const [inputText, setInputText] = useState('');

  const toggleTypingMode = (val: boolean) => {
      if (disabled) return;
      setIsTypingMode(val);
      if (onModeChange) onModeChange(val);
  };

  const handleSubmit = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (disabled) return;
    if (inputText.trim()) {
      onSubmitText(inputText);
      setInputText('');
      toggleTypingMode(false);
    }
  };

  const handleMicToggle = () => {
    if (disabled) return;
    onToggleMic();
  };

  return (
    <div className="w-full flex justify-center items-center h-24 relative">
      <AnimatePresence mode="wait">
        {!isTypingMode ? (
          <motion.div 
            key="mic-mode"
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.8 }}
            className="flex items-center gap-6"
          >
            {/* Typing Mode Toggle */}
            <button 
              onClick={() => toggleTypingMode(true)}
              disabled={disabled}
              className={`px-6 py-3 border border-black font-bold uppercase text-xs transition-colors ${
                disabled 
                  ? 'bg-gray-200 text-gray-400 cursor-not-allowed' 
                  : 'hover:bg-black hover:text-white'
              }`}
            >
              KEYBOARD
            </button>

            {/* Microphone Context */}
            <div className="relative flex justify-center items-center">
              {/* Pulse Ring when recording */}
              {isRecording && !disabled && (
                <motion.div
                  initial={{ scale: 1, opacity: 0.8 }}
                  animate={{ scale: 2.5, opacity: 0 }}
                  transition={{ repeat: Infinity, duration: 1.5, ease: "easeOut" }}
                  className="absolute w-16 h-16 rounded-full bg-neon-green"
                />
              )}
              
              <button 
                onClick={handleMicToggle}
                disabled={disabled}
                className={`relative z-10 w-20 h-20 rounded-full flex justify-center items-center border-2 border-black transition-colors ${
                  disabled 
                    ? 'bg-gray-300 text-gray-500 cursor-not-allowed' 
                    : isRecording 
                      ? 'bg-neon-green text-black' 
                      : 'bg-black text-white hover:bg-gray-800'
                }`}
              >
                <Mic size={32} />
              </button>
            </div>

            {/* End Interview */}
            <button 
              onClick={() => window.location.href = '/report'}
              className="px-6 py-3 border border-black font-bold uppercase text-xs hover:bg-black hover:text-white transition-colors"
            >
              END SESSION
            </button>
          </motion.div>
        ) : (
          <motion.div 
            key="type-mode"
            initial={{ opacity: 0, width: "0%" }}
            animate={{ opacity: 1, width: "100%" }}
            exit={{ opacity: 0, width: "0%" }}
            className="flex w-full max-w-2xl items-center gap-2"
          >
            <button 
              onClick={() => toggleTypingMode(false)}
              className="w-12 h-12 flex-shrink-0 flex justify-center items-center border border-black hover:bg-gray-100 transition-colors"
            >
              <X size={20} />
            </button>
            
            <form onSubmit={handleSubmit} className="flex-1 flex gap-2">
              <input 
                type="text"
                autoFocus
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
                placeholder={disabled ? "AI 正在说话，请稍候..." : "Type your response..."}
                disabled={disabled}
                className={`w-full h-12 px-4 border border-black focus:outline-none focus:ring-2 focus:ring-neon-green ${
                  disabled ? 'bg-gray-100 text-gray-400 cursor-not-allowed' : 'bg-white'
                }`}
              />
              <button 
                type="submit"
                disabled={disabled}
                className={`h-12 px-8 font-bold uppercase text-xs transition-colors flex items-center gap-2 border border-black ${
                  disabled 
                    ? 'bg-gray-300 text-gray-500 cursor-not-allowed' 
                    : 'bg-black text-white hover:bg-neon-green hover:text-black'
                }`}
              >
                SEND <ArrowRight size={16} />
              </button>
            </form>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

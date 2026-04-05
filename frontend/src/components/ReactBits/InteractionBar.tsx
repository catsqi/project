import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Mic, ArrowRight, X } from 'lucide-react';

interface InteractionBarProps {
  isRecording: boolean;
  onToggleMic: () => void;
  onSubmitText: (text: string) => void;
  aiState: 'idle' | 'listening' | 'thinking' | 'speaking';
}

export const InteractionBar: React.FC<InteractionBarProps> = ({ 
  isRecording, 
  onToggleMic, 
  onSubmitText,
  aiState
}) => {
  const [isTypingMode, setIsTypingMode] = useState(false);
  const [inputText, setInputText] = useState('');

  const handleSubmit = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (inputText.trim()) {
      onSubmitText(inputText);
      setInputText('');
      setIsTypingMode(false);
    }
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
              onClick={() => setIsTypingMode(true)}
              className="px-6 py-3 border border-black font-bold uppercase text-xs hover:bg-black hover:text-white transition-colors"
            >
              KEYBOARD
            </button>

            {/* Microphone Context */}
            <div className="relative flex justify-center items-center">
              {/* Pulse Ring when recording */}
              {isRecording && (
                <motion.div
                  initial={{ scale: 1, opacity: 0.8 }}
                  animate={{ scale: 2.5, opacity: 0 }}
                  transition={{ repeat: Infinity, duration: 1.5, ease: "easeOut" }}
                  className="absolute w-16 h-16 rounded-full bg-neon-green"
                />
              )}
              
              <button 
                onClick={onToggleMic}
                className={`relative z-10 w-20 h-20 rounded-full flex justify-center items-center border-2 border-black transition-colors ${
                  isRecording ? 'bg-neon-green text-black' : 'bg-black text-white hover:bg-gray-800'
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
              onClick={() => setIsTypingMode(false)}
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
                placeholder="Type your response..."
                className="w-full h-12 px-4 border border-black bg-white focus:outline-none focus:ring-2 focus:ring-neon-green"
              />
              <button 
                type="submit"
                className="h-12 px-8 bg-black text-white font-bold uppercase text-xs hover:bg-neon-green hover:text-black transition-colors flex items-center gap-2 border border-black"
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

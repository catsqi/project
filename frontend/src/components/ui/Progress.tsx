import React from 'react';
import { cn } from './Button';

interface ProgressProps extends React.HTMLAttributes<HTMLDivElement> {
  value: number; 
  max?: number;
  height?: string;
  color?: 'black' | 'neon';
}

export const Progress = React.forwardRef<HTMLDivElement, ProgressProps>(
  ({ className, value, max = 100, height = "h-4", color = "black", ...props }, ref) => {
    const percentage = Math.max(0, Math.min(100, (value / max) * 100));
    
    return (
      <div
        ref={ref}
        className={cn(`w-full bg-white border border-black p-0.5 overflow-hidden ${height}`, className)}
        {...props}
      >
        <div
          className={cn(`h-full transition-all duration-300 ease-in-out`, color === 'neon' ? 'bg-neon-green' : 'bg-black')}
          style={{ width: `${percentage}%` }}
        />
      </div>
    );
  }
);
Progress.displayName = 'Progress';

import React from 'react';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'outline' | 'ghost' | 'neon';
  size?: 'sm' | 'md' | 'lg' | 'xl';
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = 'primary', size = 'md', ...props }, ref) => {
    
    // Strict No-border / color inversion design
    const baseStyles = "inline-flex items-center justify-center font-bold transition-colors duration-150 rounded-none disabled:opacity-50 disabled:pointer-events-none";
    
    const variants = {
      primary: "bg-black text-white hover:bg-neon-green hover:text-black",
      secondary: "bg-white text-black border-2 border-black hover:bg-black hover:text-white",
      outline: "bg-transparent text-black border-2 border-black hover:bg-black hover:text-white",
      ghost: "bg-transparent text-black hover:bg-black hover:text-white",
      neon: "bg-neon-green text-black hover:bg-black hover:text-white",
    };

    const sizes = {
      sm: "h-9 px-4 text-xs tracking-widest uppercase",
      md: "h-12 px-8 text-sm tracking-widest uppercase",
      lg: "h-16 px-10 text-base tracking-widest uppercase",
      xl: "h-20 px-14 text-xl tracking-widest uppercase",
    };

    return (
      <button
        ref={ref}
        className={cn(baseStyles, variants[variant === 'primary' ? 'primary' : variant], sizes[size], className)}
        {...props}
      />
    );
  }
);
Button.displayName = 'Button';

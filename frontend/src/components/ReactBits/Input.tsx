import React from 'react';
import { cn } from './Button';

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {}

/**
 * Input
 * 仅保留底部 1px 黑色下划线，无边框和背景色
 */
export const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, type, ...props }, ref) => {
    return (
      <input
        type={type}
        className={cn(
          "flex w-full bg-transparent border-0 border-b border-black rounded-none px-0 py-4 text-base",
          "placeholder:text-gray-400 font-sans tracking-wide text-black focus:outline-none focus:border-b-4 focus:border-black transition-all",
          "disabled:cursor-not-allowed disabled:opacity-50",
          className
        )}
        ref={ref}
        {...props}
      />
    )
  }
)
Input.displayName = "Input"

interface TextareaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {}

export const Textarea = React.forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ className, ...props }, ref) => {
    return (
      <textarea
        className={cn(
          "flex min-h-[120px] w-full bg-transparent border-0 border-b border-black rounded-none px-0 py-4 text-base",
          "placeholder:text-gray-400 font-sans tracking-wide text-black focus:outline-none focus:border-b-4 focus:border-black transition-all",
          "disabled:cursor-not-allowed disabled:opacity-50 resize-y",
          className
        )}
        ref={ref}
        {...props}
      />
    )
  }
)
Textarea.displayName = "Textarea"

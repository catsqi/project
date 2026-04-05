import React from 'react';
import { cn } from './Button';

interface TextProps extends React.HTMLAttributes<HTMLHeadingElement | HTMLParagraphElement | HTMLSpanElement> {
  variant?: 'h1' | 'h2' | 'h3' | 'h4' | 'p' | 'caption' | 'display';
  as?: React.ElementType;
}

export const Text = React.forwardRef<HTMLElement, TextProps>(
  ({ className, variant = 'p', as, ...props }, ref) => {
    const Component = as || (['h1', 'h2', 'h3', 'h4', 'p'].includes(variant) ? variant : 'span') as React.ElementType;

    const variants = {
      display: "text-[80px] leading-[0.9] font-black tracking-tighter uppercase",
      h1: "text-[64px] leading-none font-bold tracking-tight",
      h2: "text-[48px] leading-tight font-bold tracking-tight",
      h3: "text-[32px] leading-tight font-bold tracking-tight",
      h4: "text-[24px] leading-snug font-bold tracking-tight",
      p: "text-lg leading-relaxed font-normal",
      caption: "text-sm leading-normal font-normal tracking-wide uppercase",
    };

    // @ts-ignore
    return (
      <Component
        ref={ref}
        className={cn(variants[variant], className)}
        {...props}
      />
    );
  }
);
Text.displayName = 'Text';

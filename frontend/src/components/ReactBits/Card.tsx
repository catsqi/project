import React from 'react';
import { cn } from './Button'; // reuse cn utility

interface CardProps extends React.HTMLAttributes<HTMLDivElement> {}

/**
 * Card
 * 极致极简杂志风：去除默认边框、阴影、背景色。
 * 仅作为布局容器使用，依靠 Margin 创造间距。
 */
export const Card = React.forwardRef<HTMLDivElement, CardProps>(
  ({ className, ...props }, ref) => {
    return (
      <div
        ref={ref}
        className={cn(
          "bg-transparent p-0 m-0", // No border, no shadows, no bg
          className
        )}
        {...props}
      />
    );
  }
);
Card.displayName = "Card";

export const CardHeader = React.forwardRef<HTMLDivElement, CardProps>(
  ({ className, ...props }, ref) => (
    <div
      ref={ref}
      className={cn("flex flex-col space-y-1.5 pb-8", className)}
      {...props}
    />
  )
)
CardHeader.displayName = "CardHeader"

export const CardContent = React.forwardRef<HTMLDivElement, CardProps>(
  ({ className, ...props }, ref) => (
    <div ref={ref} className={cn("pt-0", className)} {...props} />
  )
)
CardContent.displayName = "CardContent"

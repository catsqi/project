import React from 'react';
import { cn } from './Button';

interface ListProps extends React.HTMLAttributes<HTMLUListElement> {}

export const List = React.forwardRef<HTMLUListElement, ListProps>(
  ({ className, ...props }, ref) => {
    return (
      <ul
        ref={ref}
        className={cn("space-y-6 list-none m-0 p-0", className)}
        {...props}
      />
    );
  }
);
List.displayName = 'List';

export const ListItem = React.forwardRef<HTMLLIElement, React.HTMLAttributes<HTMLLIElement>>(
  ({ className, ...props }, ref) => {
    return (
      <li
        ref={ref}
        className={cn("flex flex-col sm:flex-row sm:items-start justify-between py-4 border-b border-black", className)}
        {...props}
      />
    );
  }
);
ListItem.displayName = 'ListItem';

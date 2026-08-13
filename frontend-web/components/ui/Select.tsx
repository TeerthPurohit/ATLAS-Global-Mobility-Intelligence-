import { SelectHTMLAttributes, forwardRef } from "react";
import { cn } from "@/lib/utils";

export const Select = forwardRef<HTMLSelectElement, SelectHTMLAttributes<HTMLSelectElement>>(
  ({ className, children, ...props }, ref) => (
    <select
      ref={ref}
      className={cn(
        "w-full rounded-sm border border-surface-border bg-surface-1 px-4 py-2.5 font-body-md text-ink-primary focus:outline-none focus:ring-2 focus:ring-brass/30 focus:border-brass/50 transition-all",
        className
      )}
      {...props}
    >
      {children}
    </select>
  )
);
Select.displayName = "Select";

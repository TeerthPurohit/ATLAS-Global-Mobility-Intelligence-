import { ButtonHTMLAttributes, forwardRef } from "react";
import { cn } from "@/lib/utils";

type Variant = "primary" | "secondary" | "ghost";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
}

const variantClasses: Record<Variant, string> = {
  primary: "bg-brass text-brass-fg hover:bg-brass/90 border border-brass",
  secondary: "bg-surface-2 text-ink-primary hover:bg-surface-2/80 border border-surface-border",
  ghost: "bg-transparent text-ink-secondary hover:text-ink-primary border border-transparent hover:border-surface-border",
};

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = "primary", ...props }, ref) => (
    <button
      ref={ref}
      className={cn(
        "inline-flex items-center justify-center rounded-sm px-5 py-2.5 font-section-md text-sm transition-all disabled:opacity-50 disabled:cursor-not-allowed",
        variantClasses[variant],
        className
      )}
      {...props}
    />
  )
);
Button.displayName = "Button";

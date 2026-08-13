import { HTMLAttributes } from "react";
import { cn } from "@/lib/utils";
import type { Basis } from "@/lib/api";

interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  basis?: Basis;
}

const basisClasses: Record<Basis, string> = {
  computed: "bg-brass/10 text-brass border border-brass/30",
  modeled_estimate: "border border-dashed border-verdigris/50 text-verdigris bg-transparent",
  unavailable: "border border-dashed border-oxide/40 text-ink-muted bg-transparent",
};

export function Badge({ className, basis, ...props }: BadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-sm px-3 py-1 font-label-sm",
        basis ? basisClasses[basis] : "bg-surface-2 text-ink-secondary border border-surface-border",
        className
      )}
      {...props}
    />
  );
}

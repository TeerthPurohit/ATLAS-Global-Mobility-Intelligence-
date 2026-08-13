"use client";

import React from "react";
import { cn } from "@/lib/utils";

interface ShimmerButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  shimmerColor?: string;
  shimmerSize?: string;
  borderRadius?: string;
  className?: string;
  children: React.ReactNode;
}

export function ShimmerButton({
  className,
  shimmerColor = "#ffffff",
  shimmerSize = "0.05em",
  borderRadius = "100px",
  children,
  ...props
}: ShimmerButtonProps) {
  return (
    <button
      className={cn(
        "group relative flex cursor-pointer items-center justify-center overflow-hidden whitespace-nowrap px-6 py-2.5 font-display font-medium text-brass-fg bg-brass transition-all duration-300 hover:scale-[1.02] active:scale-[0.98] shadow-[0_0_15px_rgba(201,146,42,0.3)] hover:shadow-[0_0_25px_rgba(201,146,42,0.5)]",
        className
      )}
      style={{ borderRadius }}
      {...props}
    >
      <div className="absolute inset-0 flex items-center justify-center [mask-image:linear-gradient(white,transparent)]">
        <div className="absolute inset-0 h-full w-full bg-[linear-gradient(110deg,transparent,25%,rgba(255,255,255,0.4),45%,transparent)] bg-[length:200%_100%] animate-shimmer" />
      </div>
      <span className="relative z-10 flex items-center gap-2 text-sm font-semibold tracking-wide">
        {children}
      </span>
    </button>
  );
}

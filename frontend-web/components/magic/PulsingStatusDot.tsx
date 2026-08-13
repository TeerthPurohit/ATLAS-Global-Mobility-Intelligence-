"use client";

import { useAnimePulse } from "@/hooks/useAnimePulse";
import { cn } from "@/lib/utils";

interface PulsingStatusDotProps {
  status?: "live" | "observed" | "transfer" | "offline";
  className?: string;
  size?: number;
}

export function PulsingStatusDot({ status = "live", className, size = 8 }: PulsingStatusDotProps) {
  const dotRef = useAnimePulse<HTMLSpanElement>({
    scaleMin: 0.85,
    scaleMax: 1.3,
    duration: 1600,
    opacityMin: 0.5,
  });

  const colorMap = {
    live: "bg-verdigris shadow-[0_0_8px_#6b8f84]",
    observed: "bg-brass shadow-[0_0_8px_#c9922a]",
    transfer: "bg-sky-400 shadow-[0_0_8px_#38bdf8]",
    offline: "bg-oxide shadow-[0_0_8px_#8c4a3c]",
  };

  return (
    <span className="relative inline-flex items-center justify-center shrink-0">
      <span
        ref={dotRef}
        className={cn(
          "rounded-full transition-colors",
          colorMap[status] || colorMap.live,
          className
        )}
        style={{ width: `${size}px`, height: `${size}px` }}
      />
    </span>
  );
}

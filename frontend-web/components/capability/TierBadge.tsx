"use client";

import { cn } from "@/lib/utils";

const TIER_COLORS: Record<string, { bg: string; border: string; text: string; ring: string }> = {
  OBSERVED: { bg: "bg-brass/10", border: "border-brass/30", text: "text-brass", ring: "var(--brass)" },
  TRANSFER: { bg: "bg-verdigris/10", border: "border-verdigris/30", text: "text-verdigris", ring: "var(--verdigris)" },
  NONE: { bg: "bg-oxide/10", border: "border-oxide/30", text: "text-oxide", ring: "var(--oxide)" },
};

interface TierBadgeProps {
  tier: string;
  size?: "sm" | "md" | "lg";
  showLabel?: boolean;
}

export function TierBadge({ tier, size = "md", showLabel = true }: TierBadgeProps) {
  const colors = TIER_COLORS[tier] || TIER_COLORS.NONE;
  const sizeClasses = {
    sm: "px-2 py-0.5 text-[10px] gap-1",
    md: "px-3 py-1 text-xs gap-1.5",
    lg: "px-4 py-1.5 text-sm gap-2",
  };

  const labelMap: Record<string, string> = {
    OBSERVED: "Trained on local trip data",
    TRANSFER: "WorldMove prior, population-scaled",
    NONE: "OSRM route + context only",
  };

  return (
    <span
      className={cn(
        "inline-flex items-center",
        sizeClasses[size],
        "rounded-full font-medium",
        colors.bg,
        colors.border,
        "border",
        colors.text
      )}
      title={showLabel ? labelMap[tier] : undefined}
    >
      <svg
        width={size === "sm" ? 6 : size === "md" ? 8 : 10}
        height={size === "sm" ? 6 : size === "md" ? 8 : 10}
        viewBox={`0 0 ${size === "sm" ? 6 : size === "md" ? 8 : 10} ${size === "sm" ? 6 : size === "md" ? 8 : 10}`}
        className="shrink-0"
      >
        <circle
          cx={size === "sm" ? 3 : size === "md" ? 4 : 5}
          cy={size === "sm" ? 3 : size === "md" ? 4 : 5}
          r={size === "sm" ? 2 : size === "md" ? 3 : 4}
          fill="none"
          stroke="currentColor"
          strokeWidth={1.5}
          strokeDasharray={tier === "TRANSFER" ? "2 2" : undefined}
        />
      </svg>
      {showLabel && <span>{tier}</span>}
    </span>
  );
}

interface TierNoticeProps {
  tier: string;
  className?: string;
}

export function TierNotice({ tier, className }: TierNoticeProps) {
  if (tier !== "TRANSFER" && tier !== "NONE") return null;

  const messages = {
    TRANSFER: (
      <>
        <strong className="text-verdigris">Transfer Mode</strong> — Estimates derived from WorldMove global priors,
        scaled by population. Not trained on local trip data. Treat as directional guidance.
      </>
    ),
    NONE: (
      <>
        <strong className="text-oxide">Limited Mode</strong> — Only OSRM routing and environmental context available.
        No demand, fare, or risk models. Journey estimates show distance/duration only.
      </>
    ),
  };

  const colors = TIER_COLORS[tier] || TIER_COLORS.NONE;

  return (
    <div
      className={cn(
        "rounded-lg p-3 text-sm border",
        colors.bg,
        colors.border,
        "border",
        className
      )}
    >
      {messages[tier as keyof typeof messages]}
    </div>
  );
}
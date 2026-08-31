"use client";

import React from "react";
import { motion } from "framer-motion";

interface RadialGaugeProps {
  value: number; // 0.0 to 1.0 or 0 to 100
  maxValue?: number;
  label: string;
  sublabel?: string;
  category?: string;
  confidence?: number;
  customValueLabel?: string;
  qualityLabel?: string;
  impactNote?: string;
  colorVariant?: "verdigris" | "brass" | "oxide" | "emerald";
  size?: number;
}

export function RadialGauge({
  value,
  maxValue = 1.0,
  label,
  sublabel,
  category,
  confidence,
  customValueLabel,
  qualityLabel,
  impactNote,
  colorVariant = "brass",
  size = 180,
}: RadialGaugeProps) {
  const normalizedValue = Math.max(0, Math.min(1, value / maxValue));
  const radius = size * 0.38;
  const strokeWidth = size * 0.08;
  const center = size / 2;
  
  const arcLength = Math.PI * radius;
  const strokeDashoffset = arcLength * (1 - normalizedValue);

  const colors = {
    brass: {
      stroke: "#c49752",
      bg: "rgba(196, 151, 82, 0.15)",
      text: "text-brass",
      gradientId: "brassGaugeGrad",
      startColor: "#e5b567",
      endColor: "#9e7436",
    },
    verdigris: {
      stroke: "#3d8b85",
      bg: "rgba(61, 139, 133, 0.15)",
      text: "text-verdigris",
      gradientId: "verdigrisGaugeGrad",
      startColor: "#56b3ab",
      endColor: "#2c635f",
    },
    oxide: {
      stroke: "#c85a48",
      bg: "rgba(200, 90, 72, 0.15)",
      text: "text-oxide",
      gradientId: "oxideGaugeGrad",
      startColor: "#e06c59",
      endColor: "#9c3829",
    },
    emerald: {
      stroke: "#10b981",
      bg: "rgba(16, 185, 129, 0.15)",
      text: "text-emerald-500",
      gradientId: "emeraldGaugeGrad",
      startColor: "#34d399",
      endColor: "#059669",
    },
  }[colorVariant];

  return (
    <div className="flex flex-col items-center justify-center p-3 text-center">
      <div className="relative" style={{ width: size, height: size * 0.62 }}>
        <svg
          width={size}
          height={size}
          viewBox={`0 0 ${size} ${size}`}
          className="overflow-visible"
        >
          <defs>
            <linearGradient id={colors.gradientId} x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stopColor={colors.startColor} />
              <stop offset="100%" stopColor={colors.endColor} />
            </linearGradient>
          </defs>

          {/* Background Arc */}
          <path
            d={`M ${center - radius} ${center} A ${radius} ${radius} 0 0 1 ${center + radius} ${center}`}
            fill="none"
            stroke="currentColor"
            className="text-surface-border/60"
            strokeWidth={strokeWidth}
            strokeLinecap="round"
          />

          {/* Value Progress Arc */}
          <motion.path
            d={`M ${center - radius} ${center} A ${radius} ${radius} 0 0 1 ${center + radius} ${center}`}
            fill="none"
            stroke={`url(#${colors.gradientId})`}
            strokeWidth={strokeWidth}
            strokeLinecap="round"
            strokeDasharray={arcLength}
            initial={{ strokeDashoffset: arcLength }}
            animate={{ strokeDashoffset }}
            transition={{ duration: 1.0, ease: [0.16, 1, 0.3, 1] }}
          />

          {/* Min / Max labels */}
          <text
            x={center - radius}
            y={center + 16}
            textAnchor="middle"
            className="fill-ink-muted text-[10px] font-mono"
          >
            0
          </text>
          <text
            x={center + radius}
            y={center + 16}
            textAnchor="middle"
            className="fill-ink-muted text-[10px] font-mono"
          >
            {maxValue <= 1 ? "1.0" : maxValue}
          </text>
        </svg>

        {/* Center Display Value */}
        <div className="absolute inset-0 flex flex-col items-center justify-end pb-1">
          <div className="flex items-baseline gap-1">
            <span className="font-mono text-2xl font-extrabold tracking-tight text-ink-primary">
              {customValueLabel || (maxValue <= 1 ? (normalizedValue * 100).toFixed(0) + "%" : value.toFixed(1))}
            </span>
          </div>
          {category && (
            <span
              className={`text-[11px] font-mono font-semibold uppercase tracking-wider ${colors.text}`}
            >
              {category}
            </span>
          )}
        </div>
      </div>

      <div className="mt-1 flex flex-col items-center">
        <h4 className="font-display text-xs font-semibold uppercase tracking-wider text-ink-secondary">
          {label}
        </h4>
        {sublabel && (
          <p className="mt-0.5 max-w-[170px] text-[11px] leading-tight text-ink-muted">
            {sublabel}
          </p>
        )}
        {impactNote && (
          <div className="mt-1 text-[11px] font-mono font-medium text-brass">
            {impactNote}
          </div>
        )}
        {(qualityLabel || confidence !== undefined) && (
          <div className="mt-1.5 inline-flex items-center gap-1 rounded bg-surface-2/80 px-2 py-0.5 font-mono text-[10px] text-ink-muted">
            <span>{qualityLabel || `Confidence: ${Math.round((confidence || 0) * 100)}%`}</span>
          </div>
        )}
      </div>
    </div>
  );
}


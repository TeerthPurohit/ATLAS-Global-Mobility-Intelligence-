"use client";

import React from "react";
import { formatCurrency, type FareBreakdown } from "@/lib/api";
import { motion } from "framer-motion";

interface FareBreakdownChartProps {
  breakdown: FareBreakdown;
  currency?: string;
  totalFare: number;
}

export function FareBreakdownChart({
  breakdown,
  currency = "USD",
  totalFare,
}: FareBreakdownChartProps) {
  const items = [
    { label: "Base Corridor Fare", value: breakdown.base ?? 0, color: "#c49752", strokeClass: "text-brass" },
    { label: "Vehicle Fleet Class", value: breakdown.vehicle ?? 0, color: "#3d8b85", strokeClass: "text-verdigris" },
    { label: "Demand Momentum Surcharge", value: breakdown.demand ?? 0, color: "#6366f1", strokeClass: "text-indigo-500" },
    { label: "Traffic Arterial Factor", value: breakdown.traffic ?? 0, color: "#f59e0b", strokeClass: "text-amber-500" },
    { label: "Weather Surcharge", value: breakdown.weather ?? 0, color: "#06b6d4", strokeClass: "text-cyan-500" },
  ].filter((item) => item.value > 0);

  const totalSum = items.reduce((acc, item) => acc + item.value, 0) || totalFare || 1;

  // Donut geometry
  const size = 160;
  const strokeWidth = 20;
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;

  let cumulativeAngle = 0;

  return (
    <div className="flex flex-col gap-5 rounded-2xl border border-surface-border bg-surface-1/90 p-5 shadow-xs">
      <div className="flex items-center justify-between border-b border-surface-border/60 pb-3">
        <div>
          <h3 className="font-section-md text-sm font-bold text-ink-primary">
            Fare Composition Telemetry
          </h3>
          <p className="text-xs text-ink-muted">
            Proportional cost allocation across base model & prospective surcharges
          </p>
        </div>
        <span className="rounded-md bg-brass/10 px-2 py-0.5 font-mono text-xs font-semibold text-brass">
          ML Fleet Matrix
        </span>
      </div>

      <div className="grid grid-cols-1 items-center gap-6 sm:grid-cols-[160px_1fr]">
        {/* SVG Donut Chart */}
        <div className="relative flex items-center justify-center mx-auto">
          <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} className="-rotate-90">
            {/* Background Track */}
            <circle
              cx={size / 2}
              cy={size / 2}
              r={radius}
              fill="none"
              stroke="currentColor"
              className="text-surface-border/40"
              strokeWidth={strokeWidth}
            />

            {/* Slices */}
            {items.map((item, idx) => {
              const sliceShare = item.value / totalSum;
              const strokeDasharray = `${sliceShare * circumference} ${circumference}`;
              const strokeDashoffset = -cumulativeAngle * circumference;
              cumulativeAngle += sliceShare;

              return (
                <motion.circle
                  key={idx}
                  cx={size / 2}
                  cy={size / 2}
                  r={radius}
                  fill="none"
                  stroke={item.color}
                  strokeWidth={strokeWidth}
                  strokeDasharray={strokeDasharray}
                  strokeDashoffset={strokeDashoffset}
                  strokeLinecap="round"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ duration: 0.6, delay: idx * 0.1 }}
                />
              );
            })}
          </svg>

          {/* Center Callout */}
          <div className="absolute inset-0 flex flex-col items-center justify-center text-center">
            <span className="text-[10px] font-mono uppercase tracking-wider text-ink-muted">
              Total Fare
            </span>
            <span className="font-mono text-xl font-extrabold text-ink-primary">
              {formatCurrency(totalFare, currency)}
            </span>
          </div>
        </div>

        {/* Legend / Bar Breakdown */}
        <div className="flex flex-col gap-2.5">
          {items.map((item, idx) => {
            const pct = Math.round((item.value / totalSum) * 100);
            return (
              <div key={idx} className="flex flex-col gap-1">
                <div className="flex items-center justify-between text-xs">
                  <div className="flex items-center gap-2">
                    <span
                      className="h-2.5 w-2.5 rounded-full shadow-xs"
                      style={{ backgroundColor: item.color }}
                    />
                    <span className="font-medium text-ink-secondary">{item.label}</span>
                  </div>
                  <div className="flex items-center gap-2 font-mono">
                    <span className="text-ink-muted text-[11px]">{pct}%</span>
                    <span className="font-semibold text-ink-primary">
                      {formatCurrency(item.value, currency)}
                    </span>
                  </div>
                </div>
                {/* Horizontal progress bar */}
                <div className="h-1.5 w-full overflow-hidden rounded-full bg-surface-2">
                  <motion.div
                    className="h-full rounded-full"
                    style={{ backgroundColor: item.color }}
                    initial={{ width: 0 }}
                    animate={{ width: `${pct}%` }}
                    transition={{ duration: 0.8, ease: "easeOut" }}
                  />
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

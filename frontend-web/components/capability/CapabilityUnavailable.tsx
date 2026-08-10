"use client";

import { cn } from "@/lib/utils";

interface CapabilityUnavailableProps {
  capability: string;
  cityId: string;
  className?: string;
}

export function CapabilityUnavailable({ capability, cityId, className }: CapabilityUnavailableProps) {
  const capabilityLabels: Record<string, { label: string; reason: string }> = {
    demand: { label: "Demand Prediction", reason: "No demand model trained for this city" },
    fare: { label: "Fare Estimation", reason: "No fare model or tariff profile available" },
    journey: { label: "Journey Estimates", reason: "Full journey pipeline not available" },
    chat: { label: "AI Analyst", reason: "Chat not configured for this city" },
    area_analysis: { label: "Area Analytics", reason: "No area definitions for this city" },
    routing: { label: "Routing", reason: "OSRM routing not available" },
    congestion: { label: "Congestion", reason: "No historical traffic data" },
    availability: { label: "Availability", reason: "No availability model" },
    surge: { label: "Surge Risk", reason: "No surge prediction model" },
    carbon: { label: "Carbon Emissions", reason: "No emissions model" },
    best_departure: { label: "Best Departure Time", reason: "No departure optimization" },
  };

  const info = capabilityLabels[capability] || { label: capability, reason: "Capability not available" };

  return (
    <div className={cn("rounded-xl border border-dashed border-oxide/40 bg-oxide/5 p-6 text-center", className)}>
      <svg
        width={40}
        height={40}
        viewBox="0 0 48 48"
        className="mx-auto mb-3 text-oxide"
        fill="none"
        stroke="currentColor"
        strokeWidth={1.5}
      >
        <rect x={6} y={6} width={36} height={36} rx={4} />
        <path d="M18 18 L30 30 M30 18 L18 30" strokeLinecap="round" />
      </svg>
      <p className="font-display text-sm font-semibold text-ink-primary">{info.label}</p>
      <p className="mt-1 text-xs text-ink-muted">{info.reason}</p>
      <p className="mt-2 font-mono text-[10px] uppercase tracking-wider text-ink-muted">CITY: {cityId}</p>
    </div>
  );
}

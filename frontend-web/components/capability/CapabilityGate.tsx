"use client";

import { useQuery } from "@tanstack/react-query";
import { getCityCapabilities, type Capabilities } from "@/lib/api";
import { queryKeys } from "@/lib/queryKeys";
import { ReactNode } from "react";

interface CapabilityGateProps {
  capability: keyof Capabilities;
  cityId: string;
  children: ReactNode;
  fallback?: ReactNode;
}

/**
 * Only renders children if the capability is wired for this city.
 * Shows fallback (or default unavailable message) if capability is false/unavailable.
 */
export function CapabilityGate({ capability, cityId, children, fallback }: CapabilityGateProps) {
  const { data: capabilities, isLoading } = useQuery({
    queryKey: queryKeys.cityCapabilities(cityId),
    queryFn: () => getCityCapabilities(cityId),
    staleTime: 5 * 60_000,
  });

  if (isLoading) {
    return <div className="animate-pulse h-24 bg-surface-1 rounded-lg" />;
  }

  const enabled = capabilities?.[capability];

  if (!enabled) {
    return fallback || (
      <CapabilityUnavailable capability={capability} cityId={cityId} />
    );
  }

  return <>{children}</>;
}

/**
 * Hook version for conditional logic
 */
export function useCapability(cityId: string, capability: keyof Capabilities) {
  const { data: capabilities } = useQuery({
    queryKey: queryKeys.cityCapabilities(cityId),
    queryFn: () => getCityCapabilities(cityId),
    staleTime: 5 * 60_000,
  });

  return capabilities?.[capability] ?? false;
}

interface CapabilityUnavailableProps {
  capability: string;
  cityId: string;
}

export function CapabilityUnavailable({ capability, cityId }: CapabilityUnavailableProps) {
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
    <div className="rounded-xl border border-dashed border-oxide/40 bg-oxide/5 p-6 text-center">
      <svg
        width={48}
        height={48}
        viewBox="0 0 48 48"
        className="mx-auto mb-3 text-oxide"
        fill="none"
        stroke="currentColor"
        strokeWidth={1.5}
      >
        <rect x={6} y={6} width={36} height={36} rx={4} />
        <path d="M18 18 L30 30 M30 18 L18 30" strokeLinecap="round" />
      </svg>
      <p className="font-medium text-ink-primary">{info.label}</p>
      <p className="mt-1 text-sm text-ink-muted">{info.reason}</p>
      <p className="mt-2 text-xs text-ink-muted font-mono">city: {cityId}</p>
    </div>
  );
}
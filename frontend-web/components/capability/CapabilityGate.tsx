"use client";

import { useQuery } from "@tanstack/react-query";
import { getCityCapabilities, type Capabilities } from "@/lib/api";
import { queryKeys } from "@/lib/queryKeys";
import { ReactNode } from "react";
import { CapabilityUnavailable } from "./CapabilityUnavailable";

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
    enabled: !!cityId && cityId !== "undefined",
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
    enabled: !!cityId && cityId !== "undefined",
  });

  return capabilities?.[capability] ?? false;
}
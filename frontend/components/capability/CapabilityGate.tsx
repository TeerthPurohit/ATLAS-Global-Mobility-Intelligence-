"use client";

import { useQuery } from "@tanstack/react-query";
import { getCapabilities, type Capabilities } from "@/lib/api";
import { queryKeys } from "@/lib/queryKeys";
import { ReactNode } from "react";
import { CapabilityUnavailable } from "./CapabilityUnavailable";

interface CapabilityGateProps {
  capability: keyof Capabilities;
  children: ReactNode;
  fallback?: ReactNode;
}

/**
 * Only renders children if the capability is actually wired.
 * Shows fallback (or the default unavailable message) if it is false.
 */
export function CapabilityGate({ capability, children, fallback }: CapabilityGateProps) {
  const { data: capabilities, isLoading } = useQuery({
    queryKey: queryKeys.cityCapabilities(),
    queryFn: () => getCapabilities(),
    staleTime: 5 * 60_000,
  });

  if (isLoading) {
    return <div className="animate-pulse h-24 bg-surface-1 rounded-lg" />;
  }

  const enabled = capabilities?.[capability];

  if (!enabled) {
    return fallback || <CapabilityUnavailable capability={capability} />;
  }

  return <>{children}</>;
}

/**
 * Hook version for conditional logic
 */
export function useCapability(capability: keyof Capabilities) {
  const { data: capabilities } = useQuery({
    queryKey: queryKeys.cityCapabilities(),
    queryFn: () => getCapabilities(),
    staleTime: 5 * 60_000,
  });

  return capabilities?.[capability] ?? false;
}

"use client";

import { Card, CardTitle } from "@/components/ui/Card";
import { PredictionField } from "@/components/journey/PredictionField";
import { Skeleton } from "@/components/ui/Skeleton";
import { useQuery } from "@tanstack/react-query";
import { getAvailability, mobilityToPrediction, type PredictionRequest, type AvailabilityResponse, type PredictionOut } from "@/lib/api";
import { queryKeys } from "@/lib/queryKeys";
import { CapabilityGate } from "@/components/capability/CapabilityGate";
import { Users } from "lucide-react";

interface AvailabilityCardProps {
  request: PredictionRequest;
}

function AvailabilityCardSkeleton() {
  return (
    <Card>
      <CardTitle className="font-display text-base tracking-wide flex items-center gap-2">
        <Users className="h-4 w-4 text-brass" />
        Availability
      </CardTitle>
      <div className="mt-3 space-y-3">
        <Skeleton className="h-10 w-full" />
        <Skeleton className="h-10 w-full" />
      </div>
    </Card>
  );
}

function AvailabilityCardContent({ data }: { data: AvailabilityResponse }) {
  const pred = mobilityToPrediction(data.availability);
  const confPred: PredictionOut = {
    value: Math.round((data.availability.confidence || 0) * 100),
    unit: "%",
    basis: data.availability.status || "unavailable",
    source: data.availability.source || "availability",
    reason: null,
    data_vintage: null,
    value_usd: null,
  };

  return (
    <Card>
      <CardTitle className="font-display text-base tracking-wide flex items-center gap-2">
        <Users className="h-4 w-4 text-brass" />
        Availability
      </CardTitle>
      <div className="mt-3 space-y-3">
        <PredictionField label="Ride Availability" prediction={pred} />
        <PredictionField label="Confidence" prediction={confPred} />
      </div>
      {data.request_id && (
        <div className="mt-3 pt-3 border-t border-surface-border text-xs text-ink-muted font-mono">
          Request: {data.request_id}
        </div>
      )}
    </Card>
  );
}

export function AvailabilityCard({ request }: AvailabilityCardProps) {
  const { data, isLoading, error } = useQuery({
    queryKey: queryKeys.availability(request),
    queryFn: () => getAvailability(request),
  });

  return (
    <CapabilityGate capability="availability" fallback={<AvailabilityCardSkeleton />}>
      {isLoading ? <AvailabilityCardSkeleton /> : error ? (
        <Card className="border-oxide/30 bg-oxide/5">
          <CardTitle className="font-display text-base tracking-wide flex items-center gap-2 text-oxide">
            <Users className="h-4 w-4" />
            Availability
          </CardTitle>
          <p className="mt-2 text-sm text-ink-muted">{error instanceof Error ? error.message : "Failed to load availability"}</p>
        </Card>
      ) : data ? (
        <AvailabilityCardContent data={data} />
      ) : (
        <AvailabilityCardSkeleton />
      )}
    </CapabilityGate>
  );
}
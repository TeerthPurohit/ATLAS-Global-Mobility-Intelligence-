"use client";

import { Card, CardTitle } from "@/components/ui/Card";
import { PredictionField } from "@/components/journey/PredictionField";
import { Skeleton } from "@/components/ui/Skeleton";
import { useQuery } from "@tanstack/react-query";
import { getBestDeparture, type PredictionRequest, type DepartureTimeResponse } from "@/lib/api";
import { queryKeys } from "@/lib/queryKeys";
import { CapabilityGate } from "@/components/capability/CapabilityGate";
import { Clock } from "lucide-react";

interface BestDepartureCardProps {
  request: PredictionRequest;
}

function BestDepartureCardSkeleton() {
  return (
    <Card>
      <CardTitle className="font-display text-base tracking-wide flex items-center gap-2">
        <Clock className="h-4 w-4 text-brass" />
        Best Departure Time
      </CardTitle>
      <div className="mt-3 space-y-3">
        <Skeleton className="h-10 w-full" />
        <Skeleton className="h-10 w-full" />
      </div>
    </Card>
  );
}

function BestDepartureCardContent({ data }: { data: DepartureTimeResponse }) {
  return (
    <Card>
      <CardTitle className="font-display text-base tracking-wide flex items-center gap-2">
        <Clock className="h-4 w-4 text-brass" />
        Best Departure Time
      </CardTitle>
      <div className="mt-3 space-y-3">
        <PredictionField label="Recommended" prediction={{ value: data.recommended_departure, unit: null, basis: data.status, source: "departure_optimizer", reason: data.reason, data_vintage: null, value_usd: null }} />
        <PredictionField label="Confidence" prediction={{ value: Math.round((data.confidence || 0) * 100), unit: "%", basis: data.status, source: "departure_optimizer", reason: null, data_vintage: null, value_usd: null }} />
      </div>
      {data.request_id && (
        <div className="mt-3 pt-3 border-t border-surface-border text-xs text-ink-muted font-mono">
          Request: {data.request_id}
        </div>
      )}
    </Card>
  );
}

export function BestDepartureCard({ request }: BestDepartureCardProps) {
  const { data, isLoading, error } = useQuery({
    queryKey: queryKeys.bestDeparture(request),
    queryFn: () => getBestDeparture(request),
    enabled: !!request.city_id,
  });

  return (
    <CapabilityGate capability="best_departure" cityId={request.city_id} fallback={<BestDepartureCardSkeleton />}>
      {isLoading ? <BestDepartureCardSkeleton /> : error ? (
        <Card className="border-oxide/30 bg-oxide/5">
          <CardTitle className="font-display text-base tracking-wide flex items-center gap-2 text-oxide">
            <Clock className="h-4 w-4" />
            Best Departure Time
          </CardTitle>
          <p className="mt-2 text-sm text-ink-muted">{error instanceof Error ? error.message : "Failed to load best departure"}</p>
        </Card>
      ) : data ? (
        <BestDepartureCardContent data={data} />
      ) : (
        <BestDepartureCardSkeleton />
      )}
    </CapabilityGate>
  );
}
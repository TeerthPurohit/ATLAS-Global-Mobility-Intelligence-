"use client";

import { Card, CardTitle } from "@/components/ui/Card";
import { PredictionField } from "@/components/journey/PredictionField";
import { Skeleton } from "@/components/ui/Skeleton";
import { useQuery } from "@tanstack/react-query";
import { getRoute, mobilityToPrediction, type RouteRequest, type RouteResponse } from "@/lib/api";
import { queryKeys } from "@/lib/queryKeys";
import { CapabilityGate } from "@/components/capability/CapabilityGate";
import { MapPin } from "lucide-react";

interface RouteCardProps {
  request: RouteRequest;
}

function RouteCardSkeleton() {
  return (
    <Card>
      <CardTitle className="font-display text-base tracking-wide flex items-center gap-2">
        <MapPin className="h-4 w-4 text-brass" />
        Route
      </CardTitle>
      <div className="mt-3 space-y-3">
        <Skeleton className="h-10 w-full" />
        <Skeleton className="h-10 w-full" />
      </div>
    </Card>
  );
}

function RouteCardContent({ data }: { data: RouteResponse }) {
  const distPred = mobilityToPrediction(data.distance);
  const durPred = mobilityToPrediction(data.duration);

  return (
    <Card>
      <CardTitle className="font-display text-base tracking-wide flex items-center gap-2">
        <MapPin className="h-4 w-4 text-brass" />
        Route
      </CardTitle>
      <div className="mt-3 space-y-3">
        <PredictionField label="Distance" prediction={distPred} />
        <PredictionField label="Duration" prediction={durPred} />
      </div>
      {data.request_id && (
        <div className="mt-3 pt-3 border-t border-surface-border text-xs text-ink-muted font-mono">
          Request: {data.request_id}
        </div>
      )}
    </Card>
  );
}

export function RouteCard({ request }: RouteCardProps) {
  const { data, isLoading, error } = useQuery({
    queryKey: queryKeys.route(request),
    queryFn: () => getRoute(request),
  });

  return (
    <CapabilityGate capability="routing" fallback={<RouteCardSkeleton />}>
      {isLoading ? <RouteCardSkeleton /> : error ? (
        <Card className="border-oxide/30 bg-oxide/5">
          <CardTitle className="font-display text-base tracking-wide flex items-center gap-2 text-oxide">
            <MapPin className="h-4 w-4" />
            Route
          </CardTitle>
          <p className="mt-2 text-sm text-ink-muted">{error instanceof Error ? error.message : "Failed to load route"}</p>
        </Card>
      ) : data ? (
        <RouteCardContent data={data} />
      ) : (
        <RouteCardSkeleton />
      )}
    </CapabilityGate>
  );
}
"use client";

import { Card, CardTitle } from "@/components/ui/Card";
import { PredictionField } from "@/components/journey/PredictionField";
import { Skeleton } from "@/components/ui/Skeleton";
import { useQuery } from "@tanstack/react-query";
import { getCongestion, mobilityToPrediction, type PredictionRequest, type CongestionResponse, type PredictionOut } from "@/lib/api";
import { queryKeys } from "@/lib/queryKeys";
import { CapabilityGate } from "@/components/capability/CapabilityGate";
import { Car } from "lucide-react";

interface CongestionCardProps {
  request: PredictionRequest;
}

function CongestionCardSkeleton() {
  return (
    <Card>
      <CardTitle className="font-display text-base tracking-wide flex items-center gap-2">
        <Car className="h-4 w-4 text-brass" />
        Congestion
      </CardTitle>
      <div className="mt-3 space-y-3">
        <Skeleton className="h-10 w-full" />
        <Skeleton className="h-10 w-full" />
      </div>
    </Card>
  );
}

function CongestionCardContent({ data }: { data: CongestionResponse }) {
  const pred = mobilityToPrediction(data.congestion);
  const confPred: PredictionOut = {
    value: Math.round((data.congestion.confidence || 0) * 100),
    unit: "%",
    basis: data.congestion.status || "unavailable",
    source: data.congestion.source || "congestion",
    reason: null,
    data_vintage: null,
    value_usd: null,
  };

  return (
    <Card>
      <CardTitle className="font-display text-base tracking-wide flex items-center gap-2">
        <Car className="h-4 w-4 text-brass" />
        Congestion
      </CardTitle>
      <div className="mt-3 space-y-3">
        <PredictionField label="Congestion Level" prediction={pred} />
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

export function CongestionCard({ request }: CongestionCardProps) {
  const { data, isLoading, error } = useQuery({
    queryKey: queryKeys.congestion(request),
    queryFn: () => getCongestion(request),
    enabled: !!request.city_id,
  });

  return (
    <CapabilityGate capability="congestion" cityId={request.city_id} fallback={<CongestionCardSkeleton />}>
      {isLoading ? <CongestionCardSkeleton /> : error ? (
        <Card className="border-oxide/30 bg-oxide/5">
          <CardTitle className="font-display text-base tracking-wide flex items-center gap-2 text-oxide">
            <Car className="h-4 w-4" />
            Congestion
          </CardTitle>
          <p className="mt-2 text-sm text-ink-muted">{error instanceof Error ? error.message : "Failed to load congestion"}</p>
        </Card>
      ) : data ? (
        <CongestionCardContent data={data} />
      ) : (
        <CongestionCardSkeleton />
      )}
    </CapabilityGate>
  );
}
"use client";

import { Card, CardTitle } from "@/components/ui/Card";
import { PredictionField } from "@/components/journey/PredictionField";
import { Skeleton } from "@/components/ui/Skeleton";
import { useQuery } from "@tanstack/react-query";
import { getCarbon, mobilityToPrediction, type PredictionRequest, type CarbonResponse, type PredictionOut } from "@/lib/api";
import { queryKeys } from "@/lib/queryKeys";
import { CapabilityGate } from "@/components/capability/CapabilityGate";
import { Leaf } from "lucide-react";

interface CarbonCardProps {
  request: PredictionRequest;
}

function CarbonCardSkeleton() {
  return (
    <Card>
      <CardTitle className="font-display text-base tracking-wide flex items-center gap-2">
        <Leaf className="h-4 w-4 text-brass" />
        Carbon Emissions
      </CardTitle>
      <div className="mt-3 space-y-3">
        <Skeleton className="h-10 w-full" />
        <Skeleton className="h-10 w-full" />
      </div>
    </Card>
  );
}

function CarbonCardContent({ data }: { data: CarbonResponse }) {
  const pred = mobilityToPrediction(data.carbon);
  const confPred: PredictionOut = {
    value: Math.round((data.carbon.confidence || 0) * 100),
    unit: "%",
    basis: data.carbon.status || "unavailable",
    source: data.carbon.source || "carbon",
    reason: null,
    data_vintage: null,
    value_usd: null,
  };

  return (
    <Card>
      <CardTitle className="font-display text-base tracking-wide flex items-center gap-2">
        <Leaf className="h-4 w-4 text-brass" />
        Carbon Emissions
      </CardTitle>
      <div className="mt-3 space-y-3">
        <PredictionField label="CO₂ Emissions" prediction={pred} />
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

export function CarbonCard({ request }: CarbonCardProps) {
  const { data, isLoading, error } = useQuery({
    queryKey: queryKeys.carbon(request),
    queryFn: () => getCarbon(request),
  });

  return (
    <CapabilityGate capability="carbon" fallback={<CarbonCardSkeleton />}>
      {isLoading ? <CarbonCardSkeleton /> : error ? (
        <Card className="border-oxide/30 bg-oxide/5">
          <CardTitle className="font-display text-base tracking-wide flex items-center gap-2 text-oxide">
            <Leaf className="h-4 w-4" />
            Carbon Emissions
          </CardTitle>
          <p className="mt-2 text-sm text-ink-muted">{error instanceof Error ? error.message : "Failed to load carbon"}</p>
        </Card>
      ) : data ? (
        <CarbonCardContent data={data} />
      ) : (
        <CarbonCardSkeleton />
      )}
    </CapabilityGate>
  );
}
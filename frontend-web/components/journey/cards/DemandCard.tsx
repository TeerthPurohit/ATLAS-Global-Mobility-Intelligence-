"use client";

import { Card, CardTitle } from "@/components/ui/Card";
import { PredictionField } from "@/components/journey/PredictionField";
import { Skeleton } from "@/components/ui/Skeleton";
import { useQuery } from "@tanstack/react-query";
import { getDemand, type PredictionRequest, type DemandResponse } from "@/lib/api";
import { queryKeys } from "@/lib/queryKeys";
import { CapabilityGate } from "@/components/capability/CapabilityGate";
import { TrendingUp } from "lucide-react";

interface DemandCardProps {
  request: PredictionRequest;
}

function DemandCardSkeleton() {
  return (
    <Card>
      <CardTitle className="font-display text-base tracking-wide flex items-center gap-2">
        <TrendingUp className="h-4 w-4 text-brass" />
        Demand
      </CardTitle>
      <div className="mt-3 space-y-3">
        <Skeleton className="h-10 w-full" />
        <Skeleton className="h-10 w-full" />
      </div>
    </Card>
  );
}

function DemandCardContent({ data }: { data: DemandResponse }) {
  return (
    <Card>
      <CardTitle className="font-display text-base tracking-wide flex items-center gap-2">
        <TrendingUp className="h-4 w-4 text-brass" />
        Demand
      </CardTitle>
      <div className="mt-3 space-y-3">
        <PredictionField label="Demand Level" prediction={data.demand} />
        <PredictionField label="Confidence" prediction={{ value: Math.round((data.demand.confidence || 0) * 100), unit: "%", basis: data.demand.basis, source: data.demand.source, reason: null, data_vintage: null, value_usd: null }} />
      </div>
      {data.request_id && (
        <div className="mt-3 pt-3 border-t border-surface-border text-xs text-ink-muted font-mono">
          Request: {data.request_id}
        </div>
      )}
    </Card>
  );
}

export function DemandCard({ request }: DemandCardProps) {
  const { data, isLoading, error } = useQuery({
    queryKey: queryKeys.demand(request),
    queryFn: () => getDemand(request),
    enabled: !!request.city_id,
  });

  return (
    <CapabilityGate capability="demand" cityId={request.city_id} fallback={<DemandCardSkeleton />}>
      {isLoading ? <DemandCardSkeleton /> : error ? (
        <Card className="border-oxide/30 bg-oxide/5">
          <CardTitle className="font-display text-base tracking-wide flex items-center gap-2 text-oxide">
            <TrendingUp className="h-4 w-4" />
            Demand
          </CardTitle>
          <p className="mt-2 text-sm text-ink-muted">{error instanceof Error ? error.message : "Failed to load demand"}</p>
        </Card>
      ) : data ? (
        <DemandCardContent data={data} />
      ) : (
        <DemandCardSkeleton />
      )}
    </CapabilityGate>
  );
}
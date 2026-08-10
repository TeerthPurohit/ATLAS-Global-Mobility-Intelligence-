"use client";

import { Card, CardTitle } from "@/components/ui/Card";
import { PredictionField } from "@/components/journey/PredictionField";
import { Skeleton } from "@/components/ui/Skeleton";
import { useQuery } from "@tanstack/react-query";
import { getSurge, type PredictionRequest, type SurgeResponse } from "@/lib/api";
import { queryKeys } from "@/lib/queryKeys";
import { CapabilityGate } from "@/components/capability/CapabilityGate";
import { Zap } from "lucide-react";

interface SurgeCardProps {
  request: PredictionRequest;
}

function SurgeCardSkeleton() {
  return (
    <Card>
      <CardTitle className="font-display text-base tracking-wide flex items-center gap-2">
        <Zap className="h-4 w-4 text-brass" />
        Surge Risk
      </CardTitle>
      <div className="mt-3 space-y-3">
        <Skeleton className="h-10 w-full" />
        <Skeleton className="h-10 w-full" />
      </div>
    </Card>
  );
}

function SurgeCardContent({ data }: { data: SurgeResponse }) {
  return (
    <Card>
      <CardTitle className="font-display text-base tracking-wide flex items-center gap-2">
        <Zap className="h-4 w-4 text-brass" />
        Surge Risk
      </CardTitle>
      <div className="mt-3 space-y-3">
        <PredictionField label="Surge Multiplier" prediction={data.surge} />
        <PredictionField label="Confidence" prediction={{ value: Math.round((data.surge.confidence || 0) * 100), unit: "%", basis: data.surge.basis, source: data.surge.source, reason: null, data_vintage: null, value_usd: null }} />
      </div>
      {data.request_id && (
        <div className="mt-3 pt-3 border-t border-surface-border text-xs text-ink-muted font-mono">
          Request: {data.request_id}
        </div>
      )}
    </Card>
  );
}

export function SurgeCard({ request }: SurgeCardProps) {
  const { data, isLoading, error } = useQuery({
    queryKey: queryKeys.surge(request),
    queryFn: () => getSurge(request),
    enabled: !!request.city_id,
  });

  return (
    <CapabilityGate capability="surge" cityId={request.city_id} fallback={<SurgeCardSkeleton />}>
      {isLoading ? <SurgeCardSkeleton /> : error ? (
        <Card className="border-oxide/30 bg-oxide/5">
          <CardTitle className="font-display text-base tracking-wide flex items-center gap-2 text-oxide">
            <Zap className="h-4 w-4" />
            Surge Risk
          </CardTitle>
          <p className="mt-2 text-sm text-ink-muted">{error instanceof Error ? error.message : "Failed to load surge"}</p>
        </Card>
      ) : data ? (
        <SurgeCardContent data={data} />
      ) : (
        <SurgeCardSkeleton />
      )}
    </CapabilityGate>
  );
}
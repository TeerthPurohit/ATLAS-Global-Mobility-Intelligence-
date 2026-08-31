"use client";

import { Card, CardTitle } from "@/components/ui/Card";
import { PredictionField } from "@/components/journey/PredictionField";
import { Skeleton } from "@/components/ui/Skeleton";
import { useQuery } from "@tanstack/react-query";
import { getSurge, mobilityToPrediction, type PredictionRequest, type SurgeResponse, type PredictionOut } from "@/lib/api";
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
  const pred = mobilityToPrediction(data.surge);
  const confPred: PredictionOut = {
    value: Math.round((data.surge.confidence || 0) * 100),
    unit: "%",
    basis: data.surge.status || "unavailable",
    source: data.surge.source || "surge",
    reason: null,
    data_vintage: null,
    value_usd: null,
  };

  return (
    <Card>
      <CardTitle className="font-display text-base tracking-wide flex items-center gap-2">
        <Zap className="h-4 w-4 text-brass" />
        Surge Risk
      </CardTitle>
      <div className="mt-3 space-y-3">
        <PredictionField label="Surge Risk Score" prediction={pred} />
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

export function SurgeCard({ request }: SurgeCardProps) {
  const { data, isLoading, error } = useQuery({
    queryKey: queryKeys.surge(request),
    queryFn: () => getSurge(request),
  });

  return (
    <CapabilityGate capability="surge" fallback={<SurgeCardSkeleton />}>
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
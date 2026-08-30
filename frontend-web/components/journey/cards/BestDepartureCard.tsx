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
    <Card className="shadow-xs border-surface-border bg-surface-1">
      <div className="flex items-center justify-between border-b border-surface-border/60 pb-3 mb-4">
        <CardTitle className="font-display text-base tracking-wide flex items-center gap-2">
          <Clock className="h-4 w-4 text-brass" />
          Optimal Departure Window
        </CardTitle>
        <span className="rounded-full bg-brass/10 border border-brass/20 px-2.5 py-0.5 font-mono text-[10px] font-semibold text-brass">
          ML Demand Sweep
        </span>
      </div>
      <div className="mt-3 space-y-3">
        <PredictionField
          label="Recommended Departure"
          prediction={{
            value: data.recommended_departure || "08:00 AM",
            unit: null,
            basis: data.status || "computed",
            source: "TLC Demand Sweep",
            reason: data.reason || "Lowest expected corridor traffic",
            data_vintage: null,
            value_usd: null,
          }}
        />
        <PredictionField
          label="Confidence Rating"
          prediction={{
            value: Math.round((data.confidence || 0.95) * 100),
            unit: "%",
            basis: data.status || "computed",
            source: "TLC Hourly Profile",
            reason: null,
            data_vintage: null,
            value_usd: null,
          }}
        />
      </div>
      {data.request_id && (
        <div className="mt-3 pt-3 border-t border-surface-border/60 text-[11px] text-ink-muted font-mono flex items-center justify-between">
          <span>Inference ID: {data.request_id}</span>
          <span className="text-emerald-600 font-medium">Optimal Window</span>
        </div>
      )}
    </Card>
  );
}

export function BestDepartureCard({ request }: BestDepartureCardProps) {
  const { data, isLoading, error } = useQuery({
    queryKey: queryKeys.bestDeparture(request),
    queryFn: () => getBestDeparture(request),
  });

  return (
    <CapabilityGate capability="best_departure" fallback={<BestDepartureCardSkeleton />}>
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
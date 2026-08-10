"use client";

import { Card, CardTitle } from "@/components/ui/Card";
import { PredictionField } from "@/components/journey/PredictionField";
import { Skeleton } from "@/components/ui/Skeleton";
import { useQuery } from "@tanstack/react-query";
import { getFare, type PredictionRequest, type FareResponse } from "@/lib/api";
import { queryKeys } from "@/lib/queryKeys";
import { CapabilityGate } from "@/components/capability/CapabilityGate";
import { DollarSign } from "lucide-react";

interface FareCardProps {
  request: PredictionRequest;
}

function FareCardSkeleton() {
  return (
    <Card>
      <CardTitle className="font-display text-base tracking-wide flex items-center gap-2">
        <DollarSign className="h-4 w-4 text-brass" />
        Fare Estimate
      </CardTitle>
      <div className="mt-3 space-y-3">
        <Skeleton className="h-10 w-full" />
        <Skeleton className="h-10 w-full" />
        <Skeleton className="h-10 w-full" />
      </div>
    </Card>
  );
}

function FareCardContent({ data }: { data: FareResponse }) {
  return (
    <Card>
      <CardTitle className="font-display text-base tracking-wide flex items-center gap-2">
        <DollarSign className="h-4 w-4 text-brass" />
        Fare Estimate
      </CardTitle>
      <div className="mt-3 space-y-3">
        <PredictionField label="Total Fare" prediction={data.fare} isCurrency emphasis />
        {data.breakdown && (
          <div className="space-y-2 pt-2 border-t border-surface-border">
            <p className="text-xs uppercase tracking-wider text-ink-muted">Breakdown</p>
            {data.breakdown.base !== null && (
              <PredictionField label="Base Fare" prediction={{ value: data.breakdown.base, unit: data.currency, basis: data.fare.basis, source: data.fare.source, reason: null, data_vintage: null, value_usd: null }} isCurrency />
            )}
            {data.breakdown.distance !== null && (
              <PredictionField label="Distance" prediction={{ value: data.breakdown.distance, unit: data.currency, basis: data.fare.basis, source: data.fare.source, reason: null, data_vintage: null, value_usd: null }} isCurrency />
            )}
            {data.breakdown.duration !== null && (
              <PredictionField label="Duration" prediction={{ value: data.breakdown.duration, unit: data.currency, basis: data.fare.basis, source: data.fare.source, reason: null, data_vintage: null, value_usd: null }} isCurrency />
            )}
            {data.breakdown.fees !== null && (
              <PredictionField label="Fees" prediction={{ value: data.breakdown.fees, unit: data.currency, basis: data.fare.basis, source: data.fare.source, reason: null, data_vintage: null, value_usd: null }} isCurrency />
            )}
            {data.breakdown.surge !== null && (
              <PredictionField label="Surge" prediction={{ value: data.breakdown.surge, unit: data.currency, basis: data.fare.basis, source: data.fare.source, reason: null, data_vintage: null, value_usd: null }} isCurrency />
            )}
          </div>
        )}
      </div>
      {data.request_id && (
        <div className="mt-3 pt-3 border-t border-surface-border text-xs text-ink-muted font-mono">
          Request: {data.request_id}
        </div>
      )}
    </Card>
  );
}

export function FareCard({ request }: FareCardProps) {
  const { data, isLoading, error } = useQuery({
    queryKey: queryKeys.fare(request),
    queryFn: () => getFare(request),
    enabled: !!request.city_id,
  });

  return (
    <CapabilityGate capability="fare" cityId={request.city_id} fallback={<FareCardSkeleton />}>
      {isLoading ? <FareCardSkeleton /> : error ? (
        <Card className="border-oxide/30 bg-oxide/5">
          <CardTitle className="font-display text-base tracking-wide flex items-center gap-2 text-oxide">
            <DollarSign className="h-4 w-4" />
            Fare Estimate
          </CardTitle>
          <p className="mt-2 text-sm text-ink-muted">{error instanceof Error ? error.message : "Failed to load fare"}</p>
        </Card>
      ) : data ? (
        <FareCardContent data={data} />
      ) : (
        <FareCardSkeleton />
      )}
    </CapabilityGate>
  );
}
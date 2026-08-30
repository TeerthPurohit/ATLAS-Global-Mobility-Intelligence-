"use client";

import { Card } from "@/components/ui/Card";
import { RouteCard } from "@/components/journey/cards/RouteCard";
import { FareCard } from "@/components/journey/cards/FareCard";
import { DemandCard } from "@/components/journey/cards/DemandCard";
import { CongestionCard } from "@/components/journey/cards/CongestionCard";
import { AvailabilityCard } from "@/components/journey/cards/AvailabilityCard";
import { SurgeCard } from "@/components/journey/cards/SurgeCard";
import { CarbonCard } from "@/components/journey/cards/CarbonCard";
import { BestDepartureCard } from "@/components/journey/cards/BestDepartureCard";
import { ContextCard } from "@/components/journey/cards/ContextCard";
import { AICard } from "@/components/journey/cards/AICard";
import { useCapability } from "@/components/capability/CapabilityGate";
import { ProvenanceSummary } from "@/components/ui/ProvenanceTooltip";
import { isInCoverage, type JourneyRequest, type PredictionRequest } from "@/lib/api";
import { useMemo } from "react";

interface JourneyResultsProps {
  request: JourneyRequest;
}

function JourneyContextSection({ request }: { request: PredictionRequest }) {
  return (
    <ContextCard
      pickupLat={request.pickup.lat}
      pickupLon={request.pickup.lon}
      dropoffLat={request.dropoff.lat}
      dropoffLon={request.dropoff.lon}
      departureTime={request.departure_time}
    />
  );
}

function AICardSection({
  request,
  fare,
  duration,
  demand,
  surge
}: {
  request: PredictionRequest;
  fare?: string;
  duration?: string;
  demand?: string;
  surge?: string;
}) {
  return (
    <AICard
      journeyRequest={{
        pickup_lat: request.pickup.lat,
        pickup_lon: request.pickup.lon,
        dropoff_lat: request.dropoff.lat,
        dropoff_lon: request.dropoff.lon,
        departure_time: request.departure_time,
        vehicle_type: request.vehicle_type,
      }}
      fare={fare}
      duration={duration}
      demand={demand}
      surge={surge}
    />
  );
}

function JourneyProvenanceSummary() {
  return (
    <Card className="border-surface-border bg-surface-1/90 shadow-xs p-4">
      <div className="flex flex-wrap items-center justify-between gap-3 text-xs">
        <div className="flex items-center gap-2">
          <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
          <span className="font-semibold text-ink-primary">Deterministic Grounding Active</span>
          <span className="text-ink-muted">·</span>
          <span className="font-mono text-[11px] text-ink-muted">DuckDB Marts + Real-Time Context Engine</span>
        </div>
        <div className="flex items-center gap-2 font-mono text-[11px]">
          <span className="rounded bg-brass/10 text-brass px-2 py-0.5 font-semibold">TLC Calibrated</span>
          <span className="rounded bg-teal-500/10 text-teal-700 dark:text-teal-400 px-2 py-0.5 font-semibold">1.4B+ Records</span>
        </div>
      </div>
    </Card>
  );
}

export function JourneyResults({ request }: JourneyResultsProps) {
  const predictionRequest = useMemo<PredictionRequest>(() => ({
    pickup: { lat: request.pickup_lat, lon: request.pickup_lon },
    dropoff: { lat: request.dropoff_lat, lon: request.dropoff_lon },
    departure_time: request.departure_time,
    vehicle_type: request.vehicle_type,
    distance_km: null,
    duration_min: null,
  }), [request]);

  const routeRequest = useMemo<PredictionRequest>(() => ({
    pickup: { lat: request.pickup_lat, lon: request.pickup_lon },
    dropoff: { lat: request.dropoff_lat, lon: request.dropoff_lon },
    departure_time: request.departure_time,
    vehicle_type: request.vehicle_type,
  }), [request]);

  // Check capabilities for conditional rendering
  const hasFare = useCapability("fare");
  const hasDemand = useCapability("demand");
  const hasCongestion = useCapability("congestion");
  const hasAvailability = useCapability("availability");
  const hasSurge = useCapability("surge");
  const hasCarbon = useCapability("carbon");
  const hasBestDeparture = useCapability("best_departure");
  const hasChat = useCapability("chat");
  const hasRouting = useCapability("routing");

  // Every zone-keyed prediction degrades to "unavailable" outside the served
  // city's coverage, so say that once here instead of rendering ten empty
  // cards. This check sits *below* the hooks deliberately: it used to return
  // early above them, which changed the hook count between renders whenever a
  // pickup moved in or out of coverage.
  if (!isInCoverage(request.pickup_lat, request.pickup_lon)) {
    return (
      <div className="space-y-4">
        <Card className="border-oxide/40 bg-surface-1">
          <p className="text-sm text-ink-secondary">
            This pickup location is outside the served city&apos;s coverage, so no
            predictions can be shown. Try picking a location from the address suggestions.
          </p>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Core journey cards - always shown (route is fastest) */}
      <RouteCard request={routeRequest} />

      {/* Progressive cards - each loads independently */}
      {hasFare && <FareCard request={predictionRequest} />}
      {hasDemand && <DemandCard request={predictionRequest} />}
      {hasCongestion && <CongestionCard request={predictionRequest} />}
      {hasAvailability && <AvailabilityCard request={predictionRequest} />}
      {hasSurge && <SurgeCard request={predictionRequest} />}
      {hasCarbon && <CarbonCard request={predictionRequest} />}
      {hasBestDeparture && <BestDepartureCard request={predictionRequest} />}

      {/* Context section */}
      {hasRouting && <JourneyContextSection request={predictionRequest} />}

      {/* AI Recommendation - shown last after other data loads */}
      {hasChat && (
        <AICardSection request={predictionRequest} />
      )}

      {/* Provenance summary at bottom */}
      <JourneyProvenanceSummary />
    </div>
  );
}

// Legacy components for backward compatibility
export function JourneyResultsSkeleton() {
  return (
    <div className="flex flex-col gap-4">
      {[0, 1, 2].map((i) => (
        <Card key={i}>
          <div className="h-4 w-24 animate-pulse bg-surface-1 rounded" />
          <div className="mt-3 flex flex-col gap-2">
            <div className="h-8 w-full animate-pulse bg-surface-1 rounded" />
            <div className="h-8 w-full animate-pulse bg-surface-1 rounded" />
            <div className="h-8 w-full animate-pulse bg-surface-1 rounded" />
          </div>
        </Card>
      ))}
    </div>
  );
}

export function JourneyResultsError({ message }: { message: string }) {
  return (
    <Card className="border-oxide/30 bg-oxide/5">
      <div className="p-4 text-center">
        <p className="font-medium text-oxide">Estimate failed</p>
        <p className="mt-1 text-sm text-ink-muted">{message}</p>
      </div>
    </Card>
  );
}
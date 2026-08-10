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
import { CapabilityGate, useCapability } from "@/components/capability/CapabilityGate";
import { TierNotice } from "@/components/capability/TierBadge";
import { ProvenanceSummary } from "@/components/ui/ProvenanceTooltip";
import { type JourneyRequest, type PredictionRequest } from "@/lib/api";
import { useMemo } from "react";

interface JourneyResultsProps {
  request: JourneyRequest;
  cityTier: string;
}

function JourneyContextSection({ request, cityId }: { request: PredictionRequest; cityId: string }) {
  return (
    <ContextCard
      cityId={cityId}
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
  cityId,
  fare,
  duration,
  demand,
  surge
}: {
  request: PredictionRequest;
  cityId: string;
  fare?: string;
  duration?: string;
  demand?: string;
  surge?: string;
}) {
  return (
    <AICard
      cityId={cityId}
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

function JourneyProvenanceSummary({ cityTier }: { cityTier: string }) {
  // This will show aggregate provenance. In a full implementation, each card
  // would contribute its predictions to a context. For now, show tier notice.
  return (
    <Card className="border-surface-border bg-surface-1">
      <h4 className="font-display text-sm tracking-wide text-ink-secondary mb-3">
        Provenance Summary
      </h4>
      <TierNotice tier={cityTier} />
      <div className="mt-3 space-y-2 text-sm">
        <p className="text-ink-muted">
          <strong>Basis Legend:</strong> Solid brass = computed from local model/tariff. Dashed verdigris = modeled estimate (WorldMove transfer). Open oxide = unavailable.
        </p>
        <p className="text-ink-muted">
          <strong>City Tier:</strong> {cityTier === "OBSERVED" && "Trained on local trip data"}
          {cityTier === "TRANSFER" && "WorldMove population-scaled priors"}
          {cityTier === "NONE" && "No model — OSRM routing + context only"}
        </p>
      </div>
      <ProvenanceSummary predictions={{}} />
    </Card>
  );
}

export function JourneyResults({ request, cityTier }: JourneyResultsProps) {
  const predictionRequest = useMemo<PredictionRequest>(() => ({
    city_id: request.city_id!,
    pickup: { lat: request.pickup_lat, lon: request.pickup_lon },
    dropoff: { lat: request.dropoff_lat, lon: request.dropoff_lon },
    departure_time: request.departure_time,
    vehicle_type: request.vehicle_type,
    distance_km: null,
    duration_min: null,
  }), [request]);

  const routeRequest = useMemo<PredictionRequest>(() => ({
    city_id: request.city_id!,
    pickup: { lat: request.pickup_lat, lon: request.pickup_lon },
    dropoff: { lat: request.dropoff_lat, lon: request.dropoff_lon },
    departure_time: request.departure_time,
    vehicle_type: request.vehicle_type,
  }), [request]);

  // Check capabilities for conditional rendering
  const hasFare = useCapability(request.city_id!, "fare");
  const hasDemand = useCapability(request.city_id!, "demand");
  const hasCongestion = useCapability(request.city_id!, "congestion");
  const hasAvailability = useCapability(request.city_id!, "availability");
  const hasSurge = useCapability(request.city_id!, "surge");
  const hasCarbon = useCapability(request.city_id!, "carbon");
  const hasBestDeparture = useCapability(request.city_id!, "best_departure");
  const hasChat = useCapability(request.city_id!, "chat");
  const hasRouting = useCapability(request.city_id!, "routing");

  return (
    <div className="space-y-4">
      {/* Tier notice at top */}
      <TierNotice tier={cityTier} />

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
      {hasRouting && <JourneyContextSection request={predictionRequest} cityId={request.city_id!} />}

      {/* AI Recommendation - shown last after other data loads */}
      {hasChat && (
        <AICardSection
          request={predictionRequest}
          cityId={request.city_id!}
        />
      )}

      {/* Provenance summary at bottom */}
      <JourneyProvenanceSummary cityTier={cityTier} />
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
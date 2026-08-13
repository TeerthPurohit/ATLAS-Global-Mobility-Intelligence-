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
  // JourneyForm now resolves the real city_id itself (bbox for NYC/London,
  // resolveCityId()'s registry lookup for everywhere else) before it ever
  // calls onSubmit -- this used to default blindly to "nyc" whenever
  // city_id was missing/"undefined", which is why every non-NYC/London
  // journey's cards silently queried NYC's data. A still-missing city_id
  // here means resolution genuinely failed (e.g. a coordinate with no
  // WorldMove coverage), not "assume NYC".
  const cityId = request.city_id && request.city_id !== "undefined" ? request.city_id : null;

  if (!cityId) {
    return (
      <div className="space-y-4">
        <Card className="border-oxide/40 bg-surface-1">
          <p className="text-sm text-ink-secondary">
            Could not resolve a city for this pickup location, so no predictions can be shown.
            Try picking a location from the address suggestions.
          </p>
        </Card>
      </div>
    );
  }

  const predictionRequest = useMemo<PredictionRequest>(() => ({
    city_id: cityId,
    pickup: { lat: request.pickup_lat, lon: request.pickup_lon },
    dropoff: { lat: request.dropoff_lat, lon: request.dropoff_lon },
    departure_time: request.departure_time,
    vehicle_type: request.vehicle_type,
    distance_km: null,
    duration_min: null,
  }), [request, cityId]);

  const routeRequest = useMemo<PredictionRequest>(() => ({
    city_id: cityId,
    pickup: { lat: request.pickup_lat, lon: request.pickup_lon },
    dropoff: { lat: request.dropoff_lat, lon: request.dropoff_lon },
    departure_time: request.departure_time,
    vehicle_type: request.vehicle_type,
  }), [request, cityId]);

  // Check capabilities for conditional rendering
  const hasFare = useCapability(cityId, "fare");
  const hasDemand = useCapability(cityId, "demand");
  const hasCongestion = useCapability(cityId, "congestion");
  const hasAvailability = useCapability(cityId, "availability");
  const hasSurge = useCapability(cityId, "surge");
  const hasCarbon = useCapability(cityId, "carbon");
  const hasBestDeparture = useCapability(cityId, "best_departure");
  const hasChat = useCapability(cityId, "chat");
  const hasRouting = useCapability(cityId, "routing");

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
      {hasRouting && <JourneyContextSection request={predictionRequest} cityId={cityId} />}

      {/* AI Recommendation - shown last after other data loads */}
      {hasChat && (
        <AICardSection
          request={predictionRequest}
          cityId={cityId}
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
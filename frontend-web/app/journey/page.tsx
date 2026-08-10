"use client";

import { useState, useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { JourneyForm } from "@/components/journey/JourneyForm";
import { JourneyMap } from "@/components/journey/JourneyMap";
import { JourneyResults, JourneyResultsSkeleton, JourneyResultsError } from "@/components/journey/JourneyResults";
import { getCityProfile, type CityProfileResponse } from "@/lib/api";
import { queryKeys } from "@/lib/queryKeys";
import { type JourneyRequest } from "@/lib/api";

const defaultPickup = { lat: 40.7484, lon: -73.9857 };
const defaultDropoff = { lat: 40.7061, lon: -74.0088 };

export default function JourneyPage() {
  const [route, setRoute] = useState({ pickup: defaultPickup, dropoff: defaultDropoff });
  const [journeyRequest, setJourneyRequest] = useState<JourneyRequest | null>(null);
  const [cityTier, setCityTier] = useState<string>("OBSERVED");

  // Fetch city profile to get tier when city_id is available
  const { data: cityProfile } = useQuery({
    queryKey: queryKeys.cityProfile(journeyRequest?.city_id || ""),
    queryFn: () => getCityProfile(journeyRequest!.city_id!),
    enabled: !!journeyRequest?.city_id,
  });

  useEffect(() => {
    if (cityProfile) {
      setCityTier(cityProfile.tier || cityProfile.model_status || "OBSERVED");
    }
  }, [cityProfile]);

  function handleSubmit(req: JourneyRequest) {
    setRoute({
      pickup: { lat: req.pickup_lat, lon: req.pickup_lon },
      dropoff: { lat: req.dropoff_lat, lon: req.dropoff_lon },
    });
    setJourneyRequest(req);
  }

  // Only show results when we have a journey request
  const showResults = !!journeyRequest;

  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-[380px_1fr]">
      <div className="flex flex-col gap-6">
        <JourneyForm onSubmit={handleSubmit} isPending={false} />
        <JourneyMap pickup={route.pickup} dropoff={route.dropoff} />
      </div>

      <div>
        {showResults && journeyRequest ? (
          <JourneyResults request={journeyRequest} cityTier={cityTier} />
        ) : (
          <div className="flex h-full items-center justify-center rounded-2xl border border-dashed border-surface-border p-12 text-center text-sm text-ink-muted">
            Fill in a journey and estimate to see fare, ETA, demand, and risk intelligence.
          </div>
        )}
      </div>
    </div>
  );
}
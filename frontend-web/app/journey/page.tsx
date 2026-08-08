"use client";

import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { JourneyForm } from "@/components/journey/JourneyForm";
import { JourneyMap } from "@/components/journey/JourneyMap";
import {
  JourneyResults,
  JourneyResultsError,
  JourneyResultsSkeleton,
} from "@/components/journey/JourneyResults";
import { estimateJourney, type JourneyRequest } from "@/lib/api";

const defaultPickup = { lat: 40.7484, lon: -73.9857 };
const defaultDropoff = { lat: 40.7061, lon: -74.0088 };

export default function JourneyPage() {
  const [route, setRoute] = useState({ pickup: defaultPickup, dropoff: defaultDropoff });

  const mutation = useMutation({
    mutationFn: estimateJourney,
  });

  function handleSubmit(req: JourneyRequest) {
    setRoute({
      pickup: { lat: req.pickup_lat, lon: req.pickup_lon },
      dropoff: { lat: req.dropoff_lat, lon: req.dropoff_lon },
    });
    mutation.mutate(req);
  }

  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-[380px_1fr]">
      <div className="flex flex-col gap-6">
        <JourneyForm onSubmit={handleSubmit} isPending={mutation.isPending} />
        <JourneyMap pickup={route.pickup} dropoff={route.dropoff} />
      </div>

      <div>
        {mutation.isPending && <JourneyResultsSkeleton />}
        {mutation.isError && (
          <JourneyResultsError
            message={mutation.error instanceof Error ? mutation.error.message : "Unknown error"}
          />
        )}
        {mutation.isSuccess && <JourneyResults estimate={mutation.data} />}
        {mutation.isIdle && (
          <div className="flex h-full items-center justify-center rounded-2xl border border-dashed border-surface-border p-12 text-center text-sm text-ink-muted">
            Fill in a journey and estimate to see fare, ETA, demand, and risk intelligence.
          </div>
        )}
      </div>
    </div>
  );
}

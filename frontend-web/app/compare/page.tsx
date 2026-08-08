"use client";

import { useState } from "react";
import { useQueries } from "@tanstack/react-query";
import { CompareForm, type CompareRequest } from "@/components/compare/CompareForm";
import { CompareCard } from "@/components/compare/CompareCard";
import { estimateJourney, type JourneyRequest, type VehicleClass } from "@/lib/api";

export default function ComparePage() {
  const [vehicles, setVehicles] = useState<VehicleClass[]>([]);
  const [baseRequest, setBaseRequest] = useState<Omit<JourneyRequest, "vehicle_type"> | null>(null);

  const results = useQueries({
    queries: vehicles.map((vehicle_type) => ({
      queryKey: ["journey-estimate", baseRequest, vehicle_type],
      queryFn: () => estimateJourney({ ...baseRequest!, vehicle_type }),
      enabled: !!baseRequest,
    })),
  });

  function handleSubmit(req: CompareRequest) {
    const { vehicles: selected, ...rest } = req;
    setBaseRequest(rest);
    setVehicles(selected);
  }

  // Winner rule: lowest numeric fare among cards with a computed/modeled fare
  // reading (skip "unavailable" basis -- can't compare what has no reading).
  const winnerIndex = (() => {
    let best = -1;
    let bestFare = Infinity;
    results.forEach((r, i) => {
      const fare = r.data?.fare;
      if (fare && fare.basis !== "unavailable" && typeof fare.value === "number" && fare.value < bestFare) {
        bestFare = fare.value;
        best = i;
      }
    });
    return best;
  })();

  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-[380px_1fr]">
      <div className="flex flex-col gap-6">
        <CompareForm onSubmit={handleSubmit} isPending={results.some((r) => r.isPending) && vehicles.length > 0} />
      </div>

      <div>
        {vehicles.length === 0 && (
          <div className="flex h-full items-center justify-center rounded-2xl border border-dashed border-surface-border p-12 text-center text-sm text-ink-muted">
            Pick a journey and a set of vehicle classes to compare fare, duration, carbon, and availability
            side by side.
          </div>
        )}

        {vehicles.length > 0 && (
          <div className="flex flex-wrap gap-4">
            {vehicles.map((vehicle, i) => {
              const r = results[i];
              return (
                <CompareCard
                  key={vehicle}
                  vehicle={vehicle}
                  isPending={r.isPending}
                  isError={r.isError}
                  error={r.error}
                  data={r.data}
                  winner={i === winnerIndex}
                />
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}

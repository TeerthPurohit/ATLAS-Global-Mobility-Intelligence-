"use client";

import { useState } from "react";
import { useQueries } from "@tanstack/react-query";
import { CompareForm, type CompareRequest } from "@/components/compare/CompareForm";
import { CompareCard } from "@/components/compare/CompareCard";
import { estimateJourney, type JourneyRequest, type VehicleClass } from "@/lib/api";
import { TrendingUp } from "lucide-react";

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
    <div className="flex flex-col gap-12">
      {/* Header */}
      <section className="flex flex-col gap-3">
        <span className="font-label-sm text-brass tracking-wider">
          Comparative Analysis
        </span>
        <h1 className="font-display-lg text-ink-primary">
          Vehicle Class Comparison
        </h1>
        <p className="font-body-md max-w-2xl text-ink-secondary">
          Compare fare, duration, carbon impact, and availability across vehicle classes for your journey.
        </p>
      </section>

      {/* Main Layout */}
      <div className="grid grid-cols-1 gap-8 lg:grid-cols-[420px_1fr]">
        {/* Sidebar Form */}
        <div className="flex flex-col gap-6">
          <CompareForm onSubmit={handleSubmit} isPending={results.some((r) => r.isPending) && vehicles.length > 0} />
        </div>

        {/* Results Grid */}
        <div>
          {vehicles.length === 0 && (
            <div className="flex h-full min-h-[400px] items-center justify-center border border-surface-border bg-surface-1 p-12 text-center rounded-sm">
              <div className="max-w-md space-y-4">
                <div className="flex justify-center">
                  <div className="p-3 bg-brass/10 rounded-sm">
                    <TrendingUp className="h-6 w-6 text-brass" />
                  </div>
                </div>
                <h3 className="font-section-lg text-ink-primary">
                  Select Vehicle Classes
                </h3>
                <p className="font-body-sm text-ink-secondary">
                  Choose a journey and vehicle classes to compare pricing, duration, environmental impact, and service availability.
                </p>
              </div>
            </div>
          )}

          {vehicles.length > 0 && (
            <div className="flex flex-col gap-8">
              {/* Results Header */}
              <div className="flex items-center justify-between border-b border-surface-border pb-6">
                <div>
                  <h2 className="font-section-lg text-ink-primary">Results</h2>
                  <p className="font-body-sm text-ink-secondary mt-1">
                    {vehicles.length} vehicle class{vehicles.length !== 1 ? 'es' : ''} compared
                  </p>
                </div>
                {winnerIndex >= 0 && (
                  <div className="text-right">
                    <span className="font-label-sm text-brass">Best Value</span>
                    <p className="font-section-md text-ink-primary mt-1">{vehicles[winnerIndex]}</p>
                  </div>
                )}
              </div>

              {/* Cards Grid */}
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
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
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

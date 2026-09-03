"use client";

import { useState } from "react";
import { useQueries } from "@tanstack/react-query";
import { CompareForm, type CompareRequest } from "@/components/compare/CompareForm";
import { CompareCard } from "@/components/compare/CompareCard";
import { estimateJourney, type JourneyRequest, type VehicleClass } from "@/lib/api";
import {
  Compass,
  ArrowRight,
  TrendingUp,
  Zap,
  Leaf,
  ShieldCheck,
  Car,
  Layers,
  Sparkles,
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

const COMPARISON_BUNDLES = [
  {
    id: "airport-suite",
    name: "Airport Fleet Suite",
    subtitle: "JFK Terminal 4 ➔ Midtown",
    classes: ["sedan", "suv", "premium", "ev"] as VehicleClass[],
    pickup: { lat: 40.6413, lon: -73.7781 },
    dropoff: { lat: 40.7580, lon: -73.9855 },
    highlight: "Optimal for luggage & premium transfer",
  },
  {
    id: "green-urban",
    name: "Eco-Fleet Comparison",
    subtitle: "Wall St ➔ Williamsburg",
    classes: ["ev", "bike", "mini", "sedan"] as VehicleClass[],
    pickup: { lat: 40.7071, lon: -74.0090 },
    dropoff: { lat: 40.7135, lon: -73.9570 },
    highlight: "Emissions minimization & rapid urban transit",
  },
  {
    id: "all-tiers",
    name: "Full TLC Spectrum Benchmark",
    subtitle: "Hudson Yards ➔ DUMBO",
    classes: ["bike", "mini", "sedan", "suv", "ev", "premium"] as VehicleClass[],
    pickup: { lat: 40.7538, lon: -74.0022 },
    dropoff: { lat: 40.7033, lon: -73.9896 },
    highlight: "Comprehensive multi-tier pricing evaluation",
  },
];

const VEHICLE_SPECS: Record<
  VehicleClass,
  { name: string; pax: string; carbon: string; baseline: string }
> = {
  bike: { name: "Micromobility", pax: "1 Pax", carbon: "0g CO₂/mi", baseline: "0.45x Base" },
  auto: { name: "Auto Rickshaw", pax: "3 Pax", carbon: "45g CO₂/mi", baseline: "0.60x Base" },
  mini: { name: "Compact Eco", pax: "3 Pax", carbon: "90g CO₂/mi", baseline: "0.80x Base" },
  sedan: { name: "Standard Sedan", pax: "4 Pax", carbon: "140g CO₂/mi", baseline: "1.00x Base" },
  suv: { name: "Full-Size SUV", pax: "6 Pax", carbon: "220g CO₂/mi", baseline: "1.45x Base" },
  ev: { name: "Zero-Emission EV", pax: "4 Pax", carbon: "0g Tailpipe", baseline: "1.05x Base" },
  premium: { name: "Luxury Black Car", pax: "4 Pax", carbon: "180g CO₂/mi", baseline: "1.85x Base" },
};

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

  function handleRunBundle(bundle: (typeof COMPARISON_BUNDLES)[0]) {
    handleSubmit({
      pickup_lat: bundle.pickup.lat,
      pickup_lon: bundle.pickup.lon,
      dropoff_lat: bundle.dropoff.lat,
      dropoff_lon: bundle.dropoff.lon,
      departure_time: new Date().toISOString().slice(0, 16),
      vehicles: bundle.classes,
    });
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
    <div className="flex flex-col gap-8 pb-12">
      {/* Header */}
      <section className="flex flex-col gap-2.5">
        <div className="flex items-center gap-2 text-xs font-mono font-semibold uppercase tracking-wider text-brass">
          <Compass className="h-4 w-4" />
          <span>Multi-Tier Fleet Benchmarking</span>
        </div>
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <h1 className="font-display-lg text-3xl font-extrabold text-ink-primary sm:text-4xl">
              Vehicle Class Comparison
            </h1>
            <p className="mt-1 max-w-2xl font-body-md text-sm text-ink-secondary sm:text-base">
              Simultaneously compare pricing, ETA, capacity, and environmental carbon metrics across NYC TLC vehicle tiers.
            </p>
          </div>
          <div className="flex items-center gap-2 rounded-xl border border-surface-border bg-surface-1/90 px-3.5 py-2 font-mono text-xs text-ink-secondary shadow-sm">
            <span className="h-2 w-2 rounded-full bg-brass animate-pulse" />
            <span>7 Vehicle Tiers Supported</span>
          </div>
        </div>
      </section>

      {/* Main Layout */}
      <div className="grid grid-cols-1 gap-8 lg:grid-cols-[430px_1fr] items-start">
        {/* Sidebar Form */}
        <div className="flex flex-col gap-6">
          <CompareForm
            onSubmit={handleSubmit}
            isPending={results.some((r) => r.isPending) && vehicles.length > 0}
          />
        </div>

        {/* Results Grid or Fleet Benchmark Deck */}
        <div>
          <AnimatePresence mode="wait">
            {vehicles.length === 0 ? (
              <motion.div
                key="fleet-deck"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="flex flex-col gap-6"
              >
                {/* 1-Click Comparison Bundles */}
                <div className="rounded-3xl border border-surface-border bg-gradient-to-br from-surface-1 via-surface-1 to-surface-2/40 p-6 shadow-sm">
                  <div className="flex flex-wrap items-center justify-between gap-4">
                    <div>
                      <div className="flex items-center gap-2">
                        <Sparkles className="h-4 w-4 text-brass" />
                        <h2 className="text-lg font-bold text-ink-primary">
                          Fleet Comparison Presets
                        </h2>
                      </div>
                      <p className="mt-1 text-xs text-ink-secondary">
                        Click any benchmark bundle to immediately simulate multi-vehicle metrics.
                      </p>
                    </div>
                    <span className="rounded-full border border-brass/30 bg-brass/10 px-3 py-1 font-mono text-xs text-brass font-medium">
                      Multi-Class Simulation
                    </span>
                  </div>

                  <div className="mt-5 grid grid-cols-1 gap-3.5 sm:grid-cols-3">
                    {COMPARISON_BUNDLES.map((bundle) => (
                      <div
                        key={bundle.id}
                        onClick={() => handleRunBundle(bundle)}
                        className="group flex flex-col justify-between cursor-pointer rounded-2xl border border-surface-border bg-surface-1/90 p-4 transition-all hover:-translate-y-0.5 hover:border-brass/50 hover:shadow-md"
                      >
                        <div>
                          <span className="text-[10px] font-mono uppercase text-ink-muted">
                            {bundle.subtitle}
                          </span>
                          <h3 className="font-section-md text-sm font-semibold text-ink-primary group-hover:text-brass transition-colors">
                            {bundle.name}
                          </h3>
                          <p className="mt-2 text-xs text-ink-secondary line-clamp-2">
                            {bundle.highlight}
                          </p>
                        </div>

                        <div className="mt-4 flex items-center justify-between border-t border-surface-border/50 pt-2.5">
                          <span className="font-mono text-[11px] text-ink-muted">
                            {bundle.classes.length} Tiers
                          </span>
                          <div className="flex items-center gap-1 text-xs font-semibold text-brass">
                            <span>Compare</span>
                            <ArrowRight className="h-3 w-3" />
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* TLC Vehicle Class Matrix */}
                <div className="rounded-3xl border border-surface-border bg-surface-1 p-6 shadow-sm">
                  <div className="flex items-center gap-2 mb-4">
                    <Layers className="h-4 w-4 text-brass" />
                    <h3 className="text-sm font-bold text-ink-primary">
                      NYC TLC Vehicle Class Specifications
                    </h3>
                  </div>

                  <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                    {(Object.keys(VEHICLE_SPECS) as VehicleClass[]).slice(0, 4).map((cls) => {
                      const spec = VEHICLE_SPECS[cls];
                      return (
                        <div
                          key={cls}
                          className="rounded-xl border border-surface-border/80 bg-surface-0/60 p-3"
                        >
                          <div className="flex items-center justify-between">
                            <span className="font-mono text-xs font-bold uppercase text-ink-primary">
                              {cls}
                            </span>
                            <span className="text-[10px] text-ink-muted">{spec.pax}</span>
                          </div>
                          <p className="mt-1 text-xs text-ink-secondary">{spec.name}</p>
                          <div className="mt-2 flex items-center justify-between text-[11px] font-mono">
                            <span className="text-emerald-600">{spec.carbon}</span>
                            <span className="text-ink-muted">{spec.baseline}</span>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>

                {/* Footnote */}
                <div className="flex items-center justify-between rounded-2xl border border-surface-border/80 bg-surface-1/70 px-5 py-3 text-xs text-ink-muted">
                  <span className="flex items-center gap-2">
                    <ShieldCheck className="h-4 w-4 text-brass" />
                    <span>Real TLC Base Rate Modeling · Sub-100ms Parallel Querying</span>
                  </span>
                </div>
              </motion.div>
            ) : (
              <motion.div
                key="results"
                initial={{ opacity: 0, y: 16 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                transition={{ duration: 0.35, ease: [0.16, 1, 0.3, 1] }}
                className="flex flex-col gap-6"
              >
                {/* Results Header */}
                <div className="flex items-center justify-between rounded-2xl border border-surface-border bg-surface-1 p-5 shadow-sm">
                  <div>
                    <h2 className="font-section-lg text-lg font-bold text-ink-primary">
                      Comparison Results
                    </h2>
                    <p className="font-body-sm text-xs text-ink-secondary mt-0.5">
                      {vehicles.length} vehicle class{vehicles.length !== 1 ? "es" : ""} evaluated in parallel
                    </p>
                  </div>
                  <div className="flex items-center gap-4">
                    {winnerIndex >= 0 && (
                      <div className="text-right">
                        <span className="font-label-sm text-xs text-brass">Best Value Tier</span>
                        <p className="font-section-md text-sm font-bold uppercase text-ink-primary">
                          {vehicles[winnerIndex]}
                        </p>
                      </div>
                    )}
                    <button
                      onClick={() => setVehicles([])}
                      className="rounded-lg border border-surface-border bg-surface-0 px-3 py-1.5 text-xs font-semibold text-ink-secondary hover:text-ink-primary transition-colors"
                    >
                      Reset
                    </button>
                  </div>
                </div>

                {/* Cards Grid */}
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
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
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </div>
  );
}

"use client";

import { Suspense, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import { JourneyForm } from "@/components/journey/JourneyForm";
import { JourneyMap } from "@/components/journey/JourneyMap";
import { JourneyResults } from "@/components/journey/JourneyResults";
import { type JourneyRequest } from "@/lib/api";
import { useGsapEntrance } from "@/hooks/useGsapEntrance";
import { motion, AnimatePresence } from "framer-motion";
import {
  Compass,
  ArrowRight,
  TrendingUp,
  Activity,
  ShieldCheck,
  Zap,
  Leaf,
  Clock,
  Sparkles,
} from "lucide-react";

const defaultPickup = { lat: 40.7484, lon: -73.9857, name: "Midtown Manhattan, New York" };
const defaultDropoff = { lat: 40.7061, lon: -74.0088, name: "Financial District, New York" };

const CORRIDOR_PRESETS = [
  {
    id: "jfk-midtown",
    title: "JFK Airport ➔ Midtown Central",
    boroughs: "Queens ➔ Manhattan",
    distance: "18.4 mi",
    typicalFare: "$58.50 - $74.00",
    surge: "Peak Air-Travel",
    pickup: { lat: 40.6413, lon: -73.7781, name: "JFK Airport Terminal 4, Queens, NY" },
    dropoff: { lat: 40.7580, lon: -73.9855, name: "Times Square / Midtown, New York, NY" },
    vehicle_type: "sedan" as const,
  },
  {
    id: "fidi-williamsburg",
    title: "Wall Street ➔ Williamsburg",
    boroughs: "Manhattan ➔ Brooklyn",
    distance: "4.8 mi",
    typicalFare: "$24.00 - $31.50",
    surge: "Bridge Inflow",
    pickup: { lat: 40.7071, lon: -74.0090, name: "Wall Street / FiDi, New York, NY" },
    dropoff: { lat: 40.7135, lon: -73.9570, name: "Bedford Ave, Williamsburg, Brooklyn, NY" },
    vehicle_type: "sedan" as const,
  },
  {
    id: "lga-grandcentral",
    title: "LGA Airport ➔ Grand Central",
    boroughs: "Queens ➔ Manhattan",
    distance: "9.2 mi",
    typicalFare: "$38.00 - $49.00",
    surge: "Triborough Flow",
    pickup: { lat: 40.7769, lon: -73.8740, name: "LaGuardia Airport Terminal B, Queens, NY" },
    dropoff: { lat: 40.7527, lon: -73.9772, name: "Grand Central Terminal, New York, NY" },
    vehicle_type: "ev" as const,
  },
  {
    id: "hudson-dumbo",
    title: "Hudson Yards ➔ DUMBO Waterfront",
    boroughs: "Manhattan ➔ Brooklyn",
    distance: "6.2 mi",
    typicalFare: "$28.50 - $36.00",
    surge: "Manhattan Bridge",
    pickup: { lat: 40.7538, lon: -74.0022, name: "Hudson Yards, New York, NY" },
    dropoff: { lat: 40.7033, lon: -73.9896, name: "DUMBO Waterfront, Brooklyn, NY" },
    vehicle_type: "premium" as const,
  },
];

export default function JourneyPage() {
  return (
    <Suspense fallback={null}>
      <JourneyPageContent />
    </Suspense>
  );
}

function JourneyPageContent() {
  const containerRef = useGsapEntrance(".gsap-reveal", { stagger: 0.1, yOffset: 16 });
  const searchParams = useSearchParams();

  const initialPickup = useMemo(() => {
    const lat = searchParams.get("pickupLat");
    const lon = searchParams.get("pickupLon");
    const name = searchParams.get("pickupName");
    if (!lat || !lon || !name) return undefined;
    return { lat: Number(lat), lon: Number(lon), name };
  }, [searchParams]);

  const initialDropoff = useMemo(() => {
    const lat = searchParams.get("dropoffLat");
    const lon = searchParams.get("dropoffLon");
    const name = searchParams.get("dropoffName");
    if (!lat || !lon || !name) return undefined;
    return { lat: Number(lat), lon: Number(lon), name };
  }, [searchParams]);

  const [route, setRoute] = useState({
    pickup: initialPickup ?? defaultPickup,
    dropoff: initialDropoff ?? defaultDropoff,
  });
  const [journeyRequest, setJourneyRequest] = useState<JourneyRequest | null>(null);

  function handleSubmit(req: JourneyRequest) {
    setRoute({
      pickup: { lat: req.pickup_lat, lon: req.pickup_lon, name: "Selected Pickup" },
      dropoff: { lat: req.dropoff_lat, lon: req.dropoff_lon, name: "Selected Dropoff" },
    });
    setJourneyRequest(req);
  }

  function handleRunPreset(preset: (typeof CORRIDOR_PRESETS)[0]) {
    const req: JourneyRequest = {
      pickup_lat: preset.pickup.lat,
      pickup_lon: preset.pickup.lon,
      dropoff_lat: preset.dropoff.lat,
      dropoff_lon: preset.dropoff.lon,
      departure_time: new Date().toISOString().slice(0, 16),
      vehicle_type: preset.vehicle_type,
    };
    handleSubmit(req);
  }

  const showResults = !!journeyRequest;

  return (
    <div ref={containerRef} className="flex flex-col gap-8 pb-12">
      {/* Header */}
      <section className="gsap-reveal flex flex-col gap-2.5">
        <div className="flex items-center gap-2 text-xs font-mono font-semibold uppercase tracking-wider text-brass">
          <Compass className="h-4 w-4" />
          <span>NYC TLC Route & Fare Telemetry</span>
        </div>
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <h1 className="font-display-lg text-3xl font-extrabold text-ink-primary sm:text-4xl">
              Journey Intelligence Engine
            </h1>
            <p className="mt-1 max-w-2xl font-body-md text-sm text-ink-secondary sm:text-base">
              Precision multi-variable mobility inference: fare modeling, congestion ETA, demand surge, and carbon emission analytics.
            </p>
          </div>
          <div className="flex items-center gap-2 rounded-xl border border-surface-border bg-surface-1/90 px-3.5 py-2 font-mono text-xs text-ink-secondary shadow-sm">
            <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
            <span>263 Zones Calibrated</span>
          </div>
        </div>
      </section>

      {/* Main Grid Layout */}
      <div className="grid grid-cols-1 gap-8 lg:grid-cols-[430px_1fr] items-start">
        {/* Sidebar Form & Interactive Map */}
        <div className="gsap-reveal flex flex-col gap-6">
          <JourneyForm
            onSubmit={handleSubmit}
            isPending={false}
            initialPickup={initialPickup}
            initialDropoff={initialDropoff}
          />
          <div className="overflow-hidden rounded-2xl border border-surface-border bg-surface-1 shadow-sm">
            <div className="border-b border-surface-border/70 bg-surface-2/40 px-4 py-2 text-xs font-mono text-ink-muted">
              Spatial Coordinates Preview
            </div>
            <div className="p-4">
              <JourneyMap pickup={route.pickup} dropoff={route.dropoff} />
            </div>
          </div>
        </div>

        {/* Results Area or Rich Corridor Command Deck */}
        <div className="gsap-reveal">
          <AnimatePresence mode="wait">
            {showResults && journeyRequest ? (
              <motion.div
                key="results"
                initial={{ opacity: 0, y: 16 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                transition={{ duration: 0.35, ease: [0.16, 1, 0.3, 1] }}
              >
                <div className="mb-4 flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="rounded bg-brass/10 px-2.5 py-1 text-xs font-mono font-semibold text-brass">
                      Active Simulation
                    </span>
                    <span className="text-xs font-mono text-ink-muted">
                      Inference Engine: TLC ML Regressor
                    </span>
                  </div>
                  <button
                    onClick={() => setJourneyRequest(null)}
                    className="text-xs font-semibold text-brass hover:underline"
                  >
                    ← Back to Corridor Command Deck
                  </button>
                </div>
                <JourneyResults request={journeyRequest} />
              </motion.div>
            ) : (
              <motion.div
                key="command-deck"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="flex flex-col gap-6"
              >
                {/* Live Corridor Showcase Header */}
                <div className="rounded-3xl border border-surface-border bg-gradient-to-br from-surface-1 via-surface-1 to-surface-2/40 p-6 shadow-sm">
                  <div className="flex flex-wrap items-center justify-between gap-4">
                    <div>
                      <div className="flex items-center gap-2">
                        <Sparkles className="h-4 w-4 text-brass" />
                        <h2 className="text-lg font-bold text-ink-primary">
                          TLC High-Volume Corridors
                        </h2>
                      </div>
                      <p className="mt-1 text-xs text-ink-secondary">
                        Click any benchmark corridor to immediately simulate pricing, duration, and carbon telemetry.
                      </p>
                    </div>
                    <span className="rounded-full border border-brass/30 bg-brass/10 px-3 py-1 font-mono text-xs text-brass font-medium">
                      1-Click Fast Simulation
                    </span>
                  </div>

                  {/* Preset Corridor Cards */}
                  <div className="mt-5 grid grid-cols-1 gap-3 sm:grid-cols-2">
                    {CORRIDOR_PRESETS.map((preset) => (
                      <div
                        key={preset.id}
                        onClick={() => handleRunPreset(preset)}
                        className="group relative cursor-pointer rounded-2xl border border-surface-border bg-surface-1/90 p-4 transition-all hover:-translate-y-0.5 hover:border-brass/50 hover:shadow-md"
                      >
                        <div className="flex items-start justify-between gap-2">
                          <div className="min-w-0">
                            <span className="text-[11px] font-mono text-ink-muted">
                              {preset.boroughs}
                            </span>
                            <h3 className="font-section-md text-sm font-semibold text-ink-primary group-hover:text-brass transition-colors">
                              {preset.title}
                            </h3>
                          </div>
                          <div className="rounded-lg bg-surface-2/80 p-2 text-ink-muted group-hover:bg-brass group-hover:text-white transition-all">
                            <ArrowRight className="h-3.5 w-3.5" />
                          </div>
                        </div>

                        <div className="mt-3 flex items-center justify-between border-t border-surface-border/50 pt-2.5 text-xs">
                          <span className="font-mono text-ink-secondary">
                            {preset.distance}
                          </span>
                          <span className="font-semibold text-brass">
                            {preset.typicalFare}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Intelligence Metrics & Capability Matrix */}
                <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
                  <div className="rounded-2xl border border-surface-border bg-surface-1 p-5 shadow-sm">
                    <div className="flex items-center gap-2 text-ink-muted">
                      <TrendingUp className="h-4 w-4 text-emerald-500" />
                      <span className="text-xs font-mono uppercase">Dynamic Pricing</span>
                    </div>
                    <p className="mt-2 text-base font-bold text-ink-primary">TLC Mart Grounded</p>
                    <p className="mt-1 text-xs text-ink-secondary">
                      Calibrated across time-of-day multipliers and real base fare distributions.
                    </p>
                  </div>

                  <div className="rounded-2xl border border-surface-border bg-surface-1 p-5 shadow-sm">
                    <div className="flex items-center gap-2 text-ink-muted">
                      <Activity className="h-4 w-4 text-indigo-500" />
                      <span className="text-xs font-mono uppercase">Congestion Radar</span>
                    </div>
                    <p className="mt-2 text-base font-bold text-ink-primary">Bridge & Tunnel Risk</p>
                    <p className="mt-1 text-xs text-ink-secondary">
                      Real-time arterial bottleneck detection across East River and Midtown crossings.
                    </p>
                  </div>

                  <div className="rounded-2xl border border-surface-border bg-surface-1 p-5 shadow-sm">
                    <div className="flex items-center gap-2 text-ink-muted">
                      <Leaf className="h-4 w-4 text-teal-500" />
                      <span className="text-xs font-mono uppercase">Green Fleet Analysis</span>
                    </div>
                    <p className="mt-2 text-base font-bold text-ink-primary">Carbon Offsets</p>
                    <p className="mt-1 text-xs text-ink-secondary">
                      Compare EV vs combustion emissions for corporate ESG accounting.
                    </p>
                  </div>
                </div>

                {/* System Specs Banner */}
                <div className="flex flex-wrap items-center justify-between rounded-2xl border border-surface-border/80 bg-surface-1/70 px-5 py-3 text-xs text-ink-muted">
                  <span className="flex items-center gap-2">
                    <ShieldCheck className="h-4 w-4 text-brass" />
                    <span>Postgres Mart · Fast Matrix Lookup · Real TLC Trip Records</span>
                  </span>
                  <span className="font-mono text-[11px] text-ink-secondary">
                    Spatial Coverage: 40.49°N to 40.92°N
                  </span>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </div>
  );
}

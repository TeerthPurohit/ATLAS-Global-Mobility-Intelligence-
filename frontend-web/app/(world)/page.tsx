"use client";

import { useQuery } from "@tanstack/react-query";
import { MapPin, TrendingUp, DollarSign } from "lucide-react";
import { ZoneMap } from "@/components/nyc/ZoneMap";
import { Card } from "@/components/ui/Card";
import { getZoneDemandTotals } from "@/lib/api";
import { queryKeys } from "@/lib/queryKeys";
import { useGsapEntrance } from "@/hooks/useGsapEntrance";
import { NumberTicker } from "@/components/magic/NumberTicker";

export default function HomePage() {
  const containerRef = useGsapEntrance(".gsap-reveal", { stagger: 0.1, yOffset: 20 });

  const { data: zones } = useQuery({
    queryKey: queryKeys.zoneDemandTotals(),
    queryFn: getZoneDemandTotals,
    staleTime: Infinity,
  });

  const totalTrips = zones?.reduce((sum, z) => sum + z.total_trips, 0) ?? 0;
  const activeZones = zones?.length ?? 0;
  const weightedFare =
    zones && totalTrips > 0
      ? zones.reduce((sum, z) => sum + (z.avg_fare ?? 0) * z.total_trips, 0) / totalTrips
      : 0;
  const topZones = zones?.slice(0, 5) ?? [];

  return (
    <div ref={containerRef}>
      {/* IMMERSIVE MAP HERO -- the map is the page. Full-bleed, bleeds up under the transparent navbar.
          Note: no overflow-x-hidden here -- the calc(50%-50vw) bleed trick is self-bounding to the
          viewport, and overflow-x-hidden on an ancestor still inside main's padded box would clip it. */}
      <section className="relative -mx-4 -mt-24 h-[100dvh] overflow-hidden border-b border-surface-border sm:-mx-6 sm:-mt-28 xl:mx-[calc(50%-50vw)]">
        <ZoneMap />

        {/* Legibility scrim -- text only, map stays readable underneath */}
        <div className="pointer-events-none absolute inset-x-0 top-0 h-72 bg-gradient-to-b from-surface-0/85 via-surface-0/20 to-transparent" />

        {/* Hero copy -- floats over the map in a soft card, not above it */}
        <div className="absolute left-6 top-[104px] z-10 max-w-[19rem] rounded-2xl bg-surface-1/90 p-5 shadow-[0_12px_36px_-12px_rgba(108,92,231,0.3)] backdrop-blur-sm sm:left-10 sm:top-[132px] sm:max-w-md">
          <span className="font-label-sm text-brass tracking-wider">New York City · TLC High-Volume For-Hire</span>
          <h1 className="mt-3 font-display-lg uppercase leading-[1.05] tracking-tight text-ink-primary sm:font-display-xl">
            265 zones.
            <br />
            Every hour.
            <br />
            Measured.
          </h1>
          <p className="mt-4 font-body-sm text-ink-secondary max-w-xs">
            Demand and fare intelligence built on real TLC trip records — no
            estimates, no priors. Hover any zone to see what it actually moved.
          </p>
          <p className="mt-4 font-label-sm text-ink-muted">
            Click a zone for pickup, click another for dropoff.
          </p>
        </div>
      </section>

      {/* DATA STORY -- bento KPI tiles, real numbers or nothing */}
      <section className="gsap-reveal mt-16 sm:mt-24">
        <span className="font-label-sm text-brass tracking-wider">Measured Coverage</span>
        <div className="mt-5 grid grid-cols-1 gap-4 sm:grid-cols-3">
          <div className="rounded-2xl bg-brass p-6 text-brass-fg shadow-[0_12px_30px_-10px_rgba(108,92,231,0.5)]">
            <TrendingUp className="h-5 w-5 opacity-80" />
            <div className="mt-4 font-data-lg leading-none">
              <NumberTicker value={totalTrips} duration={0.9} />
            </div>
            <p className="mt-2 font-label-sm opacity-80">Trips in the warehouse</p>
          </div>
          <div className="rounded-2xl p-6 text-white shadow-[0_12px_30px_-10px_rgba(59,158,229,0.5)]" style={{ background: "var(--chart-sky)" }}>
            <MapPin className="h-5 w-5 opacity-80" />
            <div className="mt-4 font-data-lg leading-none">
              <NumberTicker value={activeZones} duration={0.7} />
            </div>
            <p className="mt-2 font-label-sm opacity-80">Active zones</p>
          </div>
          <div className="rounded-2xl p-6 text-white shadow-[0_12px_30px_-10px_rgba(251,146,60,0.5)]" style={{ background: "var(--chart-amber)" }}>
            <DollarSign className="h-5 w-5 opacity-80" />
            <div className="mt-4 font-data-lg leading-none">
              {weightedFare > 0 ? `$${weightedFare.toFixed(2)}` : "—"}
            </div>
            <p className="mt-2 font-label-sm opacity-80">Avg fare</p>
          </div>
        </div>
        <p className="mt-4 font-body-sm text-ink-secondary">
          Aggregated from TLC high-volume for-hire trip records into the
          <span className="text-ink-primary"> zone_hourly_demand</span> mart.
        </p>
      </section>

      {/* BUSIEST ZONES -- real rows from the mart, ranked */}
      <section className="gsap-reveal mt-16 sm:mt-24 mb-4">
        <span className="font-label-sm text-ink-muted tracking-wider">Busiest Pickup Zones</span>
        <div className="mt-6 flex flex-col gap-3">
          {topZones.length === 0 && (
            <Card className="p-6 text-center font-body-sm text-ink-muted">
              No demand data loaded — start the backend to populate this.
            </Card>
          )}
          {topZones.map((zone, i) => (
            <Card key={zone.location_id} className="flex items-baseline gap-4 p-4">
              <span className="font-display-md w-10 shrink-0 text-brass">
                {String(i + 1).padStart(2, "0")}
              </span>
              <div className="min-w-0 flex-1">
                <h3 className="font-section-md truncate text-ink-primary">{zone.zone}</h3>
                <span className="font-label-sm text-ink-muted">{zone.borough}</span>
              </div>
              <div className="shrink-0 text-right">
                <div className="font-mono text-sm text-ink-primary">
                  {zone.total_trips.toLocaleString()}
                </div>
                <div className="font-label-sm text-ink-muted">trips</div>
              </div>
            </Card>
          ))}
        </div>
      </section>
    </div>
  );
}

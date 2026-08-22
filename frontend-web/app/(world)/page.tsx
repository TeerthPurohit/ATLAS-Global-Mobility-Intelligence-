"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { MapPin, TrendingUp, DollarSign, ArrowRight } from "lucide-react";
import { ZoneMap } from "@/components/nyc/ZoneMap";
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

        {/* Legibility scrims -- text only, map stays readable underneath */}
        <div className="pointer-events-none absolute inset-x-0 top-0 h-72 bg-gradient-to-b from-surface-0/85 via-surface-0/15 to-transparent" />
        <div className="pointer-events-none absolute inset-x-0 bottom-0 h-32 bg-gradient-to-t from-surface-0/50 to-transparent" />

        {/* Coordinate-grid viewfinder brackets */}
        <div className="pointer-events-none absolute top-3 left-3 h-3 w-3 border-t border-l border-brass/30" />
        <div className="pointer-events-none absolute top-3 right-3 h-3 w-3 border-t border-r border-brass/30" />
        <div className="pointer-events-none absolute bottom-3 left-3 h-3 w-3 border-b border-l border-brass/30" />
        <div className="pointer-events-none absolute bottom-3 right-3 h-3 w-3 border-b border-r border-brass/30" />

        {/* Hero copy -- floats over the map, not above it */}
        <div className="absolute left-6 top-[104px] z-10 max-w-[19rem] sm:left-10 sm:top-[132px] sm:max-w-md">
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
          <Link
            href="/journey"
            className="mt-6 inline-flex items-center gap-2 border-b border-brass/40 pb-1 font-label-sm text-brass transition-colors hover:border-brass"
          >
            Plan a journey
            <ArrowRight className="h-3.5 w-3.5" />
          </Link>
        </div>
      </section>

      {/* DATA STORY -- editorial numbers, not cards */}
      <section className="gsap-reveal mt-16 sm:mt-24">
        <span className="font-label-sm text-brass tracking-wider">Measured Coverage</span>
        <div className="mt-5 flex flex-col gap-10 md:flex-row md:items-end md:justify-between">
          <div>
            <div className="font-display-xl text-ink-primary leading-none">
              <NumberTicker value={totalTrips} duration={0.9} />
            </div>
            <div className="mt-3 flex items-center gap-2 font-label-sm text-ink-muted">
              <TrendingUp className="h-3.5 w-3.5 text-brass" />
              Trips in the warehouse
            </div>
            <p className="mt-2 max-w-sm font-body-sm text-ink-secondary">
              Aggregated from TLC high-volume for-hire trip records into the
              <span className="text-ink-primary"> zone_hourly_demand</span> mart.
            </p>
          </div>

          <div className="flex gap-10 sm:gap-16">
            <div>
              <div className="font-data-lg text-brass">
                <NumberTicker value={activeZones} duration={0.7} />
              </div>
              <div className="mt-1 flex items-center gap-1.5 font-label-sm text-ink-muted">
                <MapPin className="h-3.5 w-3.5" />
                Active zones
              </div>
            </div>
            <div>
              <div className="font-data-lg text-verdigris">
                ${weightedFare.toFixed(2)}
              </div>
              <div className="mt-1 flex items-center gap-1.5 font-label-sm text-ink-muted">
                <DollarSign className="h-3.5 w-3.5" />
                Avg fare
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* BUSIEST ZONES -- real rows from the mart, ranked */}
      <section className="gsap-reveal mt-16 sm:mt-24 mb-4">
        <span className="font-label-sm text-ink-muted tracking-wider">Busiest Pickup Zones</span>
        <div className="mt-6 divide-y divide-surface-border border-t border-surface-border">
          {topZones.length === 0 && (
            <p className="py-6 font-body-sm text-ink-muted">
              No demand data loaded — start the backend to populate this.
            </p>
          )}
          {topZones.map((zone, i) => (
            <div key={zone.location_id} className="flex items-baseline gap-4 py-4">
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
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}

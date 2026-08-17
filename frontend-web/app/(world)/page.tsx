"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { WorldMap } from "@/components/world/WorldMap";
import { SearchBar } from "@/components/world/SearchBar";
import { Globe, MapPin, TrendingUp, Layers, ArrowRight } from "lucide-react";
import { getCountries, searchCities } from "@/lib/api";
import { queryKeys } from "@/lib/queryKeys";
import { useGsapEntrance } from "@/hooks/useGsapEntrance";
import { NumberTicker } from "@/components/magic/NumberTicker";
import { cn } from "@/lib/utils";

const TIER_STEPS = [
  {
    id: "OBSERVED",
    index: "01",
    label: "Observed Tier",
    sub: "Local telemetry",
    desc: "Cities with trained models based on local telemetry data. These locations have the highest prediction accuracy.",
    color: "text-brass",
    hoverBg: "hover:bg-brass/5",
  },
  {
    id: "TRANSFER",
    index: "02",
    label: "Transfer Tier",
    sub: "Similar cities",
    desc: "Cities modeled using transfer learning from similar urban environments. Provides reliable baseline predictions.",
    color: "text-sky-400",
    hoverBg: "hover:bg-sky-400/5",
  },
  {
    id: "NONE",
    index: "03",
    label: "Routing Only",
    sub: "Network analysis",
    desc: "Cities with routing capabilities. Predictions based on geographic and network analysis.",
    color: "text-oxide",
    hoverBg: "hover:bg-oxide/5",
  },
] as const;

export default function WorldPage() {
  const containerRef = useGsapEntrance(".gsap-reveal", { stagger: 0.1, yOffset: 20 });
  const [highlightedTier, setHighlightedTier] = useState<string | null>(null);

  const { data: countries } = useQuery({
    queryKey: queryKeys.countries(),
    queryFn: getCountries,
  });

  const { data: citiesData } = useQuery({
    queryKey: queryKeys.cities({ limit: 1000 }),
    queryFn: () => searchCities({ limit: 1000 }),
  });

  const totalCountries = countries?.length || 0;
  const totalCities = citiesData?.total || 0;

  const tierCounts = citiesData?.results.reduce(
    (acc, city) => {
      acc[city.model_status as keyof typeof acc] = (acc[city.model_status as keyof typeof acc] || 0) + 1;
      return acc;
    },
    { OBSERVED: 0, TRANSFER: 0, NONE: 0 } as Record<string, number>
  ) || { OBSERVED: 0, TRANSFER: 0, NONE: 0 };

  return (
    <div ref={containerRef} className="overflow-x-hidden">
      {/* IMMERSIVE MAP HERO -- the map is the page. Full-bleed, bleeds up under the transparent navbar. */}
      <section className="relative -mx-4 -mt-24 h-[100dvh] overflow-hidden border-b border-surface-border sm:-mx-6 sm:-mt-28 xl:mx-[calc(50%-50vw)]">
        <WorldMap highlightedTier={highlightedTier} />

        {/* Legibility scrims -- text only, map stays readable underneath */}
        <div className="pointer-events-none absolute inset-x-0 top-0 h-72 bg-gradient-to-b from-surface-0/85 via-surface-0/15 to-transparent" />
        <div className="pointer-events-none absolute inset-x-0 bottom-0 h-32 bg-gradient-to-t from-surface-0/50 to-transparent" />

        {/* Coordinate-grid viewfinder brackets */}
        <div className="pointer-events-none absolute top-3 left-3 h-3 w-3 border-t border-l border-brass/30" />
        <div className="pointer-events-none absolute top-3 right-3 h-3 w-3 border-t border-r border-brass/30" />
        <div className="pointer-events-none absolute bottom-3 left-3 h-3 w-3 border-b border-l border-brass/30" />
        <div className="pointer-events-none absolute bottom-3 right-3 h-3 w-3 border-b border-r border-brass/30" />

        {/* Hero copy + search -- floats over the map, not above it */}
        <div className="absolute left-6 top-[104px] z-10 max-w-[19rem] sm:left-10 sm:top-[132px] sm:max-w-md">
          <span className="font-label-sm text-brass tracking-wider">Global Mobility Analysis</span>
          <h1 className="mt-3 font-display-lg uppercase leading-[1.05] tracking-tight text-ink-primary sm:font-display-xl">
            The world,
            <br />
            mapped by how
            <br />
            cities move.
          </h1>
          <p className="mt-4 font-body-sm text-ink-secondary max-w-xs">
            Live ATLAS coverage across cities and countries — observed telemetry, transfer
            learning, and routing intelligence in one network.
          </p>
          <div className="mt-6 max-w-xs sm:max-w-sm">
            <SearchBar variant="command" placeholder="Search the global network..." />
          </div>
        </div>
      </section>

      {/* DATA STORY -- editorial numbers, not cards */}
      <section className="gsap-reveal mt-16 sm:mt-24">
        <span className="font-label-sm text-brass tracking-wider">Global Coverage</span>
        <div className="mt-5 flex flex-col gap-10 md:flex-row md:items-end md:justify-between">
          <div>
            <div className="font-display-xl text-ink-primary leading-none">
              <NumberTicker value={totalCities} duration={0.9} />
            </div>
            <div className="mt-3 flex items-center gap-2 font-label-sm text-ink-muted">
              <MapPin className="h-3.5 w-3.5 text-brass" />
              Supported Cities
            </div>
            <p className="mt-2 max-w-sm font-body-sm text-ink-secondary">
              Spanning <span className="text-ink-primary">{totalCountries}</span> active countries
              in the ATLAS registry.
              <span className="ml-1 inline-flex items-center gap-1 text-ink-muted">
                <Globe className="h-3 w-3" />
              </span>
            </p>
          </div>

          <div className="flex gap-10 sm:gap-16">
            <div>
              <div className="font-data-lg text-brass">
                <NumberTicker value={tierCounts.OBSERVED} duration={0.7} />
              </div>
              <div className="mt-1 flex items-center gap-1.5 font-label-sm text-ink-muted">
                <TrendingUp className="h-3.5 w-3.5" />
                Observed
              </div>
            </div>
            <div>
              <div className="font-data-lg text-sky-400">
                <NumberTicker value={tierCounts.TRANSFER} duration={0.8} />
              </div>
              <div className="mt-1 flex items-center gap-1.5 font-label-sm text-ink-muted">
                <Layers className="h-3.5 w-3.5" />
                Transfer
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* INTELLIGENCE MODEL -- connected progression, hover emphasizes the tier on the map above */}
      <section className="gsap-reveal mt-16 sm:mt-24 mb-4">
        <span className="font-label-sm text-ink-muted tracking-wider">How ATLAS Understands a City</span>
        <div className="mt-6 flex flex-col md:flex-row md:items-start">
          {TIER_STEPS.map((step, i) => (
            <div key={step.id} className="flex flex-1 items-start md:contents">
              <button
                type="button"
                onMouseEnter={() => setHighlightedTier(step.id)}
                onMouseLeave={() => setHighlightedTier(null)}
                onFocus={() => setHighlightedTier(step.id)}
                onBlur={() => setHighlightedTier(null)}
                className={cn(
                  "flex-1 flex flex-col gap-2 text-left rounded-sm p-4 -m-4 transition-colors focus:outline-none focus-visible:bg-surface-1",
                  step.hoverBg
                )}
              >
                <span className={cn("font-display-md", step.color)}>{step.index}</span>
                <h3 className="font-section-md text-ink-primary">{step.label}</h3>
                <span className="font-label-sm text-ink-muted">{step.sub}</span>
                <p className="font-body-sm text-ink-secondary">{step.desc}</p>
              </button>

              {i < TIER_STEPS.length - 1 && (
                <div className="hidden md:flex items-center px-4 pt-10 shrink-0">
                  <span className="h-px w-8 bg-surface-border" />
                  <ArrowRight className="h-4 w-4 text-ink-muted mx-2 shrink-0" />
                  <span className="h-px w-8 bg-surface-border" />
                </div>
              )}
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}

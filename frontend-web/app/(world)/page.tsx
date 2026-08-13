"use client";

import { useQuery } from "@tanstack/react-query";
import { SearchBar } from "@/components/world/SearchBar";
import { WorldMap } from "@/components/world/WorldMap";
import { Card } from "@/components/ui/Card";
import { Globe, MapPin, TrendingUp, Layers } from "lucide-react";
import { getCountries, searchCities } from "@/lib/api";
import { queryKeys } from "@/lib/queryKeys";
import { useGsapEntrance } from "@/hooks/useGsapEntrance";
import { NumberTicker } from "@/components/magic/NumberTicker";

export default function WorldPage() {
  const containerRef = useGsapEntrance(".gsap-reveal", { stagger: 0.1, yOffset: 20 });

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
    <div ref={containerRef} className="flex flex-col gap-12">
      {/* Editorial Header */}
      <section className="gsap-reveal flex flex-col gap-6">
        <div className="flex flex-col gap-3">
          <span className="font-label-sm text-brass tracking-wider">
            Global Coverage
          </span>
          <h1 className="font-display-lg text-ink-primary">
            Global City Mobility Intelligence
          </h1>
          <p className="font-body-md max-w-2xl text-ink-secondary">
            Explore supported cities worldwide. Each location displays its intelligence tier: trained on local telemetry, modeled from global patterns, or routing-only.
          </p>
        </div>

        {/* Search Bar */}
        <div className="w-full max-w-md">
          <SearchBar placeholder="Search cities..." />
        </div>
      </section>

      {/* Hero Map Container */}
      <section className="gsap-reveal">
        <div className="relative h-[600px] overflow-hidden border border-surface-border bg-surface-1">
          <WorldMap />
          {/* Subtle overlay gradient */}
          <div className="absolute inset-0 pointer-events-none bg-gradient-to-t from-surface-0/20 via-transparent to-transparent" />
        </div>
      </section>

      {/* Divider */}
      <div className="gsap-reveal separator-line" />

      {/* Key Metrics Grid */}
      <section className="gsap-reveal">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8">
          {/* Total Countries */}
          <div className="flex flex-col gap-3">
            <div className="flex items-center gap-2">
              <Globe className="h-4 w-4 text-brass" />
              <span className="font-label-sm text-ink-muted">Active Countries</span>
            </div>
            <div className="font-data-lg text-brass">
              {totalCountries > 0 ? <NumberTicker value={totalCountries} duration={1.2} /> : "—"}
            </div>
          </div>

          {/* Total Cities */}
          <div className="flex flex-col gap-3">
            <div className="flex items-center gap-2">
              <MapPin className="h-4 w-4 text-verdigris" />
              <span className="font-label-sm text-ink-muted">Supported Cities</span>
            </div>
            <div className="font-data-lg text-verdigris">
              {totalCities > 0 ? <NumberTicker value={totalCities} duration={1.4} /> : "—"}
            </div>
          </div>

          {/* OBSERVED Tier */}
          <div className="flex flex-col gap-3">
            <div className="flex items-center gap-2">
              <TrendingUp className="h-4 w-4 text-brass" />
              <span className="font-label-sm text-ink-muted">Observed Tier</span>
            </div>
            <div className="font-data-lg text-brass">
              {tierCounts.OBSERVED > 0 ? <NumberTicker value={tierCounts.OBSERVED} duration={1} /> : "0"}
            </div>
          </div>

          {/* TRANSFER Tier */}
          <div className="flex flex-col gap-3">
            <div className="flex items-center gap-2">
              <Layers className="h-4 w-4 text-verdigris" />
              <span className="font-label-sm text-ink-muted">Transfer Tier</span>
            </div>
            <div className="font-data-lg text-verdigris">
              {tierCounts.TRANSFER > 0 ? <NumberTicker value={tierCounts.TRANSFER} duration={1.1} /> : "0"}
            </div>
          </div>
        </div>
      </section>

      {/* Information Section */}
      <section className="gsap-reveal">
        <div className="separator-line mb-8" />
        <div className="grid grid-cols-1 md:grid-cols-3 gap-12">
          <div className="flex flex-col gap-3">
            <h3 className="font-section-md text-ink-primary">Observed Tier</h3>
            <p className="font-body-sm text-ink-secondary">
              Cities with trained models based on local telemetry data. These locations have the highest prediction accuracy.
            </p>
          </div>
          <div className="flex flex-col gap-3">
            <h3 className="font-section-md text-ink-primary">Transfer Tier</h3>
            <p className="font-body-sm text-ink-secondary">
              Cities modeled using transfer learning from similar urban environments. Provides reliable baseline predictions.
            </p>
          </div>
          <div className="flex flex-col gap-3">
            <h3 className="font-section-md text-ink-primary">Routing Only</h3>
            <p className="font-body-sm text-ink-secondary">
              Cities with routing capabilities. Predictions based on geographic and network analysis.
            </p>
          </div>
        </div>
      </section>
    </div>
  );
}

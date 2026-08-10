"use client";

import { useQuery } from "@tanstack/react-query";
import { SearchBar } from "@/components/world/SearchBar";
import { WorldMap } from "@/components/world/WorldMap";
import { Card } from "@/components/ui/Card";
import { Compass, Globe, MapPin, Layers, TrendingUp } from "lucide-react";
import { getCountries, searchCities } from "@/lib/api";
import { queryKeys } from "@/lib/queryKeys";

export default function WorldPage() {
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
    <div className="flex flex-col gap-6">
      {/* Hero Header */}
      <section className="flex flex-col gap-4">
        <div className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-4">
          <div>
            <span className="flex items-center gap-2 text-xs uppercase tracking-widest text-brass font-mono font-semibold">
              <Compass className="h-4 w-4 text-brass" />
              Global Mobility Intelligence Platform
            </span>
            <h1 className="mt-2 font-display text-3xl font-bold leading-tight text-ink-primary sm:text-4xl">
              Global City Mobility Coverage
            </h1>
            <p className="mt-1 max-w-2xl text-sm sm:text-base text-ink-secondary">
              Browse supported global cities by country. Each city displays its mobility intelligence tier: trained on local telemetry, modeled from WorldMove priors, or routing-only.
            </p>
          </div>
          <div className="w-full sm:w-96">
            <SearchBar placeholder="Search cities (e.g., London, Tokyo, Mumbai)..." />
          </div>
        </div>
      </section>

      {/* World Map Container */}
      <section>
        <Card className="h-[550px] overflow-hidden p-0 border border-surface-border">
          <WorldMap />
        </Card>
      </section>

      {/* Dynamic Metrics Bar */}
      <section className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card className="flex flex-col items-center justify-center gap-1.5 p-5 text-center border border-surface-border bg-surface-1/40">
          <Globe className="h-5 w-5 text-brass mb-1" />
          <div className="font-mono text-3xl font-bold text-brass" id="stat-countries">
            {totalCountries || "—"}
          </div>
          <div className="text-xs font-medium text-ink-muted">Active Countries</div>
        </Card>

        <Card className="flex flex-col items-center justify-center gap-1.5 p-5 text-center border border-surface-border bg-surface-1/40">
          <MapPin className="h-5 w-5 text-verdigris mb-1" />
          <div className="font-mono text-3xl font-bold text-verdigris" id="stat-cities">
            {totalCities || "—"}
          </div>
          <div className="text-xs font-medium text-ink-muted">Supported Cities</div>
        </Card>

        <Card className="flex flex-col items-center justify-center gap-1.5 p-5 text-center border border-surface-border bg-surface-1/40">
          <TrendingUp className="h-5 w-5 text-brass mb-1" />
          <div className="font-mono text-3xl font-bold text-brass" id="stat-observed">
            {tierCounts.OBSERVED}
          </div>
          <div className="text-xs font-medium text-ink-muted">OBSERVED Tier Cities</div>
        </Card>

        <Card className="flex flex-col items-center justify-center gap-1.5 p-5 text-center border border-surface-border bg-surface-1/40">
          <Layers className="h-5 w-5 text-verdigris mb-1" />
          <div className="font-mono text-3xl font-bold text-verdigris" id="stat-transfer">
            {tierCounts.TRANSFER}
          </div>
          <div className="text-xs font-medium text-ink-muted">TRANSFER Tier Cities</div>
        </Card>
      </section>
    </div>
  );
}
"use client";

import { useState } from "react";
import { Card, CardTitle } from "@/components/ui/Card";
import { TierBadge } from "@/components/capability/TierBadge";
import { useQuery } from "@tanstack/react-query";
import { searchCities, type City } from "@/lib/api";
import { queryKeys } from "@/lib/queryKeys";
import { cn } from "@/lib/utils";
import { useRouter } from "next/navigation";
import { MapPin, TrendingUp, Zap, ArrowRight, Filter, Search, Globe } from "lucide-react";

const TIER_CARD_STYLES: Record<string, { bg: string; border: string; hover: string }> = {
  OBSERVED: {
    bg: "bg-surface-1/60",
    border: "border-brass/30",
    hover: "hover:border-brass/60 hover:bg-surface-1",
  },
  TRANSFER: {
    bg: "bg-surface-1/60",
    border: "border-verdigris/30",
    hover: "hover:border-verdigris/60 hover:bg-surface-1",
  },
  NONE: {
    bg: "bg-surface-1/40",
    border: "border-surface-border",
    hover: "hover:border-oxide/40 hover:bg-surface-1",
  },
};

interface CityCardProps {
  city: City;
  onClick: () => void;
}

function CityCard({ city, onClick }: CityCardProps) {
  const style = TIER_CARD_STYLES[city.model_status] || TIER_CARD_STYLES.NONE;

  return (
    <button
      onClick={onClick}
      className={cn(
        "group relative flex flex-col justify-between rounded-xl border p-5 text-left transition-all duration-200 min-h-[160px]",
        style.bg,
        style.border,
        style.hover
      )}
    >
      <div>
        <div className="flex items-start justify-between gap-2 mb-2">
          <div>
            <h3 className="font-display text-base font-semibold text-ink-primary group-hover:text-brass transition-colors">
              {city.name}
            </h3>
            <p className="text-xs text-ink-muted font-mono uppercase tracking-wider mt-0.5">
              {city.country_code} &bull; {city.id}
            </p>
          </div>
          <TierBadge tier={city.model_status} size="sm" />
        </div>

        <div className="mt-3 flex flex-wrap items-center gap-1.5 text-[11px] text-ink-secondary">
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-surface-2/60 border border-surface-border">
            <Globe className="h-3 w-3 text-brass" />
            {city.geography_type}
          </span>
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-surface-2/60 border border-surface-border">
            <TrendingUp className="h-3 w-3 text-verdigris" />
            {city.mobility_mode}
          </span>
        </div>
      </div>

      <div className="mt-4 pt-3 border-t border-surface-border/60 flex items-center justify-between text-xs text-ink-muted">
        <span className="font-mono text-[11px]">
          {city.model_status === "OBSERVED" ? "Model: local trip data" : city.model_status === "TRANSFER" ? "Model: WorldMove transfer" : "Routing + context only"}
        </span>
        <ArrowRight className="h-4 w-4 text-ink-muted transition-transform group-hover:translate-x-1 group-hover:text-brass" />
      </div>
    </button>
  );
}

interface FilterBarProps {
  searchQuery: string;
  onSearchChange: (q: string) => void;
  selectedTier: string | null;
  onTierChange: (tier: string | null) => void;
}

function FilterBar({ searchQuery, onSearchChange, selectedTier, onTierChange }: FilterBarProps) {
  return (
    <Card className="flex flex-col sm:flex-row items-center gap-3 p-3.5 border border-surface-border bg-surface-0/80">
      <div className="relative flex-1 w-full">
        <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-ink-muted" />
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => onSearchChange(e.target.value)}
          placeholder="Filter cities by name or ID..."
          className="w-full pl-10 pr-4 py-2 rounded-lg bg-surface-1 border border-surface-border text-sm text-ink-primary placeholder-ink-muted focus:outline-none focus:ring-2 focus:ring-brass/50"
        />
      </div>

      <div className="flex items-center gap-2 w-full sm:w-auto">
        <Filter className="h-4 w-4 text-ink-muted shrink-0 hidden sm:block" />
        <select
          value={selectedTier || ""}
          onChange={(e) => onTierChange(e.target.value || null)}
          className="w-full sm:w-44 px-3 py-2 rounded-lg bg-surface-1 border border-surface-border text-xs text-ink-primary focus:outline-none focus:ring-2 focus:ring-brass/50"
        >
          <option value="">All Tiers</option>
          <option value="OBSERVED">OBSERVED (Local Data)</option>
          <option value="TRANSFER">TRANSFER (WorldMove)</option>
          <option value="NONE">NONE (Routing Only)</option>
        </select>
      </div>
    </Card>
  );
}

export function CityGrid({ countryCode }: { countryCode: string }) {
  const router = useRouter();
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedTier, setSelectedTier] = useState<string | null>(null);

  const { data, isLoading, error } = useQuery({
    queryKey: queryKeys.cities({ country: countryCode, tier: selectedTier, q: searchQuery || undefined }),
    queryFn: () => searchCities({ country: countryCode, tier: selectedTier || undefined, q: searchQuery || undefined }),
  });

  const filteredCities = data?.results.filter((city) => {
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      return city.name.toLowerCase().includes(q) || city.id.toLowerCase().includes(q);
    }
    return true;
  });

  if (isLoading) {
    return (
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
        {Array.from({ length: 8 }).map((_, i) => (
          <div key={i} className="h-44 rounded-xl bg-surface-1 animate-pulse border border-surface-border" />
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <Card className="border-dashed border-oxide/40 bg-oxide/5 p-8 text-center text-oxide">
        <p className="font-display text-base font-semibold">Failed to Load Cities</p>
        <p className="mt-1 text-xs text-ink-muted">Unable to retrieve city directory for country: {countryCode}</p>
      </Card>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      <FilterBar
        searchQuery={searchQuery}
        onSearchChange={setSearchQuery}
        selectedTier={selectedTier}
        onTierChange={setSelectedTier}
      />

      {filteredCities && filteredCities.length > 0 ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {filteredCities.map((city) => (
            <CityCard
              key={city.id}
              city={city}
              onClick={() => router.push(`/city/${city.id}`)}
            />
          ))}
        </div>
      ) : (
        <Card className="py-12 text-center text-ink-muted border border-surface-border">
          <p className="font-display text-sm font-semibold">No Cities Match Criteria</p>
          <p className="mt-1 text-xs text-ink-muted">Try clearing search filters or tier selections.</p>
        </Card>
      )}
    </div>
  );
}
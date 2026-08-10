"use client";

import Map from "react-map-gl/maplibre";
import "maplibre-gl/dist/maplibre-gl.css";
import { Card, CardTitle } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { useQuery } from "@tanstack/react-query";
import { getCountries, type Country } from "@/lib/api";
import { queryKeys } from "@/lib/queryKeys";
import { cn } from "@/lib/utils";
import { useRouter } from "next/navigation";
import { Globe, MapPin } from "lucide-react";

const MAP_STYLE = {
  version: 8 as const,
  sources: {
    osm: {
      type: "vector" as const,
      url: "https://vectortiles.openmaptiles.org/osm.json",
      attribution: "&copy; OpenMapTiles &copy; OpenStreetMap contributors",
    },
  },
  layers: [
    {
      id: "background",
      type: "background" as const,
      paint: { "background-color": "var(--surface-0)" },
    },
    {
      id: "water",
      type: "fill" as const,
      source: "osm",
      "source-layer": "water",
      paint: { "fill-color": "#121b2e", "fill-opacity": 0.9 },
    },
    {
      id: "land",
      type: "fill" as const,
      source: "osm",
      "source-layer": "landuse",
      paint: { "fill-color": "var(--surface-1)", "fill-opacity": 0.5 },
    },
    {
      id: "country-boundary",
      type: "line" as const,
      source: "osm",
      "source-layer": "boundary",
      filter: ["==", "boundary", "administrative"],
      paint: { "line-color": "var(--surface-border)", "line-width": 1, "line-opacity": 0.6 },
    },
    {
      id: "country-label",
      type: "symbol" as const,
      source: "osm",
      "source-layer": "place",
      filter: ["in", "class", "country"],
      layout: {
        "text-field": ["get", "name"],
        "text-font": ["Inter Medium"],
        "text-size": 13,
        "text-anchor": "center",
      },
      paint: {
        "text-color": "var(--ink-secondary)",
        "text-halo-color": "var(--surface-0)",
        "text-halo-width": 2,
      },
    },
  ],
};

const TIER_COLORS: Record<string, { bg: string; border: string; text: string; ring: string }> = {
  OBSERVED: { bg: "bg-brass/10", border: "border-brass/30", text: "text-brass", ring: "var(--brass)" },
  TRANSFER: { bg: "bg-verdigris/10", border: "border-verdigris/30", text: "text-verdigris", ring: "var(--verdigris)" },
  NONE: { bg: "bg-oxide/10", border: "border-oxide/30", text: "text-oxide", ring: "var(--oxide)" },
};

interface CountryClusterProps {
  country: Country;
  onClick: () => void;
}

function CountryCluster({ country, onClick }: CountryClusterProps) {
  const colors = TIER_COLORS[country.supported ? "OBSERVED" : "NONE"];
  return (
    <button
      onClick={onClick}
      className={cn(
        "rounded-xl p-3 transition-all hover:scale-[1.02] text-left w-full border",
        colors.bg,
        colors.border
      )}
    >
      <div className="flex items-center justify-between gap-2">
        <div>
          <p className={cn("font-semibold text-xs sm:text-sm", colors.text)}>{country.name}</p>
          <p className="text-[11px] text-ink-muted mt-0.5 flex items-center gap-1">
            <MapPin className="h-3 w-3" />
            {country.supported_city_count} {country.supported_city_count === 1 ? "city" : "cities"}
          </p>
        </div>
        <Badge basis={country.supported ? "computed" : "unavailable"} className="shrink-0 text-[10px]">
          {country.supported ? "Active" : "Planned"}
        </Badge>
      </div>
    </button>
  );
}

function TierLegend() {
  return (
    <Card className="absolute bottom-4 right-4 w-60 z-10 p-3.5 border border-surface-border bg-surface-0/90 backdrop-blur">
      <CardTitle className="font-display text-xs tracking-wider uppercase text-brass font-mono">
        City Tier Spectrum
      </CardTitle>
      <div className="mt-2.5 flex flex-col gap-2 text-xs">
        {[
          { tier: "OBSERVED", label: "Trained on local telemetry" },
          { tier: "TRANSFER", label: "WorldMove prior + pop scaled" },
          { tier: "NONE", label: "OSRM route + context only" },
        ].map(({ tier, label }) => {
          const colors = TIER_COLORS[tier];
          return (
            <div key={tier} className="flex items-center gap-2">
              <span className={cn("w-5 h-5 rounded-full border flex items-center justify-center shrink-0", colors.border, colors.bg)}>
                <svg width={8} height={8} viewBox="0 0 10 10">
                  <circle cx={5} cy={5} r={3} fill="none" stroke={colors.ring} strokeWidth={1.5} strokeDasharray={tier === "TRANSFER" ? "2 2" : undefined} />
                </svg>
              </span>
              <div className="flex flex-col min-w-0">
                <span className={cn("font-semibold text-[11px]", colors.text)}>{tier}</span>
                <span className="text-[10px] text-ink-muted truncate">{label}</span>
              </div>
            </div>
          );
        })}
      </div>
    </Card>
  );
}

export function WorldMap() {
  const { data: countries, isLoading, error } = useQuery({
    queryKey: queryKeys.countries(),
    queryFn: getCountries,
  });
  const router = useRouter();

  if (isLoading) {
    return (
      <div className="h-full w-full flex items-center justify-center bg-surface-0 text-ink-muted text-sm font-mono animate-pulse">
        Initializing map vector engine...
      </div>
    );
  }

  if (error) {
    return (
      <div className="h-full w-full flex items-center justify-center bg-oxide/5 text-oxide text-sm p-6 text-center">
        Failed to initialize map tiles. Check internet connection.
      </div>
    );
  }

  return (
    <div className="relative h-full w-full">
      <Map
        initialViewState={{ longitude: 0, latitude: 22, zoom: 1.3 }}
        mapStyle={MAP_STYLE}
        style={{ width: "100%", height: "100%" }}
      />

      <TierLegend />

      {/* Floating Country Selector Drawer */}
      <div className="absolute top-4 left-4 z-10 max-w-[280px] w-full">
        <Card className="p-3.5 border border-surface-border bg-surface-0/90 backdrop-blur shadow-xl">
          <CardTitle className="font-display text-xs tracking-wider uppercase text-ink-muted font-mono flex items-center gap-1.5 mb-2.5">
            <Globe className="h-3.5 w-3.5 text-brass" />
            Global Territories ({countries?.length || 0})
          </CardTitle>
          <div className="flex flex-col gap-2 max-h-[380px] overflow-y-auto pr-1">
            {countries?.map((country) => (
              <CountryCluster
                key={country.iso_code}
                country={country}
                onClick={() => router.push(`/country/${country.iso_code.toLowerCase()}`)}
              />
            ))}
          </div>
        </Card>
      </div>
    </div>
  );
}
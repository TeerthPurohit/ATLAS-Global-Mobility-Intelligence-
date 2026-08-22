"use client";

/**
 * ZoneMap — the landing page's hero. All 263 NYC TLC taxi zones, shaded by
 * their real measured trip volume from `zone_hourly_demand` (ADR-011).
 *
 * Geometry is the TLC's own shapefile, converted once offline by
 * scripts/build_zone_geojson.py and served from /data/taxi_zones.geojson.
 * Demand comes from GET /marts/zone_demand_totals, which the backend
 * precomputes at startup — no per-request table scan (rule 8).
 */

import { useMemo, useState } from "react";
import MapGL, { Layer, Source, type MapLayerMouseEvent } from "react-map-gl/maplibre";
import "maplibre-gl/dist/maplibre-gl.css";
import { useQuery } from "@tanstack/react-query";
import { getZoneDemandTotals, type ZoneDemandTotal } from "@/lib/api";
import { queryKeys } from "@/lib/queryKeys";

const NYC_VIEW = { longitude: -73.95, latitude: 40.71, zoom: 10.1 };

const MAP_STYLE = "https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json";

interface HoveredZone {
  x: number;
  y: number;
  zone: string;
  borough: string;
  trips: number;
  avgFare: number | null;
}

export function ZoneMap() {
  const [hovered, setHovered] = useState<HoveredZone | null>(null);

  const { data: demand } = useQuery({
    queryKey: queryKeys.zoneDemandTotals(),
    queryFn: getZoneDemandTotals,
    staleTime: Infinity, // a precomputed mart, not live data
  });

  const byLocationId = useMemo(() => {
    const map = new Map<number, ZoneDemandTotal>();
    for (const row of demand ?? []) map.set(row.location_id, row);
    return map;
  }, [demand]);

  // Trip volume is heavily long-tailed (Midtown dwarfs Staten Island), so the
  // color ramp interpolates over sqrt(trips) — a linear ramp would render all
  // but a dozen zones as the same flat minimum.
  const maxSqrt = useMemo(() => {
    const max = Math.max(0, ...(demand ?? []).map((d) => d.total_trips));
    return Math.sqrt(max) || 1;
  }, [demand]);

  // maplibre can't join across sources, so demand rides along as a feature
  // property on the geometry itself.
  const { data: zones } = useQuery({
    queryKey: ["taxi-zones-geojson"],
    queryFn: async () => {
      const resp = await fetch("/data/taxi_zones.geojson");
      if (!resp.ok) throw new Error("failed to load zone geometry");
      return resp.json() as Promise<GeoJSON.FeatureCollection>;
    },
    staleTime: Infinity,
  });

  const shaded = useMemo(() => {
    if (!zones) return null;
    return {
      ...zones,
      features: zones.features.map((f) => {
        const row = byLocationId.get(f.properties?.location_id as number);
        const trips = row?.total_trips ?? 0;
        return {
          ...f,
          properties: {
            ...f.properties,
            trips,
            avg_fare: row?.avg_fare ?? null,
            intensity: Math.sqrt(trips) / maxSqrt,
          },
        };
      }),
    } as GeoJSON.FeatureCollection;
  }, [zones, byLocationId, maxSqrt]);

  function handleHover(e: MapLayerMouseEvent) {
    const f = e.features?.[0];
    if (!f) {
      setHovered(null);
      return;
    }
    setHovered({
      x: e.point.x,
      y: e.point.y,
      zone: (f.properties?.zone_name as string) ?? "Unknown",
      borough: (f.properties?.borough as string) ?? "",
      trips: (f.properties?.trips as number) ?? 0,
      avgFare: (f.properties?.avg_fare as number | null) ?? null,
    });
  }

  return (
    <div className="absolute inset-0">
      <MapGL
        initialViewState={NYC_VIEW}
        mapStyle={MAP_STYLE}
        interactiveLayerIds={["zone-fill"]}
        onMouseMove={handleHover}
        onMouseLeave={() => setHovered(null)}
        attributionControl={false}
        style={{ width: "100%", height: "100%" }}
      >
        {shaded && (
          <Source id="zones" type="geojson" data={shaded}>
            <Layer
              id="zone-fill"
              type="fill"
              paint={{
                "fill-color": [
                  "interpolate",
                  ["linear"],
                  ["get", "intensity"],
                  0, "#1a1a1a",
                  0.35, "#5a4418",
                  0.7, "#a3701c",
                  1, "#c9922a",
                ],
                "fill-opacity": 0.72,
              }}
            />
            <Layer
              id="zone-outline"
              type="line"
              paint={{ "line-color": "#c9922a", "line-width": 0.4, "line-opacity": 0.25 }}
            />
          </Source>
        )}
      </MapGL>

      {hovered && (
        <div
          className="pointer-events-none absolute z-20 rounded-sm border border-brass/40 bg-surface-0/95 px-3 py-2 shadow-lg backdrop-blur-sm"
          style={{ left: hovered.x + 12, top: hovered.y + 12 }}
        >
          <div className="font-label-sm text-ink-primary">{hovered.zone}</div>
          <div className="mt-0.5 font-mono text-[11px] text-ink-muted">{hovered.borough}</div>
          <div className="mt-1.5 font-mono text-xs text-brass">
            {hovered.trips.toLocaleString()} trips
          </div>
          {hovered.avgFare !== null && (
            <div className="font-mono text-[11px] text-ink-secondary">
              ${hovered.avgFare.toFixed(2)} avg fare
            </div>
          )}
        </div>
      )}
    </div>
  );
}

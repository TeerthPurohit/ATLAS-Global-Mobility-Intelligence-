"use client";

/**
 * ZoneMap — the landing page's hero. All 263 NYC TLC taxi zones, shaded by
 * their real measured trip volume from `zone_hourly_demand` (ADR-011).
 *
 * Geometry is the TLC's own shapefile, converted once offline by
 * scripts/build_zone_geojson.py and served from /data/taxi_zones.geojson.
 * Demand comes from GET /marts/zone_demand_totals, which the backend
 * precomputes at startup — no per-request table scan (rule 8).
 *
 * Interaction: the map opens zoomed out over the region and eases into the
 * city (entrance motion), a left rail filters zones by borough (real data,
 * not a fabricated POI-category list), and clicking zones drops a pickup
 * pin, then a dropoff pin, with a straight guide line between them — never
 * presented as a routed path — before handing both off to /journey.
 */

import { useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import MapGL, {
  Layer,
  Marker,
  NavigationControl,
  Source,
  type MapLayerMouseEvent,
  type MapRef,
} from "react-map-gl/maplibre";
import "maplibre-gl/dist/maplibre-gl.css";
import { useQuery } from "@tanstack/react-query";
import { X } from "lucide-react";
import { getZoneDemandTotals, type ZoneDemandTotal } from "@/lib/api";
import { queryKeys } from "@/lib/queryKeys";

const NYC_VIEW = { longitude: -73.95, latitude: 40.71, zoom: 10.1 };
const ENTRANCE_VIEW = { longitude: -73.95, latitude: 40.71, zoom: 7.1 };

const MAP_STYLE = "https://basemaps.cartocdn.com/gl/positron-gl-style/style.json";

interface HoveredZone {
  x: number;
  y: number;
  zone: string;
  borough: string;
  trips: number;
  avgFare: number | null;
}

interface Waypoint {
  locationId: number;
  lat: number;
  lon: number;
  name: string;
  borough: string;
}

export function ZoneMap() {
  const router = useRouter();
  const mapRef = useRef<MapRef | null>(null);
  const [hovered, setHovered] = useState<HoveredZone | null>(null);
  const [selectedBorough, setSelectedBorough] = useState<string | null>(null);
  const [pickup, setPickup] = useState<Waypoint | null>(null);
  const [dropoff, setDropoff] = useState<Waypoint | null>(null);

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

  // Real boroughs from the zone geometry itself — never a fabricated POI
  // category list (ATMs, cafes, bus stops) we have no data for.
  const boroughs = useMemo(() => {
    if (!shaded) return [];
    const counts = new Map<string, number>();
    for (const f of shaded.features) {
      const b = (f.properties?.borough as string) ?? "Unknown";
      counts.set(b, (counts.get(b) ?? 0) + 1);
    }
    return [...counts.entries()].sort((a, b) => b[1] - a[1]);
  }, [shaded]);

  const stats = useMemo(() => {
    const rows = selectedBorough
      ? (shaded?.features ?? []).filter((f) => f.properties?.borough === selectedBorough)
      : (shaded?.features ?? []);
    const trips = rows.reduce((sum, f) => sum + ((f.properties?.trips as number) ?? 0), 0);
    return { zoneCount: rows.length, trips };
  }, [shaded, selectedBorough]);

  const route = useMemo(() => {
    if (!pickup || !dropoff) return null;
    return {
      type: "Feature",
      properties: {},
      geometry: {
        type: "LineString",
        coordinates: [
          [pickup.lon, pickup.lat],
          [dropoff.lon, dropoff.lat],
        ],
      },
    } as GeoJSON.Feature<GeoJSON.LineString>;
  }, [pickup, dropoff]);

  function flyToBorough(borough: string | null) {
    const map = mapRef.current?.getMap();
    if (!map) return;
    if (!borough) {
      map.easeTo({ ...NYC_VIEW, duration: 1100 });
      return;
    }
    const features = (shaded?.features ?? []).filter((f) => f.properties?.borough === borough);
    if (features.length === 0) return;
    let minLon = Infinity, minLat = Infinity, maxLon = -Infinity, maxLat = -Infinity;
    for (const f of features) {
      const geom = f.geometry;
      const coords =
        geom.type === "Polygon" ? geom.coordinates.flat(1) : geom.type === "MultiPolygon" ? geom.coordinates.flat(2) : [];
      for (const c of coords as number[][]) {
        minLon = Math.min(minLon, c[0]);
        maxLon = Math.max(maxLon, c[0]);
        minLat = Math.min(minLat, c[1]);
        maxLat = Math.max(maxLat, c[1]);
      }
    }
    map.fitBounds([[minLon, minLat], [maxLon, maxLat]], { padding: 64, duration: 1100 });
  }

  function handleBoroughClick(borough: string) {
    const next = selectedBorough === borough ? null : borough;
    setSelectedBorough(next);
    flyToBorough(next);
  }

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

  function handleClick(e: MapLayerMouseEvent) {
    const f = e.features?.[0];
    if (!f) return;
    const point: Waypoint = {
      locationId: f.properties?.location_id as number,
      lat: e.lngLat.lat,
      lon: e.lngLat.lng,
      name: (f.properties?.zone_name as string) ?? "Unknown zone",
      borough: (f.properties?.borough as string) ?? "",
    };
    if (!pickup) {
      setPickup(point);
    } else if (!dropoff && point.locationId !== pickup.locationId) {
      setDropoff(point);
    } else {
      setPickup(point);
      setDropoff(null);
    }
  }

  function clearSelection() {
    setPickup(null);
    setDropoff(null);
  }

  function planJourney() {
    if (!pickup) return;
    const params = new URLSearchParams({
      pickupLat: String(pickup.lat),
      pickupLon: String(pickup.lon),
      pickupName: `${pickup.name}, ${pickup.borough}`,
    });
    if (dropoff) {
      params.set("dropoffLat", String(dropoff.lat));
      params.set("dropoffLon", String(dropoff.lon));
      params.set("dropoffName", `${dropoff.name}, ${dropoff.borough}`);
    }
    router.push(`/journey?${params.toString()}`);
  }

  return (
    <div className="absolute inset-0">
      <MapGL
        ref={mapRef}
        initialViewState={ENTRANCE_VIEW}
        mapStyle={MAP_STYLE}
        interactiveLayerIds={["zone-fill"]}
        cursor={hovered ? "pointer" : "grab"}
        onLoad={(e) => e.target.easeTo({ ...NYC_VIEW, duration: 2200, easing: (t) => t * (2 - t) })}
        onMouseMove={handleHover}
        onMouseLeave={() => setHovered(null)}
        onClick={handleClick}
        attributionControl={false}
        style={{ width: "100%", height: "100%" }}
      >
        <NavigationControl position="top-right" showCompass={false} />

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
                  0, "#e7e5fa",
                  0.35, "#b3aaf0",
                  0.7, "#8a78ea",
                  1, "#6c5ce7",
                ],
                "fill-opacity": selectedBorough
                  ? ["case", ["==", ["get", "borough"], selectedBorough], 0.85, 0.12]
                  : 0.75,
              }}
            />
            <Layer
              id="zone-outline"
              type="line"
              paint={{ "line-color": "#6c5ce7", "line-width": 0.4, "line-opacity": 0.3 }}
            />
          </Source>
        )}

        {route && (
          <Source id="route-line" type="geojson" data={route} lineMetrics>
            <Layer
              id="route-line-layer"
              type="line"
              layout={{ "line-cap": "round", "line-join": "round" }}
              paint={{
                "line-width": 2.5,
                "line-gradient": ["interpolate", ["linear"], ["line-progress"], 0, "#6c5ce7", 1, "#14b8a6"],
              }}
            />
          </Source>
        )}

        {pickup && (
          <Marker longitude={pickup.lon} latitude={pickup.lat}>
            <WaypointPin index={1} color="brass" label={pickup.name} />
          </Marker>
        )}
        {dropoff && (
          <Marker longitude={dropoff.lon} latitude={dropoff.lat}>
            <WaypointPin index={2} color="verdigris" label={dropoff.name} />
          </Marker>
        )}
      </MapGL>

      {/* Legibility scrims -- text only, map stays readable underneath */}
      <div className="pointer-events-none absolute inset-x-0 top-0 h-72 bg-gradient-to-b from-surface-0/85 via-surface-0/15 to-transparent" />
      <div className="pointer-events-none absolute inset-x-0 bottom-0 h-32 bg-gradient-to-t from-surface-0/50 to-transparent" />

      {/* Borough rail — real data, filters the shaded zones and flies to bounds */}
      {boroughs.length > 0 && (
        <nav className="pointer-events-auto absolute bottom-16 left-6 z-10 hidden flex-col gap-2 rounded-2xl border border-surface-border bg-surface-1/90 p-4 shadow-[0_8px_30px_-12px_rgba(108,92,231,0.25)] backdrop-blur-sm sm:bottom-20 sm:left-10 sm:flex">
          <button
            onClick={() => handleBoroughClick("")}
            className={`text-left font-label-sm tracking-wider transition-colors ${
              selectedBorough === null ? "text-brass" : "text-ink-muted hover:text-ink-secondary"
            }`}
          >
            All zones
          </button>
          {boroughs.map(([borough, count]) => (
            <button
              key={borough}
              onClick={() => handleBoroughClick(borough)}
              className={`text-left font-label-sm tracking-wider transition-colors ${
                selectedBorough === borough ? "text-brass" : "text-ink-muted hover:text-ink-secondary"
              }`}
            >
              {borough} <span className="font-mono text-[11px] text-ink-muted">({count})</span>
            </button>
          ))}
        </nav>
      )}

      {/* Bottom-left status strip — real measured coverage, not a weather widget */}
      <div className="pointer-events-none absolute bottom-4 left-6 z-10 rounded-full border border-surface-border bg-surface-1/90 px-3 py-1.5 font-mono text-[11px] text-ink-muted shadow-sm backdrop-blur-sm sm:left-10">
        {selectedBorough && <span className="text-brass">{selectedBorough} · </span>}
        {stats.zoneCount} zones · {stats.trips.toLocaleString()} trips measured
      </div>

      {/* Selection card -- appears once a pickup pin is set */}
      {pickup && (
        <div className="pointer-events-auto absolute bottom-4 right-4 z-20 w-64 rounded-2xl border border-surface-border bg-surface-1/95 p-3 shadow-[0_12px_36px_-12px_rgba(108,92,231,0.35)] backdrop-blur-sm sm:right-6">
          <div className="flex items-start justify-between gap-2">
            <div className="min-w-0">
              <div className="flex items-center gap-1.5 font-label-sm text-brass">
                <span className="flex h-3.5 w-3.5 items-center justify-center rounded-full bg-brass text-[9px] font-bold text-brass-fg">1</span>
                <span className="truncate">{pickup.name}</span>
              </div>
              {dropoff ? (
                <div className="mt-1 flex items-center gap-1.5 font-label-sm text-verdigris">
                  <span className="flex h-3.5 w-3.5 items-center justify-center rounded-full bg-verdigris text-[9px] font-bold text-surface-0">2</span>
                  <span className="truncate">{dropoff.name}</span>
                </div>
              ) : (
                <p className="mt-1 font-body-sm text-ink-muted">Click another zone for dropoff, or plan with pickup only.</p>
              )}
            </div>
            <button onClick={clearSelection} aria-label="Clear selection" className="shrink-0 text-ink-muted hover:text-ink-primary">
              <X className="h-3.5 w-3.5" />
            </button>
          </div>
          <button
            onClick={planJourney}
            className="mt-3 w-full rounded-xl bg-brass py-1.5 font-label-sm text-brass-fg transition-opacity hover:opacity-90"
          >
            Plan this journey
          </button>
        </div>
      )}

      {hovered && (
        <div
          className="pointer-events-none absolute z-20 rounded-xl border border-surface-border bg-surface-1/95 px-3 py-2 shadow-[0_12px_36px_-12px_rgba(108,92,231,0.35)] backdrop-blur-sm"
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

function WaypointPin({ index, color, label }: { index: number; color: "brass" | "verdigris"; label: string }) {
  const bg = color === "brass" ? "bg-brass" : "bg-verdigris";
  const fg = "text-white";
  const text = color === "brass" ? "text-brass" : "text-verdigris";
  return (
    <div className="flex flex-col items-center">
      <span className={`flex h-5 w-5 items-center justify-center rounded-full border-2 border-surface-1 text-[10px] font-bold shadow-lg ${bg} ${fg}`}>
        {index}
      </span>
      <div className="mt-1 max-w-[140px] truncate rounded-full bg-surface-1/95 px-2 py-0.5 text-center text-[10px] leading-tight shadow-md backdrop-blur-sm">
        <span className={text}>{label}</span>
      </div>
    </div>
  );
}

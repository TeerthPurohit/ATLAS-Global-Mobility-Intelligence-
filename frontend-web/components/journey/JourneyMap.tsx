"use client";

import { useMemo, useEffect, useRef, useState, useCallback } from "react";
import Map, { Marker, Layer, Source } from "react-map-gl/maplibre";
import "maplibre-gl/dist/maplibre-gl.css";
import maplibregl from "maplibre-gl";
import { Card } from "@/components/ui/Card";
import { cn } from "@/lib/utils";
import { useWebGLPreservation, useReducedMotion } from "@/hooks/useWebGLPreservation";
import { useReverseGeocode } from "@/hooks/useReverseGeocode";

interface JourneyMapProps {
  pickup: { lat: number; lon: number };
  dropoff: { lat: number; lon: number };
  routeGeometry?: GeoJSON.LineString | null;
  fitBounds?: boolean;
  className?: string;
  height?: number | string;
  /** When true, shows full-screen map on mobile with toggle */
  mobileFullScreen?: boolean;
}

const MAP_STYLE = {
  version: 8 as const,
  name: "Mobility Intelligence",
  metadata: { "mapbox:autocomposite": true },
  sources: {
    openmaptiles: {
      type: "vector" as const,
      url: "https://tiles.openfreemap.org/styles/liberty",
      attribution: "&copy; OpenMapTiles &copy; OpenStreetMap contributors",
    },
  },
  layers: [
    { id: "background", type: "background" as const, paint: { "background-color": "#0f0f0f" } },
    {
      id: "land",
      type: "fill" as const,
      source: "openmaptiles",
      "source-layer": "landuse",
      filter: ["in", "class", "park", "forest", "wood"],
      paint: { "fill-color": "#1a1a1a", "fill-opacity": 0.8 },
    },
    {
      id: "water",
      type: "fill" as const,
      source: "openmaptiles",
      "source-layer": "water",
      paint: { "fill-color": "#0d1b2a", "fill-opacity": 1 },
    },
    {
      id: "roads",
      type: "line" as const,
      source: "openmaptiles",
      "source-layer": "transportation",
      filter: ["in", "class", "motorway", "trunk", "primary", "secondary", "tertiary"],
      paint: {
        "line-color": "#2a2a2a",
        "line-width": ["interpolate", ["linear"], ["zoom"], 8, 0.5, 12, 1.5, 16, 3],
        "line-opacity": 0.6,
      },
    },
    {
      id: "road-labels",
      type: "symbol" as const,
      source: "openmaptiles",
      "source-layer": "transportation",
      filter: ["in", "class", "motorway", "trunk", "primary"],
      layout: {
        "text-field": ["get", "name"],
        "text-font": ["Open Sans Semibold"],
        "text-size": 10,
        "symbol-placement": "line",
      },
      paint: { "text-color": "#3a3a3a", "text-halo-color": "#0f0f0f", "text-halo-width": 1 },
    },
    {
      id: "place-labels",
      type: "symbol" as const,
      source: "openmaptiles",
      "source-layer": "place",
      filter: [">=", "rank", 10],
      layout: {
        "text-field": ["get", "name"],
        "text-font": ["Open Sans Regular"],
        "text-size": ["interpolate", ["linear"], ["zoom"], 8, 10, 12, 14],
      },
      paint: { "text-color": "#4a4a4a", "text-halo-color": "#0f0f0f", "text-halo-width": 1 },
    },
  ],
  glyphs: "https://fonts.openmaptiles.org/{fontstack}/{range}.pbf",
  sprite: "https://tiles.openfreemap.org/styles/liberty/sprite",
};

const ROUTE_LINE_LAYER: maplibregl.AddLayerObject = {
  id: "route-line",
  type: "line",
  source: "route-source",
  layout: { "line-join": "round", "line-cap": "round" },
  paint: {
    "line-color": "#c9922a",
    "line-width": ["interpolate", ["linear"], ["zoom"], 10, 3, 14, 6, 18, 10],
    "line-opacity": 0.9,
    "line-dasharray": [8, 4],
  },
};

const ROUTE_SOURCE_ID = "route-source";

export function JourneyMap({
  pickup,
  dropoff,
  routeGeometry,
  fitBounds = true,
  className,
  height = 320,
  mobileFullScreen = true,
}: JourneyMapProps) {
  const mapRef = useRef<maplibregl.Map | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [mapLoaded, setMapLoaded] = useState(false);
  const [routeAdded, setRouteAdded] = useState(false);
  const [isMobile, setIsMobile] = useState(false);
  const [isFullScreen, setIsFullScreen] = useState(false);
  const [viewport, setViewport] = useState({ width: 0, height: 0 });
  const [mapKey, setMapKey] = useState(0);

  // WebGL context preservation on tab switch
  const { enablePreservation, disablePreservation } = useWebGLPreservation(mapRef);

  // Reduced motion preference
  const reducedMotion = useReducedMotion();

  useEffect(() => {
    enablePreservation();
    return disablePreservation;
  }, [enablePreservation, disablePreservation]);

  const center = useMemo(
    () => ({
      longitude: (pickup.lon + dropoff.lon) / 2,
      latitude: (pickup.lat + dropoff.lat) / 2,
    }),
    [pickup, dropoff]
  );

  const bounds = useMemo(() => {
    if (!routeGeometry) return null;
    const coords = routeGeometry.coordinates;
    let minLon = coords[0][0], maxLon = coords[0][0];
    let minLat = coords[0][1], maxLat = coords[0][1];
    for (const [lon, lat] of coords) {
      minLon = Math.min(minLon, lon);
      maxLon = Math.max(maxLon, lon);
      minLat = Math.min(minLat, lat);
      maxLat = Math.max(maxLat, lat);
    }
    return [[minLon, minLat], [maxLon, maxLat]] as maplibregl.LngLatBoundsLike;
  }, [routeGeometry]);

  // Detect mobile
  useEffect(() => {
    const checkMobile = () => {
      const mobile = window.innerWidth < 768;
      setIsMobile(mobile);
      if (!mobile) setIsFullScreen(false);
    };
    checkMobile();
    window.addEventListener("resize", checkMobile);
    return () => window.removeEventListener("resize", checkMobile);
  }, []);

  // Track container size
  useEffect(() => {
    const resizeObserver = new ResizeObserver((entries) => {
      for (const entry of entries) {
        setViewport({ width: entry.contentRect.width, height: entry.contentRect.height });
      }
    });
    if (containerRef.current) {
      resizeObserver.observe(containerRef.current);
    }
    return () => resizeObserver.disconnect();
  }, []);

  // Initialize map
  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;

    const map = new maplibregl.Map({
      container: containerRef.current,
      style: "https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json",
      center: [center.longitude, center.latitude],
      zoom: 11,
      attributionControl: false,
      preserveDrawingBuffer: true,
      failIfMajorPerformanceCaveat: false,
    });

    map.addControl(new maplibregl.AttributionControl({ compact: true }), "bottom-right");
    map.addControl(new maplibregl.GeolocateControl({ positionOptions: { enableHighAccuracy: true }, trackUserLocation: false }), "top-right");

    map.on("load", () => {
      setMapLoaded(true);
      if (routeGeometry) {
        map.addSource(ROUTE_SOURCE_ID, { type: "geojson", data: routeGeometry });
        map.addLayer(ROUTE_LINE_LAYER as maplibregl.AddLayerObject);
        setRouteAdded(true);
      }
    });

    mapRef.current = map;

    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, []);

  // Update route when geometry changes
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !mapLoaded) return;

    if (routeGeometry) {
      const source = map.getSource(ROUTE_SOURCE_ID) as maplibregl.GeoJSONSource | undefined;
      if (source) {
        source.setData(routeGeometry);
      } else {
        map.addSource(ROUTE_SOURCE_ID, { type: "geojson", data: routeGeometry });
        if (!map.getLayer(ROUTE_LINE_LAYER.id)) {
          map.addLayer(ROUTE_LINE_LAYER);
        }
      }
      setRouteAdded(true);
    } else {
      if (map.getLayer(ROUTE_LINE_LAYER.id)) {
        map.removeLayer(ROUTE_LINE_LAYER.id);
      }
      if (map.getSource(ROUTE_SOURCE_ID)) {
        map.removeSource(ROUTE_SOURCE_ID);
      }
      setRouteAdded(false);
    }
  }, [routeGeometry, mapLoaded]);

  // Fit bounds when route is added
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !mapLoaded || !fitBounds || !bounds) return;

    map.fitBounds(bounds, {
      padding: 50,
      maxZoom: 15,
      duration: reducedMotion ? 0 : 800
    });
  }, [bounds, mapLoaded, fitBounds, reducedMotion]);

  const toggleFullScreen = useCallback(() => {
    setIsFullScreen((prev) => !prev);
  }, []);

  // Named markers using Nominatim reverse geocoding
  const pickupName = useReverseGeocode(pickup.lat, pickup.lon);
  const dropoffName = useReverseGeocode(dropoff.lat, dropoff.lon);

  const PickupMarker = () => (
    <div className="flex flex-col items-center" role="img" aria-label={`Pickup: ${pickupName}`}>
      <div className="w-3 h-3 rounded-full bg-brass border-2 border-surface-0 shadow-lg animate-pulse" />
      <div className="mt-1 max-w-[140px] text-center text-[10px] font-medium text-ink-primary bg-surface-0/95 backdrop-blur-sm px-1.5 py-0.5 rounded shadow-md leading-tight">
        <span className="block text-brass text-[9px] font-semibold uppercase tracking-wide">Pickup</span>
        <span className="block truncate">{pickupName}</span>
      </div>
    </div>
  );

  const DropoffMarker = () => (
    <div className="flex flex-col items-center" role="img" aria-label={`Dropoff: ${dropoffName}`}>
      <div className="w-3 h-3 rounded-full bg-verdigris border-2 border-surface-0 shadow-lg" />
      <div className="mt-1 max-w-[140px] text-center text-[10px] font-medium text-ink-primary bg-surface-0/95 backdrop-blur-sm px-1.5 py-0.5 rounded shadow-md leading-tight">
        <span className="block text-verdigris text-[9px] font-semibold uppercase tracking-wide">Dropoff</span>
        <span className="block truncate">{dropoffName}</span>
      </div>
    </div>
  );

  const mapHeight = isFullScreen ? "100vh" : typeof height === "number" ? `${height}px` : height;
  const cardHeight = isFullScreen ? "calc(100vh - 60px)" : typeof height === "number" ? `${height}px` : height;
  const mapKeyValue = `${center.latitude}-${center.longitude}-${viewport.width}-${mapKey}`;

  // Mobile full-screen overlay
  if (isMobile && mobileFullScreen) {
    return (
      <div className={cn("relative", className)}>
        {/* Map card */}
        <Card
          className={cn(
            "overflow-hidden border-2 border-brass/40 p-0 shadow-[0_0_0_1px_rgba(201,146,42,0.15)]",
            isFullScreen ? "fixed inset-0 z-50 rounded-none border-0" : "",
            className
          )}
          style={{ height: cardHeight }}
        >
          <div ref={containerRef} className="h-full w-full" style={{ width: "100%", height: "100%" }}>
            <Map
              key={mapKeyValue}
              initialViewState={{ ...center, zoom: 11 }}
              mapStyle="https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json"
              style={{ width: "100%", height: "100%" }}
              onLoad={() => setMapLoaded(true)}
            >
              <Marker longitude={pickup.lon} latitude={pickup.lat}>
                <PickupMarker />
              </Marker>
              <Marker longitude={dropoff.lon} latitude={dropoff.lat}>
                <DropoffMarker />
              </Marker>
            </Map>
            {!mapLoaded && (
              <div className="absolute inset-0 flex items-center justify-center bg-surface-0/90 z-10">
                <div className="flex flex-col items-center gap-2 text-ink-muted">
                  <div className="w-8 h-8 border-2 border-brass/30 border-t-brass rounded-full animate-spin" />
                  <span className="text-sm">Loading map...</span>
                </div>
              </div>
            )}
          </div>

          {/* Mobile full-screen toggle bar */}
          <div
            className={cn(
              "absolute bottom-0 left-0 right-0 px-4 py-3 bg-gradient-to-t from-surface-0/95 to-transparent z-20",
              isFullScreen ? "border-t border-brass/30" : ""
            )}
          >
            <button
              onClick={toggleFullScreen}
              className="w-full flex items-center justify-center gap-2 px-4 py-2 rounded-lg bg-surface-1 border border-surface-border text-ink-primary text-sm font-medium hover:bg-brass/10 hover:border-brass/30 transition-colors"
              aria-label={isFullScreen ? "Exit full screen" : "Enter full screen"}
              aria-expanded={isFullScreen}
            >
              {isFullScreen ? (
                <>
                  <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
                    <path d="M8 3v3a2 2 0 0 1-2 2H3m18 0h-3a2 2 0 0 1-2-2V3m0 18v-3a2 2 0 0 1 2-2h3M3 16h3a2 2 0 0 1 2 2v3" />
                  </svg>
                  <span>Exit full screen</span>
                </>
              ) : (
                <>
                  <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
                    <path d="M8 3H5a2 2 0 0 0-2 2v3m18 0V5a2 2 0 0 0-2-2h-3m0 18h3a2 2 0 0 1 2 2v3M3 16v3a2 2 0 0 0 2 2h3" />
                  </svg>
                  <span>Full screen map</span>
                </>
              )}
            </button>
          </div>
        </Card>
      </div>
    );
  }

  // Desktop/tablet layout
  return (
    <Card
      className={cn("overflow-hidden border-2 border-brass/40 p-0 shadow-[0_0_0_1px_rgba(201,146,42,0.15)]", className)}
      style={{ height: mapHeight }}
    >
      <div ref={containerRef} className="h-full w-full" style={{ width: "100%", height: "100%" }}>
        <Map
          key={mapKeyValue}
          initialViewState={{ ...center, zoom: 11 }}
          mapStyle="https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json"
          style={{ width: "100%", height: "100%" }}
          onLoad={() => setMapLoaded(true)}
        >
          <Marker longitude={pickup.lon} latitude={pickup.lat}>
            <PickupMarker />
          </Marker>
          <Marker longitude={dropoff.lon} latitude={dropoff.lat}>
            <DropoffMarker />
          </Marker>
        </Map>
        {!mapLoaded && (
          <div className="absolute inset-0 flex items-center justify-center bg-surface-0/90 z-10">
            <div className="flex flex-col items-center gap-2 text-ink-muted">
              <div className="w-8 h-8 border-2 border-brass/30 border-t-brass rounded-full animate-spin" />
              <span className="text-sm">Loading map...</span>
            </div>
          </div>
        )}
      </div>
    </Card>
  );
}
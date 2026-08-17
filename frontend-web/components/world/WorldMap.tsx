"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import Map from "react-map-gl/maplibre";
import "maplibre-gl/dist/maplibre-gl.css";
import { DeckGL } from "@deck.gl/react";
import { ScatterplotLayer } from "@deck.gl/layers";
import { FlyToInterpolator, WebMercatorViewport, type PickingInfo } from "@deck.gl/core";
import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { Compass, Minus, Plus } from "lucide-react";
import { searchCities, type City } from "@/lib/api";
import { queryKeys } from "@/lib/queryKeys";
import { useAnimePulse } from "@/hooks/useAnimePulse";
import { checkReducedMotion } from "@/lib/motion";
import { cn } from "@/lib/utils";
import { PulsingStatusDot } from "@/components/magic/PulsingStatusDot";

// RGBA -- deck.gl layers take raw [r,g,b,a], not CSS strings.
const PARCHMENT: [number, number, number] = [244, 239, 228];
const BRASS: [number, number, number] = [201, 146, 42];
const ICE_BLUE: [number, number, number] = [56, 189, 248]; // = Tailwind sky-400 (#38bdf8)
const OXIDE: [number, number, number] = [140, 74, 60];

const TIER_RING: Record<string, [number, number, number]> = {
  OBSERVED: BRASS,
  TRANSFER: ICE_BLUE,
  NONE: OXIDE,
};

const TIER_DESC: Record<string, string> = {
  OBSERVED: "Local telemetry",
  TRANSFER: "Similar cities",
  NONE: "Network analysis",
};

const TIER_TEXT_CLASS: Record<string, string> = {
  OBSERVED: "text-brass",
  TRANSFER: "text-sky-400",
  NONE: "text-oxide",
};

const INITIAL_VIEW = { longitude: 10, latitude: 24, zoom: 1.35, pitch: 0, bearing: 0 };
const SETTLE_START_VIEW = { ...INITIAL_VIEW, zoom: INITIAL_VIEW.zoom + 1.3 };
const NYC_VIEW = { longitude: -73.97, latitude: 40.75, zoom: 9, pitch: 0, bearing: 0 };

function clampZoom(z: number) {
  return Math.min(14, Math.max(0.8, z));
}

interface WorldMapProps {
  /** When set, non-matching cities dim and matching cities emphasize -- driven by hovering a tier below the fold. */
  highlightedTier?: string | null;
}

export function WorldMap({ highlightedTier = null }: WorldMapProps) {
  const router = useRouter();
  const reducedMotion = checkReducedMotion();
  const { data: citiesData, isLoading, error } = useQuery({
    queryKey: queryKeys.cities({ limit: 1000 }),
    queryFn: () => searchCities({ limit: 1000 }),
  });

  const [viewState, setViewState] = useState(reducedMotion ? INITIAL_VIEW : SETTLE_START_VIEW);
  const [hoverInfo, setHoverInfo] = useState<{ city: City; x: number; y: number } | null>(null);
  const [mounted, setMounted] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const [size, setSize] = useState({ width: 0, height: 0 });

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const ro = new ResizeObserver((entries) => {
      const rect = entries[0]?.contentRect;
      if (rect) setSize({ width: rect.width, height: rect.height });
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  // Wow-moment: fade the canvas in, then settle from a tighter zoom out to the full network view.
  useEffect(() => {
    const raf = requestAnimationFrame(() => setMounted(true));
    if (!reducedMotion) {
      const t = setTimeout(() => {
        setViewState((prev) => ({
          ...prev,
          ...INITIAL_VIEW,
          transitionDuration: 1400,
          transitionInterpolator: new FlyToInterpolator({ speed: 1.1 }),
        }));
      }, 450);
      return () => {
        cancelAnimationFrame(raf);
        clearTimeout(t);
      };
    }
    return () => cancelAnimationFrame(raf);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const cities = citiesData?.results ?? [];
  const nycCity = useMemo(() => cities.find((c) => c.id === "nyc") ?? null, [cities]);
  const otherCities = useMemo(() => cities.filter((c) => c.id !== "nyc"), [cities]);
  const countryCount = useMemo(() => new Set(cities.map((c) => c.country_code)).size, [cities]);
  const tierCounts = useMemo(
    () =>
      cities.reduce(
        (acc, c) => {
          acc[c.model_status as keyof typeof acc] = (acc[c.model_status as keyof typeof acc] || 0) + 1;
          return acc;
        },
        { OBSERVED: 0, TRANSFER: 0, NONE: 0 } as Record<string, number>
      ),
    [cities]
  );

  function flyTo(next: Partial<typeof INITIAL_VIEW>) {
    setViewState((prev) => ({
      ...prev,
      ...next,
      transitionDuration: 700,
      transitionInterpolator: new FlyToInterpolator({ speed: 1.6 }),
    }));
  }

  function zoomBy(delta: number) {
    flyTo({ zoom: clampZoom(viewState.zoom + delta) });
  }

  // Screen position of NYC's marker -- recomputed from viewState/container size
  // so the DOM "home port" ping tracks the WebGL layer underneath it exactly.
  const nycScreen = useMemo(() => {
    if (!nycCity || size.width === 0 || size.height === 0) return null;
    try {
      const viewport = new WebMercatorViewport({ ...viewState, width: size.width, height: size.height });
      const [x, y] = viewport.project([nycCity.longitude, nycCity.latitude]);
      if (x < -40 || x > size.width + 40 || y < -40 || y > size.height + 40) return null;
      return { x, y };
    } catch {
      return null;
    }
  }, [nycCity, viewState, size]);

  const layers = useMemo(
    () => [
      new ScatterplotLayer<City>({
        id: "cities-other",
        data: otherCities,
        pickable: true,
        radiusUnits: "pixels",
        stroked: true,
        getPosition: (d) => [d.longitude, d.latitude],
        getRadius: (d) => {
          if (hoverInfo?.city.id === d.id) return 5.5;
          if (highlightedTier && d.model_status === highlightedTier) return 4;
          return 3;
        },
        getFillColor: (d) => {
          const alpha =
            hoverInfo?.city.id === d.id
              ? 255
              : highlightedTier
                ? d.model_status === highlightedTier
                  ? 230
                  : 55
                : 190;
          return [...PARCHMENT, alpha];
        },
        getLineColor: (d) => {
          const dim = highlightedTier && d.model_status !== highlightedTier;
          return [...(TIER_RING[d.model_status] ?? OXIDE), dim ? 70 : 200];
        },
        getLineWidth: (d) => (hoverInfo?.city.id === d.id ? 2.2 : 1.2),
        lineWidthUnits: "pixels",
        updateTriggers: {
          getRadius: [hoverInfo?.city.id, highlightedTier],
          getFillColor: [hoverInfo?.city.id, highlightedTier],
          getLineColor: highlightedTier,
          getLineWidth: hoverInfo?.city.id,
        },
        transitions: { getRadius: 120, getLineWidth: 120, getFillColor: 200 },
        onHover: (info: PickingInfo<City>) =>
          setHoverInfo(info.object ? { city: info.object, x: info.x ?? 0, y: info.y ?? 0 } : null),
        onClick: (info: PickingInfo<City>) => info.object && router.push(`/city/${info.object.id}`),
      }),
      nycCity &&
        new ScatterplotLayer<City>({
          id: "city-nyc",
          data: [nycCity],
          pickable: true,
          radiusUnits: "pixels",
          stroked: true,
          getPosition: (d) => [d.longitude, d.latitude],
          getRadius: 7,
          getFillColor: [...BRASS, 255],
          getLineColor: [...BRASS, 140],
          getLineWidth: 5,
          lineWidthUnits: "pixels",
          onHover: (info: PickingInfo<City>) =>
            setHoverInfo(info.object ? { city: info.object, x: info.x ?? 0, y: info.y ?? 0 } : null),
          onClick: () => router.push("/city/nyc"),
        }),
    ],
    [otherCities, nycCity, hoverInfo, highlightedTier, router]
  );

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

  // Tooltip clamped inside the container so it never runs off the map edge.
  const TT_W = 208;
  const TT_H = 128;
  const ttLeft = hoverInfo ? Math.min(hoverInfo.x + 18, Math.max(8, size.width - TT_W - 8)) : 0;
  const ttTop = hoverInfo ? Math.min(hoverInfo.y + 18, Math.max(8, size.height - TT_H - 8)) : 0;

  return (
    <div
      ref={containerRef}
      className={cn("relative h-full w-full transition-opacity ease-out", mounted ? "opacity-100 duration-1000" : "opacity-0 duration-0")}
    >
      <DeckGL
        viewState={viewState}
        onViewStateChange={({ viewState: vs }) => setViewState(vs as typeof INITIAL_VIEW)}
        controller={true}
        layers={layers}
        getCursor={({ isHovering }) => (isHovering ? "pointer" : "grab")}
        style={{ position: "absolute", inset: "0" }}
      >
        <Map
          reuseMaps
          mapStyle="https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json"
          style={{ width: "100%", height: "100%" }}
        />
      </DeckGL>

      {/* Home-port ping + small reference tag: DOM-layer, tracks NYC's projected pixel position */}
      {nycScreen && <HomePortPing x={nycScreen.x} y={nycScreen.y} />}

      {/* Cursor-following hover tooltip */}
      {hoverInfo && (
        <div
          className="pointer-events-none absolute z-20 w-52 rounded-sm border border-brass/30 bg-surface-0/95 px-4 py-3.5 backdrop-blur-md shadow-xl"
          style={{ left: ttLeft, top: ttTop }}
        >
          <p className="font-section-md text-ink-primary leading-tight">{hoverInfo.city.name}</p>
          <p className="font-label-sm text-ink-muted mt-0.5">{hoverInfo.city.country_code.toUpperCase()}</p>
          <div className="separator-line my-2.5" />
          <p className={cn("font-label-sm", TIER_TEXT_CLASS[hoverInfo.city.model_status] ?? "text-oxide")}>
            {hoverInfo.city.model_status === "NONE" ? "Routing Only" : hoverInfo.city.model_status}
          </p>
          <p className="font-body-sm text-ink-secondary text-xs mt-0.5">
            {TIER_DESC[hoverInfo.city.model_status] ?? "Network analysis"}
          </p>
          <p className="font-label-sm text-brass mt-2.5">Open City &rarr;</p>
        </div>
      )}

      {/* Zoom + recenter controls -- vertical strip on the trailing edge, clear of corner HUD */}
      <div className="absolute right-4 top-1/2 z-10 flex -translate-y-1/2 flex-col gap-1.5">
        <button
          onClick={() => zoomBy(1)}
          aria-label="Zoom in"
          className="flex h-9 w-9 items-center justify-center rounded-sm border border-surface-border bg-surface-0/90 text-ink-primary backdrop-blur transition-colors active:scale-95 hover:border-brass/50 hover:text-brass"
        >
          <Plus className="h-4 w-4" />
        </button>
        <button
          onClick={() => zoomBy(-1)}
          aria-label="Zoom out"
          className="flex h-9 w-9 items-center justify-center rounded-sm border border-surface-border bg-surface-0/90 text-ink-primary backdrop-blur transition-colors active:scale-95 hover:border-brass/50 hover:text-brass"
        >
          <Minus className="h-4 w-4" />
        </button>
        <button
          onClick={() => flyTo(NYC_VIEW)}
          aria-label="Center on New York City"
          title="Center on New York City -- the reference implementation"
          className="flex h-9 w-9 items-center justify-center rounded-sm border border-brass/40 bg-surface-0/90 text-brass backdrop-blur transition-colors active:scale-95 hover:border-brass hover:bg-brass/10"
        >
          <Compass className="h-4 w-4" />
        </button>
      </div>

      {/* Top-right: live network readout -- floating instrumentation, no box */}
      <div className="absolute top-6 right-6 z-10 hidden flex-col items-end gap-1 text-right sm:flex">
        <span className="flex items-center gap-1.5 font-label-sm text-verdigris">
          <PulsingStatusDot status="live" size={5} />
          Live
        </span>
        <div className="mt-1 flex items-baseline gap-1.5">
          <span className="font-data-md text-brass">{cities.length}</span>
          <span className="font-label-sm text-ink-muted">Cities</span>
        </div>
        <div className="flex items-baseline gap-1.5">
          <span className="font-data-md text-ink-secondary">{countryCount}</span>
          <span className="font-label-sm text-ink-muted">Countries</span>
        </div>
      </div>

      {/* Bottom-left: tier coverage breakdown */}
      <div className="absolute bottom-6 left-6 z-10 hidden flex-col gap-1.5 sm:flex">
        <span className="font-label-sm text-ink-muted mb-0.5">Coverage</span>
        <div className="flex items-center gap-2">
          <span className="h-2 w-2 rounded-full border border-brass" />
          <span className="font-label-sm text-ink-secondary">Observed</span>
          <span className="font-mono text-xs text-brass">{tierCounts.OBSERVED}</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="h-2 w-2 rounded-full border border-sky-400" />
          <span className="font-label-sm text-ink-secondary">Transfer</span>
          <span className="font-mono text-xs text-sky-400">{tierCounts.TRANSFER}</span>
        </div>
      </div>

      {/* Bottom-right: reference city callout */}
      <div className="absolute bottom-6 right-6 z-10 hidden text-right sm:block">
        <span className="font-label-sm text-ink-muted">Reference</span>
        <p className="font-section-md text-brass leading-tight">New York</p>
        <span className="font-label-sm text-ink-muted">Observed</span>
      </div>
    </div>
  );
}

function HomePortPing({ x, y }: { x: number; y: number }) {
  const ringRef = useAnimePulse<HTMLSpanElement>({ scaleMin: 1, scaleMax: 2.6, duration: 2000, opacityMin: 0 });
  const reduced = checkReducedMotion();

  return (
    <div className="pointer-events-none absolute z-10" style={{ left: x, top: y, transform: "translate(-50%, -50%)" }}>
      <span className="relative flex h-3 w-3 items-center justify-center">
        {!reduced && <span ref={ringRef} className="absolute inline-block h-3 w-3 rounded-full bg-brass/70" />}
        <span className={cn("relative inline-block h-2 w-2 rounded-full bg-brass shadow-[0_0_10px_#c9922a]")} />
      </span>
      <span className="absolute left-2.5 top-2.5 whitespace-nowrap font-mono text-[9px] font-semibold tracking-[0.15em] text-brass/90">
        REFERENCE
      </span>
    </div>
  );
}

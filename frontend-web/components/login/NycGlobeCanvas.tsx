"use client";

/**
 * The actual WebGL globe (globe.gl, already-installed-adjacent deck.gl was
 * evaluated and rejected: it has no purpose-built "ambient spinning globe"
 * mode, so using it here would mean hand-building rotation/lighting/camera
 * that globe.gl gives for free). Client-only -- mounted via next/dynamic
 * with ssr:false from NycOrbit.tsx, since it touches the DOM/WebGL directly.
 *
 * The sphere uses a real world country dataset with NYC highlighted as the
 * local focus.
 */

import { useEffect, useRef } from "react";

const NYC = { lat: 40.7128, lng: -74.006 };

// Arcs "arrive" from a few points scattered around the sphere so at least
// one is visible from most rotation angles, matching the reference's
// converging-traffic motif -- but every one still ends at NYC only.
const ARC_ORIGINS = [
  { lat: 51.5, lng: -0.1 },
  { lat: -23.5, lng: -46.6 },
  { lat: 35.7, lng: 139.7 },
  { lat: -33.9, lng: 151.2 },
];

export default function NycGlobeCanvas({ className }: { className?: string }) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let globeInstance: { _destructor?: () => void } | null = null;
    let ro: ResizeObserver | null = null;
    let cancelled = false;

    (async () => {
      const [{ default: Globe }, worldGeojson] = await Promise.all([
        import("globe.gl"),
        fetch("/data/world_countries.geojson").then((r) => r.json()),
      ]);
      if (cancelled || !containerRef.current) return;

      const el = containerRef.current;
      const globe = new Globe(el)
        .backgroundColor("rgba(0,0,0,0)")
        .showAtmosphere(true)
        .atmosphereColor("#6c5ce7")
        .atmosphereAltitude(0.22)
        .polygonsData(worldGeojson.features)
        .polygonCapColor(() => "rgba(108,92,231,0.18)")
        .polygonSideColor(() => "rgba(108,92,231,0.08)")
        .polygonStrokeColor(() => "rgba(108,92,231,0.38)")
        .polygonAltitude(0.006)
        .pointsData([{ ...NYC, size: 2.4, color: "#14b8a6" }])
        .pointColor("color")
        .pointRadius("size")
        .pointAltitude(0.03)
        .labelsData([{ lat: NYC.lat - 2.2, lng: NYC.lng, text: "New York City" }])
        .labelText("text")
        .labelColor(() => "#1c1b33")
        .labelSize(0.4)
        .labelDotRadius(0)
        .labelAltitude(0.06)
        .labelResolution(3)
        .arcsData(ARC_ORIGINS.map((o) => ({ startLat: o.lat, startLng: o.lng, endLat: NYC.lat, endLng: NYC.lng })))
        .arcColor(() => ["rgba(108,92,231,0.35)", "#14b8a6"])
        .arcDashLength(0.5)
        .arcDashGap(1.5)
        .arcDashAnimateTime(3200)
        .arcStroke(0.6)
        .arcAltitudeAutoScale(0.45);

      globe.globeMaterial().color.set("#f3f2fc");
      globe.globeMaterial().opacity = 0.92;
      globe.globeMaterial().transparent = true;

      globe.pointOfView({ ...NYC, altitude: 1.6 }, 0);
      const controls = globe.controls();
      controls.autoRotate = true;
      controls.autoRotateSpeed = 0.6;
      controls.enableZoom = false;
      controls.enablePan = false;

      ro = new ResizeObserver(() => {
        globe.width(el.clientWidth).height(el.clientHeight);
      });
      ro.observe(el);
      globe.width(el.clientWidth).height(el.clientHeight);

      globeInstance = globe;
    })();

    return () => {
      cancelled = true;
      ro?.disconnect();
      globeInstance?._destructor?.();
    };
  }, []);

  return <div ref={containerRef} className={className} />;
}

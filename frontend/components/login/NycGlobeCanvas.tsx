"use client";

import { useEffect, useRef, useState } from "react";

const NYC = { lat: 40.7128, lng: -74.006 };

const ARC_ORIGINS = [
  { lat: 51.5, lng: -0.1, name: "London" },
  { lat: -23.5, lng: -46.6, name: "São Paulo" },
  { lat: 35.7, lng: 139.7, name: "Tokyo" },
  { lat: -33.9, lng: 151.2, name: "Sydney" },
  { lat: 48.85, lng: 2.35, name: "Paris" },
  { lat: 1.35, lng: 103.8, name: "Singapore" },
  { lat: 25.2, lng: 55.3, name: "Dubai" },
];

function generateWorldTexture(features: any[]): string {
  if (typeof document === "undefined") return "";
  const canvas = document.createElement("canvas");
  canvas.width = 2048;
  canvas.height = 1024;
  const ctx = canvas.getContext("2d");
  if (!ctx) return "";

  // Base sphere surface color
  ctx.fillStyle = "#f5f4fd";
  ctx.fillRect(0, 0, canvas.width, canvas.height);

  // Subtle coordinate grid for high-end spatial instrumentation look
  ctx.strokeStyle = "rgba(108, 92, 231, 0.08)";
  ctx.lineWidth = 1;
  for (let lat = -80; lat <= 80; lat += 20) {
    const y = ((90 - lat) / 180) * canvas.height;
    ctx.beginPath();
    ctx.moveTo(0, y);
    ctx.lineTo(canvas.width, y);
    ctx.stroke();
  }
  for (let lng = -180; lng <= 180; lng += 30) {
    const x = ((lng + 180) / 360) * canvas.width;
    ctx.beginPath();
    ctx.moveTo(x, 0);
    ctx.lineTo(x, canvas.height);
    ctx.stroke();
  }

  // Draw landmasses
  ctx.fillStyle = "rgba(108, 92, 231, 0.20)";
  ctx.strokeStyle = "rgba(108, 92, 231, 0.55)";
  ctx.lineWidth = 1.2;

  function project(coord: [number, number]): [number, number] {
    const x = ((coord[0] + 180) / 360) * canvas.width;
    const y = ((90 - coord[1]) / 180) * canvas.height;
    return [x, y];
  }

  function drawRing(ring: [number, number][]) {
    if (!ring || ring.length < 3 || !ctx) return;
    const [startX, startY] = project(ring[0]);
    ctx.beginPath();
    ctx.moveTo(startX, startY);
    for (let i = 1; i < ring.length; i++) {
      const [px, py] = project(ring[i]);
      ctx.lineTo(px, py);
    }
    ctx.closePath();
    ctx.fill();
    ctx.stroke();
  }

  for (const feature of features) {
    const geom = feature.geometry;
    if (!geom) continue;
    if (geom.type === "Polygon") {
      for (const ring of geom.coordinates) {
        drawRing(ring);
      }
    } else if (geom.type === "MultiPolygon") {
      for (const poly of geom.coordinates) {
        for (const ring of poly) {
          drawRing(ring);
        }
      }
    }
  }

  // Draw NYC beacon glow directly on texture
  const [nycX, nycY] = project([NYC.lng, NYC.lat]);
  const grad = ctx.createRadialGradient(nycX, nycY, 2, nycX, nycY, 24);
  grad.addColorStop(0, "rgba(20, 184, 166, 0.9)");
  grad.addColorStop(0.4, "rgba(20, 184, 166, 0.35)");
  grad.addColorStop(1, "rgba(20, 184, 166, 0)");
  ctx.fillStyle = grad;
  ctx.beginPath();
  ctx.arc(nycX, nycY, 24, 0, Math.PI * 2);
  ctx.fill();

  return canvas.toDataURL("image/png");
}

export default function NycGlobeCanvas({ className }: { className?: string }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    let globeInstance: any = null;
    let ro: ResizeObserver | null = null;
    let animFrame: number | null = null;
    let cancelled = false;

    (async () => {
      try {
        const [{ default: Globe }, worldGeojson] = await Promise.all([
          import("globe.gl"),
          fetch("/data/world_countries_lowres.geojson").then((r) => {
            if (!r.ok) throw new Error("Geojson fetch failed");
            return r.json();
          }),
        ]);

        if (cancelled || !containerRef.current) return;
        const el = containerRef.current;

        // Generate 1-pass hardware texture (0 polygon triangulation draw overhead!)
        const textureUrl = generateWorldTexture(worldGeojson.features || []);

        const globe = new Globe(el)
          .backgroundColor("rgba(0,0,0,0)")
          .globeImageUrl(textureUrl)
          .showAtmosphere(true)
          .atmosphereColor("#6c5ce7")
          .atmosphereAltitude(0.24)
          .pointsData([
            { ...NYC, size: 3.2, color: "#14b8a6", name: "NYC TLC Hub" },
            { lat: NYC.lat + 0.3, lng: NYC.lng - 0.2, size: 1.6, color: "#6c5ce7", name: "JFK" },
            { lat: NYC.lat + 0.1, lng: NYC.lng + 0.2, size: 1.6, color: "#e17055", name: "LGA" },
          ])
          .pointColor("color")
          .pointRadius("size")
          .pointAltitude(0.02)
          .labelsData([{ lat: NYC.lat - 2.8, lng: NYC.lng, text: "NYC HUB" }])
          .labelText("text")
          .labelColor(() => "#1c1b33")
          .labelSize(0.45)
          .labelDotRadius(0)
          .labelAltitude(0.04)
          .labelResolution(2)
          .arcsData(
            ARC_ORIGINS.map((o) => ({
              startLat: o.lat,
              startLng: o.lng,
              endLat: NYC.lat,
              endLng: NYC.lng,
            }))
          )
          .arcColor(() => ["rgba(108,92,231,0.55)", "#14b8a6"])
          .arcDashLength(0.6)
          .arcDashGap(1.2)
          .arcDashAnimateTime(2000)
          .arcStroke(0.8)
          .arcAltitudeAutoScale(0.42);

        // Hardware-acceleration & DPR optimization
        const renderer = globe.renderer();
        if (renderer) {
          renderer.setPixelRatio(Math.min(typeof window !== "undefined" ? window.devicePixelRatio : 1, 1.5));
          renderer.powerPreference = "high-performance";
        }

        // Camera viewpoint looking at NYC
        globe.pointOfView({ ...NYC, altitude: 1.6 }, 0);

        // Auto-rotation controls with fluid, responsive speed
        const controls = globe.controls();
        if (controls) {
          controls.autoRotate = true;
          controls.autoRotateSpeed = 2.4; // Fluid, lively rotation speed (~25s full circle instead of 8min crawl)
          controls.enableZoom = false;
          controls.enablePan = false;
          controls.rotateSpeed = 0.8;
          controls.dampingFactor = 0.05;
        }

        const updateSize = () => {
          if (!el) return;
          const w = el.clientWidth;
          const h = el.clientHeight;
          if (w > 0 && h > 0) {
            globe.width(w).height(h);
          }
        };

        ro = new ResizeObserver(() => {
          updateSize();
        });
        ro.observe(el);
        updateSize();

        globeInstance = globe;
        setLoaded(true);
      } catch (err) {
        console.error("Failed to initialize globe:", err);
      }
    })();

    return () => {
      cancelled = true;
      ro?.disconnect();
      if (animFrame) cancelAnimationFrame(animFrame);
      globeInstance?._destructor?.();
    };
  }, []);

  return (
    <div
      ref={containerRef}
      className={`h-full w-full transition-opacity duration-500 ${loaded ? "opacity-100" : "opacity-0"} ${className ?? ""}`}
    />
  );
}

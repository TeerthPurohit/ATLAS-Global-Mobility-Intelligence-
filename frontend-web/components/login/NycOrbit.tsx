"use client";

/**
 * NycOrbit — decorative auth-page backdrop: a real rotating 3D globe
 * (NycGlobeCanvas, globe.gl) showing only NYC's own zone geometry, not a
 * world map (ADR-011 dropped global coverage) -- so it stays a bare sphere
 * everywhere except the one landmass it exists to highlight, with arcs
 * converging on it and an auto-rotating camera. The only numbers on it are
 * real (same zone_hourly_demand total the home page shows) or omitted --
 * no invented transaction ticker.
 */

import dynamic from "next/dynamic";
import { Compass } from "lucide-react";
import { PulsingStatusDot } from "@/components/magic/PulsingStatusDot";

const NycGlobeCanvas = dynamic(() => import("./NycGlobeCanvas"), { ssr: false });

export function NycOrbit({ className }: { className?: string }) {
  return (
    <div
      className={`relative aspect-square w-full overflow-hidden rounded-[2rem] border border-surface-border bg-[radial-gradient(circle_at_50%_35%,var(--surface-2),var(--surface-0))] ${className ?? ""}`}
    >
      <NycGlobeCanvas className="absolute inset-0 h-full w-full" />

      {/* Brand mark */}
      <div className="pointer-events-none absolute left-5 top-5 flex items-center gap-2">
        <Compass className="h-4 w-4 text-brass" />
        <span className="font-section-md text-sm text-ink-primary">ATLAS</span>
      </div>

      {/* Live pill */}
      <div className="pointer-events-none absolute right-5 top-5 flex items-center gap-1.5 rounded-full border border-surface-border bg-surface-1/90 px-3 py-1 font-label-sm text-ink-secondary shadow-sm">
        <PulsingStatusDot status="live" size={6} />
        Live
      </div>

      {/* Provenance card -- true claim, not a fabricated transaction */}
      <div className="pointer-events-none absolute bottom-6 right-5 max-w-[13rem] rounded-2xl border border-surface-border bg-surface-1/95 px-3 py-2 shadow-[0_12px_30px_-12px_rgba(108,92,231,0.35)]">
        <p className="font-body-sm text-ink-secondary">
          Real TLC trip records — no estimates, no priors.
        </p>
      </div>
    </div>
  );
}

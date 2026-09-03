"use client";

import dynamic from "next/dynamic";
import { Compass } from "lucide-react";
import { PulsingStatusDot } from "@/components/magic/PulsingStatusDot";

const NycGlobeCanvas = dynamic(() => import("./NycGlobeCanvas"), {
  ssr: false,
  loading: () => (
    <div className="absolute inset-0 flex items-center justify-center">
      <div className="flex items-center gap-2.5 rounded-full border border-surface-border bg-surface-1/80 px-4 py-2 text-xs text-ink-muted backdrop-blur-md">
        <span className="h-2 w-2 animate-ping rounded-full bg-brass" />
        Initialising globe...
      </div>
    </div>
  ),
});

export function NycOrbit({ className }: { className?: string }) {
  return (
    <div
      className={`relative aspect-square w-full max-w-[540px] mx-auto overflow-hidden rounded-[2.5rem] border border-surface-border bg-[radial-gradient(circle_at_50%_35%,var(--surface-2),var(--surface-0))] shadow-[0_24px_60px_-24px_rgba(108,92,231,0.25)] ${className ?? ""}`}
    >
      {/* 3D WebGL Globe canvas */}
      <NycGlobeCanvas className="absolute inset-0 h-full w-full" />

      {/* Ambient soft glow */}
      <div className="pointer-events-none absolute -left-16 -top-16 h-48 w-48 rounded-full bg-brass/10 blur-3xl" />
      <div className="pointer-events-none absolute -bottom-16 -right-16 h-48 w-48 rounded-full bg-accent-primary/10 blur-3xl" />

      {/* Minimal Brand & Live Pill */}
      <div className="pointer-events-none absolute left-6 top-6 flex items-center gap-2 rounded-xl border border-surface-border/80 bg-surface-1/90 px-3.5 py-1.5 backdrop-blur-md shadow-xs">
        <Compass className="h-4 w-4 text-brass" />
        <span className="font-section-md text-xs tracking-wider text-ink-primary font-bold">ATLAS</span>
      </div>

      <div className="pointer-events-none absolute right-6 top-6 flex items-center gap-1.5 rounded-full border border-surface-border/80 bg-surface-1/90 px-3 py-1 font-label-sm text-ink-secondary backdrop-blur-md shadow-xs">
        <PulsingStatusDot status="live" size={6} />
        <span className="text-[11px] font-medium text-ink-primary">Live</span>
      </div>
    </div>
  );
}

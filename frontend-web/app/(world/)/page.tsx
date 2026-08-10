import { Metadata } from "next";
import { WorldMap } from "@/components/world/WorldMap";

export const metadata: Metadata = {
  title: "Global Mobility Intelligence",
  description: "Explore ride intelligence across cities worldwide.",
};

export default function WorldPage() {
  return (
    <div className="flex flex-col gap-6">
      <div>
        <span className="flex items-center gap-2 text-xs uppercase tracking-widest text-ink-muted">
          <svg className="h-4 w-4 text-brass" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
            <circle cx={12} cy={12} r={10} />
            <line x1={2} y1={12} x2={22} y2={12} />
            <line x1={12} y1={2} x2={12} y2={22} />
          </svg>
          World
        </span>
        <h1 className="mt-2 font-display text-3xl font-semibold text-ink-primary">Global Mobility Intelligence</h1>
        <p className="mt-1 text-sm text-ink-secondary max-w-2xl">
          Select a country to explore its onboarded cities. Each city is tiered by data availability:
          <strong className="text-brass"> OBSERVED</strong> (local training data),
          <strong className="text-verdigris"> TRANSFER</strong> (WorldMove priors), or
          <strong className="text-oxide"> NONE</strong> (routing + context only).
        </p>
      </div>

      <WorldMap />
    </div>
  );
}
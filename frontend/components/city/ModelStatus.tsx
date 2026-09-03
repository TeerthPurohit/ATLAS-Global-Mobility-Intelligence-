"use client";

import { Card, CardTitle } from "@/components/ui/Card";
import type { CityProfileResponse } from "@/lib/api";
import { Cpu, ShieldCheck, Database, Layers } from "lucide-react";
import { cn } from "@/lib/utils";

interface ModelStatusProps {
  profile: CityProfileResponse;
  className?: string;
}

export function ModelStatus({ profile, className }: ModelStatusProps) {
  return (
    <Card className={cn("p-6 flex flex-col gap-4", className)}>
      <div className="flex items-center justify-between border-b border-surface-border pb-3">
        <div className="flex items-center gap-2">
          <Cpu className="h-4 w-4 text-brass" />
          <CardTitle className="font-display text-base font-semibold text-ink-primary">
            Model & Provenance Status
          </CardTitle>
        </div>
      </div>

      <div className="space-y-2.5 text-xs">
        <div className="flex items-center justify-between rounded-lg bg-surface-1/50 px-3 py-2 border border-surface-border">
          <span className="flex items-center gap-2 text-ink-muted">
            <Layers className="h-3.5 w-3.5 text-brass" />
            Model Status
          </span>
          <span className="font-mono font-semibold text-ink-primary">{profile.model_status}</span>
        </div>

        <div className="flex items-center justify-between rounded-lg bg-surface-1/50 px-3 py-2 border border-surface-border">
          <span className="flex items-center gap-2 text-ink-muted">
            <Database className="h-3.5 w-3.5 text-verdigris" />
            Primary Data Source
          </span>
          <span className="font-mono font-semibold text-ink-primary truncate max-w-[180px]" title={profile.data_source}>
            {profile.data_source}
          </span>
        </div>

        <div className="flex items-center justify-between rounded-lg bg-surface-1/50 px-3 py-2 border border-surface-border">
          <span className="flex items-center gap-2 text-ink-muted">
            <ShieldCheck className="h-3.5 w-3.5 text-brass" />
            Overall Confidence
          </span>
          <span className="font-mono font-semibold text-ink-primary">
            {(profile.confidence * 100).toFixed(0)}%
          </span>
        </div>
      </div>

      <div className="rounded-xl border border-brass/30 bg-brass/10 p-3.5 text-xs text-brass leading-relaxed">
        <p className="font-semibold mb-0.5 flex items-center gap-1.5">
          <ShieldCheck className="h-3.5 w-3.5" />
          Observed
        </p>
        Trained directly on this city&rsquo;s own trip records — every fare, ETA,
        and demand figure is measured, not transferred.
      </div>
    </Card>
  );
}

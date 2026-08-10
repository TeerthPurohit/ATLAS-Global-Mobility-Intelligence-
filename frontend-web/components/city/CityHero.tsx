"use client";

import { Card } from "@/components/ui/Card";
import { TierBadge } from "@/components/capability/TierBadge";
import type { CityProfileResponse } from "@/lib/api";
import { cn } from "@/lib/utils";
import { MapPin, Globe, DollarSign, Users, Clock, Database } from "lucide-react";

interface CityHeroProps {
  profile: CityProfileResponse;
}

export function CityHero({ profile }: CityHeroProps) {
  return (
    <Card className="relative overflow-hidden border border-surface-border bg-surface-0/90 p-6 sm:p-8">
      {/* Ambient gradient overlay based on tier */}
      <div
        className={cn(
          "absolute -top-24 -right-24 h-64 w-64 rounded-full blur-3xl opacity-15 pointer-events-none",
          profile.tier === "OBSERVED" && "bg-brass",
          profile.tier === "TRANSFER" && "bg-verdigris",
          profile.tier === "NONE" && "bg-oxide"
        )}
      />

      <div className="relative z-10 flex flex-col gap-6 lg:flex-row lg:items-center lg:justify-between">
        <div className="flex items-start gap-4">
          <div
            className={cn(
              "flex h-14 w-14 shrink-0 items-center justify-center rounded-2xl border bg-surface-1 shadow-sm",
              profile.tier === "OBSERVED" && "border-brass/30 text-brass",
              profile.tier === "TRANSFER" && "border-verdigris/30 text-verdigris",
              profile.tier === "NONE" && "border-oxide/30 text-oxide"
            )}
          >
            <MapPin className="h-7 w-7" />
          </div>

          <div>
            <div className="flex flex-wrap items-center gap-3">
              <h1 className="font-display text-2xl font-bold tracking-tight text-ink-primary sm:text-3xl">
                {profile.name}
              </h1>
              <TierBadge tier={profile.tier} size="lg" />
            </div>

            <p className="mt-1 text-sm font-medium text-ink-secondary">
              {profile.country} &bull; <span className="font-mono text-xs text-ink-muted">{profile.timezone}</span>
            </p>

            <div className="mt-2 flex items-center gap-4 text-xs font-mono text-ink-muted">
              <span>LAT: {profile.latitude.toFixed(4)}</span>
              <span>LON: {profile.longitude.toFixed(4)}</span>
            </div>
          </div>
        </div>

        {/* Key Metrics Grid */}
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 lg:flex lg:items-center lg:gap-6">
          <div className="flex flex-col gap-1 rounded-xl border border-surface-border bg-surface-1/50 p-3 lg:border-none lg:bg-transparent lg:p-0">
            <span className="flex items-center gap-1.5 text-xs text-ink-muted">
              <Globe className="h-3.5 w-3.5 text-brass" />
              Geography
            </span>
            <span className="font-mono text-xs font-semibold uppercase text-ink-primary">
              {profile.geography_type}
            </span>
          </div>

          <div className="flex flex-col gap-1 rounded-xl border border-surface-border bg-surface-1/50 p-3 lg:border-none lg:bg-transparent lg:p-0">
            <span className="flex items-center gap-1.5 text-xs text-ink-muted">
              <DollarSign className="h-3.5 w-3.5 text-verdigris" />
              Currency
            </span>
            <span className="font-mono text-xs font-semibold text-ink-primary">
              {profile.currency}
            </span>
          </div>

          <div className="flex flex-col gap-1 rounded-xl border border-surface-border bg-surface-1/50 p-3 lg:border-none lg:bg-transparent lg:p-0">
            <span className="flex items-center gap-1.5 text-xs text-ink-muted">
              <Users className="h-3.5 w-3.5 text-ink-secondary" />
              Population
            </span>
            <span className="font-mono text-xs font-semibold text-ink-primary">
              {profile.population ? profile.population.toLocaleString() : "—"}
            </span>
          </div>

          <div className="flex flex-col gap-1 rounded-xl border border-surface-border bg-surface-1/50 p-3 lg:border-none lg:bg-transparent lg:p-0">
            <span className="flex items-center gap-1.5 text-xs text-ink-muted">
              <Database className="h-3.5 w-3.5 text-brass" />
              Data Source
            </span>
            <span className="truncate font-mono text-xs font-semibold text-ink-primary" title={profile.data_source}>
              {profile.data_source}
            </span>
          </div>
        </div>
      </div>
    </Card>
  );
}

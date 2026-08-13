"use client";

import { MapPin, TrendingUp, Layers, Users, Globe } from "lucide-react";
import { Card, CardTitle } from "@/components/ui/Card";
import { TierBadge } from "@/components/capability/TierBadge";
import { cn } from "@/lib/utils";

interface CountryHeaderProps {
  country: {
    iso_code: string;
    name: string;
    supported_city_count: number;
    supported: boolean;
  };
  tierSummary?: {
    OBSERVED: number;
    TRANSFER: number;
    NONE: number;
  };
}

export function CountryHeader({
  country,
  tierSummary,
}: CountryHeaderProps) {
  const flagUrl = `https://flagcdn.com/w320/${country.iso_code.toLowerCase()}.png`;

  return (
    <Card className="relative overflow-hidden">
      {/* Background flag with overlay */}
      <div className="absolute inset-0 z-0 opacity-10">
        <img
          src={flagUrl}
          alt=""
          className="w-full h-full object-cover"
          onError={(e) => {
            e.currentTarget.style.display = "none";
          }}
        />
        <div className="absolute inset-0 bg-gradient-to-b from-surface-0/80 to-surface-0" />
      </div>

      <div className="relative z-10 p-6">
        <div className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-4">
          <div className="flex items-center gap-4">
            <div className="w-16 h-16 sm:w-20 sm:h-20 rounded-xl overflow-hidden border border-surface-border bg-surface-1 flex-shrink-0">
              <img
                src={flagUrl}
                alt={`${country.name} flag`}
                className="w-full h-full object-cover"
                onError={(e) => {
                  e.currentTarget.style.display = "none";
                  e.currentTarget.nextElementSibling?.classList.remove("hidden");
                }}
              />
              <div className="hidden w-full h-full flex items-center justify-center bg-surface-1 text-ink-muted">
                <Globe className="h-8 w-8" />
              </div>
            </div>
            <div>
              <h1 className="font-display text-2xl sm:text-3xl font-semibold text-ink-primary">
                {country.name}
              </h1>
              <p className="mt-1 text-sm text-ink-muted flex items-center gap-1">
                <MapPin className="h-4 w-4" />
                {country.supported_city_count} {country.supported_city_count === 1 ? "city" : "cities"} supported
              </p>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <TierBadge tier={country.supported ? "OBSERVED" : "NONE"} size="lg" />
            <div className="hidden sm:flex items-center gap-4 text-sm text-ink-muted border-l border-surface-border pl-4">
              {tierSummary && (
                <>
                  <TierBadge tier="OBSERVED" size="sm" showLabel={false} title={`${tierSummary.OBSERVED} cities`} />
                  <TierBadge tier="TRANSFER" size="sm" showLabel={false} title={`${tierSummary.TRANSFER} cities`} />
                  <TierBadge tier="NONE" size="sm" showLabel={false} title={`${tierSummary.NONE} cities`} />
                </>
              )}
            </div>
          </div>
        </div>

        {/* Tier Summary Bar */}
        {tierSummary && (
          <div className="mt-6 pt-6 border-t border-surface-border">
            <div className="grid grid-cols-3 gap-4">
              {[
                { tier: "OBSERVED", count: tierSummary.OBSERVED, label: "Trained locally", icon: TrendingUp },
                { tier: "TRANSFER", count: tierSummary.TRANSFER, label: "WorldMove priors", icon: Layers },
                { tier: "NONE", count: tierSummary.NONE, label: "Routing only", icon: Users },
              ].map(({ tier, count, label, icon: Icon }) => {
                const colors = {
                  OBSERVED: "text-brass",
                  TRANSFER: "text-verdigris",
                  NONE: "text-oxide",
                }[tier];
                return (
                  <div key={tier} className="flex flex-col items-center gap-1 text-center">
                    <div className="flex items-center gap-1.5">
                      <Icon className={cn("h-4 w-4", colors)} />
                      <span className={cn("font-medium", colors)}>{count}</span>
                    </div>
                    <span className="text-xs text-ink-muted">{label}</span>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>
    </Card>
  );
}
"use client";

import { Card, CardTitle } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { type CityTariffResponse } from "@/lib/api";
import { DollarSign, AlertTriangle, ShieldCheck } from "lucide-react";
import { cn } from "@/lib/utils";

interface TariffCardProps {
  tariff: CityTariffResponse;
  className?: string;
}

export function TariffCard({ tariff, className }: TariffCardProps) {
  const displayTariff = tariff;

  if (!displayTariff.available) {
    return (
      <Card className={cn("border border-dashed border-oxide/40 bg-oxide/5 p-6 text-center", className)}>
        <div className="flex items-center justify-center gap-2 text-oxide font-display text-sm font-semibold">
          <AlertTriangle className="h-4 w-4" />
          No Tariff Profile
        </div>
        <p className="mt-2 text-xs text-ink-muted">
          {displayTariff.reason || "Tariff parameters unavailable for this city."}
        </p>
      </Card>
    );
  }

  const items = [
    { label: "Currency", value: displayTariff.currency },
    { label: "Base Fare", value: displayTariff.base_fare ? `${displayTariff.currency} ${displayTariff.base_fare.toFixed(2)}` : "—" },
    { label: "Distance Rate", value: displayTariff.per_km ? `${displayTariff.currency} ${displayTariff.per_km.toFixed(2)} / km` : "—" },
    { label: "Time Rate", value: displayTariff.per_min ? `${displayTariff.currency} ${displayTariff.per_min.toFixed(2)} / min` : "—" },
    { label: "Minimum Fare", value: displayTariff.min_fare ? `${displayTariff.currency} ${displayTariff.min_fare.toFixed(2)}` : "—" },
    { label: "Peak Multiplier", value: displayTariff.peak_multiplier ? `${displayTariff.peak_multiplier.toFixed(2)}x` : "—" },
    { label: "Night Multiplier", value: displayTariff.night_multiplier ? `${displayTariff.night_multiplier.toFixed(2)}x` : "—" },
    { label: "Airport Surcharge", value: displayTariff.airport_surcharge ? `${displayTariff.currency} ${displayTariff.airport_surcharge.toFixed(2)}` : "—" },
    { label: "Surge Ceiling", value: displayTariff.surge_multiplier ? `${displayTariff.surge_multiplier.toFixed(2)}x` : "—" },
    { label: "Profile Source", value: displayTariff.source_type || "—" },
    { label: "Effective Date", value: displayTariff.effective_from || "—" },
    { label: "Profile Version", value: displayTariff.version || "—" },
  ];

  return (
    <Card className={cn("p-6", className)}>
      <div className="flex items-center justify-between border-b border-surface-border pb-4">
        <div className="flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg border border-brass/30 bg-brass/10 text-brass">
            <DollarSign className="h-4 w-4" />
          </div>
          <div>
            <CardTitle className="font-display text-base font-semibold text-ink-primary">
              Tariff Profile
            </CardTitle>
            <p className="text-xs text-ink-muted">Linear fare calculation basis & surcharges</p>
          </div>
        </div>

        {displayTariff.confidence && (
          <Badge basis={displayTariff.confidence > 0.7 ? "computed" : "modeled_estimate"}>
            <ShieldCheck className="h-3 w-3 mr-1" />
            Confidence {(displayTariff.confidence * 100).toFixed(0)}%
          </Badge>
        )}
      </div>

      <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-3">
        {items.map((item) => (
          <div
            key={item.label}
            className="flex flex-col gap-0.5 rounded-lg border border-surface-border bg-surface-1/40 p-2.5"
          >
            <span className="text-[11px] font-medium text-ink-muted">{item.label}</span>
            <span className="font-mono text-xs font-semibold text-ink-primary">{item.value}</span>
          </div>
        ))}
      </div>
    </Card>
  );
}

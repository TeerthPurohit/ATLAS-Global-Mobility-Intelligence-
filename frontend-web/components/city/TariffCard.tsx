"use client";

import { Card, CardTitle } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import type { CityTariffResponse } from "@/lib/api";
import { DollarSign, AlertTriangle, ShieldCheck } from "lucide-react";
import { cn } from "@/lib/utils";

interface TariffCardProps {
  tariff: CityTariffResponse;
  className?: string;
}

export function TariffCard({ tariff, className }: TariffCardProps) {
  if (!tariff.available) {
    return (
      <Card className={cn("border border-dashed border-oxide/40 bg-oxide/5 p-6 text-center", className)}>
        <div className="flex items-center justify-center gap-2 text-oxide font-display text-sm font-semibold">
          <AlertTriangle className="h-4 w-4" />
          No Tariff Profile
        </div>
        <p className="mt-2 text-xs text-ink-muted">
          {tariff.reason || "Tariff parameters unavailable for this city."}
        </p>
      </Card>
    );
  }

  const items = [
    { label: "Currency", value: tariff.currency },
    { label: "Base Fare", value: tariff.base_fare ? `${tariff.currency} ${tariff.base_fare.toFixed(2)}` : "—" },
    { label: "Distance Rate", value: tariff.per_km ? `${tariff.currency} ${tariff.per_km.toFixed(2)} / km` : "—" },
    { label: "Time Rate", value: tariff.per_min ? `${tariff.currency} ${tariff.per_min.toFixed(2)} / min` : "—" },
    { label: "Minimum Fare", value: tariff.min_fare ? `${tariff.currency} ${tariff.min_fare.toFixed(2)}` : "—" },
    { label: "Peak Multiplier", value: tariff.peak_multiplier ? `${tariff.peak_multiplier.toFixed(2)}x` : "—" },
    { label: "Night Multiplier", value: tariff.night_multiplier ? `${tariff.night_multiplier.toFixed(2)}x` : "—" },
    { label: "Airport Surcharge", value: tariff.airport_surcharge ? `${tariff.currency} ${tariff.airport_surcharge.toFixed(2)}` : "—" },
    { label: "Surge Ceiling", value: tariff.surge_multiplier ? `${tariff.surge_multiplier.toFixed(2)}x` : "—" },
    { label: "Profile Source", value: tariff.source_type || "Tariff Database" },
    { label: "Effective Date", value: tariff.effective_from || "2024-01-01" },
    { label: "Profile Version", value: tariff.version || "v1.0" },
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

        {tariff.confidence && (
          <Badge basis={tariff.confidence > 0.7 ? "computed" : "modeled_estimate"}>
            <ShieldCheck className="h-3 w-3 mr-1" />
            Confidence {(tariff.confidence * 100).toFixed(0)}%
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

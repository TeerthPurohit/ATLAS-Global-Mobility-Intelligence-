"use client";

import { useEffect, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { useQueryClient } from "@tanstack/react-query";
import { Card, CardTitle } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { PulsingStatusDot } from "@/components/magic/PulsingStatusDot";
import { streamTariffEnrichment, mergeTariffProfile, type CityTariffResponse } from "@/lib/api";
import { queryKeys } from "@/lib/queryKeys";
import { DollarSign, AlertTriangle, ShieldCheck, Sparkles } from "lucide-react";
import { cn } from "@/lib/utils";

interface TariffCardProps {
  tariff: CityTariffResponse;
  className?: string;
  // nyc/london price from a real trained fare model, never a tariff profile
  // (backend/routers/cities.py's WS route refuses enrichment for them too) --
  // without this, their page permanently shows a pointless "analyzing" flash
  // followed by an enrichment error, since they never have a cached profile.
  skipEnrichment?: boolean;
}

export function TariffCard({ tariff, className, skipEnrichment }: TariffCardProps) {
  const queryClient = useQueryClient();
  const [statusMessages, setStatusMessages] = useState<string[]>([]);
  const [enriching, setEnriching] = useState(false);
  const [liveTariff, setLiveTariff] = useState<CityTariffResponse | null>(null);
  const [enrichError, setEnrichError] = useState<string | null>(null);

  // A never-validated tariff (validation_method === null) needs on-demand
  // enrichment -- but skip the CityProfile placeholder (reason set in
  // CityProfile.tsx's defaultTariff) so this doesn't fire before the real
  // GET /api/cities/{city_id}/tariff response is in.
  const cityId = tariff.city_id;
  const needsEnrichment = !skipEnrichment && tariff.validation_method === null && tariff.reason !== "Tariff profile not loaded";

  useEffect(() => {
    if (!needsEnrichment || !cityId) return;
    setStatusMessages([]);
    setEnrichError(null);
    const close = streamTariffEnrichment(cityId, {
      onFrame: (frame) => {
        if (frame.type === "status") {
          setEnriching(true);
          setStatusMessages((msgs) => [...msgs, frame.message]);
        } else if (frame.type === "result") {
          setEnriching(false);
          setLiveTariff((prev) => mergeTariffProfile(prev ?? tariff, frame.profile));
          queryClient.invalidateQueries({ queryKey: queryKeys.cityTariff(cityId) });
        } else if (frame.type === "error") {
          setEnriching(false);
          setEnrichError(frame.message);
        }
      },
    });
    return close;
    // eslint-disable-next-line react-hooks/exhaustive-deps -- only re-open when the city or its validation state changes
  }, [needsEnrichment, cityId]);

  const displayTariff = liveTariff ?? tariff;
  const latestStatus = statusMessages[statusMessages.length - 1] ?? "Connecting to agent...";

  // needsEnrichment (not just `enriching`) covers the brief gap between mount
  // and the first WS status frame arriving -- without this, a never-validated
  // city would flash its old/possibly-templated numbers for a moment before
  // the "analyzing" state kicks in, which defeats the point of not showing
  // stale duplicate data.
  if (needsEnrichment && !liveTariff && !enrichError) {
    return (
      <Card className={cn("p-6", className)}>
        <div className="flex items-center gap-2 border-b border-surface-border pb-4">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg border border-brass/30 bg-brass/10 text-brass">
            <Sparkles className="h-4 w-4" />
          </div>
          <div>
            <CardTitle className="font-display text-base font-semibold text-ink-primary">
              Tariff Profile
            </CardTitle>
            <p className="text-xs text-ink-muted">Analyzing this city&apos;s fare structure for the first time...</p>
          </div>
        </div>

        <div className="mt-4 flex items-center gap-2.5 rounded-lg border border-brass/20 bg-brass/5 p-4">
          <PulsingStatusDot status="observed" />
          <AnimatePresence mode="wait">
            <motion.span
              key={latestStatus}
              initial={{ opacity: 0, y: 4 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -4 }}
              transition={{ duration: 0.2 }}
              className="font-mono text-xs text-ink-secondary"
            >
              {latestStatus}
            </motion.span>
          </AnimatePresence>
        </div>
      </Card>
    );
  }

  if (!displayTariff.available) {
    return (
      <Card className={cn("border border-dashed border-oxide/40 bg-oxide/5 p-6 text-center", className)}>
        <div className="flex items-center justify-center gap-2 text-oxide font-display text-sm font-semibold">
          <AlertTriangle className="h-4 w-4" />
          No Tariff Profile
        </div>
        <p className="mt-2 text-xs text-ink-muted">
          {enrichError || displayTariff.reason || "Tariff parameters unavailable for this city."}
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

      {enrichError && (
        <p className="mt-3 flex items-center gap-1.5 text-xs text-oxide">
          <AlertTriangle className="h-3 w-3" />
          Enrichment failed, showing last known tariff: {enrichError}
        </p>
      )}

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

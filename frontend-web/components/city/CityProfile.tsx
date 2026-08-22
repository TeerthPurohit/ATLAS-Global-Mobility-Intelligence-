"use client";

import { useQuery, keepPreviousData } from "@tanstack/react-query";
import {
  getCityProfile,
  getCityCapabilities,
  getCityTariff,
  getCityZones,
  type CityTariffResponse,
} from "@/lib/api";
import { queryKeys } from "@/lib/queryKeys";
import { Card, CardTitle } from "@/components/ui/Card";
import { CityHero } from "./CityHero";
import { CapabilityMatrix } from "./CapabilityMatrix";
import { TariffCard } from "./TariffCard";
import { ModelStatus } from "./ModelStatus";
import { QuickActions } from "./QuickActions";
import { Search } from "lucide-react";

export function CityProfile({ cityId }: { cityId: string }) {
  const { data: profile, isLoading: profileLoading, error: profileError } = useQuery({
    queryKey: queryKeys.cityProfile(cityId),
    queryFn: () => getCityProfile(cityId),
    enabled: !!cityId,
    placeholderData: keepPreviousData,
  });

  const { data: capabilities } = useQuery({
    queryKey: queryKeys.cityCapabilities(cityId),
    queryFn: () => getCityCapabilities(cityId),
    enabled: !!cityId,
    placeholderData: keepPreviousData,
  });

  const { data: tariff } = useQuery({
    queryKey: queryKeys.cityTariff(cityId),
    queryFn: () => getCityTariff(cityId),
    enabled: !!cityId,
    placeholderData: keepPreviousData,
  });

  const { data: zones } = useQuery({
    queryKey: queryKeys.cityZones(cityId),
    queryFn: () => getCityZones(cityId),
    enabled: cityId === "nyc",
  });

  if (profileLoading) {
    return (
      <div className="flex flex-col gap-6 animate-pulse">
        <div className="h-40 rounded-2xl bg-surface-1" />
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 h-96 rounded-2xl bg-surface-1" />
          <div className="h-96 rounded-2xl bg-surface-1" />
        </div>
      </div>
    );
  }

  if (profileError || !profile) {
    return (
      <Card className="border-dashed border-oxide/40 bg-oxide/5 p-8 text-center text-oxide">
        <p className="font-display text-base font-semibold">City Profile Not Found</p>
        <p className="mt-1 text-xs text-ink-muted">Unable to load profile data for city ID: {cityId}</p>
      </Card>
    );
  }

  const hasCapabilities = Boolean(capabilities?.demand || capabilities?.fare || capabilities?.journey);

  const defaultCaps = {
    demand: false,
    fare: false,
    journey: false,
    chat: false,
    area_analysis: false,
    routing: false,
    congestion: false,
    availability: false,
    surge: false,
    carbon: false,
    best_departure: false,
    chat_tier: "sql_only" as const,
    mobility_mode: "",
    area_type: "",
    forecast: false,
    transit_coverage: false,
  };

  const defaultTariff: CityTariffResponse = {
    available: false,
    city_id: cityId,
    reason: "Tariff profile not loaded",
    currency: null,
    base_fare: null,
    per_km: null,
    per_min: null,
    min_fare: null,
    night_multiplier: null,
    airport_surcharge: null,
    booking_fee: null,
    platform_fee: null,
    tolls: null,
    peak_multiplier: null,
    vehicle_multiplier: null,
    surge_multiplier: null,
    effective_from: null,
    version: null,
    source_type: null,
    confidence: null,
    notes: null,
    generated_at: null,
    model_id: null,
    validation_method: null,
    evidence_sources: null,
    validated_at: null,
  };

  return (
    <div className="flex flex-col gap-6">
      <CityHero profile={profile} />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 flex flex-col gap-6">
          <CapabilityMatrix capabilities={capabilities || defaultCaps} />
          <TariffCard tariff={tariff || defaultTariff} />

          {/* Zones list (NYC Specialization) */}
          {zones?.available && zones.zones && (
            <Card className="p-6">
              <div className="flex items-center justify-between border-b border-surface-border pb-3">
                <div className="flex items-center gap-2">
                  <Search className="h-4 w-4 text-brass" />
                  <CardTitle className="font-display text-base font-semibold text-ink-primary">
                    Taxi & Mobility Zones
                  </CardTitle>
                </div>
                <span className="font-mono text-xs font-semibold text-brass">
                  {zones.zones.length} ZONES
                </span>
              </div>

              <div className="mt-4 flex flex-wrap gap-2 max-h-60 overflow-y-auto pr-1">
                {zones.zones.map((zone) => (
                  <span
                    key={zone.zone_id}
                    className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-surface-1 text-xs font-mono text-ink-secondary border border-surface-border"
                  >
                    <span className="text-brass font-bold">{zone.zone_id}</span> &bull; {zone.zone}{" "}
                    <span className="text-ink-muted">({zone.borough})</span>
                  </span>
                ))}
              </div>
            </Card>
          )}
        </div>

        <div className="flex flex-col gap-6">
          <QuickActions cityId={cityId} hasCapabilities={hasCapabilities} />
          <ModelStatus profile={profile} />
        </div>
      </div>
    </div>
  );
}
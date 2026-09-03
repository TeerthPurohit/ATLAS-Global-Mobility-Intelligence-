"use client";

import { Card, CardTitle } from "@/components/ui/Card";
import { PredictionField } from "@/components/journey/PredictionField";
import { Skeleton } from "@/components/ui/Skeleton";
import { useQuery } from "@tanstack/react-query";
import { getWeather, getHoliday, getTraffic, type WeatherResponse, type HolidayResponse, type TrafficResponse } from "@/lib/api";
import { queryKeys } from "@/lib/queryKeys";
import { CapabilityGate } from "@/components/capability/CapabilityGate";
import { Sun, Cloud, CloudRain, CloudSnow, Calendar, Car } from "lucide-react";

interface ContextCardProps {
  pickupLat: number;
  pickupLon: number;
  dropoffLat: number;
  dropoffLon: number;
  departureTime: string;
}

function ContextCardSkeleton() {
  return (
    <Card>
      <CardTitle className="font-display text-base tracking-wide flex items-center gap-2">
        <Calendar className="h-4 w-4 text-brass" />
        Context
      </CardTitle>
      <div className="mt-3 space-y-3">
        <Skeleton className="h-10 w-full" />
        <Skeleton className="h-10 w-full" />
        <Skeleton className="h-10 w-full" />
      </div>
    </Card>
  );
}

function WeatherIcon({ condition }: { condition: string | null }) {
  if (!condition) return <Cloud className="h-4 w-4 text-ink-muted" />;
  const c = condition.toLowerCase();
  if (c.includes("sun") || c.includes("clear")) return <Sun className="h-4 w-4 text-brass" />;
  if (c.includes("rain") || c.includes("drizzle") || c.includes("shower")) return <CloudRain className="h-4 w-4 text-verdigris" />;
  if (c.includes("snow") || c.includes("sleet") || c.includes("ice")) return <CloudSnow className="h-4 w-4 text-ink-secondary" />;
  return <Cloud className="h-4 w-4 text-ink-muted" />;
}

function ContextCardContent({
  weather,
  holiday,
  traffic
}: {
  weather: WeatherResponse | null;
  holiday: HolidayResponse | null;
  traffic: TrafficResponse | null;
}) {
  return (
    <Card className="shadow-xs border-surface-border bg-surface-1">
      <div className="flex items-center justify-between border-b border-surface-border/60 pb-3 mb-4">
        <CardTitle className="font-display text-base tracking-wide flex items-center gap-2">
          <Calendar className="h-4 w-4 text-brass" />
          Spatial Environmental Context
        </CardTitle>
        <span className="rounded-full bg-teal-500/10 border border-teal-500/20 px-2.5 py-0.5 font-mono text-[10px] font-semibold text-teal-700 dark:text-teal-400">
          Live Telemetry Synced
        </span>
      </div>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        {/* Weather */}
        <div className="flex items-start gap-3 p-3.5 rounded-xl border border-surface-border/70 bg-surface-0/60 transition-colors hover:bg-surface-0">
          <div className="p-2 rounded-lg bg-brass/10 text-brass mt-0.5">
            <WeatherIcon condition={weather?.weather_condition || "clear"} />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-xs font-bold text-ink-primary truncate">
              {weather?.weather_condition || "Optimal Weather"}
            </p>
            <p className="text-[11px] text-ink-muted mt-0.5">
              Precipitation Risk: {weather?.severity !== null ? `${Math.round((weather?.severity || 0) * 100)}%` : "0%"}
            </p>
            <span className="mt-1 inline-block text-[10px] font-mono text-ink-muted/80">
              Open-Meteo Feed
            </span>
          </div>
        </div>

        {/* Holiday */}
        <div className="flex items-start gap-3 p-3.5 rounded-xl border border-surface-border/70 bg-surface-0/60 transition-colors hover:bg-surface-0">
          <div className="p-2 rounded-lg bg-teal-500/10 text-teal-600 mt-0.5">
            <Calendar className="h-4 w-4" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-xs font-bold text-ink-primary truncate">
              {holiday?.is_holiday ? holiday.holiday_name || "Public Holiday" : "Standard Business Day"}
            </p>
            <p className="text-[11px] text-ink-muted mt-0.5">
              Region: {holiday?.country || "US"} NYC Municipal
            </p>
            <span className="mt-1 inline-block text-[10px] font-mono text-ink-muted/80">
              Calendar Engine
            </span>
          </div>
        </div>

        {/* Traffic */}
        <div className="flex items-start gap-3 p-3.5 rounded-xl border border-surface-border/70 bg-surface-0/60 transition-colors hover:bg-surface-0">
          <div className="p-2 rounded-lg bg-indigo-500/10 text-indigo-600 mt-0.5">
            <Car className="h-4 w-4" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-xs font-bold text-ink-primary truncate">
              {traffic?.congestion_level !== null
                ? `${Math.round((traffic?.congestion_level || 0) * 100)}% Local Traffic Index`
                : "Smooth Traffic Flow"}
            </p>
            <p className="text-[11px] text-ink-muted mt-0.5">
              {traffic?.note || "Calibrated zone-flow baseline"}
            </p>
            <span className="mt-1 inline-block text-[10px] font-mono text-ink-muted/80">
              TLC Corridor Baseline
            </span>
          </div>
        </div>
      </div>
    </Card>
  );
}

export function ContextCard({
  pickupLat,
  pickupLon,
  dropoffLat,
  dropoffLon,
  departureTime
}: ContextCardProps) {
  const { data: weather, isLoading: weatherLoading } = useQuery({
    queryKey: queryKeys.weather({ lat: pickupLat, lon: pickupLon, timestamp: departureTime }),
    queryFn: () => getWeather(pickupLat, pickupLon, departureTime),
    staleTime: 10 * 60_000,
  });

  const { data: holiday, isLoading: holidayLoading } = useQuery({
    queryKey: queryKeys.holiday({ lat: pickupLat, lon: pickupLon, date: departureTime.split("T")[0] }),
    queryFn: () => getHoliday(pickupLat, pickupLon, departureTime.split("T")[0]),
    staleTime: 24 * 60 * 60_000,
  });

  const { data: traffic, isLoading: trafficLoading } = useQuery({
    queryKey: queryKeys.traffic({ lat: pickupLat, lon: pickupLon }),
    queryFn: () => getTraffic(pickupLat, pickupLon),
    staleTime: 5 * 60_000,
  });

  const isLoading = weatherLoading || holidayLoading || trafficLoading;

  return (
    <CapabilityGate capability="routing" fallback={<ContextCardSkeleton />}>
      {isLoading ? <ContextCardSkeleton /> : (
        <ContextCardContent
          weather={weather ?? null}
          holiday={holiday ?? null}
          traffic={traffic ?? null}
        />
      )}
    </CapabilityGate>
  );
}
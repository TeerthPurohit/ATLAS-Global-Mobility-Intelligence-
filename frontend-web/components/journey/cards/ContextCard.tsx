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
    <Card>
      <CardTitle className="font-display text-base tracking-wide flex items-center gap-2">
        <Calendar className="h-4 w-4 text-brass" />
        Context
      </CardTitle>
      <div className="mt-3 space-y-4">
        {/* Weather */}
        {weather && (
          <div className="flex items-center gap-3 p-3 rounded-lg bg-surface-1">
            <WeatherIcon condition={weather.weather_condition} />
            <div className="flex-1">
              <p className="font-medium text-ink-primary">
                {weather.severity !== null
                  ? `Severity ${Math.round(weather.severity * 100)}%`
                  : weather.temperature !== null
                    ? `${Math.round(weather.temperature)}°C`
                    : "—"}
                {weather.weather_condition && ` · ${weather.weather_condition}`}
              </p>
              <p className="text-xs text-ink-muted">
                Source: {weather.source} · {new Date(weather.timestamp).toLocaleString()}
              </p>
            </div>
          </div>
        )}

        {/* Holiday */}
        {holiday && (
          <div className="flex items-center gap-3 p-3 rounded-lg bg-surface-1">
            <Calendar className="h-4 w-4 text-verdigris" />
            <div className="flex-1">
              <p className="font-medium text-ink-primary">
                {holiday.is_holiday ? holiday.holiday_name || "Holiday" : "No holiday today"}
              </p>
              <p className="text-xs text-ink-muted">
                {holiday.country} · Source: {holiday.source}
              </p>
            </div>
            {holiday.is_holiday && (
              <span className="px-2 py-1 text-xs rounded-full bg-verdigris/10 text-verdigris border border-verdigris/30">
                Holiday
              </span>
            )}
          </div>
        )}

        {/* Traffic */}
        {traffic && (
          <div className="flex items-center gap-3 p-3 rounded-lg bg-surface-1">
            <Car className="h-4 w-4 text-oxide" />
            <div className="flex-1">
              <p className="font-medium text-ink-primary">
                {traffic.congestion_level !== null
                  ? `${Math.round(traffic.congestion_level * 100)}% congestion`
                  : "No data"}
                {traffic.is_live && <span className="ml-2 text-xs text-verdigris">LIVE</span>}
              </p>
              <p className="text-xs text-ink-muted">
                Source: {traffic.source} · {new Date(traffic.timestamp).toLocaleString()}
                {traffic.note && ` · ${traffic.note}`}
              </p>
            </div>
          </div>
        )}

        {!weather && !holiday && !traffic && (
          <p className="text-sm text-ink-muted text-center py-4">
            No context data available
          </p>
        )}
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
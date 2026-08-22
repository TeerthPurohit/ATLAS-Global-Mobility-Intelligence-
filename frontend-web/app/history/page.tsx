"use client";

import { useState } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { Card, CardTitle } from "@/components/ui/Card";
import { Skeleton } from "@/components/ui/Skeleton";
import { Dialog } from "@/components/ui/Dialog";
import { PredictionField } from "@/components/journey/PredictionField";
import { JourneyResults } from "@/components/journey/JourneyResults";
import { getJourneyHistory, type JourneyEstimate, type JourneyHistoryEntry, type PredictionOut, type JourneyRequest } from "@/lib/api";
import { Clock, MapPin } from "lucide-react";

function coordLabel(lat: number, lon: number) {
  return `${lat.toFixed(4)}, ${lon.toFixed(4)}`;
}

function HistoryEntryCard({ entry, onOpen }: { entry: JourneyHistoryEntry; onOpen: () => void }) {
  const fare: PredictionOut = {
    value: entry.fare_value,
    unit: entry.fare_value ? "USD" : null,
    basis: entry.fare_basis ?? "unavailable",
    source: "journey/history",
    reason: null,
    data_vintage: null,
    value_usd: entry.fare_value ? Number(entry.fare_value) : null,
  };

  const requestTime = new Date(entry.requested_at);
  const departureTime = new Date(entry.departure_time);

  return (
    <button
      type="button"
      onClick={onOpen}
      className="w-full text-left"
    >
      <Card className="cursor-pointer transition-colors hover:border-brass/40 p-6">
        <div className="flex items-start justify-between gap-6">
          <div className="flex flex-col gap-4 flex-1">
            {/* Trip ID and Time */}
            <div className="flex items-center gap-3">
              <span className="font-label-sm text-brass">Trip #{entry.id}</span>
              <span className="font-body-sm text-ink-muted">
                {requestTime.toLocaleDateString()} at {requestTime.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
              </span>
            </div>

            {/* Route */}
            <div className="flex items-start gap-3">
              <MapPin className="h-4 w-4 text-brass mt-0.5 shrink-0" />
              <div className="flex flex-col gap-1">
                <p className="font-body-sm text-ink-secondary">
                  {coordLabel(entry.pickup_lat, entry.pickup_lon)} → {coordLabel(entry.dropoff_lat, entry.dropoff_lon)}
                </p>
                <p className="font-body-sm text-ink-muted">
                  {entry.vehicle_type} · Departs {departureTime.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                </p>
              </div>
            </div>
          </div>

          {/* Fare */}
          <div className="text-right shrink-0">
            <PredictionField label="Fare" prediction={fare} />
          </div>
        </div>
      </Card>
    </button>
  );
}

export default function HistoryPage() {
  const [openEntry, setOpenEntry] = useState<JourneyHistoryEntry | null>(null);
  const { data, isLoading, isError, error } = useQuery({
    queryKey: ["journey-history"],
    queryFn: () => getJourneyHistory(50),
  });

  const request: JourneyRequest | null = openEntry
    ? {
        city_id: openEntry.city_id || "nyc",
        pickup_lat: openEntry.pickup_lat,
        pickup_lon: openEntry.pickup_lon,
        dropoff_lat: openEntry.dropoff_lat,
        dropoff_lon: openEntry.dropoff_lon,
        departure_time: openEntry.departure_time,
        vehicle_type: openEntry.vehicle_type,
      }
    : null;

  return (
    <div className="flex flex-col gap-12">
      {/* Header */}
      <section className="flex flex-col gap-3">
        <span className="font-label-sm text-brass tracking-wider">
          Past Journeys
        </span>
        <h1 className="font-display-lg text-ink-primary">
          Journey Log
        </h1>
        <p className="font-body-md max-w-2xl text-ink-secondary">
          Browse your journey history and re-analyze past routes.
        </p>
      </section>

      {/* Content */}
      {isLoading && (
        <div className="flex flex-col gap-4">
          {[0, 1, 2].map((i) => (
            <Card key={i} className="p-6">
              <Skeleton className="h-4 w-40" />
              <Skeleton className="mt-4 h-4 w-64" />
              <Skeleton className="mt-2 h-3 w-48" />
            </Card>
          ))}
        </div>
      )}

      {isError && (
        <Card className="border-oxide/40 bg-oxide/5 p-8">
          <div className="flex items-start gap-4">
            <div className="p-2 bg-oxide/10 rounded-sm">
              <Clock className="h-5 w-5 text-oxide" />
            </div>
            <div>
              <CardTitle className="font-section-md text-oxide">Could not load journey log</CardTitle>
              <p className="mt-2 font-body-sm text-ink-secondary">
                {error instanceof Error ? error.message : "Unknown error"}
              </p>
            </div>
          </div>
        </Card>
      )}

      {!isLoading && !isError && data && data.length === 0 && (
        <Card className="border-surface-border bg-surface-1 p-12 text-center">
          <div className="flex justify-center mb-4">
            <div className="p-3 bg-brass/10 rounded-sm">
              <Clock className="h-6 w-6 text-brass" />
            </div>
          </div>
          <h3 className="font-section-md text-ink-primary">No journeys yet</h3>
          <p className="mt-2 font-body-sm text-ink-secondary">
            Start by plotting a journey to build your history.
          </p>
          <Link href="/journey" className="mt-4 inline-block font-section-md text-brass hover:opacity-80 transition-opacity">
            Plot a Journey →
          </Link>
        </Card>
      )}

      {!isLoading && !isError && data && data.length > 0 && (
        <div className="flex flex-col gap-4">
          {data.map((entry) => (
            <HistoryEntryCard key={entry.id} entry={entry} onOpen={() => setOpenEntry(entry)} />
          ))}
        </div>
      )}

      <Dialog
        open={openEntry !== null}
        onClose={() => setOpenEntry(null)}
        title={openEntry ? `Trip #${openEntry.id}` : undefined}
        className="max-w-2xl max-h-[85vh] overflow-y-auto"
      >
        {request ? (
          <JourneyResults request={request} />
        ) : (
          <p className="font-body-sm text-ink-muted">Could not parse trip request details.</p>
        )}
      </Dialog>
    </div>
  );
}

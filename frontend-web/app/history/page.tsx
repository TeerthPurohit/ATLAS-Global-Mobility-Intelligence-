"use client";

import { useState } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { Card, CardTitle } from "@/components/ui/Card";
import { Skeleton } from "@/components/ui/Skeleton";
import { Dialog } from "@/components/ui/Dialog";
import { PredictionField } from "@/components/journey/PredictionField";
import { JourneyResults } from "@/components/journey/JourneyResults";
import { getJourneyHistory, type JourneyEstimate, type JourneyHistoryEntry } from "@/lib/api";

function coordLabel(lat: number, lon: number) {
  return `${lat.toFixed(4)}, ${lon.toFixed(4)}`;
}

function HistoryEntryCard({ entry, onOpen }: { entry: JourneyHistoryEntry; onOpen: () => void }) {
  const fare = {
    value: entry.fare_value,
    unit: entry.fare_value ? "USD" : null,
    basis: entry.fare_basis ?? "unavailable",
    source: "journey/history",
    reason: null,
  } as const;

  return (
    <button
      type="button"
      onClick={onOpen}
      className="w-full text-left"
    >
      <Card className="cursor-pointer transition-colors hover:border-brass/50">
        <div className="flex items-start justify-between gap-4">
          <div className="flex flex-col gap-1">
            <CardTitle className="font-display text-sm tracking-wide">Trip #{entry.id}</CardTitle>
            <span className="text-xs text-ink-muted">
              {new Date(entry.requested_at).toLocaleString()}
            </span>
            <span className="text-xs text-ink-secondary">
              Pickup {coordLabel(entry.pickup_lat, entry.pickup_lon)} → Dropoff{" "}
              {coordLabel(entry.dropoff_lat, entry.dropoff_lon)}
            </span>
            <span className="text-xs text-ink-secondary">
              {entry.vehicle_type} · departs {new Date(entry.departure_time).toLocaleString()}
            </span>
          </div>
          <PredictionField label="Fare" prediction={fare} />
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

  let parsedEstimate: JourneyEstimate | null = null;
  if (openEntry) {
    try {
      parsedEstimate = JSON.parse(openEntry.response_json) as JourneyEstimate;
    } catch {
      parsedEstimate = null;
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <h1 className="font-display text-2xl tracking-wide text-ink-primary">Journey Log</h1>

      {isLoading && (
        <div className="flex flex-col gap-3">
          {[0, 1, 2].map((i) => (
            <Card key={i}>
              <Skeleton className="h-4 w-40" />
              <Skeleton className="mt-2 h-4 w-64" />
            </Card>
          ))}
        </div>
      )}

      {isError && (
        <Card className="border-danger/30 bg-danger/5">
          <CardTitle className="text-danger">Could not reach the log</CardTitle>
          <p className="mt-2 text-sm text-ink-secondary">
            {error instanceof Error ? error.message : "Unknown error"}
          </p>
        </Card>
      )}

      {!isLoading && !isError && data && data.length === 0 && (
        <Card className="text-center">
          <p className="text-sm text-ink-secondary">No journeys logged yet.</p>
          <Link href="/journey" className="mt-2 inline-block text-sm text-brass hover:underline">
            Plot a journey →
          </Link>
        </Card>
      )}

      {!isLoading && !isError && data && data.length > 0 && (
        <div className="flex flex-col gap-3">
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
        {parsedEstimate ? (
          <JourneyResults estimate={parsedEstimate} />
        ) : (
          <p className="text-sm text-ink-muted">Could not parse this trip's stored estimate.</p>
        )}
      </Dialog>
    </div>
  );
}

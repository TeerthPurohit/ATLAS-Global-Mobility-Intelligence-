"use client";

import { Card } from "@/components/ui/Card";
import { JourneyDashboard } from "@/components/journey/dashboard/JourneyDashboard";
import { isInCoverage, type JourneyRequest } from "@/lib/api";

interface JourneyResultsProps {
  request: JourneyRequest;
}

export function JourneyResults({ request }: JourneyResultsProps) {
  if (!isInCoverage(request.pickup_lat, request.pickup_lon)) {
    return (
      <div className="space-y-4">
        <Card className="border-oxide/40 bg-surface-1 p-6 text-center">
          <p className="text-sm font-medium text-oxide">Location Outside Service Coverage</p>
          <p className="mt-1 text-xs text-ink-secondary">
            The selected pickup coordinates are outside the calibrated 5-Borough NYC service zone. Please select a valid address from the location search.
          </p>
        </Card>
      </div>
    );
  }

  return <JourneyDashboard request={request} />;
}

export function JourneyResultsSkeleton() {
  return (
    <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
      {[0, 1, 2, 3].map((i) => (
        <Card key={i} className="p-5">
          <div className="h-4 w-20 animate-pulse bg-surface-2 rounded" />
          <div className="mt-3 h-8 w-32 animate-pulse bg-surface-2 rounded" />
          <div className="mt-2 h-3 w-24 animate-pulse bg-surface-2 rounded" />
        </Card>
      ))}
    </div>
  );
}

export function JourneyResultsError({ message }: { message: string }) {
  return (
    <Card className="border-oxide/30 bg-oxide/5 p-6 text-center">
      <p className="font-medium text-oxide">Telemetry Retrieval Incomplete</p>
      <p className="mt-1 text-xs text-ink-muted">{message}</p>
    </Card>
  );
}
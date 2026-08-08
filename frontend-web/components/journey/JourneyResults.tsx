import { Card, CardTitle } from "@/components/ui/Card";
import { Skeleton } from "@/components/ui/Skeleton";
import { PredictionField } from "@/components/journey/PredictionField";
import type { JourneyEstimate } from "@/lib/api";

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <Card>
      <CardTitle className="font-display text-base tracking-wide">{title}</CardTitle>
      <div className="mt-2 divide-y divide-surface-border">{children}</div>
    </Card>
  );
}

export function JourneyResultsSkeleton() {
  return (
    <div className="flex flex-col gap-4">
      {[0, 1, 2].map((i) => (
        <Card key={i}>
          <Skeleton className="h-4 w-24" />
          <div className="mt-3 flex flex-col gap-2">
            <Skeleton className="h-8 w-full" />
            <Skeleton className="h-8 w-full" />
            <Skeleton className="h-8 w-full" />
          </div>
        </Card>
      ))}
    </div>
  );
}

export function JourneyResultsError({ message }: { message: string }) {
  return (
    <Card className="border-danger/30 bg-danger/5">
      <CardTitle className="text-danger">Estimate failed</CardTitle>
      <p className="mt-2 text-sm text-ink-secondary">{message}</p>
    </Card>
  );
}

export function JourneyResults({ estimate }: { estimate: JourneyEstimate }) {
  return (
    <div className="flex flex-col gap-4">
      <Section title="Journey">
        <PredictionField label="Fare" prediction={estimate.fare} emphasis />
        <PredictionField label="Fare range" prediction={estimate.fare_range} />
        <PredictionField label="Duration" prediction={estimate.duration} />
        <PredictionField label="Distance" prediction={estimate.distance} />
        <PredictionField label="Confidence" prediction={estimate.confidence} emphasis />
      </Section>

      <Section title="Mobility">
        <PredictionField label="Congestion" prediction={estimate.congestion} />
        <PredictionField label="Demand" prediction={estimate.demand} />
        <PredictionField label="Ride availability" prediction={estimate.ride_availability} />
        <PredictionField label="Surge risk" prediction={estimate.surge_risk} />
        <PredictionField label="Best departure time" prediction={estimate.best_departure_time} />
      </Section>

      <Section title="Environment">
        <PredictionField label="Carbon emissions" prediction={estimate.carbon_emissions} />
      </Section>

      <Section title="AI">
        <PredictionField label="Recommendation" prediction={estimate.ai_recommendation} />
      </Section>

      {Object.keys(estimate.fare_breakdown).length > 0 && (
        <Section title="Fare breakdown">
          {Object.entries(estimate.fare_breakdown).map(([key, pred]) => (
            <PredictionField key={key} label={key} prediction={pred} />
          ))}
        </Section>
      )}
    </div>
  );
}

import { Bike, Car, CarFront, CarTaxiFront, Sparkles, Truck, Zap, type LucideIcon } from "lucide-react";
import { Card, CardTitle } from "@/components/ui/Card";
import { Skeleton } from "@/components/ui/Skeleton";
import { PredictionField } from "@/components/journey/PredictionField";
import { cn } from "@/lib/utils";
import { CertaintyRing } from "@/components/journey/CertaintyRing";
import type { JourneyEstimate, VehicleClass } from "@/lib/api";

const VEHICLE_ICONS: Record<VehicleClass, LucideIcon> = {
  bike: Bike,
  auto: CarTaxiFront,
  mini: Car,
  sedan: CarFront,
  suv: Truck,
  ev: Zap,
  premium: Sparkles,
};

interface CompareCardProps {
  vehicle: VehicleClass;
  isPending: boolean;
  isError: boolean;
  error: unknown;
  data?: JourneyEstimate;
  winner?: boolean;
}

function BasisBadge({ basis }: { basis: string }) {
  const colors = {
    computed: "bg-brass/10 text-brass border-brass/30",
    modeled_estimate: "bg-verdigris/10 text-verdigris border-verdigris/30",
    unavailable: "bg-oxide/10 text-oxide border-oxide/30",
  };
  const labels = {
    computed: "computed",
    modeled_estimate: "modeled",
    unavailable: "N/A",
  };
  return (
    <span className={cn("inline-flex items-center gap-1 px-1.5 py-0.5 text-[10px] font-medium rounded border", colors[basis as keyof typeof colors] || colors.unavailable)}>
      <CertaintyRing basis={basis as "computed" | "modeled_estimate" | "unavailable"} size={10} />
      {labels[basis as keyof typeof labels] || basis}
    </span>
  );
}

function ComparisonCell({ label, prediction, winner = false }: { label: string; prediction: JourneyEstimate["fare"]; winner?: boolean }) {
  return (
    <div className={cn("py-1.5", winner && "bg-brass/5")}>
      <div className="flex items-center justify-between gap-2">
        <span className="flex items-center gap-1.5 text-xs uppercase tracking-wider text-ink-muted">
          <CertaintyRing basis={prediction.basis} size={12} title={prediction.reason ?? prediction.basis} />
          {label}
        </span>
        <div className="flex items-center gap-2">
          <BasisBadge basis={prediction.basis} />
          {prediction.basis === "unavailable" ? (
            <span className="font-mono text-sm text-ink-muted">no reading</span>
          ) : (
            <span className={cn("font-mono text-sm font-medium", prediction.basis === "modeled_estimate" && "text-verdigris")}>
              {typeof prediction.value === "number" ? prediction.value.toFixed(prediction.unit === "%" ? 0 : 2) : String(prediction.value ?? "--")}
              {prediction.unit && <span className="ml-1 text-xs text-ink-muted">{prediction.unit}</span>}
            </span>
          )}
        </div>
      </div>
      {prediction.reason && prediction.basis !== "unavailable" && (
        <span className="text-xs text-ink-muted ml-14">{prediction.reason}</span>
      )}
    </div>
  );
}

export function CompareCard({ vehicle, isPending, isError, error, data, winner }: CompareCardProps) {
  const Icon = VEHICLE_ICONS[vehicle];

  return (
    <Card
      className={cn(
        "flex min-w-[280px] flex-1 flex-col gap-1",
        winner && "border-2 border-brass shadow-[0_0_0_1px_rgba(201,146,42,0.25),0_0_24px_rgba(201,146,42,0.15)]"
      )}
    >
      <div className="flex items-center justify-between">
        <CardTitle className="flex items-center gap-2 font-display text-base capitalize tracking-wide">
          <Icon className="h-4 w-4 text-brass" />
          {vehicle}
        </CardTitle>
        {winner && (
          <span className="rounded-full bg-brass/15 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-brass">
            Lowest fare
          </span>
        )}
      </div>

      {isPending && (
        <div className="mt-3 flex flex-col gap-2">
          <Skeleton className="h-8 w-full" />
          <Skeleton className="h-6 w-full" />
          <Skeleton className="h-6 w-full" />
          <Skeleton className="h-6 w-full" />
          <Skeleton className="h-6 w-full" />
        </div>
      )}

      {isError && (
        <p className="mt-2 text-sm text-danger">
          {error instanceof Error ? error.message : "Estimate failed"}
        </p>
      )}

      {data && (
        <div className="mt-1 divide-y divide-surface-border">
          <ComparisonCell label="Fare" prediction={data.fare} winner={winner} />
          <ComparisonCell label="Duration" prediction={data.duration} />
          <ComparisonCell label="Carbon" prediction={data.carbon_emissions} />
          <ComparisonCell label="Availability" prediction={data.ride_availability} />
          <ComparisonCell label="Confidence" prediction={data.confidence} />
        </div>
      )}
    </Card>
  );
}
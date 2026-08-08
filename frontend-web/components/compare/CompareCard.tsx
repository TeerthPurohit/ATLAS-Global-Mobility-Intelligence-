import { Bike, Car, CarFront, CarTaxiFront, Sparkles, Truck, Zap, type LucideIcon } from "lucide-react";
import { Card, CardTitle } from "@/components/ui/Card";
import { Skeleton } from "@/components/ui/Skeleton";
import { PredictionField } from "@/components/journey/PredictionField";
import { cn } from "@/lib/utils";
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

export function CompareCard({ vehicle, isPending, isError, error, data, winner }: CompareCardProps) {
  const Icon = VEHICLE_ICONS[vehicle];

  return (
    <Card
      className={cn(
        "flex min-w-[260px] flex-1 flex-col gap-1",
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
        </div>
      )}

      {isError && (
        <p className="mt-2 text-sm text-danger">
          {error instanceof Error ? error.message : "Estimate failed"}
        </p>
      )}

      {data && (
        <div className="mt-1 divide-y divide-surface-border">
          <PredictionField label="Fare" prediction={data.fare} emphasis />
          <PredictionField label="Duration" prediction={data.duration} />
          <PredictionField label="Carbon emissions" prediction={data.carbon_emissions} />
          <PredictionField label="Ride availability" prediction={data.ride_availability} />
          <PredictionField label="Confidence" prediction={data.confidence} />
        </div>
      )}
    </Card>
  );
}

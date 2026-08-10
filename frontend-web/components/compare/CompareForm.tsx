"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Card, CardTitle } from "@/components/ui/Card";
import { VEHICLE_CLASSES, type VehicleClass } from "@/lib/api";

const schema = z.object({
  pickup_lat: z.coerce.number().min(-90).max(90),
  pickup_lon: z.coerce.number().min(-180).max(180),
  dropoff_lat: z.coerce.number().min(-90).max(90),
  dropoff_lon: z.coerce.number().min(-180).max(180),
  departure_time: z.string().min(1, "required"),
  city_id: z.string().optional(),
});

type FormValues = z.infer<typeof schema>;

const defaultValues: FormValues = {
  pickup_lat: 40.7484,
  pickup_lon: -73.9857,
  dropoff_lat: 40.7061,
  dropoff_lon: -74.0088,
  departure_time: new Date().toISOString().slice(0, 16),
  city_id: "",
};

export interface CompareRequest extends FormValues {
  vehicles: VehicleClass[];
}

interface CompareFormProps {
  onSubmit: (req: CompareRequest) => void;
  isPending: boolean;
}

export function CompareForm({ onSubmit, isPending }: CompareFormProps) {
  const {
    register,
    handleSubmit,
    setError,
    formState: { errors },
  } = useForm<FormValues>({ defaultValues });

  const [vehicles, setVehicles] = useState<VehicleClass[]>(["sedan", "suv", "ev", "premium"]);

  function toggleVehicle(v: VehicleClass) {
    setVehicles((prev) => (prev.includes(v) ? prev.filter((x) => x !== v) : [...prev, v]));
  }

  const submit = handleSubmit((values) => {
    const parsed = schema.safeParse(values);
    if (!parsed.success) {
      for (const issue of parsed.error.issues) {
        setError(issue.path[0] as keyof FormValues, { message: issue.message });
      }
      return;
    }
    if (vehicles.length === 0) return;
    onSubmit({
      ...parsed.data,
      departure_time: new Date(parsed.data.departure_time).toISOString(),
      city_id: parsed.data.city_id?.trim() || undefined,
      vehicles,
    });
  });

  return (
    <Card>
      <CardTitle className="font-display text-base tracking-wide">Compare — new journey</CardTitle>
      <form onSubmit={submit} className="mt-4 flex flex-col gap-4">
        <div>
          <label className="mb-1 block text-xs uppercase tracking-wider text-ink-muted">
            City (only needed outside NYC/London — e.g. "mumbai", "tokyo")
          </label>
          <Input type="text" placeholder="auto-detected for NYC/London" {...register("city_id")} />
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="mb-1 block text-xs uppercase tracking-wider text-ink-muted">Pickup lat</label>
            <Input type="number" step="any" {...register("pickup_lat")} />
            {errors.pickup_lat && <p className="mt-1 text-xs text-danger">{errors.pickup_lat.message}</p>}
          </div>
          <div>
            <label className="mb-1 block text-xs uppercase tracking-wider text-ink-muted">Pickup lon</label>
            <Input type="number" step="any" {...register("pickup_lon")} />
            {errors.pickup_lon && <p className="mt-1 text-xs text-danger">{errors.pickup_lon.message}</p>}
          </div>
          <div>
            <label className="mb-1 block text-xs uppercase tracking-wider text-ink-muted">Dropoff lat</label>
            <Input type="number" step="any" {...register("dropoff_lat")} />
            {errors.dropoff_lat && <p className="mt-1 text-xs text-danger">{errors.dropoff_lat.message}</p>}
          </div>
          <div>
            <label className="mb-1 block text-xs uppercase tracking-wider text-ink-muted">Dropoff lon</label>
            <Input type="number" step="any" {...register("dropoff_lon")} />
            {errors.dropoff_lon && <p className="mt-1 text-xs text-danger">{errors.dropoff_lon.message}</p>}
          </div>
        </div>

        <div>
          <label className="mb-1 block text-xs uppercase tracking-wider text-ink-muted">Departure time</label>
          <Input type="datetime-local" {...register("departure_time")} />
          {errors.departure_time && (
            <p className="mt-1 text-xs text-danger">{errors.departure_time.message}</p>
          )}
        </div>

        <div>
          <label className="mb-2 block text-xs uppercase tracking-wider text-ink-muted">Vehicle classes</label>
          <div className="flex flex-wrap gap-2">
            {VEHICLE_CLASSES.map((v) => {
              const active = vehicles.includes(v);
              return (
                <button
                  key={v}
                  type="button"
                  onClick={() => toggleVehicle(v)}
                  className={
                    active
                      ? "rounded-lg border border-brass bg-brass/15 px-3 py-1.5 text-xs font-medium capitalize text-brass"
                      : "rounded-lg border border-surface-border bg-surface-1 px-3 py-1.5 text-xs font-medium capitalize text-ink-muted hover:text-ink-secondary"
                  }
                >
                  {v}
                </button>
              );
            })}
          </div>
          {vehicles.length === 0 && (
            <p className="mt-1 text-xs text-danger">Select at least one vehicle class</p>
          )}
        </div>

        <Button type="submit" disabled={isPending || vehicles.length === 0}>
          {isPending ? "Comparing..." : "Compare vehicles"}
        </Button>
      </form>
    </Card>
  );
}
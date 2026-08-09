"use client";

import { useForm } from "react-hook-form";
import { z } from "zod";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { Card, CardTitle } from "@/components/ui/Card";
import { VEHICLE_CLASSES, type JourneyRequest } from "@/lib/api";

const schema = z.object({
  pickup_lat: z.coerce.number().min(-90).max(90),
  pickup_lon: z.coerce.number().min(-180).max(180),
  dropoff_lat: z.coerce.number().min(-90).max(90),
  dropoff_lon: z.coerce.number().min(-180).max(180),
  departure_time: z.string().min(1, "required"),
  vehicle_type: z.enum(VEHICLE_CLASSES),
  city_id: z.string().optional(),
});

type FormValues = z.infer<typeof schema>;

// NYC defaults so the form is fillable at a glance without a geocoder (later work).
const defaultValues: FormValues = {
  pickup_lat: 40.7484,
  pickup_lon: -73.9857,
  dropoff_lat: 40.7061,
  dropoff_lon: -74.0088,
  departure_time: new Date().toISOString().slice(0, 16),
  vehicle_type: "sedan",
  city_id: "",
};

interface JourneyFormProps {
  onSubmit: (req: JourneyRequest) => void;
  isPending: boolean;
}

export function JourneyForm({ onSubmit, isPending }: JourneyFormProps) {
  const {
    register,
    handleSubmit,
    setError,
    formState: { errors },
  } = useForm<FormValues>({ defaultValues });

  // ponytail: no @hookform/resolvers dep -- schema.safeParse inline is a
  // one-line validation bridge, add the resolver package if forms grow.
  const submit = handleSubmit((values) => {
    const parsed = schema.safeParse(values);
    if (!parsed.success) {
      for (const issue of parsed.error.issues) {
        setError(issue.path[0] as keyof FormValues, { message: issue.message });
      }
      return;
    }
    onSubmit({
      ...parsed.data,
      departure_time: new Date(parsed.data.departure_time).toISOString(),
      city_id: parsed.data.city_id?.trim() || undefined,
    });
  });

  return (
    <Card>
      <CardTitle className="font-display text-base tracking-wide">Journey log — new entry</CardTitle>
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
          <label className="mb-1 block text-xs uppercase tracking-wider text-ink-muted">Vehicle type</label>
          <Select {...register("vehicle_type")}>
            {VEHICLE_CLASSES.map((v) => (
              <option key={v} value={v}>
                {v}
              </option>
            ))}
          </Select>
        </div>

        <Button type="submit" disabled={isPending}>
          {isPending ? "Estimating..." : "Estimate journey"}
        </Button>
      </form>
    </Card>
  );
}

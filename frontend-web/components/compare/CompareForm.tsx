"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Card, CardTitle } from "@/components/ui/Card";
import { VEHICLE_CLASSES, resolveCityId, type VehicleClass } from "@/lib/api";
import { AddressSearch } from "@/components/journey/AddressSearch";

const schema = z.object({
  pickup_lat: z.coerce.number().min(-90).max(90),
  pickup_lon: z.coerce.number().min(-180).max(180),
  dropoff_lat: z.coerce.number().min(-90).max(90),
  dropoff_lon: z.coerce.number().min(-180).max(180),
  departure_time: z.string().min(1, "required"),
});

type FormValues = z.infer<typeof schema>;

// NYC defaults — Empire State Building → Wall Street
const NYC_PICKUP  = { lat: 40.7484, lon: -73.9857, name: "Midtown Manhattan, New York" };
const NYC_DROPOFF = { lat: 40.7061, lon: -74.0088, name: "Financial District, New York" };

export interface CompareRequest extends FormValues {
  vehicles: VehicleClass[];
  city_id?: string;
}

interface CompareFormProps {
  onSubmit: (req: CompareRequest) => void;
  isPending: boolean;
}

export function CompareForm({ onSubmit, isPending }: CompareFormProps) {
  const [pickup, setPickup] = useState(NYC_PICKUP);
  const [dropoff, setDropoff] = useState(NYC_DROPOFF);
  const [coordError, setCoordError] = useState<string | null>(null);
  // See JourneyForm.tsx's identical field for why this replaced a
  // disconnected manual "City" text input.
  const [resolvedCityId, setResolvedCityId] = useState<string | null>("nyc");
  const [cityResolving, setCityResolving] = useState(false);

  const {
    register,
    handleSubmit,
    setValue,
    formState: { errors },
  } = useForm<FormValues>({
    defaultValues: {
      pickup_lat: NYC_PICKUP.lat,
      pickup_lon: NYC_PICKUP.lon,
      dropoff_lat: NYC_DROPOFF.lat,
      dropoff_lon: NYC_DROPOFF.lon,
      departure_time: new Date().toISOString().slice(0, 16),
    },
  });

  const [vehicles, setVehicles] = useState<VehicleClass[]>(["sedan", "suv", "ev", "premium"]);

  function toggleVehicle(v: VehicleClass) {
    setVehicles((prev) => (prev.includes(v) ? prev.filter((x) => x !== v) : [...prev, v]));
  }

  const submit = handleSubmit((values) => {
    const parsed = schema.safeParse(values);
    if (!parsed.success) return;

    if (!pickup.lat || !pickup.lon) {
      setCoordError("Please select a pickup location from the suggestions.");
      return;
    }
    if (!dropoff.lat || !dropoff.lon) {
      setCoordError("Please select a dropoff location from the suggestions.");
      return;
    }

    if (vehicles.length === 0) return;

    setCoordError(null);
    onSubmit({
      ...parsed.data,
      pickup_lat: pickup.lat,
      pickup_lon: pickup.lon,
      dropoff_lat: dropoff.lat,
      dropoff_lon: dropoff.lon,
      departure_time: new Date(parsed.data.departure_time).toISOString(),
      city_id: resolvedCityId ?? undefined,
      vehicles,
    });
  });

  return (
    <Card>
      <CardTitle className="font-display text-base tracking-wide">Compare — new journey</CardTitle>
      <form onSubmit={submit} className="mt-4 flex flex-col gap-4">
        
        {/* Address search inputs */}
        <AddressSearch
          label="Pickup location"
          color="brass"
          defaultValue={NYC_PICKUP.name}
          placeholder="e.g. Midtown Manhattan, Empire State Building…"
          onSelect={(place) => {
            setPickup(place);
            setValue("pickup_lat", place.lat);
            setValue("pickup_lon", place.lon);
            setCoordError(null);
            setResolvedCityId(null);
            setCityResolving(true);
            resolveCityId(place.lat, place.lon, place.city, place.countryCode)
              .then(setResolvedCityId)
              .finally(() => setCityResolving(false));
          }}
        />

        <AddressSearch
          label="Dropoff location"
          color="verdigris"
          defaultValue={NYC_DROPOFF.name}
          placeholder="e.g. Heathrow Airport, London Bridge…"
          onSelect={(place) => {
            setDropoff(place);
            setValue("dropoff_lat", place.lat);
            setValue("dropoff_lon", place.lon);
            setCoordError(null);
          }}
        />

        {/* Hidden coordinate inputs */}
        <input type="hidden" {...register("pickup_lat")} value={pickup.lat} />
        <input type="hidden" {...register("pickup_lon")} value={pickup.lon} />
        <input type="hidden" {...register("dropoff_lat")} value={dropoff.lat} />
        <input type="hidden" {...register("dropoff_lon")} value={dropoff.lon} />

        {coordError && (
          <p className="text-xs text-oxide">{coordError}</p>
        )}

        {/* Selected coordinate display */}
        <div className="flex gap-3 text-[11px] text-ink-muted font-mono">
          <span className="text-brass">↑</span>
          <span>{pickup.lat.toFixed(5)}, {pickup.lon.toFixed(5)}</span>
          <span className="mx-1">→</span>
          <span className="text-verdigris">↓</span>
          <span>{dropoff.lat.toFixed(5)}, {dropoff.lon.toFixed(5)}</span>
        </div>

        <div className="text-xs text-ink-muted">
          <span className="uppercase tracking-wider">Detected city: </span>
          {cityResolving ? (
            <span className="italic">resolving…</span>
          ) : resolvedCityId ? (
            <span className="font-mono text-brass">{resolvedCityId}</span>
          ) : (
            <span className="text-oxide">not resolvable — pick a pickup location from the suggestions</span>
          )}
        </div>

        <div>
          <label className="mb-1 block text-xs uppercase tracking-wider text-ink-muted">Departure time</label>
          <Input type="datetime-local" {...register("departure_time")} />
          {errors.departure_time && (
            <p className="mt-1 text-xs text-oxide">{errors.departure_time.message}</p>
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
            <p className="mt-1 text-xs text-oxide">Select at least one vehicle class</p>
          )}
        </div>

        <Button type="submit" disabled={isPending || vehicles.length === 0}>
          {isPending ? "Comparing..." : "Compare vehicles"}
        </Button>
      </form>
    </Card>
  );
}
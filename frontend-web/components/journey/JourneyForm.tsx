"use client";

import { useForm, Controller } from "react-hook-form";
import { z } from "zod";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { Card, CardTitle } from "@/components/ui/Card";
import { VEHICLE_CLASSES, resolveCityId, type JourneyRequest } from "@/lib/api";
import { AddressSearch } from "./AddressSearch";
import { type GeocodedPlace } from "@/hooks/useReverseGeocode";
import { useState } from "react";

const schema = z.object({
  pickup_lat: z.coerce.number().min(-90).max(90),
  pickup_lon: z.coerce.number().min(-180).max(180),
  dropoff_lat: z.coerce.number().min(-90).max(90),
  dropoff_lon: z.coerce.number().min(-180).max(180),
  departure_time: z.string().min(1, "required"),
  vehicle_type: z.enum(VEHICLE_CLASSES),
});

type FormValues = z.infer<typeof schema>;

// NYC defaults — Empire State Building → Wall Street
const NYC_PICKUP  = { lat: 40.7484, lon: -73.9857, name: "Midtown Manhattan, New York" };
const NYC_DROPOFF = { lat: 40.7061, lon: -74.0088, name: "Financial District, New York" };

interface JourneyFormProps {
  onSubmit: (req: JourneyRequest) => void;
  isPending: boolean;
}

export function JourneyForm({ onSubmit, isPending }: JourneyFormProps) {
  // Coordinates are stored as plain state — AddressSearch sets them on selection.
  // The form registers them as hidden inputs for validation.
  const [pickup, setPickup] = useState(NYC_PICKUP);
  const [dropoff, setDropoff] = useState(NYC_DROPOFF);
  const [coordError, setCoordError] = useState<string | null>(null);
  // Resolved from the pickup address's own coordinates/city name -- real
  // registry lookup (resolveCityId), not user free-text. Previously a
  // disconnected manual "City" input existed here that nothing populated,
  // so every non-NYC/London journey silently queried "nyc" downstream
  // (JourneyResults.tsx's old fallback). null = still resolving or
  // unresolvable; every /api/mobility/* card degrades honestly on that,
  // it never guesses "nyc".
  const [resolvedCityId, setResolvedCityId] = useState<string | null>("nyc");
  const [cityResolving, setCityResolving] = useState(false);

  const {
    register,
    handleSubmit,
    setValue,
    formState: { errors },
  } = useForm<FormValues>({
    defaultValues: {
      pickup_lat:  NYC_PICKUP.lat,
      pickup_lon:  NYC_PICKUP.lon,
      dropoff_lat: NYC_DROPOFF.lat,
      dropoff_lon: NYC_DROPOFF.lon,
      departure_time: new Date().toISOString().slice(0, 16),
      vehicle_type: "sedan",
    },
  });

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

    setCoordError(null);
    onSubmit({
      ...parsed.data,
      pickup_lat:  pickup.lat,
      pickup_lon:  pickup.lon,
      dropoff_lat: dropoff.lat,
      dropoff_lon: dropoff.lon,
      departure_time: new Date(parsed.data.departure_time).toISOString(),
      city_id: resolvedCityId ?? undefined,
    });
  });

  return (
    <Card>
      <CardTitle className="font-display text-base tracking-wide">Journey log — new entry</CardTitle>
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

        {/* Hidden coordinate inputs (used for form validation) */}
        <input type="hidden" {...register("pickup_lat")} value={pickup.lat} />
        <input type="hidden" {...register("pickup_lon")} value={pickup.lon} />
        <input type="hidden" {...register("dropoff_lat")} value={dropoff.lat} />
        <input type="hidden" {...register("dropoff_lon")} value={dropoff.lon} />

        {coordError && (
          <p className="text-xs text-oxide">{coordError}</p>
        )}

        {/* Selected coordinate display (compact, for power users) */}
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
          <label className="mb-1 block text-xs uppercase tracking-wider text-ink-muted">Vehicle type</label>
          <Select {...register("vehicle_type")}>
            {VEHICLE_CLASSES.map((v) => (
              <option key={v} value={v}>{v}</option>
            ))}
          </Select>
        </div>

        <Button type="submit" disabled={isPending}>
          {isPending ? "Estimating…" : "Estimate journey"}
        </Button>
      </form>
    </Card>
  );
}

"use client";

import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { Card } from "@/components/ui/Card";
import { CountryHeader } from "@/components/country/CountryHeader";
import { CityGrid } from "@/components/country/CityGrid";
import { getCountries, searchCities, type Country } from "@/lib/api";
import { queryKeys } from "@/lib/queryKeys";
import { SearchBar } from "@/components/world/SearchBar";
import { ArrowLeft, MapPin } from "lucide-react";
import Link from "next/link";
import { cn } from "@/lib/utils";

export default function CountryPage() {
  const params = useParams();
  const countryCode = params.code as string;

  const { data: countries, isLoading: countriesLoading } = useQuery({
    queryKey: queryKeys.countries(),
    queryFn: getCountries,
  });

  const country = countries?.find((c) => c.iso_code.toLowerCase() === countryCode.toLowerCase());

  if (countriesLoading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] text-center gap-4">
        <div className="h-16 w-16 rounded-xl bg-surface-1 animate-pulse" />
        <div className="h-6 w-48 bg-surface-1 animate-pulse rounded" />
      </div>
    );
  }

  const { data: tierData } = useQuery({
    queryKey: queryKeys.cities({ country: countryCode }),
    queryFn: () => searchCities({ country: countryCode, limit: 1000 }),
  });

  const tierSummary = tierData?.results.reduce(
    (acc, city) => {
      const status = city.model_status as keyof typeof acc;
      if (status in acc) {
        acc[status] = (acc[status] || 0) + 1;
      }
      return acc;
    },
    { OBSERVED: 0, TRANSFER: 0, NONE: 0 } as { OBSERVED: number; TRANSFER: number; NONE: number }
  );

  if (!country) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] text-center">
        <MapPin className="h-12 w-12 text-ink-muted mb-4" />
        <h2 className="font-display text-xl font-semibold text-ink-primary">Country not found</h2>
        <p className="mt-2 text-ink-muted">No data for country code: {countryCode.toUpperCase()}</p>
        <Link
          href="/"
          className="mt-4 inline-flex items-center gap-2 text-brass hover:underline"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to world
        </Link>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      {/* Back link + Header */}
      <div className="flex items-center justify-between">
        <Link
          href="/"
          className="inline-flex items-center gap-2 text-sm text-ink-secondary hover:text-ink-primary"
        >
          <ArrowLeft className="h-4 w-4" />
          World
        </Link>
        <SearchBar placeholder="Search cities in this country..." />
      </div>

      {/* Country Header */}
      <CountryHeader country={country} tierSummary={tierSummary} />

      {/* City Grid */}
      <CityGrid countryCode={countryCode} />
    </div>
  );
}
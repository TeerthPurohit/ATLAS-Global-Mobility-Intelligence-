"use client";

import { useParams } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, MapPin } from "lucide-react";
import { SearchBar } from "@/components/world/SearchBar";
import { CityProfile } from "@/components/city/CityProfile";
import { useQuery } from "@tanstack/react-query";
import { getCityProfile } from "@/lib/api";
import { queryKeys } from "@/lib/queryKeys";

export default function CityPage() {
  const params = useParams();
  const cityId = params.city_id as string;

  const { data: profile } = useQuery({
    queryKey: queryKeys.cityProfile(cityId),
    queryFn: () => getCityProfile(cityId),
  });

  return (
    <div className="flex flex-col gap-6">
      {/* Top Bar Navigation */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <Link
            href={profile ? `/country/${profile.country.toLowerCase()}` : "/"}
            className="inline-flex items-center gap-1.5 rounded-lg border border-surface-border bg-surface-1 px-3 py-1.5 text-xs font-medium text-ink-secondary hover:border-brass/40 hover:text-ink-primary transition-colors"
          >
            <ArrowLeft className="h-3.5 w-3.5" />
            {profile ? `Back to ${profile.country}` : "Back to World"}
          </Link>

          <nav className="flex items-center gap-1 text-xs text-ink-muted">
            <Link href="/" className="hover:text-ink-primary transition-colors">
              World
            </Link>
            <span>/</span>
            {profile && (
              <>
                <Link
                  href={`/country/${profile.country.toLowerCase()}`}
                  className="hover:text-ink-primary transition-colors"
                >
                  {profile.country}
                </Link>
                <span>/</span>
              </>
            )}
            <span className="font-semibold text-brass truncate max-w-[120px]">
              {profile ? profile.name : cityId}
            </span>
          </nav>
        </div>

        <div className="w-full sm:w-80">
          <SearchBar placeholder="Search another city..." />
        </div>
      </div>

      {/* Main City Profile View */}
      <CityProfile cityId={cityId} />
    </div>
  );
}

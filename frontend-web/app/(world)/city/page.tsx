"use client";

import { useEffect } from "react";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { CityProfile } from "@/components/city/CityProfile";
import { useQuery } from "@tanstack/react-query";
import { getCityProfile, type City } from "@/lib/api";
import { queryKeys } from "@/lib/queryKeys";
import { useAppContext } from "@/context/AppContext";

export default function CityPage() {
  const { setSelectedCity } = useAppContext();

  const { data: profile } = useQuery({
    queryKey: queryKeys.cityProfile(),
    queryFn: () => getCityProfile(),
  });

  // The Ask page reads selectedCity to label which city it is answering
  // about. Chat itself is no longer city-scoped (ADR-013).
  useEffect(() => {
    if (profile) setSelectedCity({ ...profile, model_status: profile.model_status as City["model_status"] });
  }, [profile, setSelectedCity]);

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center gap-3">
        <Link
          href="/"
          className="inline-flex items-center gap-1.5 rounded-lg border border-surface-border bg-surface-1 px-3 py-1.5 text-xs font-medium text-ink-secondary hover:border-brass/40 hover:text-ink-primary transition-colors"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          Back
        </Link>

        <nav className="flex items-center gap-1 text-xs text-ink-muted">
          <Link href="/" className="hover:text-ink-primary transition-colors">
            Explore
          </Link>
          <span>/</span>
          <span className="font-semibold text-brass truncate max-w-[160px]">
            {profile ? profile.name : "Loading..."}
          </span>
        </nav>
      </div>

      <CityProfile />
    </div>
  );
}

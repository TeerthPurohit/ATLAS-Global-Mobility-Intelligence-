import { Metadata } from "next";
import { CityProfile } from "@/components/city/CityProfile";
import { getCountries, getCityProfile, type Country, type CityProfileResponse } from "@/lib/api";
import { notFound } from "next/navigation";

interface CityPageProps {
  params: Promise<{ city_id: string }>;
}

export async function generateMetadata({ params }: CityPageProps): Promise<Metadata> {
  const { city_id } = await params;
  try {
    const profile = await getCityProfile(city_id);
    return {
      title: `${profile.name} — Journey Intelligence`,
      description: `Fare, ETA, demand, and risk intelligence for ${profile.name}.`,
    };
  } catch {
    return { title: "City Not Found" };
  }
}

export default async function CityPage({ params }: CityPageProps) {
  const { city_id } = await params;

  // Verify city exists
  try {
    await getCityProfile(city_id);
  } catch {
    notFound();
  }

  return (
    <div className="flex flex-col gap-6">
      <nav className="flex items-center gap-2 text-xs text-ink-muted">
        <a href="/" className="hover:text-ink-primary">World</a>
        <span>/</span>
        <span className="hover:text-ink-primary cursor-pointer">Country</span>
        <span>/</span>
        <span className="font-medium text-ink-secondary">{city_id}</span>
      </nav>

      <CityProfile cityId={city_id} />
    </div>
  );
}
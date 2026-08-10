import { Metadata } from "next";
import { CityGrid } from "@/components/country/CityGrid";
import { getCountries, type Country } from "@/lib/api";
import { notFound } from "next/navigation";

interface CountryPageProps {
  params: Promise<{ code: string }>;
}

export async function generateMetadata({ params }: CountryPageProps): Promise<Metadata> {
  const { code } = await params;
  const countries = await getCountries();
  const country = countries.find((c) => c.iso_code.toLowerCase() === code.toLowerCase());
  if (!country) return { title: "Country Not Found" };
  return {
    title: `${country.name} Cities`,
    description: `Explore ${country.supported_city_count} cities in ${country.name}.`,
  };
}

export default async function CountryPage({ params }: CountryPageProps) {
  const { code } = await params;
  const countries = await getCountries();
  const country = countries.find((c) => c.iso_code.toLowerCase() === code.toLowerCase());

  if (!country) notFound();

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <nav className="flex items-center gap-2 text-xs text-ink-muted mb-2">
            <a href="/" className="hover:text-ink-primary">World</a>
            <span>/</span>
            <span className="font-medium text-ink-secondary">{country.name}</span>
          </nav>
          <h1 className="font-display text-3xl font-semibold text-ink-primary">{country.name}</h1>
          <p className="mt-1 text-sm text-ink-secondary">
            {country.supported_city_count} onboarded cities · {country.supported ? "Supported" : "Not supported"}
          </p>
        </div>
      </div>

      <CityGrid countryCode={country.iso_code} />
    </div>
  );
}
/**
 * useReverseGeocode — converts lat/lng → human-readable place name
 * using OpenStreetMap Nominatim (free, no API key).
 *
 * Returns suburb > city > town hierarchy, e.g.:
 *   "Midtown Manhattan, New York"
 *   "Westminster, London"
 *   "Shibuya, Tokyo"
 */

"use client";

import { useEffect, useState } from "react";

interface NominatimAddress {
  suburb?: string;
  neighbourhood?: string;
  quarter?: string;
  city_district?: string;
  borough?: string;
  town?: string;
  village?: string;
  city?: string;
  county?: string;
  state?: string;
  country?: string;
  country_code?: string; // Nominatim always lowercases this (ISO 3166-1 alpha-2)
}

interface NominatimResult {
  display_name: string;
  address: NominatimAddress;
}

/** Returns the most readable short label for a coordinate pair. */
function formatPlaceName(result: NominatimResult): string {
  const addr = result.address;

  // Level 1: sub-city area (most specific meaningful label)
  const area =
    addr.suburb ||
    addr.neighbourhood ||
    addr.quarter ||
    addr.city_district ||
    addr.borough;

  // Level 2: city/town
  const city = addr.city || addr.town || addr.village || addr.county;

  if (area && city) return `${area}, ${city}`;
  if (area) return area;
  if (city) return city;
  return result.display_name?.split(",")[0] ?? "Unknown location";
}

const cache = new Map<string, string>();

async function reverseGeocode(lat: number, lon: number): Promise<string> {
  const key = `${lat.toFixed(5)},${lon.toFixed(5)}`;
  if (cache.has(key)) return cache.get(key)!;

  const url = `https://nominatim.openstreetmap.org/reverse?lat=${lat}&lon=${lon}&format=json&zoom=14&addressdetails=1`;

  const res = await fetch(url, {
    headers: { "Accept-Language": "en", "User-Agent": "NycRideMobilityApp/1.0" },
  });

  if (!res.ok) return `${lat.toFixed(4)}, ${lon.toFixed(4)}`;

  const data: NominatimResult = await res.json();
  const name = formatPlaceName(data);
  cache.set(key, name);
  return name;
}

export function useReverseGeocode(lat: number, lon: number): string {
  const [name, setName] = useState<string>(`${lat.toFixed(4)}, ${lon.toFixed(4)}`);

  useEffect(() => {
    if (!lat || !lon) return;
    let cancelled = false;
    reverseGeocode(lat, lon).then((n) => {
      if (!cancelled) setName(n);
    });
    return () => { cancelled = true; };
  }, [lat, lon]);

  return name;
}

/** Forward geocoder: address string → {lat, lon, display_name} */
export interface GeocodedPlace {
  lat: number;
  lon: number;
  displayName: string;
  shortName: string;
  // Carried through for display/labelling -- undefined only if Nominatim's
  // own address block omitted them for this result. Coverage is decided from
  // the coordinates (api.ts's isInCoverage), never from this name.
  city?: string;
  countryCode?: string;
}

const fwdCache = new Map<string, GeocodedPlace[]>();

export async function forwardGeocode(query: string): Promise<GeocodedPlace[]> {
  const key = query.toLowerCase().trim();
  if (fwdCache.has(key)) return fwdCache.get(key)!;

  const url = `https://nominatim.openstreetmap.org/search?q=${encodeURIComponent(query)}&format=json&addressdetails=1&limit=5`;

  const res = await fetch(url, {
    headers: { "Accept-Language": "en", "User-Agent": "NycRideMobilityApp/1.0" },
  });

  if (!res.ok) return [];

  const data: (NominatimResult & { lat: string; lon: string })[] = await res.json();

  const results: GeocodedPlace[] = data.map((item) => ({
    lat: parseFloat(item.lat),
    lon: parseFloat(item.lon),
    displayName: item.display_name,
    shortName: formatPlaceName(item),
    city: item.address.city || item.address.town || item.address.village,
    countryCode: item.address.country_code,
  }));

  fwdCache.set(key, results);
  return results;
}

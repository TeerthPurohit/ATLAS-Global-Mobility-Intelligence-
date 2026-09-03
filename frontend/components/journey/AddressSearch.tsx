"use client";

/**
 * AddressSearch — a type-ahead input that uses Nominatim forward geocoding
 * to convert a typed address into lat/lon.
 *
 * Props:
 *   label       — e.g. "Pickup location"
 *   color       — "brass" | "verdigris"  (matches marker colors)
 *   onSelect    — called with { lat, lon, name } when user picks a result
 *   defaultValue — pre-filled address string (shown on mount)
 */

import { useState, useEffect, useRef, useCallback } from "react";
import { MapPin, Search, Loader2 } from "lucide-react";
import { forwardGeocode, type GeocodedPlace } from "@/hooks/useReverseGeocode";
import { cn } from "@/lib/utils";

interface AddressSearchProps {
  label: string;
  color?: "brass" | "verdigris";
  onSelect: (place: { lat: number; lon: number; name: string; city?: string; countryCode?: string }) => void;
  defaultValue?: string;
  placeholder?: string;
}

export function AddressSearch({
  label,
  color = "brass",
  onSelect,
  defaultValue = "",
  placeholder = "Type an address or area…",
}: AddressSearchProps) {
  const [query, setQuery] = useState(defaultValue);
  const [results, setResults] = useState<GeocodedPlace[]>([]);
  const [isOpen, setIsOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [selectedName, setSelectedName] = useState(defaultValue);
  const debounceRef = useRef<ReturnType<typeof setTimeout>>();
  const containerRef = useRef<HTMLDivElement>(null);

  const accentClass = color === "brass" ? "text-brass" : "text-verdigris";
  const dotClass = color === "brass" ? "bg-brass" : "bg-verdigris";
  const ringClass = color === "brass" ? "focus:ring-brass/40" : "focus:ring-verdigris/40";

  useEffect(() => {
    if (query.length < 3) {
      setResults([]);
      setIsOpen(false);
      return;
    }
    clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(async () => {
      setIsLoading(true);
      try {
        const hits = await forwardGeocode(query);
        setResults(hits);
        setIsOpen(hits.length > 0);
      } catch {
        setResults([]);
      } finally {
        setIsLoading(false);
      }
    }, 350);
    return () => clearTimeout(debounceRef.current);
  }, [query]);

  // Close on outside click
  useEffect(() => {
    const handleClick = (e: MouseEvent) => {
      if (!containerRef.current?.contains(e.target as Node)) setIsOpen(false);
    };
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  const handleSelect = useCallback((place: GeocodedPlace) => {
    setQuery(place.shortName);
    setSelectedName(place.shortName);
    setIsOpen(false);
    onSelect({ lat: place.lat, lon: place.lon, name: place.shortName, city: place.city, countryCode: place.countryCode });
  }, [onSelect]);

  const isConfirmed = query === selectedName && selectedName !== "";

  return (
    <div ref={containerRef} className="relative">
      <label className="mb-1 flex items-center gap-1.5 text-xs uppercase tracking-wider text-ink-muted">
        <span className={cn("h-2 w-2 rounded-full", dotClass)} />
        {label}
      </label>

      <div className="relative">
        <input
          type="text"
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            setSelectedName(""); // clear confirmation when editing
          }}
          onFocus={() => results.length > 0 && setIsOpen(true)}
          placeholder={placeholder}
          className={cn(
            "w-full rounded-xl border bg-surface-1 py-2.5 pl-9 pr-10",
            "text-sm text-ink-primary placeholder-ink-muted",
            "focus:outline-none focus:ring-2 transition-all",
            ringClass,
            isConfirmed ? "border-verdigris/40" : "border-surface-border"
          )}
          autoComplete="off"
        />

        {/* Left icon */}
        <MapPin className={cn("absolute left-2.5 top-1/2 -translate-y-1/2 h-4 w-4", accentClass)} />

        {/* Right status */}
        <div className="absolute right-2.5 top-1/2 -translate-y-1/2">
          {isLoading ? (
            <Loader2 className="h-4 w-4 text-ink-muted animate-spin" />
          ) : isConfirmed ? (
            <svg className="h-4 w-4 text-verdigris" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2.5}>
              <polyline points="20 6 9 17 4 12" />
            </svg>
          ) : query.length >= 3 ? (
            <Search className="h-4 w-4 text-ink-muted" />
          ) : null}
        </div>
      </div>

      {/* Dropdown */}
      {isOpen && results.length > 0 && (
        <div className="absolute top-full left-0 right-0 z-50 mt-2 max-h-64 overflow-y-auto rounded-2xl border border-surface-border bg-surface-1/95 p-1.5 shadow-[0_16px_40px_-12px_rgba(28,27,51,0.25)] backdrop-blur-xl">
          <ul className="flex flex-col gap-1">
            {results.map((place, i) => (
              <li key={i}>
                <button
                  type="button"
                  onClick={() => handleSelect(place)}
                  className="w-full flex items-center gap-3 rounded-xl px-3 py-2.5 text-left hover:bg-surface-0 transition-colors group"
                >
                  <div className={cn("flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-surface-0 border border-surface-border/80 group-hover:border-brass/40", accentClass)}>
                    <MapPin className="h-3.5 w-3.5" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-xs font-semibold text-ink-primary truncate">{place.shortName}</p>
                    <p className="text-[11px] text-ink-muted truncate">{place.displayName}</p>
                  </div>
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

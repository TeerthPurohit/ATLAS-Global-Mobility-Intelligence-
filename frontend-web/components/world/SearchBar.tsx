"use client";

import { useState, useEffect, useCallback } from "react";
import { Search, X, MapPin, Globe } from "lucide-react";
import { useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { searchCities, type City } from "@/lib/api";
import { queryKeys } from "@/lib/queryKeys";
import { cn } from "@/lib/utils";

interface SearchBarProps {
  placeholder?: string;
  onResultClick?: (city: City) => void;
}

export function SearchBar({ placeholder = "Search cities, countries...", onResultClick }: SearchBarProps) {
  const [query, setQuery] = useState("");
  const [isOpen, setIsOpen] = useState(false);
  const [focusedIndex, setFocusedIndex] = useState(-1);
  const router = useRouter();
  const inputRef = useRef<HTMLInputElement>(null);

  const { data, isLoading } = useQuery({
    queryKey: queryKeys.cities({ q: query || undefined }),
    queryFn: () => searchCities({ q: query, limit: 10 }),
    enabled: query.length >= 2,
  });

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (!isOpen) return;
      const results = data?.results || [];
      if (e.key === "ArrowDown") {
        e.preventDefault();
        setFocusedIndex((prev) => Math.min(prev + 1, results.length - 1));
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        setFocusedIndex((prev) => Math.max(prev - 1, -1));
      } else if (e.key === "Enter" && focusedIndex >= 0) {
        e.preventDefault();
        const city = results[focusedIndex];
        handleSelect(city);
      } else if (e.key === "Escape") {
        setIsOpen(false);
        setFocusedIndex(-1);
        inputRef.current?.blur();
      }
    };

    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, data, focusedIndex]);

  const handleSelect = useCallback((city: City) => {
    if (onResultClick) {
      onResultClick(city);
    } else {
      router.push(`/city/${city.id}`);
    }
    setQuery("");
    setIsOpen(false);
    setFocusedIndex(-1);
  }, [onResultClick, router]);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    setQuery(value);
    setIsOpen(value.length >= 2);
    setFocusedIndex(-1);
  };

  const clearQuery = () => {
    setQuery("");
    setIsOpen(false);
    setFocusedIndex(-1);
    inputRef.current?.focus();
  };

  return (
    <div className="relative">
      <div className="relative">
        <label htmlFor="global-search" className="sr-only">
          Global search
        </label>
        <input
          ref={inputRef}
          id="global-search"
          type="text"
          value={query}
          onChange={handleInputChange}
          onFocus={() => query.length >= 2 && setIsOpen(true)}
          onBlur={() => setTimeout(() => setIsOpen(false), 200)}
          placeholder={placeholder}
          className={cn(
            "w-full px-4 py-3 pl-11 pr-11 rounded-xl bg-surface-1 border",
            "text-ink-primary placeholder-ink-muted",
            "focus:outline-none focus:ring-2 focus:ring-brass/50",
            "transition-colors"
          )}
          autoComplete="off"
          aria-autocomplete="list"
          aria-controls="search-results"
          aria-expanded={isOpen && (data?.results.length ?? 0) > 0}
        />
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-ink-muted" aria-hidden="true" />
        {query && (
          <button
            onClick={clearQuery}
            className="absolute right-3 top-1/2 -translate-y-1/2 p-1 rounded-lg hover:bg-surface-2 transition-colors"
            aria-label="Clear search"
          >
            <X className="h-5 w-5 text-ink-muted" />
          </button>
        )}
      </div>

      {isOpen && data && (
        <ul
          id="search-results"
          role="listbox"
          className="absolute top-full left-0 right-0 mt-2 z-50 max-h-80 overflow-y-auto rounded-xl bg-surface-0 border border-surface-border shadow-xl"
        >
          {isLoading ? (
            <li className="px-4 py-3 text-center text-ink-muted">
              <div className="flex items-center justify-center gap-2">
                <div className="w-4 h-4 border-2 border-brass/30 border-t-brass rounded-full animate-spin" />
                <span>Searching...</span>
              </div>
            </li>
          ) : data.results.length > 0 ? (
            data.results.map((city, index) => (
              <li
                key={city.id}
                role="option"
                aria-selected={index === focusedIndex}
                onClick={() => handleSelect(city)}
                onMouseEnter={() => setFocusedIndex(index)}
                className={cn(
                  "px-4 py-3 flex items-center gap-3 cursor-pointer transition-colors",
                  index === focusedIndex ? "bg-brass/10" : "hover:bg-surface-1"
                )}
              >
                <MapPin className="h-5 w-5 text-brass shrink-0" />
                <div className="flex-1 min-w-0">
                  <p className="font-medium text-ink-primary truncate">{city.name}</p>
                  <p className="text-xs text-ink-muted flex items-center gap-1">
                    <Globe className="h-3 w-3" />
                    {city.country_code.toUpperCase()}
                  </p>
                </div>
                <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-surface-1 text-ink-muted">
                  {city.model_status}
                </span>
              </li>
            ))
          ) : (
            <li className="px-4 py-6 text-center text-ink-muted">
              No cities found
            </li>
          )}
        </ul>
      )}
    </div>
  );
}

import { useRef } from "react";
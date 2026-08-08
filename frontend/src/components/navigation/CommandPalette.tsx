import React, { useState, useEffect, useRef } from "react";
import { Search, Globe, MapPin, X, ArrowRight, Sparkles, CheckCircle2, Cpu, Compass } from "lucide-react";
import { useMobility } from "../../context/MobilityContext";
import { GlobalCitySearchResult, searchGlobalCities } from "../../api/client";
import { useNavigate } from "react-router-dom";

interface CommandPaletteProps {
  isOpen: boolean;
  onClose: () => void;
}

export const CommandPalette: React.FC<CommandPaletteProps> = ({ isOpen, onClose }) => {
  const { selectGlobalCity, setIsAnalyzing } = useMobility();
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<GlobalCitySearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const navigate = useNavigate();

  useEffect(() => {
    if (isOpen) {
      setTimeout(() => inputRef.current?.focus(), 50);
      setQuery("");
      setResults([]);
      setSelectedIndex(0);
      // Fetch initial top global cities
      fetchInitialCities();
    }
  }, [isOpen]);

  const fetchInitialCities = async () => {
    setLoading(true);
    try {
      const topCities = await searchGlobalCities("a", 8);
      setResults(topCities);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  // Debounced search when query changes
  useEffect(() => {
    if (!query.trim()) {
      fetchInitialCities();
      return;
    }

    const timer = setTimeout(async () => {
      setLoading(true);
      try {
        const searchRes = await searchGlobalCities(query, 12);
        setResults(searchRes);
        setSelectedIndex(0);
      } catch (e) {
        console.error("City search error:", e);
      } finally {
        setLoading(false);
      }
    }, 200);

    return () => clearTimeout(timer);
  }, [query]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Escape") {
      onClose();
    } else if (e.key === "ArrowDown") {
      e.preventDefault();
      setSelectedIndex((prev) => (prev + 1) % Math.max(1, results.length));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setSelectedIndex((prev) => (prev - 1 + results.length) % Math.max(1, results.length));
    } else if (e.key === "Enter" && results.length > 0) {
      e.preventDefault();
      handleSelectCity(results[selectedIndex]);
    }
  };

  const handleSelectCity = (city: GlobalCitySearchResult) => {
    if (!city) return;
    selectGlobalCity(city.id);
    setIsAnalyzing(true);
    onClose();
    const countryCode = city.country_code ? city.country_code.toLowerCase() : "global";
    navigate(`/explore/${countryCode}/${city.id}`);
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-[2000] flex items-start justify-center pt-16 sm:pt-24 px-4 bg-slate-950/80 backdrop-blur-md animate-fadeIn">
      {/* Backdrop click */}
      <div className="fixed inset-0 -z-10" onClick={onClose} />

      <div className="w-full max-w-2xl bg-slate-900 border border-slate-800 rounded-2xl shadow-2xl overflow-hidden flex flex-col transition-all">
        {/* Search Input Bar */}
        <div className="flex items-center px-4 border-b border-slate-800 bg-slate-950/50">
          <Search className="w-5 h-5 text-brand-400 mr-3 shrink-0" />
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Search Mumbai, Jaipur, Cape Town, Dubai, Tokyo, London, NYC..."
            className="w-full py-4 bg-transparent text-slate-100 placeholder-slate-500 text-sm focus:outline-none font-sans"
          />
          {query && (
            <button onClick={() => setQuery("")} className="p-1 text-slate-400 hover:text-white mr-2">
              <X className="w-4 h-4" />
            </button>
          )}
          <kbd className="hidden sm:inline-block px-2 py-0.5 text-[10px] font-mono text-slate-400 bg-slate-800 rounded border border-slate-700">
            ESC
          </kbd>
        </div>

        {/* Results List */}
        <div className="max-h-96 overflow-y-auto p-2 space-y-1">
          {loading ? (
            <div className="p-8 text-center text-slate-400 text-xs font-mono animate-pulse">
              Querying backend global geography engine...
            </div>
          ) : results.length === 0 ? (
            <div className="p-8 text-center text-slate-400 text-xs">
              <Compass className="w-8 h-8 text-slate-600 mx-auto mb-2" />
              <p className="font-semibold text-slate-300">No matching cities found</p>
              <p className="text-slate-500 mt-1">Try searching for "Mumbai", "Dubai", "Tokyo", or "London"</p>
            </div>
          ) : (
            results.map((city, idx) => {
              const isSelected = idx === selectedIndex;

              // Render capability badges strictly from backend response properties
              let badgeText = "GEOGRAPHIC ONLY";
              let badgeClass = "bg-slate-800 text-slate-400 border-slate-700";
              if (city.mobility_available) {
                badgeText = "OBSERVED MOBILITY";
                badgeClass = "bg-emerald-500/10 text-emerald-400 border-emerald-500/20";
              } else if (city.modeling_available) {
                badgeText = "MODELED MOBILITY";
                badgeClass = "bg-brand-500/10 text-brand-400 border-brand-500/20";
              }

              return (
                <div
                  key={city.id}
                  onClick={() => handleSelectCity(city)}
                  onMouseEnter={() => setSelectedIndex(idx)}
                  className={`flex items-center justify-between p-3.5 rounded-xl cursor-pointer text-xs transition-all ${
                    isSelected
                      ? "bg-brand-500/15 border border-brand-500/30 text-slate-100"
                      : "hover:bg-slate-800/50 border border-transparent text-slate-300"
                  }`}
                >
                  <div className="flex items-center space-x-3.5">
                    <div className="w-9 h-9 rounded-lg bg-slate-950 border border-slate-800 flex items-center justify-center font-mono font-bold text-xs text-brand-400 shrink-0">
                      {city.country_code || "WORLD"}
                    </div>
                    <div>
                      <div className="font-bold text-sm text-slate-100 flex items-center gap-2">
                        <span>{city.name}</span>
                        {city.country && <span className="text-xs text-slate-400 font-normal">({city.country})</span>}
                        <span className={`inline-flex items-center text-[10px] px-2 py-0.5 rounded-full font-mono border ${badgeClass}`}>
                          {badgeText}
                        </span>
                      </div>
                      <div className="text-[11px] font-mono text-slate-400 mt-0.5 flex items-center gap-3">
                        {city.timezone && <span>Timezone: {city.timezone}</span>}
                        {city.population && (
                          <span>Pop: {(city.population / 1_000_000).toFixed(1)}M</span>
                        )}
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center text-brand-400 text-xs font-semibold space-x-1">
                    <span>Analyze</span>
                    <ArrowRight className="w-3.5 h-3.5" />
                  </div>
                </div>
              );
            })
          )}
        </div>

        {/* Command Footer */}
        <div className="px-4 py-2.5 bg-slate-950 border-t border-slate-800 flex items-center justify-between text-[11px] text-slate-400 font-mono">
          <div className="flex items-center space-x-3">
            <span className="flex items-center gap-1">
              <kbd className="px-1.5 py-0.5 bg-slate-800 rounded border border-slate-700">↑</kbd>
              <kbd className="px-1.5 py-0.5 bg-slate-800 rounded border border-slate-700">↓</kbd>
              <span className="ml-1">Navigate</span>
            </span>
            <span className="flex items-center gap-1">
              <kbd className="px-1.5 py-0.5 bg-slate-800 rounded border border-slate-700">↵</kbd>
              <span className="ml-1">Select</span>
            </span>
          </div>
          <div className="flex items-center space-x-1 text-slate-500">
            <Sparkles className="w-3 h-3 text-brand-400" />
            <span>Live Backend Geography API</span>
          </div>
        </div>
      </div>
    </div>
  );
};

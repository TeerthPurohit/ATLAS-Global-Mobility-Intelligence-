import React, { useState, useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { useMobility } from "../../context/MobilityContext";
import { GlobalCitySearchResult, searchGlobalCities } from "../../api/client";
import { Sparkles, Search, MapPin, ArrowRight, Bot, Building2, CheckCircle2, ChevronLeft, Globe } from "lucide-react";
import { useNavigate } from "react-router-dom";

// A handful of example queries to seed "Featured Global Cities" -- NOT a
// claim of support. Every card shown is whatever the backend's own search
// actually returns for these (real mobility_available/modeling_available
// flags, real population), never a hardcoded per-city record.
const FEATURED_QUERIES = ["Mumbai", "Dubai", "Tokyo", "New York City", "London"];

export const ConversationalCityPicker: React.FC = () => {
  const { selectedCountry, countryCities, selectGlobalCity, resetToWorld } = useMobility();
  const [searchTerm, setSearchTerm] = useState("");
  const [debouncedTerm, setDebouncedTerm] = useState("");
  const navigate = useNavigate();

  useEffect(() => {
    const timer = setTimeout(() => setDebouncedTerm(searchTerm.trim()), 200);
    return () => clearTimeout(timer);
  }, [searchTerm]);

  const { data: featured = [] } = useQuery({
    queryKey: ["citypickerFeatured"],
    queryFn: async () => {
      const results = await Promise.all(FEATURED_QUERIES.map((q) => searchGlobalCities(q, 1).catch(() => [])));
      return results.flat();
    },
    staleTime: 1000 * 60 * 30,
  });

  const { data: liveResults = [], isFetching: loading } = useQuery({
    queryKey: ["citypickerSearch", debouncedTerm],
    queryFn: () => searchGlobalCities(debouncedTerm, 8),
    enabled: debouncedTerm.length > 0,
  });

  const searchResults = debouncedTerm ? liveResults : featured;

  const handleSelectCity = (city: GlobalCitySearchResult) => {
    selectGlobalCity(city.id);
    const countryCode = city.country_code ? city.country_code.toLowerCase() : "global";
    navigate(`/explore/${countryCode}/${city.id}`);
  };

  return (
    <div className="min-h-[calc(100vh-4rem)] bg-slate-950 flex flex-col items-center justify-center p-6 text-slate-100 font-sans select-none relative">
      {/* Back button */}
      <button
        onClick={resetToWorld}
        className="absolute top-6 left-6 px-3 py-2 rounded-xl bg-slate-900 border border-slate-800 hover:bg-slate-800 text-slate-300 text-xs font-semibold flex items-center space-x-1.5 transition-colors shadow-lg"
      >
        <ChevronLeft className="w-4 h-4" />
        <span>Back to World Map</span>
      </button>

      {/* Main Conversational Box */}
      <div className="w-full max-w-2xl bg-slate-900/90 border border-slate-800 backdrop-blur-xl p-8 rounded-3xl shadow-2xl space-y-6">
        {/* Country Badge Header */}
        <div className="flex items-center justify-between border-b border-slate-800 pb-4">
          <div className="flex items-center space-x-2.5">
            <span className="w-8 h-8 rounded-lg bg-brand-500/20 text-brand-400 border border-brand-500/30 flex items-center justify-center font-mono font-bold text-xs">
              {selectedCountry?.iso_code || "GLOBE"}
            </span>
            <div>
              <p className="text-[10px] uppercase font-mono font-bold text-slate-500 tracking-wider">
                Geographic Context
              </p>
              <h3 className="text-sm font-bold text-slate-200">{selectedCountry?.name || "Global Search Engine"}</h3>
            </div>
          </div>
          <span className="px-2.5 py-1 rounded-full text-[10px] font-mono bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            Backend API Wired
          </span>
        </div>

        {/* AI Greeting Bubble */}
        <div className="flex items-start space-x-3.5 bg-slate-950 p-4 rounded-2xl border border-slate-800">
          <div className="w-10 h-10 rounded-xl bg-brand-500 flex items-center justify-center text-slate-950 font-bold shrink-0 shadow-md shadow-brand-500/30">
            <Bot className="w-5 h-5" />
          </div>
          <div className="space-y-1">
            <div className="flex items-center space-x-2">
              <span className="text-xs font-bold text-slate-200">AI Mobility Analyst</span>
              <span className="text-[9px] font-mono px-1.5 py-0.5 rounded bg-brand-500/20 text-brand-400">
                Global Discovery
              </span>
            </div>
            <p className="text-sm text-slate-300 font-medium">
              "Which city would you like to analyze? Search Mumbai, Jaipur, Cape Town, Dubai, Tokyo, London, or NYC."
            </p>
          </div>
        </div>

        {/* Live Search Input */}
        <div className="relative">
          <Search className="w-4 h-4 text-brand-400 absolute left-4 top-3.5" />
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Search Mumbai, Jaipur, Cape Town, Dubai, Tokyo, London, NYC..."
            className="w-full pl-11 pr-4 py-3 bg-slate-950 border border-slate-800 rounded-xl text-slate-100 text-xs placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-brand-500/40 font-sans"
          />
        </div>

        {/* Search Results List */}
        <div>
          <p className="text-[11px] font-mono uppercase text-slate-500 font-semibold mb-2.5">
            {searchTerm ? "Search Results" : "Featured Global Cities"}
          </p>
          {loading ? (
            <div className="p-6 text-center text-xs font-mono text-slate-400 animate-pulse">
              Querying backend geography search engine...
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 max-h-72 overflow-y-auto p-1">
              {searchResults.map((city) => {
                let badgeText = "GEOGRAPHIC";
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
                    className="p-3.5 rounded-2xl bg-slate-950 border border-slate-800 hover:border-brand-500/50 hover:bg-slate-950/90 cursor-pointer transition-all duration-200 group flex items-center justify-between shadow-md"
                  >
                    <div className="flex items-center space-x-3">
                      <div className="w-9 h-9 rounded-xl bg-slate-900 border border-slate-800 group-hover:border-brand-500/40 flex items-center justify-center text-brand-400 transition-colors">
                        <Building2 className="w-4 h-4" />
                      </div>
                      <div>
                        <div className="flex items-center space-x-1.5">
                          <h4 className="text-xs font-bold text-slate-100 group-hover:text-brand-300 transition-colors">
                            {city.name}
                          </h4>
                          {city.country_code && (
                            <span className="text-[10px] font-mono text-slate-500">({city.country_code})</span>
                          )}
                        </div>
                        <p className="text-[10px] font-mono text-slate-400 mt-0.5">
                          <span className={`px-1.5 py-0.2 rounded border ${badgeClass}`}>{badgeText}</span>
                        </p>
                      </div>
                    </div>

                    <div className="w-7 h-7 rounded-lg bg-slate-900 flex items-center justify-center text-slate-400 group-hover:text-brand-400 group-hover:bg-slate-800 transition-colors">
                      <ArrowRight className="w-3.5 h-3.5" />
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Footnote */}
        <div className="pt-2 border-t border-slate-800/80 flex items-center justify-between text-[11px] text-slate-400 font-mono">
          <span>Backend Geography Discovery API</span>
          <span className="text-slate-400">Zero Hardcoded Capabilities</span>
        </div>
      </div>
    </div>
  );
};

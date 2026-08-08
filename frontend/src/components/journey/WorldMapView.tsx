import React, { useState } from "react";
import { MapContainer, TileLayer, CircleMarker, Tooltip } from "react-leaflet";
import { useMobility } from "../../context/MobilityContext";
import { GeographyCountry } from "../../api/client";
import { Search, Globe, Sparkles, CheckCircle2, ArrowRight, ShieldCheck, Navigation, Activity, Cpu } from "lucide-react";
import { CommandPalette } from "../navigation/CommandPalette";
import { useNavigate } from "react-router-dom";

// Major global city nodes for global cartographic rendering
const GLOBAL_MAJOR_NODES: { id: string; name: string; countryCode: string; lat: number; lng: number; mode: "OBSERVED_MOBILITY" | "MODELED_MOBILITY" }[] = [
  { id: "nyc", name: "New York City", countryCode: "US", lat: 40.7128, lng: -74.006, mode: "OBSERVED_MOBILITY" },
  { id: "london", name: "London", countryCode: "GB", lat: 51.5074, lng: -0.1278, mode: "OBSERVED_MOBILITY" },
  { id: "mumbai", name: "Mumbai", countryCode: "IN", lat: 19.076, lng: 72.8777, mode: "MODELED_MOBILITY" },
  { id: "tokyo", name: "Tokyo", countryCode: "JP", lat: 35.6762, lng: 139.6503, mode: "MODELED_MOBILITY" },
  { id: "dubai", name: "Dubai", countryCode: "AE", lat: 25.2048, lng: 55.2708, mode: "MODELED_MOBILITY" },
  { id: "cape_town", name: "Cape Town", countryCode: "ZA", lat: -33.9249, lng: 18.4241, mode: "MODELED_MOBILITY" },
];

export const WorldMapView: React.FC = () => {
  const { geographyCountries, allCountries, selectGlobalCity, setIsAnalyzing } = useMobility();
  const [commandPaletteOpen, setCommandPaletteOpen] = useState<boolean>(false);
  const navigate = useNavigate();

  const totalGeographicCountries = geographyCountries.length || 248;
  const totalMobilityCountries = allCountries.filter((c) => c.supported).length || 2;

  const handleCityClick = (cityId: string, countryCode: string) => {
    selectGlobalCity(cityId);
    setIsAnalyzing(true);
    navigate(`/explore/${countryCode.toLowerCase()}/${cityId}`);
  };

  return (
    <div className="relative w-full h-[calc(100vh-4rem)] bg-slate-950 overflow-hidden flex flex-col font-sans select-none">
      {/* Background Cartographic Leaflet Map */}
      <div className="absolute inset-0 z-0">
        <MapContainer
          center={[20, 10]}
          zoom={2.5}
          minZoom={2}
          maxZoom={6}
          style={{ width: "100%", height: "100%", background: "#020617" }}
          zoomControl={false}
          scrollWheelZoom={true}
        >
          <TileLayer
            attribution='&copy; <a href="https://carto.com/">CARTO</a>'
            url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
          />

          {/* Render status-encoded global nodes */}
          {GLOBAL_MAJOR_NODES.map((node) => {
            const isObserved = node.mode === "OBSERVED_MOBILITY";
            const nodeColor = isObserved ? "#2dd4a7" : "#f59e0b";

            return (
              <React.Fragment key={node.id}>
                {/* Outer Pulse */}
                <CircleMarker
                  center={[node.lat, node.lng]}
                  radius={isObserved ? 18 : 12}
                  pathOptions={{
                    color: nodeColor,
                    fillColor: nodeColor,
                    fillOpacity: 0.15,
                    weight: 1,
                  }}
                />
                {/* Core Node Marker */}
                <CircleMarker
                  center={[node.lat, node.lng]}
                  radius={6}
                  pathOptions={{
                    color: "#ffffff",
                    fillColor: nodeColor,
                    fillOpacity: 1,
                    weight: 2,
                  }}
                  eventHandlers={{
                    click: () => handleCityClick(node.id, node.countryCode),
                  }}
                >
                  <Tooltip direction="top" offset={[0, -8]} opacity={1} permanent={false}>
                    <div className="text-xs font-mono p-1 space-y-0.5">
                      <div className="font-bold flex items-center gap-1.5" style={{ color: nodeColor }}>
                        <span>● {node.name}</span>
                        <span className="text-[9px] uppercase px-1 rounded bg-slate-900 border border-slate-700">
                          {isObserved ? "Observed" : "Modeled"}
                        </span>
                      </div>
                      <div className="text-[10px] text-slate-300 font-sans font-normal">
                        Click to load backend city profile & context
                      </div>
                    </div>
                  </Tooltip>
                </CircleMarker>
              </React.Fragment>
            );
          })}
        </MapContainer>
      </div>

      {/* Hero Header & Search Overlay */}
      <div className="relative z-10 p-6 md:p-10 pointer-events-none flex flex-col justify-between h-full">
        {/* Top Hero Card */}
        <div className="max-w-xl pointer-events-auto">
          <div className="inline-flex items-center space-x-2 px-3 py-1.5 rounded-full bg-slate-900/90 border border-slate-800 backdrop-blur-md shadow-xl text-xs mb-4">
            <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
            <span className="text-slate-300 font-mono">Backend Telemetry Live</span>
            <span className="text-slate-600">|</span>
            <span className="text-brand-400 font-mono">Global Geography Engine</span>
          </div>

          <h1 className="text-3xl md:text-5xl font-extrabold text-slate-100 tracking-tight leading-tight drop-shadow-lg">
            Global Mobility <br />
            <span className="bg-gradient-to-r from-brand-400 via-emerald-400 to-teal-300 bg-clip-text text-transparent">
              Intelligence
            </span>
          </h1>

          <p className="mt-3 text-slate-400 text-sm md:text-base leading-relaxed max-w-lg">
            Search any city globally (Mumbai, Cape Town, Dubai, Tokyo, London, NYC) to inspect geographic profile, environmental facts, observed mobility metrics, or cross-city models.
          </p>

          {/* Search Trigger Button */}
          <div className="mt-6 flex flex-wrap items-center gap-3">
            <button
              onClick={() => setCommandPaletteOpen(true)}
              className="px-5 py-3 rounded-xl bg-brand-500 hover:bg-brand-400 text-slate-950 font-bold text-sm flex items-center space-x-2.5 shadow-lg shadow-brand-500/20 transition-all duration-200"
            >
              <Search className="w-4 h-4" />
              <span>Search Any City (Mumbai, Dubai, Tokyo...)</span>
              <kbd className="px-1.5 py-0.5 text-[10px] font-mono bg-slate-950/20 rounded text-slate-900 border border-slate-950/30">
                ⌘K
              </kbd>
            </button>
          </div>
        </div>

        {/* Floating Bottom Live Coverage Telemetry Bar */}
        <div className="pointer-events-auto w-full max-w-4xl mx-auto bg-slate-900/95 border border-slate-800 backdrop-blur-md p-4 rounded-2xl shadow-2xl space-y-3">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-xs border-b border-slate-800/80 pb-2.5">
            <div className="flex items-center space-x-2 font-mono text-slate-400">
              <Globe className="w-4 h-4 text-brand-400" />
              <span className="font-bold text-slate-200">System Coverage Status</span>
            </div>
            <div className="flex items-center space-x-4 text-[11px] font-mono">
              <span className="text-slate-400">
                GLOBAL GEOGRAPHIC COVERAGE:{" "}
                <strong className="text-slate-100">{totalGeographicCountries} Countries</strong>
              </span>
              <span className="text-slate-600">|</span>
              <span className="text-brand-400">
                MOBILITY INTELLIGENCE COVERAGE:{" "}
                <strong className="text-emerald-400">{totalMobilityCountries} Active Regions</strong>
              </span>
            </div>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 text-xs font-mono">
            <div className="p-2.5 rounded-xl bg-slate-950 border border-slate-800 flex items-center space-x-2">
              <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 shrink-0" />
              <div>
                <p className="text-[10px] text-slate-400">OBSERVED</p>
                <p className="font-bold text-slate-200">NYC, London</p>
              </div>
            </div>

            <div className="p-2.5 rounded-xl bg-slate-950 border border-slate-800 flex items-center space-x-2">
              <span className="w-2.5 h-2.5 rounded-full bg-amber-400 shrink-0" />
              <div>
                <p className="text-[10px] text-slate-400">MODELED</p>
                <p className="font-bold text-slate-200">Mumbai, Tokyo, Dubai</p>
              </div>
            </div>

            <div className="p-2.5 rounded-xl bg-slate-950 border border-slate-800 flex items-center space-x-2">
              <span className="w-2.5 h-2.5 rounded-full bg-teal-400 shrink-0" />
              <div>
                <p className="text-[10px] text-slate-400">CONTEXT ONLY</p>
                <p className="font-bold text-slate-200">Global Cities</p>
              </div>
            </div>

            <div className="p-2.5 rounded-xl bg-slate-950 border border-slate-800 flex items-center space-x-2">
              <span className="w-2.5 h-2.5 rounded-full bg-slate-500 shrink-0" />
              <div>
                <p className="text-[10px] text-slate-400">GEOGRAPHIC ONLY</p>
                <p className="font-bold text-slate-200">GeoNames DB</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Command Search Modal */}
      <CommandPalette isOpen={commandPaletteOpen} onClose={() => setCommandPaletteOpen(false)} />
    </div>
  );
};

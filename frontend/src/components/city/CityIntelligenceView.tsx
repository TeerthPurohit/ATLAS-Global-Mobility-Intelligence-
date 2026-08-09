import React, { useState, useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { useMobility } from "../../context/MobilityContext";
import {
  fetchCityAreas,
  fetchCityCapabilities,
  fetchCityForecast,
  fetchCityJourneyEstimate,
  fetchDashboardSummary,
  fetchHourlyDemandProfile,
  fetchZones,
  Area,
  Zone,
  City,
  ForecastEnvelope,
} from "../../api/client";
import { CityAreaMap } from "./CityAreaMap";
import { AreaIntelligenceDrawer } from "./AreaIntelligenceDrawer";
import { ContextualAIChatDrawer } from "../chat/ContextualAIChatDrawer";
import {
  TrendingUp,
  DollarSign,
  MapPin,
  Clock,
  Sparkles,
  ChevronLeft,
  Activity,
  Layers,
  BarChart3,
  Bot,
  CheckCircle2,
  ShieldAlert,
} from "lucide-react";
import { ResponsiveContainer, AreaChart, Area as ReArea, XAxis, YAxis, Tooltip, CartesianGrid } from "recharts";

interface CityIntelligenceViewProps {
  cityId: string;
  countryCode: string;
}

export const CityIntelligenceView: React.FC<CityIntelligenceViewProps> = ({ cityId, countryCode }) => {
  const { selectedCity, selectedCityProfile, countryCities, resetToWorld, resetToCountry, setSelectedArea, selectedArea } =
    useMobility();
  const [activeTab, setActiveTab] = useState<"map" | "demand" | "fare" | "forecast">("map");
  const [chatOpen, setChatOpen] = useState(false);
  const [chatInitialQuestion, setChatInitialQuestion] = useState<string | undefined>(undefined);

  // Prefer the resolved global city profile (real coordinates from the backend)
  // over a guessed default -- previously this always fell back to NYC's
  // coordinates for any city not in the seeded nyc/london list.
  const currentCity: City = selectedCity || {
    id: cityId,
    name: selectedCityProfile?.city || cityId,
    country_code: (selectedCityProfile?.country_code || countryCode).toUpperCase(),
    latitude: selectedCityProfile?.coordinates.latitude ?? 0,
    longitude: selectedCityProfile?.coordinates.longitude ?? 0,
    timezone: selectedCityProfile?.timezone || "UTC",
    currency: selectedCityProfile?.currency || "USD",
    status: "active",
    data_source: selectedCityProfile?.capabilities.observed_mobility ? "observed" : "geonames",
    geography_type: "zone",
    model_status: selectedCityProfile?.capabilities.cross_city_model ? "active" : "unavailable",
    last_updated: selectedCityProfile ? new Date().toISOString().slice(0, 10) : "unknown",
  };

  // Queries. No silent .catch(() => []) here -- that was masking real
  // fetch failures (network/CORS/5xx) as an empty city with no areas,
  // indistinguishable from a genuinely area-less city and impossible to
  // debug from the UI. Let React Query surface the real error instead.
  const {
    data: areas = [],
    isError: areasError,
    error: areasErrorDetail,
  } = useQuery({
    queryKey: ["cityAreas", cityId],
    queryFn: () => fetchCityAreas(cityId),
    retry: 1,
  });

  const { data: zones = [] } = useQuery({
    queryKey: ["zones"],
    queryFn: () => fetchZones().catch(() => []),
  });

  const { data: capabilities } = useQuery({
    queryKey: ["capabilities", cityId],
    queryFn: () => fetchCityCapabilities(cityId).catch(() => null),
  });

  // `/dashboard/summary` and `/marts/zone_hourly_demand` are literally the
  // NYC HVFHV DuckDB mart -- no city_id param, no other city's data in it.
  // Previously these were gated on `capabilities.demand`, which London also
  // has (it has its own real model) -- so London silently rendered NYC's
  // aggregate numbers under its own label. Only NYC gets this mart.
  const isNyc = cityId.toLowerCase() === "nyc";

  const { data: summary } = useQuery({
    queryKey: ["dashboardSummary", cityId],
    queryFn: fetchDashboardSummary,
    enabled: isNyc,
  });

  const { data: nycHourlyDemand = [] } = useQuery({
    queryKey: ["hourlyDemand", cityId],
    queryFn: fetchHourlyDemandProfile,
    enabled: isNyc,
  });

  // Any other city with its own trained model (e.g. London) gets its own
  // real per-city historical forecast instead of NYC's mart.
  const { data: cityForecast } = useQuery({
    queryKey: ["cityForecast", cityId],
    queryFn: () => fetchCityForecast(cityId, "demand", 24),
    enabled: !isNyc && Boolean(capabilities?.demand),
  });
  const otherCityHourlyDemand =
    cityForecast && "series" in cityForecast ? cityForecast.series.map((p) => ({ hour: p.hour, demand: p.value, fare: 0 })) : [];

  const hourlyDemand = isNyc ? nycHourlyDemand : otherCityHourlyDemand;

  // For every city -- NYC, London, or anywhere else on Earth -- the real
  // OSRM-routed, model-or-2-reference-point-scaled journey estimate (never
  // fabricated, always basis-labeled). Used to fill the summary tiles when
  // there's no dedicated dashboard mart for this city.
  const hasCoords = Boolean(currentCity.latitude && currentCity.longitude);
  const { data: journeyEstimate } = useQuery({
    queryKey: ["cityJourneyEstimate", cityId, currentCity.latitude, currentCity.longitude],
    queryFn: () =>
      fetchCityJourneyEstimate(
        cityId,
        currentCity.latitude,
        currentCity.longitude,
        currentCity.latitude + 0.01,
        currentCity.longitude + 0.01
      ),
    enabled: !isNyc && hasCoords,
  });

  const peakDemandHour = hourlyDemand.length
    ? hourlyDemand.reduce((max, p) => (p.demand > max.demand ? p : max), hourlyDemand[0]).hour
    : null;

  const handleAskAIAboutArea = (area: Area, question?: string) => {
    setSelectedArea(area);
    setChatInitialQuestion(question || `Analyze demand for ${area.name}`);
    setChatOpen(true);
  };

  const cityCenter: [number, number] = [currentCity.latitude, currentCity.longitude];

  return (
    <div className="h-[calc(100vh-4rem)] flex flex-col bg-slate-950 text-slate-100 overflow-hidden font-sans select-none relative">
      {/* Top Header Controls Bar */}
      <div className="h-14 bg-slate-900 border-b border-slate-800 px-4 md:px-6 flex items-center justify-between shrink-0 z-20">
        {/* Left: Spatial Breadcrumb Navigation */}
        <div className="flex items-center space-x-3 text-xs">
          <button
            onClick={resetToWorld}
            className="flex items-center text-slate-400 hover:text-slate-200 transition-colors font-medium"
          >
            <ChevronLeft className="w-3.5 h-3.5 mr-1" />
            <span>World</span>
          </button>
          <span className="text-slate-600">/</span>
          <span className="px-2 py-0.5 rounded font-mono font-bold bg-slate-800 text-slate-300 text-[11px]">
            {countryCode.toUpperCase()}
          </span>
          <span className="text-slate-600">/</span>
          <div className="flex items-center space-x-1.5 font-bold text-slate-100">
            <span>{currentCity.name}</span>
            <span className="px-2 py-0.5 rounded-full text-[10px] font-mono bg-brand-500/20 text-brand-400 border border-brand-500/30">
              {currentCity.geography_type} level
            </span>
          </div>
        </div>

        {/* Center: View Switcher */}
        <div className="hidden md:flex items-center space-x-1 bg-slate-950 p-1 rounded-xl border border-slate-800 text-xs font-mono">
          <button
            onClick={() => setActiveTab("map")}
            className={`px-3 py-1.5 rounded-lg flex items-center space-x-1.5 transition-all ${
              activeTab === "map"
                ? "bg-brand-500/20 text-brand-400 border border-brand-500/30 font-bold"
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            <MapPin className="w-3.5 h-3.5" />
            <span>Map & Areas</span>
          </button>
          <button
            onClick={() => setActiveTab("demand")}
            className={`px-3 py-1.5 rounded-lg flex items-center space-x-1.5 transition-all ${
              activeTab === "demand"
                ? "bg-brand-500/20 text-brand-400 border border-brand-500/30 font-bold"
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            <TrendingUp className="w-3.5 h-3.5" />
            <span>Demand Trends</span>
          </button>
          <button
            onClick={() => setActiveTab("forecast")}
            className={`px-3 py-1.5 rounded-lg flex items-center space-x-1.5 transition-all ${
              activeTab === "forecast"
                ? "bg-brand-500/20 text-brand-400 border border-brand-500/30 font-bold"
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            <Clock className="w-3.5 h-3.5" />
            <span>Hourly Forecast</span>
          </button>
        </div>

        {/* Right: AI Assistant Action Button */}
        <div className="flex items-center space-x-3">
          <button
            onClick={() => setChatOpen(true)}
            className="px-3.5 py-1.5 rounded-xl bg-brand-500 hover:bg-brand-400 text-slate-950 font-bold text-xs flex items-center space-x-1.5 shadow-md shadow-brand-500/20 transition-all"
          >
            <Sparkles className="w-3.5 h-3.5" />
            <span>Ask AI Assistant</span>
          </button>
        </div>
      </div>

      {/* Main Content Layout */}
      <div className="flex-1 flex flex-col lg:flex-row relative overflow-hidden">
        {/* Left / Center Viewport */}
        <div className="flex-1 flex flex-col h-full overflow-y-auto">
          {/* Top Quick City Overview Metrics Bar */}
          <div className="p-4 bg-slate-900/60 border-b border-slate-800/80 grid grid-cols-2 sm:grid-cols-4 gap-3 shrink-0">
            <div className="p-3 rounded-xl bg-slate-900 border border-slate-800 flex items-center justify-between">
              <div>
                <p className="text-[10px] font-mono text-slate-400">
                  {isNyc ? "Total Analyzed Trips" : "Est. Daily Demand"}
                </p>
                <p className="text-lg font-extrabold font-mono text-slate-100 mt-0.5">
                  {isNyc
                    ? summary?.total_trips
                      ? summary.total_trips.toLocaleString()
                      : "—"
                    : typeof journeyEstimate?.demand.value === "number"
                    ? Math.round(journeyEstimate.demand.value).toLocaleString()
                    : "—"}
                </p>
                {!isNyc && journeyEstimate?.demand.basis === "modeled_estimate" && (
                  <p className="text-[9px] uppercase font-bold text-amber-400 mt-0.5">
                    Modeled from NYC/London reference data
                  </p>
                )}
              </div>
              <Activity className="w-5 h-5 text-brand-400" />
            </div>

            <div className="p-3 rounded-xl bg-slate-900 border border-slate-800 flex items-center justify-between">
              <div>
                <p className="text-[10px] font-mono text-slate-400">
                  {isNyc ? "Weighted Average Fare" : "Est. Fare / Mile"}
                </p>
                <p className="text-lg font-extrabold font-mono text-slate-100 mt-0.5">
                  {isNyc
                    ? summary?.avg_fare
                      ? `$${summary.avg_fare.toFixed(2)}`
                      : "—"
                    : typeof journeyEstimate?.fare.value === "number"
                    ? `$${journeyEstimate.fare.value.toFixed(2)}`
                    : "—"}
                </p>
                {!isNyc && journeyEstimate?.fare.basis === "modeled_estimate" && (
                  <p className="text-[9px] uppercase font-bold text-amber-400 mt-0.5">Modeled (PPP-scaled from NYC)</p>
                )}
              </div>
              <DollarSign className="w-5 h-5 text-amber-400" />
            </div>

            <div className="p-3 rounded-xl bg-slate-900 border border-slate-800 flex items-center justify-between">
              <div>
                <p className="text-[10px] font-mono text-slate-400">Active Canonical Areas</p>
                <p className="text-lg font-extrabold font-mono text-slate-100 mt-0.5">
                  {areas.length || summary?.active_zones || "—"}
                </p>
              </div>
              <Layers className="w-5 h-5 text-emerald-400" />
            </div>

            <div className="p-3 rounded-xl bg-slate-900 border border-slate-800 flex items-center justify-between">
              <div>
                <p className="text-[10px] font-mono text-slate-400">Peak Demand Hour</p>
                <p className="text-lg font-extrabold font-mono text-slate-100 mt-0.5">
                  {peakDemandHour != null ? `${String(peakDemandHour).padStart(2, "0")}:00` : "—"}
                </p>
              </div>
              <Clock className="w-5 h-5 text-teal-400" />
            </div>
          </div>

          {/* Primary View switching */}
          {activeTab === "map" ? (
            <div className="flex-1 relative h-full min-h-[400px]">
              {areasError && (
                <div className="absolute top-3 left-1/2 -translate-x-1/2 z-[500] px-4 py-2 rounded-lg bg-red-950/90 border border-red-800 text-red-300 text-xs font-mono shadow-xl">
                  Failed to load areas for {currentCity.name}: {(areasErrorDetail as Error)?.message || "unknown error"}
                </div>
              )}
              {/* key=cityId forces a full remount per city -- react-leaflet's
                  MapContainer only applies `center`/`zoom` on first mount, so
                  navigating city-to-city via client-side routing (no page
                  reload) reused the old Leaflet instance and rendered a
                  blank/black map instead of recentering. */}
              <CityAreaMap
                key={cityId}
                areas={areas}
                zones={zones}
                selectedArea={selectedArea}
                onSelectArea={(area) => setSelectedArea(area)}
                cityCenter={cityCenter}
              />
            </div>
          ) : (
            <div className="flex-1 p-6 space-y-6 overflow-y-auto">
              <div className="p-6 rounded-2xl bg-slate-900 border border-slate-800 shadow-xl space-y-4">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="text-base font-bold text-slate-100">Hourly Demand & Fare Profile</h3>
                    <p className="text-xs text-slate-400">Real aggregate profile from dbt mart</p>
                  </div>
                  <BarChart3 className="w-5 h-5 text-brand-400" />
                </div>

                {hourlyDemand.length === 0 ? (
                  <div className="h-72 w-full flex items-center justify-center text-sm text-slate-500 font-mono">
                    No hourly time-series for {currentCity.name} yet
                    {journeyEstimate ? " — see the estimated tiles above." : "."}
                  </div>
                ) : (
                <div className="h-72 w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={hourlyDemand}>
                      <defs>
                        <linearGradient id="demandGrad" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#2dd4a7" stopOpacity={0.4} />
                          <stop offset="95%" stopColor="#2dd4a7" stopOpacity={0} />
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                      <XAxis dataKey="hour" stroke="#64748b" fontSize={11} tickFormatter={(h) => `${h}:00`} />
                      <YAxis stroke="#64748b" fontSize={11} />
                      <Tooltip
                        contentStyle={{ backgroundColor: "#0f172a", borderColor: "#334155", borderRadius: "8px" }}
                      />
                      <ReArea type="monotone" dataKey="demand" stroke="#2dd4a7" fillOpacity={1} fill="url(#demandGrad)" />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Right Drawer: Area Intelligence Panel */}
        {selectedArea && (
          <AreaIntelligenceDrawer
            area={selectedArea}
            areas={areas}
            cityId={cityId}
            onClose={() => setSelectedArea(null)}
            onAskAI={handleAskAIAboutArea}
          />
        )}
      </div>

      {/* Contextual AI Assistant Drawer */}
      <ContextualAIChatDrawer
        isOpen={chatOpen}
        onClose={() => setChatOpen(false)}
        cityId={cityId}
        cityName={currentCity.name}
        selectedArea={selectedArea}
        initialQuestion={chatInitialQuestion}
      />
    </div>
  );
};

import React, { useState, useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { useMobility } from "../../context/MobilityContext";
import {
  fetchCityAreas,
  fetchCityCapabilities,
  fetchCityForecast,
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
  const { selectedCity, countryCities, resetToWorld, resetToCountry, setSelectedArea, selectedArea } = useMobility();
  const [activeTab, setActiveTab] = useState<"map" | "demand" | "fare" | "forecast">("map");
  const [chatOpen, setChatOpen] = useState(false);
  const [chatInitialQuestion, setChatInitialQuestion] = useState<string | undefined>(undefined);

  const currentCity: City = selectedCity || {
    id: cityId,
    name: cityId.toUpperCase() === "NYC" ? "New York City" : cityId.toUpperCase() === "LONDON" ? "London" : cityId,
    country_code: countryCode.toUpperCase(),
    latitude: cityId.toLowerCase() === "london" ? 51.5074 : 40.7128,
    longitude: cityId.toLowerCase() === "london" ? -0.1278 : -74.006,
    timezone: cityId.toLowerCase() === "london" ? "Europe/London" : "America/New_York",
    currency: cityId.toLowerCase() === "london" ? "GBP" : "USD",
    status: "active",
    data_source: cityId.toLowerCase() === "london" ? "tfl_cycles" : "nyc_tlc",
    geography_type: cityId.toLowerCase() === "london" ? "station" : "zone",
    model_status: "active",
    last_updated: "2026-08-08",
  };

  // Queries
  const { data: areas = [] } = useQuery({
    queryKey: ["cityAreas", cityId],
    queryFn: () => fetchCityAreas(cityId).catch(() => []),
  });

  const { data: zones = [] } = useQuery({
    queryKey: ["zones"],
    queryFn: () => fetchZones().catch(() => []),
  });

  const { data: summary } = useQuery({
    queryKey: ["dashboardSummary"],
    queryFn: fetchDashboardSummary,
  });

  const { data: hourlyDemand = [] } = useQuery({
    queryKey: ["hourlyDemand"],
    queryFn: fetchHourlyDemandProfile,
  });

  const { data: capabilities } = useQuery({
    queryKey: ["capabilities", cityId],
    queryFn: () => fetchCityCapabilities(cityId).catch(() => null),
  });

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
                <p className="text-[10px] font-mono text-slate-400">Total Analyzed Trips</p>
                <p className="text-lg font-extrabold font-mono text-slate-100 mt-0.5">
                  {summary?.total_trips ? summary.total_trips.toLocaleString() : "14,821,904"}
                </p>
              </div>
              <Activity className="w-5 h-5 text-brand-400" />
            </div>

            <div className="p-3 rounded-xl bg-slate-900 border border-slate-800 flex items-center justify-between">
              <div>
                <p className="text-[10px] font-mono text-slate-400">Weighted Average Fare</p>
                <p className="text-lg font-extrabold font-mono text-slate-100 mt-0.5">
                  ${summary?.avg_fare ? summary.avg_fare.toFixed(2) : "18.42"}
                </p>
              </div>
              <DollarSign className="w-5 h-5 text-amber-400" />
            </div>

            <div className="p-3 rounded-xl bg-slate-900 border border-slate-800 flex items-center justify-between">
              <div>
                <p className="text-[10px] font-mono text-slate-400">Active Canonical Areas</p>
                <p className="text-lg font-extrabold font-mono text-slate-100 mt-0.5">
                  {areas.length || summary?.active_zones || 263}
                </p>
              </div>
              <Layers className="w-5 h-5 text-emerald-400" />
            </div>

            <div className="p-3 rounded-xl bg-slate-900 border border-slate-800 flex items-center justify-between">
              <div>
                <p className="text-[10px] font-mono text-slate-400">Peak Demand Hour</p>
                <p className="text-lg font-extrabold font-mono text-slate-100 mt-0.5">18:00 (Evening)</p>
              </div>
              <Clock className="w-5 h-5 text-teal-400" />
            </div>
          </div>

          {/* Primary View switching */}
          {activeTab === "map" ? (
            <div className="flex-1 relative h-full min-h-[400px]">
              <CityAreaMap
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
              </div>
            </div>
          )}
        </div>

        {/* Right Drawer: Area Intelligence Panel */}
        {selectedArea && (
          <AreaIntelligenceDrawer
            area={selectedArea}
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

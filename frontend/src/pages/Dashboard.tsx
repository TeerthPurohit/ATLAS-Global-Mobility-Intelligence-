import React from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  fetchZones,
  fetchHealth,
  fetchDashboardSummary,
  fetchHourlyDemandProfile,
  fetchWarehouseStats,
  fetchModelMetrics,
} from "../api/client";
import {
  TrendingUp,
  DollarSign,
  MapPin,
  Cpu,
  ArrowUpRight,
  Sparkles,
  Database,
  MessageSquare,
} from "lucide-react";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  BarChart,
  Bar,
} from "recharts";
import { Provenance } from "../components/ui/Provenance";

const MODEL_LABELS: Record<string, string> = {
  ewma: "EWMA Baseline",
  linear: "Linear Baseline",
  lstm: "LSTM Neural Net",
  xgboost: "XGBoost (Best)",
};

export const Dashboard: React.FC = () => {
  const { data: zones, isLoading } = useQuery({
    queryKey: ["zones"],
    queryFn: fetchZones,
  });
  const { data: health } = useQuery({ queryKey: ["health"], queryFn: fetchHealth });
  const { data: summary, isLoading: summaryLoading } = useQuery({
    queryKey: ["dashboard-summary"],
    queryFn: fetchDashboardSummary,
  });
  const { data: hourlyDemand } = useQuery({
    queryKey: ["mart-zone-hourly-demand"],
    queryFn: fetchHourlyDemandProfile,
  });
  const { data: warehouseStats } = useQuery({
    queryKey: ["warehouse-stats"],
    queryFn: fetchWarehouseStats,
  });
  const { data: modelMetrics } = useQuery({
    queryKey: ["model-metrics"],
    queryFn: fetchModelMetrics,
  });

  const modelChartData = modelMetrics
    ? Object.entries(modelMetrics.demand).map(([key, m]) => ({
        model: MODEL_LABELS[key] || key,
        rmse: m.rmse,
        mae: m.mae,
      }))
    : [];
  const bestModel = modelChartData.length
    ? [...modelChartData].sort((a, b) => a.rmse - b.rmse)[0]
    : null;

  return (
    <div className="p-6 space-y-6">
      {/* Title & Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-slate-100 flex items-center gap-2">
            Executive Operations Dashboard
            <span
              className={`px-2 py-0.5 rounded text-[10px] font-mono font-semibold border ${
                health?.status === "healthy"
                  ? "bg-brand-500/20 text-brand-400 border-brand-500/30"
                  : "bg-slate-800 text-slate-400 border-slate-700"
              }`}
            >
              {health ? (health.status === "healthy" ? "Live Warehouse" : "Degraded") : "Checking..."}
            </span>
          </h1>
          <p className="text-xs text-slate-400 mt-0.5">
            NYC TLC HVFHV Trip Data Platform · DuckDB + XGBoost + RAG Analytics
          </p>
        </div>
        <div className="flex items-center space-x-2">
          <Link
            to="/analyst"
            className="px-3 py-1.5 rounded-lg bg-brand-500 hover:bg-brand-400 text-slate-950 text-xs font-semibold transition-colors flex items-center space-x-1.5 shadow-lg shadow-brand-500/20"
          >
            <Sparkles className="w-3.5 h-3.5" />
            <span>Ask AI Analyst</span>
          </Link>
        </div>
      </div>

      {/* Enterprise Platform Telemetry Header Bar */}
      <div className="p-3 rounded-xl bg-slate-900 border border-slate-800 flex flex-wrap items-center justify-between gap-3 text-[11px] font-mono text-slate-400">
        <div className="flex items-center space-x-4">
          <span className="flex items-center gap-1.5 text-slate-200">
            <Database className="w-3.5 h-3.5 text-brand-400" />
            <span>Warehouse: <strong className="text-slate-100">nyc_rides.duckdb</strong></span>
          </span>
          <span className="hidden md:inline text-slate-600">|</span>
          <span className="hidden md:flex items-center gap-1">
            <span>Pipeline:</span>{" "}
            <strong className={health?.duckdb === "online" ? "text-emerald-400" : "text-slate-500"}>
              dbt Mart (stg_trips)
            </strong>
          </span>
          <span className="hidden md:inline text-slate-600">|</span>
          <span className="hidden md:flex items-center gap-1">
            <span>Rows:</span>{" "}
            <strong className="text-slate-200">
              {warehouseStats ? warehouseStats.total_rows.toLocaleString() : "..."}
            </strong>
          </span>
        </div>
        <div className="flex items-center space-x-3 text-[10px]">
          <span className="px-2 py-0.5 rounded bg-slate-950 border border-slate-800 text-slate-300">
            Env: {import.meta.env.MODE === "production" ? "Production" : "Development"}
          </span>
          <span
            className={`px-2 py-0.5 rounded bg-slate-950 border border-slate-800 font-semibold flex items-center gap-1 ${
              health?.duckdb === "online" ? "text-emerald-400" : "text-red-400"
            }`}
          >
            <span
              className={`w-1.5 h-1.5 rounded-full ${
                health?.duckdb === "online" ? "bg-emerald-400 animate-pulse" : "bg-red-400"
              }`}
            />
            DuckDB: {health ? health.duckdb : "checking..."}
          </span>
        </div>
      </div>

      {/* KPI Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* KPI 1 */}
        <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 relative overflow-hidden flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-slate-400">Total Analyzed Trips</span>
              <div className="p-2 rounded-lg bg-brand-500/10 text-brand-400">
                <TrendingUp className="w-4 h-4" />
              </div>
            </div>
            <div className="mt-3">
              <h2 className="text-2xl font-bold text-slate-100 font-mono font-meter">
                {summaryLoading || !summary
                  ? "..."
                  : `${(summary.total_trips / 1_000_000).toFixed(2)} M`}
              </h2>
              <p className="text-[11px] text-emerald-400 flex items-center gap-1 mt-1">
                <span>Jan, Mar, Jun 2024</span>
              </p>
            </div>
          </div>
          <Provenance type="mart" source="zone_hourly_demand" />
        </div>

        {/* KPI 2 */}
        <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 relative overflow-hidden flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-slate-400">Average Trip Fare</span>
              <div className="p-2 rounded-lg bg-emerald-500/10 text-emerald-400">
                <DollarSign className="w-4 h-4" />
              </div>
            </div>
            <div className="mt-3">
              <h2 className="text-2xl font-bold text-slate-100 font-mono font-meter">
                {summaryLoading || !summary ? "..." : `$${summary.avg_fare.toFixed(2)}`}
              </h2>
              <p className="text-[11px] text-slate-400 mt-1">Base + Surcharges + Tips</p>
            </div>
          </div>
          <Provenance type="mart" source="zone_hourly_demand" />
        </div>

        {/* KPI 3 */}
        <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 relative overflow-hidden flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-slate-400">Active TLC Zones</span>
              <div className="p-2 rounded-lg bg-indigo-500/10 text-indigo-400">
                <MapPin className="w-4 h-4" />
              </div>
            </div>
            <div className="mt-3">
              <h2 className="text-2xl font-bold text-slate-100 font-mono font-meter">
                {isLoading || !zones ? "..." : zones.length}
              </h2>
              <p className="text-[11px] text-indigo-400 mt-1">KD-Tree Centroid Mapped</p>
            </div>
          </div>
          <Provenance type="live" source="GET /zones" />
        </div>

        {/* KPI 4 */}
        <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 relative overflow-hidden flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-slate-400">Demand Model RMSE</span>
              <div className="p-2 rounded-lg bg-amber-500/10 text-amber-400">
                <Cpu className="w-4 h-4" />
              </div>
            </div>
            <div className="mt-3">
              <h2 className="text-2xl font-bold text-slate-100 font-mono font-meter">
                {bestModel ? bestModel.rmse.toFixed(2) : "..."}
              </h2>
              <p className="text-[11px] text-emerald-400 mt-1">XGBoost Chrono-Split Best</p>
            </div>
          </div>
          <Provenance type="artifact" source="compare_results.json" />
        </div>
      </div>

      {/* Analytics Charts Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Chart 1: Demand & Fare Hourly Profile */}
        <div className="lg:col-span-2 p-5 rounded-xl bg-slate-900 border border-slate-800 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-4">
              <div>
                <h3 className="text-sm font-semibold text-slate-100">Hourly Demand & Fare Profile</h3>
                <p className="text-[11px] text-slate-400">Aggregated trip counts vs average fares across 24h</p>
              </div>
              <span className="text-[10px] font-mono text-slate-400 bg-slate-950 px-2 py-1 rounded border border-slate-800">
                zone_hourly_demand
              </span>
            </div>
            <div className="h-64 w-full mt-2">
              {hourlyDemand ? (
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={hourlyDemand}>
                    <defs>
                      <linearGradient id="demandGradient" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#0c93eb" stopOpacity={0.4} />
                        <stop offset="95%" stopColor="#0c93eb" stopOpacity={0.0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                    <XAxis dataKey="hour" stroke="#64748b" fontSize={11} />
                    <YAxis stroke="#64748b" fontSize={11} />
                    <Tooltip
                      contentStyle={{ backgroundColor: "#0f172a", borderColor: "#334155", borderRadius: "8px" }}
                      labelStyle={{ color: "#f8fafc", fontWeight: "bold", fontSize: "12px" }}
                    />
                    <Area type="monotone" dataKey="demand" stroke="#0c93eb" strokeWidth={2} fillOpacity={1} fill="url(#demandGradient)" name="Demand (Trips)" />
                  </AreaChart>
                </ResponsiveContainer>
              ) : (
                <div className="h-full w-full flex items-center justify-center text-xs text-slate-500">
                  Querying dbt mart...
                </div>
              )}
            </div>
          </div>
          <Provenance type="mart" source="zone_hourly_demand" />
        </div>

        {/* Chart 2: Model Ladder Comparison */}
        <div className="p-5 rounded-xl bg-slate-900 border border-slate-800 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-4">
              <div>
                <h3 className="text-sm font-semibold text-slate-100">Model Ladder RMSE</h3>
                <p className="text-[11px] text-slate-400">Evaluated on June holdout block</p>
              </div>
              <Link to="/models" className="text-xs text-brand-400 hover:underline flex items-center">
                Details <ArrowUpRight className="w-3 h-3 ml-0.5" />
              </Link>
            </div>
            <div className="h-56 w-full">
              {modelChartData.length ? (
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={modelChartData} layout="vertical">
                    <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                    <XAxis type="number" stroke="#64748b" fontSize={11} domain={[0, 9]} />
                    <YAxis dataKey="model" type="category" stroke="#64748b" fontSize={10} width={90} />
                    <Tooltip
                      contentStyle={{ backgroundColor: "#0f172a", borderColor: "#334155", borderRadius: "8px" }}
                    />
                    <Bar dataKey="rmse" fill="#0c93eb" radius={[0, 4, 4, 0]} name="RMSE" />
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <div className="h-full w-full flex items-center justify-center text-xs text-slate-500">
                  Loading model artifacts...
                </div>
              )}
            </div>
          </div>
          {bestModel && (
            <div className="p-3 rounded-lg bg-slate-950 border border-slate-800 text-[11px] text-slate-300 mt-2">
              <span className="font-semibold text-emerald-400">{bestModel.model} Best:</span> RMSE{" "}
              {bestModel.rmse.toFixed(2)} / MAE {bestModel.mae.toFixed(2)} outperforming other baselines.
            </div>
          )}
          <Provenance type="artifact" source="compare_results.json" detail="Split: Chrono-June" />
        </div>
      </div>

      {/* Quick Action Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Link
          to="/map"
          className="p-4 rounded-xl bg-gradient-to-br from-slate-900 to-slate-900/60 border border-slate-800 hover:border-brand-500/50 transition-all group"
        >
          <div className="flex items-center justify-between">
            <div className="p-2.5 rounded-lg bg-brand-500/10 text-brand-400 group-hover:bg-brand-500 group-hover:text-slate-950 transition-colors">
              <MapPin className="w-5 h-5" />
            </div>
            <ArrowUpRight className="w-4 h-4 text-slate-500 group-hover:text-brand-400 transition-colors" />
          </div>
          <h3 className="text-sm font-semibold text-slate-200 mt-3">Interactive Zone Map</h3>
          <p className="text-xs text-slate-400 mt-1">
            Explore TLC zone centroids, PageRank hub scores, and spatial KD-tree lookup.
          </p>
        </Link>

        <Link
          to="/demand"
          className="p-4 rounded-xl bg-gradient-to-br from-slate-900 to-slate-900/60 border border-slate-800 hover:border-brand-500/50 transition-all group"
        >
          <div className="flex items-center justify-between">
            <div className="p-2.5 rounded-lg bg-indigo-500/10 text-indigo-400 group-hover:bg-indigo-500 group-hover:text-white transition-colors">
              <TrendingUp className="w-5 h-5" />
            </div>
            <ArrowUpRight className="w-4 h-4 text-slate-500 group-hover:text-indigo-400 transition-colors" />
          </div>
          <h3 className="text-sm font-semibold text-slate-200 mt-3">Demand Forecast</h3>
          <p className="text-xs text-slate-400 mt-1">
            Query live XGBoost model predictions across {zones ? zones.length : "all"} zones for any hour and day.
          </p>
        </Link>

        <Link
          to="/analyst"
          className="p-4 rounded-xl bg-gradient-to-br from-slate-900 to-slate-900/60 border border-slate-800 hover:border-brand-500/50 transition-all group"
        >
          <div className="flex items-center justify-between">
            <div className="p-2.5 rounded-lg bg-emerald-500/10 text-emerald-400 group-hover:bg-emerald-500 group-hover:text-white transition-colors">
              <MessageSquare className="w-5 h-5 text-emerald-400" />
            </div>
            <ArrowUpRight className="w-4 h-4 text-slate-500 group-hover:text-emerald-400 transition-colors" />
          </div>
          <h3 className="text-sm font-semibold text-slate-200 mt-3">Hybrid RAG Analyst</h3>
          <p className="text-xs text-slate-400 mt-1">
            Ask natural language questions routed automatically to NL-to-SQL or Qdrant vector retrieval.
          </p>
        </Link>
      </div>
    </div>
  );
};

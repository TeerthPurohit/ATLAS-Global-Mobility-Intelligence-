import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Workflow,
  CheckCircle2,
  ArrowRight,
  AlertTriangle,
  Terminal,
} from "lucide-react";
import {
  fetchPipelineStatus,
  fetchWarehouseStats,
  fetchAlgorithmBenchmarks,
  fetchModelMetrics,
  fetchZones,
} from "../api/client";

interface PipelineNodeSpec {
  id: string;
  stageNumber: string;
  title: string;
  category: "Ingestion" | "Warehouse" | "Transformation" | "ML & Algs" | "Serving";
  engine: string;
  inputs: string[];
  outputs: string[];
  logicSummary: string;
  codeSnippet: string;
}

// Architecture documentation -- real file/command names in this repo, verifiable
// against scripts/, dbt_project/, algorithms/, models/, backend/. Duration and
// row-count numbers are NOT hardcoded here; they're filled in below from real
// endpoints, or shown as "not tracked" where this repo has no run-log for that
// stage yet (see ARCHITECTURE_AUDIT.md).
const PIPELINE_SPEC: PipelineNodeSpec[] = [
  {
    id: "ingestion",
    stageNumber: "01",
    title: "HVFHV Parquet Raw Ingestion",
    category: "Ingestion",
    engine: "PyArrow / DuckDB",
    inputs: ["nyc_tripdata_2024-01.parquet", "nyc_tripdata_2024-03.parquet", "nyc_tripdata_2024-06.parquet"],
    outputs: ["data/warehouse/nyc_rides.duckdb (raw tables)"],
    logicSummary: "Load High Volume For-Hire Vehicle (Uber/Lyft) trip parquet files directly into persistent DuckDB tables.",
    codeSnippet: "python scripts/load_raw_to_duckdb.py --source-dir data/raw/",
  },
  {
    id: "dbt_staging",
    stageNumber: "02",
    title: "dbt Staging & Total Fare Cleansing",
    category: "Warehouse",
    engine: "dbt-duckdb 1.11",
    inputs: ["raw_trips"],
    outputs: ["stg_trips", "stg_zones"],
    logicSummary: "Calculate total passenger fare (base + tolls + BCF + sales tax + congestion surcharge + airport fee + tips) and filter outlier fares outside $0 - $1000 range.",
    codeSnippet: "dbt run --select stg_trips stg_zones",
  },
  {
    id: "dbt_marts",
    stageNumber: "03",
    title: "dbt Analytics Mart Aggregation",
    category: "Transformation",
    engine: "dbt-duckdb 1.11",
    inputs: ["stg_trips", "stg_zones"],
    outputs: ["zone_hourly_demand", "zone_fare_stats", "zone_pair_flows"],
    logicSummary: "Aggregate hourly trip volume per zone, calculate average passenger fares, and map directed zone-to-zone pair transit flows.",
    codeSnippet: "dbt run --select marts.zone_hourly_demand marts.zone_fare_stats marts.zone_pair_flows",
  },
  {
    id: "algorithms",
    stageNumber: "04",
    title: "Spatial KD-Tree & PageRank Hubs",
    category: "ML & Algs",
    engine: "Python (from-scratch)",
    inputs: ["zone_centroids.csv", "zone_pair_flows"],
    outputs: ["algorithms/spatial/output/kdtree_benchmark.json", "algorithms/graph/output/pagerank_hubs.json"],
    logicSummary: "Derive 2D Euclidean spatial KD-Tree centroids and PageRank hub scores across transit flow graphs.",
    codeSnippet: "python scripts/generate_algorithm_artifacts.py",
  },
  {
    id: "model_training",
    stageNumber: "05",
    title: "XGBoost Chrono-Split Training",
    category: "ML & Algs",
    engine: "XGBoost Regressor / PyTorch",
    inputs: ["zone_hourly_demand (Jan+Mar train, June test)"],
    outputs: ["xgb_model.json", "fare_xgb_model.json"],
    logicSummary: "Train demand and fare prediction models on chronological whole-timestamp split blocks. Test set held out as entire June block.",
    codeSnippet: "python models/xgboost_model/train_xgboost.py && python models/fare_prediction/train_fare_xgb.py",
  },
  {
    id: "serving",
    stageNumber: "06",
    title: "FastAPI Backend & Lifespan Service",
    category: "Serving",
    engine: "FastAPI / Uvicorn",
    inputs: ["xgb_model.json", "nyc_rides.duckdb"],
    outputs: ["REST API (port 8000)", "WebSocket /chat/stream"],
    logicSummary: "Load model artifacts and momentum features once at startup via lifespan hook (rule 8). Serve REST predictions and RAG chat.",
    codeSnippet: "uvicorn backend.main:app --host 0.0.0.0 --port 8000",
  },
];

export const DataPipeline: React.FC = () => {
  const [selectedId, setSelectedId] = useState<string>("dbt_marts");
  const { data: pipelineStatus } = useQuery({ queryKey: ["pipeline-status"], queryFn: fetchPipelineStatus });
  const { data: warehouseStats } = useQuery({ queryKey: ["warehouse-stats"], queryFn: fetchWarehouseStats });
  const { data: benchmarks } = useQuery({ queryKey: ["algorithm-benchmarks"], queryFn: fetchAlgorithmBenchmarks });
  const { data: modelMetrics } = useQuery({ queryKey: ["model-metrics"], queryFn: fetchModelMetrics });
  const { data: zones } = useQuery({ queryKey: ["zones"], queryFn: fetchZones });

  const dbtStage = (unique_id_contains: string) =>
    pipelineStatus?.stages.find((s) => s.unique_id.includes(unique_id_contains));

  // Real duration/row-count per stage, sourced from actual endpoints. "not tracked"
  // where this repo has no run-log for that stage (see ARCHITECTURE_AUDIT.md).
  const runtime: Record<string, { duration: string; rowCount: string; status: "measured" | "not_tracked" }> = {
    ingestion: {
      duration: "not tracked",
      rowCount: warehouseStats ? `${warehouseStats.row_counts.stg_trips.toLocaleString()} trips` : "...",
      status: "not_tracked",
    },
    dbt_staging: {
      duration: dbtStage("stg_trips") ? `${dbtStage("stg_trips")!.execution_time_seconds.toFixed(2)}s` : "...",
      rowCount: warehouseStats ? `${warehouseStats.row_counts.stg_trips.toLocaleString()} cleaned rows` : "...",
      status: "measured",
    },
    dbt_marts: {
      duration: dbtStage("zone_hourly_demand") ? `${dbtStage("zone_hourly_demand")!.execution_time_seconds.toFixed(2)}s` : "...",
      rowCount: warehouseStats ? `${warehouseStats.row_counts.zone_hourly_demand.toLocaleString()} hourly blocks` : "...",
      status: "measured",
    },
    algorithms: {
      duration: "not tracked",
      rowCount: benchmarks?.kdtree ? `${benchmarks.kdtree.n_zones} zone centroids` : "...",
      status: "not_tracked",
    },
    model_training: {
      duration: "not tracked",
      rowCount: modelMetrics?.demand.xgboost ? `Demand RMSE ${modelMetrics.demand.xgboost.rmse.toFixed(2)}` : "...",
      status: "not_tracked",
    },
    serving: {
      duration: "not tracked",
      rowCount: zones ? `${zones.length} zones served` : "...",
      status: "not_tracked",
    },
  };

  const selectedSpec = PIPELINE_SPEC.find((n) => n.id === selectedId)!;
  const selectedRuntime = runtime[selectedId];

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Title */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-4">
        <div>
          <h1 className="text-lg font-bold text-slate-100 flex items-center gap-2">
            <Workflow className="w-5 h-5 text-brand-400" />
            End-to-End Data Pipeline Architecture
          </h1>
          <p className="text-xs text-slate-400 mt-0.5">
            Node-based pipeline dependency graph with interactive stage execution inspector -- dbt stage
            timings and row counts read live from dbt's run_results.json and the warehouse
          </p>
        </div>
        <div className="flex items-center space-x-2 text-xs font-mono">
          <span className="px-3 py-1 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-semibold flex items-center gap-1.5">
            <CheckCircle2 className="w-3.5 h-3.5" />
            {pipelineStatus?.available ? "dbt Run Available" : "Checking dbt Status..."}
          </span>
        </div>
      </div>

      {/* Dataset Gap Warning Callout */}
      <div className="p-4 rounded-xl bg-amber-500/10 border border-amber-500/20 text-amber-200 text-xs flex items-start space-x-3">
        <AlertTriangle className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
        <div>
          <h4 className="font-bold text-amber-200">Dataset Month Gap Notice (Jan, Mar, Jun 2024 Only)</h4>
          <p className="mt-0.5 text-amber-300/80 leading-relaxed">
            February, April, and May 2024 are missing from the source dataset. Pipeline feature calculations enforce strict 3-block separation to prevent temporal leakage across month gaps.
          </p>
        </div>
      </div>

      {/* Interactive Visual Pipeline Node Flow */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 space-y-4">
        <h3 className="text-xs font-semibold text-slate-300 uppercase tracking-wider font-mono">
          Execution DAG Topology
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-6 gap-3 relative">
          {PIPELINE_SPEC.map((node) => {
            const isSelected = selectedId === node.id;
            const nodeRuntime = runtime[node.id];
            return (
              <button
                key={node.id}
                onClick={() => setSelectedId(node.id)}
                className={`p-4 rounded-xl text-left border transition-all flex flex-col justify-between space-y-3 relative group ${
                  isSelected
                    ? "bg-slate-950 border-brand-500 ring-2 ring-brand-500/30 shadow-lg shadow-brand-500/10"
                    : "bg-slate-950/60 border-slate-800 hover:border-slate-700 hover:bg-slate-950"
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="text-[10px] font-mono font-bold text-brand-400">
                    STAGE {node.stageNumber}
                  </span>
                  <span
                    className={`w-2 h-2 rounded-full ${
                      nodeRuntime?.status === "measured" ? "bg-emerald-400" : "bg-slate-600"
                    }`}
                  />
                </div>

                <div>
                  <h4 className="text-xs font-bold text-slate-100 group-hover:text-brand-300 transition-colors leading-tight">
                    {node.title}
                  </h4>
                  <p className="text-[10px] font-mono text-slate-400 mt-1">{node.engine}</p>
                </div>

                <div className="pt-2 border-t border-slate-800/80 flex items-center justify-between text-[10px] text-slate-400 font-mono">
                  <span>{nodeRuntime?.duration ?? "..."}</span>
                  <ArrowRight className="w-3 h-3 text-slate-600 group-hover:text-brand-400 group-hover:translate-x-0.5 transition-all" />
                </div>
              </button>
            );
          })}
        </div>
      </div>

      {/* Expanded Node Telemetry Inspector */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 space-y-6">
        <div className="flex items-center justify-between border-b border-slate-800 pb-4">
          <div>
            <span className="text-[10px] font-mono font-bold uppercase text-brand-400">
              Stage {selectedSpec.stageNumber} Inspector
            </span>
            <h2 className="text-base font-bold text-slate-100 mt-0.5">{selectedSpec.title}</h2>
          </div>
          <div className="flex items-center space-x-3 text-xs font-mono">
            <span className="text-slate-400">Duration: <strong className="text-slate-200">{selectedRuntime?.duration ?? "..."}</strong></span>
            <span
              className={`px-2.5 py-0.5 rounded text-[10px] font-bold border ${
                selectedRuntime?.status === "measured"
                  ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
                  : "bg-slate-800 text-slate-400 border-slate-700"
              }`}
            >
              {selectedRuntime?.status === "measured" ? "Measured (dbt run_results.json)" : "Not Run-Logged"}
            </span>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Logic & Inputs/Outputs */}
          <div className="lg:col-span-2 space-y-4">
            <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-2">
              <h4 className="text-xs font-semibold text-slate-300">Transformation Logic</h4>
              <p className="text-xs text-slate-300 leading-relaxed">{selectedSpec.logicSummary}</p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-2">
                <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider font-mono">Inputs</h4>
                <ul className="space-y-1 text-xs font-mono text-slate-300">
                  {selectedSpec.inputs.map((inp, i) => (
                    <li key={i} className="flex items-center gap-1.5">
                      <span className="w-1.5 h-1.5 rounded-full bg-brand-400" />
                      <span>{inp}</span>
                    </li>
                  ))}
                </ul>
              </div>

              <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-2">
                <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider font-mono">Outputs</h4>
                <ul className="space-y-1 text-xs font-mono text-emerald-400">
                  {selectedSpec.outputs.map((out, i) => (
                    <li key={i} className="flex items-center gap-1.5">
                      <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                      <span>{out}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </div>

          {/* Execution Command Snippet */}
          <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 flex flex-col justify-between font-mono">
            <div>
              <div className="flex items-center space-x-2 text-xs text-slate-400 font-semibold mb-3">
                <Terminal className="w-4 h-4 text-brand-400" />
                <span>Execution Command</span>
              </div>
              <pre className="p-3 rounded-lg bg-slate-900 border border-slate-800 text-xs text-emerald-400 overflow-x-auto whitespace-pre-wrap">
                {selectedSpec.codeSnippet}
              </pre>
            </div>

            <div className="mt-4 pt-3 border-t border-slate-800/80 text-[11px] text-slate-400 flex justify-between">
              <span>Output:</span>
              <span className="font-bold text-slate-200">{selectedRuntime?.rowCount ?? "..."}</span>
            </div>
          </div>
        </div>

        {/* Node Component Provenance Footer */}
        <div className="pt-3 border-t border-slate-800 flex items-center justify-between text-[10px] font-mono text-slate-400">
          <span>Pipeline Manifest: <strong className="text-brand-400">dbt_project/target/run_results.json</strong></span>
          <span className="text-slate-500">
            {pipelineStatus?.generated_at ? `dbt run: ${pipelineStatus.generated_at}` : "..."}
          </span>
        </div>
      </div>
    </div>
  );
};

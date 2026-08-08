import React from "react";
import { useQuery } from "@tanstack/react-query";
import { FlaskConical } from "lucide-react";
import { fetchModelMetrics } from "../api/client";

const MODEL_NAMES: Record<string, { name: string; arch: string }> = {
  ewma: { name: "EWMA Baseline Alpha Sweep", arch: "EWMA Baseline" },
  linear: { name: "Linear Regression Baseline", arch: "Linear Model" },
  xgboost: { name: "XGBoost Demand Forecast", arch: "XGBoost Regressor" },
  lstm: { name: "LSTM Sequential Demand", arch: "PyTorch LSTM" },
};

export const Experiments: React.FC = () => {
  const { data: metrics, isLoading } = useQuery({ queryKey: ["model-metrics"], queryFn: fetchModelMetrics });

  const demandRuns = metrics
    ? Object.entries(metrics.demand)
        .map(([key, m]) => ({ key, ...MODEL_NAMES[key], rmse: m.rmse, mae: m.mae, n_rows: m.n_rows }))
        .sort((a, b) => a.rmse - b.rmse)
    : [];
  const bestKey = demandRuns[0]?.key;
  const fareRun = metrics?.fare;

  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto">
      {/* Title */}
      <div>
        <h1 className="text-xl font-bold text-slate-100 flex items-center gap-2">
          <FlaskConical className="w-5 h-5 text-brand-400" />
          Model Experiment Tracking Registry
        </h1>
        <p className="text-xs text-slate-400 mt-0.5">
          Read live from GET /models/metrics, which reads models/evaluation/compare_results.json and each model's
          metadata sidecar -- this is a single-process portfolio project, not MLflow
        </p>
      </div>

      <div className="p-5 rounded-xl bg-slate-900 border border-slate-800 space-y-4 flex flex-col justify-between">
        <div>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-950 border-b border-slate-800 text-slate-400 font-semibold uppercase text-[10px] font-mono">
                <tr>
                  <th className="p-3">Experiment Name</th>
                  <th className="p-3">Model Architecture</th>
                  <th className="p-3">Test RMSE</th>
                  <th className="p-3">Test MAE</th>
                  <th className="p-3">Test Rows</th>
                  <th className="p-3">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 text-slate-200 font-mono">
                {isLoading && (
                  <tr>
                    <td colSpan={6} className="p-6 text-center text-slate-500">
                      Loading model metadata...
                    </td>
                  </tr>
                )}
                {demandRuns.map((r) => (
                  <tr key={r.key} className="hover:bg-slate-800/40">
                    <td className="p-3 font-medium text-slate-100 font-sans">{r.name}</td>
                    <td className="p-3 text-slate-300">{r.arch}</td>
                    <td className="p-3 font-bold text-emerald-400">{r.rmse.toFixed(2)}</td>
                    <td className="p-3 text-slate-300">{r.mae.toFixed(2)}</td>
                    <td className="p-3 text-slate-400">{r.n_rows.toLocaleString()}</td>
                    <td className="p-3">
                      <span
                        className={`px-2 py-0.5 rounded text-[10px] font-semibold ${
                          r.key === bestKey
                            ? "bg-brand-500 text-slate-950 font-bold"
                            : "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                        }`}
                      >
                        {r.key === bestKey ? "Best Model" : "Completed"}
                      </span>
                    </td>
                  </tr>
                ))}
                {fareRun && (
                  <tr className="hover:bg-slate-800/40">
                    <td className="p-3 font-medium text-slate-100 font-sans">XGBoost Passenger Fare</td>
                    <td className="p-3 text-slate-300">XGBoost Fare</td>
                    <td className="p-3 font-bold text-emerald-400">{fareRun.metrics.test_rmse.toFixed(2)}</td>
                    <td className="p-3 text-slate-300">{fareRun.metrics.test_mae.toFixed(2)}</td>
                    <td className="p-3 text-slate-400">--</td>
                    <td className="p-3">
                      <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                        Completed
                      </span>
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Provenance Footer */}
        <div className="pt-3 border-t border-slate-800 flex items-center justify-between text-[10px] font-mono text-slate-400">
          <span>Source: <strong className="text-brand-400">GET /models/metrics</strong></span>
          <span className="text-slate-500">Evaluation: June 2024 Holdout Block</span>
        </div>
      </div>
    </div>
  );
};

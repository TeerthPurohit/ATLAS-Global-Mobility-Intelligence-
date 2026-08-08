import React from "react";
import { useQuery } from "@tanstack/react-query";
import { Cpu, Award } from "lucide-react";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";
import { fetchModelMetrics, fetchZones } from "../api/client";

const MODEL_DISPLAY: Record<string, { name: string; type: string; features: string }> = {
  ewma: { name: "EWMA Baseline", type: "Timeseries Baseline", features: "Alpha=0.5 exponential weighting" },
  linear: { name: "Linear Baseline", type: "Linear Regression", features: "Hour/day + rolling lag_1h/24h" },
  lstm: { name: "LSTM Neural Net", type: "PyTorch LSTM (3 Epochs)", features: "Sequence window on CPU" },
  xgboost: { name: "XGBoost", type: "Gradient Boosted Trees", features: "Categorical splits, lags, 7d avg" },
};

export const ModelCenter: React.FC = () => {
  const { data: metrics, isLoading } = useQuery({ queryKey: ["model-metrics"], queryFn: fetchModelMetrics });
  const { data: zones } = useQuery({ queryKey: ["zones"], queryFn: fetchZones });

  const demandModels = metrics
    ? Object.entries(metrics.demand)
        .map(([key, m]) => ({ key, ...MODEL_DISPLAY[key], ...m }))
        .sort((a, b) => a.rmse - b.rmse)
    : [];
  const bestKey = demandModels[0]?.key;
  const xgboostImportances = metrics?.demand?.xgboost?.feature_importances;
  const featureImportanceData = xgboostImportances
    ? Object.entries(xgboostImportances)
        .map(([feature, importance]) => ({ feature, importance }))
        .sort((a, b) => a.importance - b.importance)
    : [];
  const fare = metrics?.fare;

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Title */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-4">
        <div>
          <h1 className="text-lg font-bold text-slate-100 flex items-center gap-2">
            <Cpu className="w-5 h-5 text-brand-400" />
            Model Ladder & Registry Center
          </h1>
          <p className="text-xs text-slate-400 mt-0.5">
            Vertex AI / HuggingFace style registry with honest evaluation on a held-out June 2024 test block
          </p>
        </div>
        {demandModels[0] && (
          <div className="flex items-center space-x-2 text-xs font-mono">
            <span className="px-3 py-1 rounded-full bg-brand-500/10 text-brand-400 border border-brand-500/20 font-semibold flex items-center gap-1.5">
              <Award className="w-3.5 h-3.5" />
              {demandModels[0].name} Selected Best (RMSE {demandModels[0].rmse.toFixed(2)})
            </span>
          </div>
        )}
      </div>

      {/* Model Ladder Registry Grid */}
      {isLoading ? (
        <div className="py-12 text-center text-xs text-slate-500">Loading models/evaluation/compare_results.json...</div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {demandModels.map((m) => {
            const best = m.key === bestKey;
            return (
              <div
                key={m.key}
                className={`p-5 rounded-xl border flex flex-col justify-between transition-all ${
                  best
                    ? "bg-slate-900 border-brand-500 ring-2 ring-brand-500/30 shadow-lg shadow-brand-500/10"
                    : "bg-slate-900 border-slate-800 hover:border-slate-700"
                }`}
              >
                <div>
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] font-mono text-slate-400 font-medium">{m.type}</span>
                    {best && (
                      <span className="px-2 py-0.5 rounded text-[9px] font-mono font-bold bg-brand-500 text-slate-950 uppercase tracking-wider">
                        Best Model
                      </span>
                    )}
                  </div>
                  <h3 className="text-sm font-bold text-slate-100 mt-2">{m.name}</h3>

                  <div className="mt-4 grid grid-cols-2 gap-2 text-center">
                    <div className="p-2.5 rounded-lg bg-slate-950 border border-slate-800">
                      <span className="text-[9px] font-mono text-slate-400 uppercase font-bold">RMSE</span>
                      <div className={`text-base font-extrabold font-mono mt-0.5 ${best ? "text-brand-400" : "text-slate-100"}`}>
                        {m.rmse.toFixed(2)}
                      </div>
                    </div>
                    <div className="p-2.5 rounded-lg bg-slate-950 border border-slate-800">
                      <span className="text-[9px] font-mono text-slate-400 uppercase font-bold">MAE</span>
                      <div className="text-base font-extrabold font-mono text-slate-100 mt-0.5">{m.mae.toFixed(2)}</div>
                    </div>
                  </div>
                </div>

                <div>
                  <div className="mt-4 border-t border-slate-800 pt-3">
                    <span className="text-[10px] font-mono text-slate-400 block">Features:</span>
                    <p className="text-xs text-slate-300 mt-0.5">{m.features}</p>
                  </div>

                  {/* Provenance Footer */}
                  <div className="mt-3 pt-2 border-t border-slate-800/80 flex items-center justify-between text-[10px] font-mono text-slate-400">
                    <span>Latency:</span>
                    <span className="text-brand-400">{m.latency_ms_per_row.toFixed(4)} ms/row</span>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Feature Importance & Fare Model Sidecar */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* XGBoost Feature Importance */}
        <div className="lg:col-span-2 p-5 rounded-xl bg-slate-900 border border-slate-800 space-y-4 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div>
                <h3 className="text-sm font-bold text-slate-100">XGBoost Demand Feature Importance</h3>
                <p className="text-[11px] text-slate-400">Gain-based importance metrics extracted from model booster</p>
              </div>
              <span className="text-[10px] font-mono text-slate-400 bg-slate-950 px-2.5 py-1 rounded border border-slate-800">
                xgboost_demand_v1
              </span>
            </div>

            <div className="h-64 w-full mt-3">
              {featureImportanceData.length ? (
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={featureImportanceData} layout="vertical">
                    <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                    <XAxis type="number" stroke="#64748b" fontSize={11} />
                    <YAxis dataKey="feature" type="category" stroke="#64748b" fontSize={11} width={130} />
                    <Tooltip contentStyle={{ backgroundColor: "#0f172a", borderColor: "#334155", borderRadius: "8px" }} />
                    <Bar dataKey="importance" fill="#0c93eb" radius={[0, 4, 4, 0]} name="Gain Importance" />
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <div className="h-full w-full flex items-center justify-center text-xs text-slate-500">
                  Loading models/xgboost_model/xgb_metadata.json...
                </div>
              )}
            </div>
          </div>

          {/* Component Provenance Footer */}
          <div className="mt-4 pt-3 border-t border-slate-800 flex items-center justify-between text-[10px] font-mono text-slate-400">
            <span>Source: <strong className="text-brand-400">models/xgboost_model/xgb_metadata.json</strong></span>
            <span className="text-slate-500">Pipeline: XGBoost Booster Feature Extractor</span>
          </div>
        </div>

        {/* Fare Model Sidecar Card */}
        <div className="p-5 rounded-xl bg-slate-900 border border-slate-800 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div>
                <h3 className="text-sm font-bold text-slate-100">Fare Model Registry</h3>
                <p className="text-[11px] text-slate-400">models/fare_prediction/fare_xgb_model.json</p>
              </div>
              <span className="px-2 py-0.5 rounded text-[10px] bg-emerald-500/10 text-emerald-400 font-mono font-semibold border border-emerald-500/20">
                XGBoost Fare
              </span>
            </div>

            <div className="mt-4 space-y-3">
              <div className="p-3 rounded-lg bg-slate-950 border border-slate-800 flex justify-between items-center text-xs font-mono">
                <span className="text-slate-400">Test RMSE:</span>
                <span className="font-bold text-emerald-400">
                  {fare ? `$${fare.metrics.test_rmse.toFixed(2)}` : "..."}
                </span>
              </div>
              <div className="p-3 rounded-lg bg-slate-950 border border-slate-800 flex justify-between items-center text-xs font-mono">
                <span className="text-slate-400">Test MAE:</span>
                <span className="font-bold text-slate-100">
                  {fare ? `$${fare.metrics.test_mae.toFixed(2)}` : "..."}
                </span>
              </div>
              <div className="p-3 rounded-lg bg-slate-950 border border-slate-800 flex justify-between items-center text-xs">
                <span className="text-slate-400">Categorical Splits:</span>
                <span className="text-slate-200 font-mono">int32 Dtype Preserved</span>
              </div>
            </div>
          </div>

          <div>
            <div className="p-3 rounded-lg bg-slate-950 border border-slate-800 text-[11px] text-slate-400 mt-4 leading-relaxed font-mono">
              <span className="text-emerald-400 font-semibold">Chronological Split:</span> Whole-timestamp boundary splits prevent data leakage across {zones ? zones.length : "all"} concurrent TLC zones.
            </div>

            {/* Provenance Footer */}
            <div className="mt-3 pt-2.5 border-t border-slate-800 flex items-center justify-between text-[10px] font-mono text-slate-400">
              <span>Source: <strong className="text-emerald-400">models/fare_prediction/fare_xgb_metadata.json</strong></span>
              <span className="text-slate-500">Status: Registered</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

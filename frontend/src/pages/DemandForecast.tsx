import React, { useState } from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { fetchZones, predictDemand, DemandPrediction } from "../api/client";
import { TrendingUp, Cpu, AlertCircle, ArrowRight, ArrowUpRight } from "lucide-react";

export const DemandForecast: React.FC = () => {
  const [zoneId, setZoneId] = useState<number>(132); // Default to JFK Airport
  const [hour, setHour] = useState<number>(8);
  const [dayOfWeek, setDayOfWeek] = useState<number>(1);
  const [prediction, setPrediction] = useState<DemandPrediction | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const { data: zones } = useQuery({ queryKey: ["zones"], queryFn: fetchZones });

  const handlePredict = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const res = await predictDemand(zoneId, hour, dayOfWeek);
      setPrediction(res);
    } catch (err: any) {
      setError(err.message || "Prediction failed");
    } finally {
      setLoading(false);
    }
  };

  const selectedZoneObj = zones?.find((z) => z.zone_id === zoneId);

  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto">
      {/* Title */}
      <div>
        <h1 className="text-xl font-bold text-slate-100 flex items-center gap-2">
          <TrendingUp className="w-5 h-5 text-brand-400" />
          Hourly Demand Forecast Engine
        </h1>
        <p className="text-xs text-slate-400 mt-0.5">
          Predict pickup trip volume per TLC zone using pre-trained XGBoost model artifacts
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Input Form Card */}
        <div className="p-5 rounded-xl bg-slate-900 border border-slate-800 space-y-4 flex flex-col justify-between">
          <div>
            <h2 className="text-sm font-semibold text-slate-200 flex items-center gap-1.5 border-b border-slate-800 pb-3">
              <Cpu className="w-4 h-4 text-brand-400" />
              Forecast Parameters
            </h2>

            <form onSubmit={handlePredict} className="space-y-4 mt-4">
              <div>
                <label className="block text-xs font-medium text-slate-400 mb-1">Target TLC Zone</label>
                <select
                  value={zoneId}
                  onChange={(e) => setZoneId(Number(e.target.value))}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-brand-500"
                >
                  {zones?.map((z) => (
                    <option key={z.zone_id} value={z.zone_id}>
                      #{z.zone_id} - {z.zone} ({z.borough})
                    </option>
                  ))}
                </select>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-slate-400 mb-1">Hour of Day (0-23)</label>
                  <select
                    value={hour}
                    onChange={(e) => setHour(Number(e.target.value))}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-brand-500"
                  >
                    {Array.from({ length: 24 }).map((_, i) => (
                      <option key={i} value={i}>
                        {i.toString().padStart(2, "0")}:00
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-medium text-slate-400 mb-1">Day of Week</label>
                  <select
                    value={dayOfWeek}
                    onChange={(e) => setDayOfWeek(Number(e.target.value))}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-brand-500"
                  >
                    {["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"].map((d, idx) => (
                      <option key={idx} value={idx}>
                        {d}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full py-2.5 px-4 rounded-lg bg-brand-500 hover:bg-brand-400 text-slate-950 text-xs font-semibold shadow-lg shadow-brand-500/20 transition-all flex items-center justify-center space-x-2"
              >
                {loading ? (
                  <span>Executing Inference...</span>
                ) : (
                  <>
                    <span>Compute Forecast</span>
                    <ArrowRight className="w-4 h-4" />
                  </>
                )}
              </button>
            </form>

            {error && (
              <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-xs flex items-start space-x-2 mt-4">
                <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
                <span>{error}</span>
              </div>
            )}
          </div>

          <div className="pt-3 border-t border-slate-800 text-[10px] font-mono text-slate-400 flex items-center justify-between">
            <span>Inference Endpoint:</span>
            <span className="text-brand-400 font-medium">FastAPI GET /predict/demand</span>
          </div>
        </div>

        {/* Prediction Results & Comparison */}
        <div className="lg:col-span-2 p-5 rounded-xl bg-slate-900 border border-slate-800 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div>
                <h3 className="text-sm font-semibold text-slate-100">Model Output & Model Ladder Comparison</h3>
                <p className="text-[11px] text-slate-400">
                  {selectedZoneObj ? `${selectedZoneObj.zone} (${selectedZoneObj.borough})` : "Select zone"}
                </p>
              </div>
              <span className="px-2 py-0.5 rounded text-[10px] bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-mono font-semibold">
                XGBoost Ready
              </span>
            </div>

            {prediction ? (
              <div className="mt-5 space-y-6">
                <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 flex items-center justify-between">
                  <div>
                    <span className="text-xs text-slate-400 font-medium">Predicted Pickup Demand</span>
                    <div className="text-3xl font-extrabold text-slate-100 font-mono mt-1">
                      {Math.round(prediction.predicted_demand)}{" "}
                      <span className="text-xs font-normal text-slate-400">trips/hr</span>
                    </div>
                  </div>
                  <div className="text-right text-xs text-slate-400">
                    <p className="font-semibold text-slate-200 font-mono">{prediction.model}</p>
                    <p>Hour {prediction.hour}:00 · Day {prediction.day_of_week}</p>
                  </div>
                </div>

                <Link
                  to="/models"
                  className="flex items-center justify-between p-3 rounded-lg bg-slate-950 border border-slate-800 text-xs text-slate-400 hover:border-brand-500/50 hover:text-brand-400 transition-colors"
                >
                  <span>
                    Only the deployed XGBoost model runs inference here — see holdout RMSE/MAE for every model in the ladder
                  </span>
                  <ArrowUpRight className="w-4 h-4 shrink-0" />
                </Link>
              </div>
            ) : (
              <div className="py-16 text-center text-xs text-slate-500">
                Submit parameters to trigger XGBoost model inference.
              </div>
            )}
          </div>

          <div>
            <div className="p-3 rounded-lg bg-slate-950 border border-slate-800 text-[11px] text-slate-400 mt-4 font-mono">
              <span className="text-slate-200 font-medium">Feature Store Note:</span> Demand momentum features (lags 1h/24h/168h, EWMA, rolling 7d avg) are served from zone_hourly_demand.
            </div>

            {/* Provenance Footer */}
            <div className="mt-3 pt-2.5 border-t border-slate-800 flex items-center justify-between text-[10px] font-mono text-slate-400">
              <span>Source: <strong className="text-emerald-400">Precomputed Model Artifact: models/xgboost_model/xgb_model.json</strong></span>
              <span className="text-slate-500">Status: Live API Response</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { fetchZones, predictFare, fetchModelMetrics, FarePrediction as FarePredictionResult } from "../api/client";
import { DollarSign, ArrowRight, Calculator, AlertCircle } from "lucide-react";

export const FarePrediction: React.FC = () => {
  const [pickupZone, setPickupZone] = useState<number>(132); // JFK Airport
  const [dropoffZone, setDropoffZone] = useState<number>(230); // Times Sq/Theatre District
  const [hour, setHour] = useState<number>(14);
  const [prediction, setPrediction] = useState<FarePredictionResult | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const { data: zones } = useQuery({ queryKey: ["zones"], queryFn: fetchZones });
  const { data: modelMetrics } = useQuery({ queryKey: ["model-metrics"], queryFn: fetchModelMetrics });
  const fareMetrics = modelMetrics?.fare?.metrics;

  const handlePredict = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const res = await predictFare(pickupZone, dropoffZone, hour);
      setPrediction(res);
    } catch (err: any) {
      setError(err.message || "Fare prediction failed");
    } finally {
      setLoading(false);
    }
  };

  const pickupObj = zones?.find((z) => z.zone_id === pickupZone);
  const dropoffObj = zones?.find((z) => z.zone_id === dropoffZone);

  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto">
      {/* Title */}
      <div>
        <h1 className="text-xl font-bold text-slate-100 flex items-center gap-2">
          <DollarSign className="w-5 h-5 text-emerald-400" />
          Trip Fare Prediction Model
        </h1>
        <p className="text-xs text-slate-400 mt-0.5">
          Estimate HVFHV total passenger fare using pickup/dropoff zone centroids and haversine distance features
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Form Card */}
        <div className="p-5 rounded-xl bg-slate-900 border border-slate-800 space-y-4 flex flex-col justify-between">
          <div>
            <h2 className="text-sm font-semibold text-slate-200 flex items-center gap-1.5 border-b border-slate-800 pb-3">
              <Calculator className="w-4 h-4 text-emerald-400" />
              Route & Fare Input
            </h2>

            <form onSubmit={handlePredict} className="space-y-4 mt-4">
              <div>
                <label className="block text-xs font-medium text-slate-400 mb-1">Pickup Zone</label>
                <select
                  value={pickupZone}
                  onChange={(e) => setPickupZone(Number(e.target.value))}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-emerald-500"
                >
                  {zones?.map((z) => (
                    <option key={z.zone_id} value={z.zone_id}>
                      #{z.zone_id} - {z.zone} ({z.borough})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-400 mb-1">Dropoff Zone</label>
                <select
                  value={dropoffZone}
                  onChange={(e) => setDropoffZone(Number(e.target.value))}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-emerald-500"
                >
                  {zones?.map((z) => (
                    <option key={z.zone_id} value={z.zone_id}>
                      #{z.zone_id} - {z.zone} ({z.borough})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-400 mb-1">Departure Hour (0-23)</label>
                <select
                  value={hour}
                  onChange={(e) => setHour(Number(e.target.value))}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-emerald-500"
                >
                  {Array.from({ length: 24 }).map((_, i) => (
                    <option key={i} value={i}>
                      {i.toString().padStart(2, "0")}:00
                    </option>
                  ))}
                </select>
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full py-2.5 px-4 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold shadow-lg shadow-emerald-500/20 transition-all flex items-center justify-center space-x-2"
              >
                {loading ? (
                  <span>Calculating Fare...</span>
                ) : (
                  <>
                    <span>Estimate Total Fare</span>
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

          <div className="pt-3 border-t border-slate-800 text-[10px] font-mono text-slate-400 flex justify-between">
            <span>Endpoint:</span>
            <span className="text-emerald-400">FastAPI GET /predict/fare</span>
          </div>
        </div>

        {/* Prediction Results */}
        <div className="lg:col-span-2 p-5 rounded-xl bg-slate-900 border border-slate-800 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div>
                <h3 className="text-sm font-semibold text-slate-100">Estimated Passenger Fare</h3>
                <p className="text-[11px] text-slate-400">
                  {pickupObj?.zone} → {dropoffObj?.zone}
                </p>
              </div>
              <span className="px-2 py-0.5 rounded text-[10px] bg-emerald-500/10 text-emerald-400 font-mono font-semibold border border-emerald-500/20">
                XGBoost Regressor
              </span>
            </div>

            {prediction ? (
              <div className="mt-6 space-y-6">
                <div className="p-6 rounded-xl bg-slate-950 border border-slate-800 text-center">
                  <span className="text-xs text-slate-400 font-medium">Estimated Total Fare</span>
                  <div className="text-4xl font-extrabold text-emerald-400 font-mono mt-2">
                    ${prediction.predicted_fare.toFixed(2)}
                  </div>
                  <p className="text-xs text-slate-400 font-mono mt-2">
                    {fareMetrics
                      ? `Evaluated on June holdout: RMSE $${fareMetrics.test_rmse.toFixed(2)} / MAE $${fareMetrics.test_mae.toFixed(2)}`
                      : "Loading holdout metrics..."}
                  </p>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 font-mono">
                    <span className="text-xs text-slate-400 font-medium">Pickup Borough</span>
                    <p className="text-sm font-semibold text-slate-200 mt-1">{pickupObj?.borough}</p>
                  </div>
                  <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 font-mono">
                    <span className="text-xs text-slate-400 font-medium">Dropoff Borough</span>
                    <p className="text-sm font-semibold text-slate-200 mt-1">{dropoffObj?.borough}</p>
                  </div>
                </div>
              </div>
            ) : (
              <div className="py-20 text-center text-xs text-slate-500">
                Select pickup and dropoff zones to run fare estimation model.
              </div>
            )}
          </div>

          <div>
            <div className="p-3 rounded-lg bg-slate-950 border border-slate-800 text-[11px] text-slate-400 mt-4 font-mono">
              <span className="text-slate-200 font-medium">HVFHV Fare Schema:</span> Includes base passenger fare, tolls, BCF, sales tax, congestion surcharge, airport fees, and passenger tips.
            </div>

            {/* Provenance Footer */}
            <div className="mt-3 pt-2.5 border-t border-slate-800 flex items-center justify-between text-[10px] font-mono text-slate-400">
              <span>Source: <strong className="text-emerald-400">Precomputed Model Artifact: models/fare_prediction/fare_xgb_model.json</strong></span>
              <span className="text-slate-500">Status: Live API Response</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

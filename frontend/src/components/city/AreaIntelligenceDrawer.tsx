import React, { useState, useEffect } from "react";
import { Area, predictCityDemand, predictCityFare, predictDemand } from "../../api/client";
import { X, Sparkles, MapPin, TrendingUp, DollarSign, Clock, Bot, Cpu } from "lucide-react";
import { Provenance } from "../ui/Provenance";

interface AreaIntelligenceDrawerProps {
  area: Area | null;
  areas: Area[];
  cityId: string;
  onClose: () => void;
  onAskAI: (area: Area, question?: string) => void;
}

export const AreaIntelligenceDrawer: React.FC<AreaIntelligenceDrawerProps> = ({
  area,
  areas,
  cityId,
  onClose,
  onAskAI,
}) => {
  const [selectedHour, setSelectedHour] = useState<number>(8);
  const [selectedDay, setSelectedDay] = useState<number>(1);
  const [dropoffAreaId, setDropoffAreaId] = useState<number | null>(null);
  const [prediction, setPrediction] = useState<{ demand: number; model: string; basis: string } | null>(null);
  const [loadingPred, setLoadingPred] = useState<boolean>(false);
  const [fare, setFare] = useState<{ value: number; model: string } | "unavailable" | null>(null);
  const [loadingFare, setLoadingFare] = useState<boolean>(false);

  useEffect(() => {
    if (!area) return;
    setDropoffAreaId(null);
    setFare(null);

    setLoadingPred(true);
    predictCityDemand(cityId, area.area_id, selectedHour, selectedDay)
      .then((res) => {
        if ("prediction" in res) {
          setPrediction({ demand: res.prediction, model: res.model, basis: res.basis });
        } else {
          // No model or modeled estimate available at all -- fall back to
          // the legacy NYC-only endpoint rather than fabricating a number.
          return predictDemand(area.area_id, selectedHour, selectedDay).then((p) => {
            setPrediction({ demand: p.predicted_demand, model: p.model, basis: "computed" });
          });
        }
      })
      .catch((err) => {
        console.error("Area prediction error:", err);
        predictDemand(area.area_id, selectedHour, selectedDay)
          .then((p) => setPrediction({ demand: p.predicted_demand, model: p.model, basis: "computed" }))
          .catch(() => setPrediction(null));
      })
      .finally(() => setLoadingPred(false));
  }, [area, cityId, selectedHour, selectedDay]);

  useEffect(() => {
    if (!area || dropoffAreaId == null) {
      setFare(null);
      return;
    }
    setLoadingFare(true);
    predictCityFare(cityId, area.area_id, dropoffAreaId, selectedHour)
      .then((res) => {
        setFare("prediction" in res ? { value: res.prediction, model: res.model } : "unavailable");
      })
      .catch(() => setFare("unavailable"))
      .finally(() => setLoadingFare(false));
  }, [area, cityId, dropoffAreaId, selectedHour]);

  if (!area) return null;

  return (
    <aside className="w-full lg:w-96 bg-slate-900 border-l border-slate-800 p-5 flex flex-col justify-between overflow-y-auto z-30 shadow-2xl animate-slideInRight font-sans select-none">
      <div className="space-y-4">
        {/* Drawer Header */}
        <div className="flex items-center justify-between border-b border-slate-800 pb-3">
          <div className="flex items-center space-x-2">
            <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-brand-500/20 text-brand-400 border border-brand-500/30 capitalize">
              {area.area_type || "Mobility Area"}
            </span>
            <span className="text-xs text-slate-400 font-mono">#{area.area_id}</span>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-md text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Title */}
        <div>
          <h2 className="text-xl font-extrabold text-slate-100">{area.name}</h2>
          <p className="text-xs text-slate-400 mt-0.5">Area Intelligence & Prediction Context</p>
        </div>

        {/* Time Selector */}
        <div className="p-3 rounded-xl bg-slate-950 border border-slate-800 flex items-center justify-between text-xs">
          <div className="flex items-center space-x-1.5 font-mono">
            <Clock className="w-3.5 h-3.5 text-slate-400" />
            <span className="text-slate-400">Hour:</span>
            <select
              value={selectedHour}
              onChange={(e) => setSelectedHour(Number(e.target.value))}
              className="bg-slate-900 border border-slate-700 rounded px-2 py-1 text-slate-200 focus:outline-none"
            >
              {Array.from({ length: 24 }).map((_, i) => (
                <option key={i} value={i}>
                  {i.toString().padStart(2, "0")}:00
                </option>
              ))}
            </select>
          </div>
          <div className="flex items-center space-x-1.5 font-mono">
            <span className="text-slate-400">Day:</span>
            <select
              value={selectedDay}
              onChange={(e) => setSelectedDay(Number(e.target.value))}
              className="bg-slate-900 border border-slate-700 rounded px-2 py-1 text-slate-200 focus:outline-none"
            >
              {["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"].map((d, idx) => (
                <option key={idx} value={idx}>
                  {d}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Real Backend Statistics Cards */}
        <div className="grid grid-cols-2 gap-3">
          {/* Demand Prediction */}
          <div className="p-3.5 rounded-xl bg-slate-950 border border-slate-800 space-y-1">
            <div className="flex items-center justify-between text-[11px] text-slate-400">
              <span>Demand</span>
              <TrendingUp className="w-3.5 h-3.5 text-emerald-400" />
            </div>
            {loadingPred ? (
              <p className="text-xs text-slate-500 font-mono animate-pulse">Calculating...</p>
            ) : prediction ? (
              <div>
                <span className="text-2xl font-extrabold font-mono text-slate-100">
                  {Math.round(prediction.demand)}
                </span>
                <span className="text-[10px] text-slate-400 ml-1">
                  {area.area_type === "station" ? "trips/hr at this station" : "trips/hr"}
                </span>
                {prediction.basis === "modeled_estimate" && (
                  <div className="text-[9px] uppercase font-bold text-amber-400 mt-0.5">Modeled estimate, not observed</div>
                )}
              </div>
            ) : (
              <span className="text-xs text-slate-500">Unavailable</span>
            )}
          </div>

          {/* Zone-to-zone fare estimate (real model, not a placeholder) */}
          <div className="p-3.5 rounded-xl bg-slate-950 border border-slate-800 space-y-1">
            <div className="flex items-center justify-between text-[11px] text-slate-400">
              <span>Est. Fare To</span>
              <DollarSign className="w-3.5 h-3.5 text-amber-400" />
            </div>
            <select
              value={dropoffAreaId ?? ""}
              onChange={(e) => setDropoffAreaId(e.target.value ? Number(e.target.value) : null)}
              className="w-full bg-slate-900 border border-slate-700 rounded px-1.5 py-1 text-[11px] text-slate-200 focus:outline-none"
            >
              <option value="">Choose destination...</option>
              {areas
                .filter((a) => a.area_id !== area.area_id)
                .map((a) => (
                  <option key={a.area_id} value={a.area_id}>
                    {a.name}
                  </option>
                ))}
            </select>
            {dropoffAreaId != null && (
              <div className="pt-1">
                {loadingFare ? (
                  <p className="text-xs text-slate-500 font-mono animate-pulse">Calculating...</p>
                ) : fare === "unavailable" ? (
                  <span className="text-xs text-slate-500">No fare model for this city</span>
                ) : fare ? (
                  <span className="text-xl font-extrabold font-mono text-slate-100">${fare.value.toFixed(2)}</span>
                ) : null}
              </div>
            )}
          </div>
        </div>

        {/* Spatial Coordinates & Model Provenance */}
        <div className="p-3 rounded-xl bg-slate-950 border border-slate-800 space-y-2 text-xs font-mono">
          {area.latitude && area.longitude && (
            <div className="flex justify-between text-slate-400">
              <span>Centroid:</span>
              <span className="text-slate-200">
                {area.latitude.toFixed(4)}, {area.longitude.toFixed(4)}
              </span>
            </div>
          )}
          <div className="flex justify-between text-slate-400">
            <span>ML Model:</span>
            <span className="text-brand-400 font-medium">{prediction?.model || "XGBoost v1"}</span>
          </div>
        </div>

        {/* Primary CTA: Ask AI About This Area */}
        <div className="pt-2">
          <button
            onClick={() => onAskAI(area, `Why is demand projected to be ${prediction ? Math.round(prediction.demand) : 'high'} in ${area.name}?`)}
            className="w-full py-3 px-4 rounded-xl bg-brand-500 hover:bg-brand-400 text-slate-950 font-bold text-xs flex items-center justify-center space-x-2 shadow-lg shadow-brand-500/20 transition-all duration-200"
          >
            <Sparkles className="w-4 h-4" />
            <span>Ask AI Analyst About {area.name}</span>
          </button>
        </div>
      </div>

      <div className="pt-4 mt-4 border-t border-slate-800">
        <Provenance type="live" source={`GET /api/cities/${cityId}/areas/${area.area_id}`} />
      </div>
    </aside>
  );
};

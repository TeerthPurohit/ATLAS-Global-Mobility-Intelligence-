import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { MapContainer, TileLayer, CircleMarker, Tooltip as LeafletTooltip } from "react-leaflet";
import { fetchZones, predictDemand, sendChatMessage, Zone, DemandPrediction } from "../api/client";
import { MapPin, Sparkles, X } from "lucide-react";
import { Provenance } from "../components/ui/Provenance";

// Manhattan gets the medallion-yellow accent — the borough the yellow cab
// livery actually belongs to. Outer boroughs use the "boro taxi" green
// family (green street-hail livery, introduced 2013) instead of an
// arbitrary rainbow, so the legend means something rather than just
// separating categories.
const BOROUGH_COLORS: Record<string, string> = {
  Manhattan: "#f7b733",
  Queens: "#2dd4a7",
  Brooklyn: "#1f9d7c",
  Bronx: "#c9782e",
  "Staten Island": "#e2574c",
  "EWR / Unknown": "#64748b",
};

export const NYCMap: React.FC = () => {
  const [selectedZone, setSelectedZone] = useState<Zone | null>(null);
  const [selectedHour, setSelectedHour] = useState<number>(8);
  const [selectedDay, setSelectedDay] = useState<number>(1);
  const [prediction, setPrediction] = useState<DemandPrediction | null>(null);
  const [loadingPred, setLoadingPred] = useState<boolean>(false);
  const [insight, setInsight] = useState<string | null>(null);
  const [insightError, setInsightError] = useState<boolean>(false);
  const [loadingInsight, setLoadingInsight] = useState<boolean>(false);

  const { data: zones } = useQuery({
    queryKey: ["zones"],
    queryFn: fetchZones,
  });

  const handleZoneClick = async (zone: Zone) => {
    setSelectedZone(zone);
    setLoadingPred(true);
    setLoadingInsight(true);
    setInsight(null);
    setInsightError(false);
    try {
      const res = await predictDemand(zone.zone_id, selectedHour, selectedDay);
      setPrediction(res);
    } catch (err) {
      console.error(err);
      setPrediction(null);
    } finally {
      setLoadingPred(false);
    }
    try {
      const res = await sendChatMessage(`Tell me about zone ${zone.zone_id} (${zone.zone})`);
      setInsight(res.answer);
    } catch (err) {
      console.error(err);
      setInsightError(true);
    } finally {
      setLoadingInsight(false);
    }
  };

  return (
    <div className="h-[calc(100vh-4rem)] flex flex-col lg:flex-row relative bg-slate-950 overflow-hidden">
      {/* Main Map Viewport */}
      <div className="flex-1 h-full relative">
        {/* Controls Floating Bar */}
        <div className="absolute top-4 left-4 z-[1000] bg-slate-900/90 backdrop-blur-md border border-slate-800 p-3 rounded-xl shadow-xl flex items-center space-x-3 text-xs">
          <div className="flex items-center space-x-1.5 font-mono">
            <span className="text-slate-400 font-medium">Hour:</span>
            <select
              value={selectedHour}
              onChange={(e) => setSelectedHour(Number(e.target.value))}
              className="bg-slate-950 border border-slate-800 rounded px-2 py-1 text-slate-200 focus:outline-none focus:ring-2 focus:ring-brand-500/40"
            >
              {Array.from({ length: 24 }).map((_, i) => (
                <option key={i} value={i}>
                  {i.toString().padStart(2, "0")}:00
                </option>
              ))}
            </select>
          </div>
          <div className="flex items-center space-x-1.5 font-mono">
            <span className="text-slate-400 font-medium">Day:</span>
            <select
              value={selectedDay}
              onChange={(e) => setSelectedDay(Number(e.target.value))}
              className="bg-slate-950 border border-slate-800 rounded px-2 py-1 text-slate-200 focus:outline-none focus:ring-2 focus:ring-brand-500/40"
            >
              {["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"].map((d, idx) => (
                <option key={idx} value={idx}>
                  {d}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Legend Overlay */}
        <div className="absolute bottom-6 left-4 z-[1000] bg-slate-900/90 backdrop-blur-md border border-slate-800 p-3 rounded-xl shadow-xl text-xs space-y-1.5 hidden sm:block font-mono">
          <p className="font-semibold text-slate-300 mb-1">Borough Palette</p>
          {Object.entries(BOROUGH_COLORS).map(([b, color]) => (
            <div key={b} className="flex items-center space-x-2">
              <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: color }} />
              <span className="text-slate-400">{b}</span>
            </div>
          ))}
        </div>

        {/* Leaflet Map */}
        <MapContainer
          center={[40.7128, -74.006]}
          zoom={11}
          style={{ width: "100%", height: "100%", background: "#020617" }}
          scrollWheelZoom={true}
        >
          <TileLayer
            attribution='&copy; <a href="https://carto.com/">CARTO</a>'
            url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
          />
          {zones?.map((z) => (
            <CircleMarker
              key={z.zone_id}
              center={[z.latitude, z.longitude]}
              radius={selectedZone?.zone_id === z.zone_id ? 9 : 5}
              pathOptions={{
                color: selectedZone?.zone_id === z.zone_id ? "#ffffff" : BOROUGH_COLORS[z.borough] || "#64748b",
                fillColor: BOROUGH_COLORS[z.borough] || "#64748b",
                fillOpacity: 0.8,
                weight: selectedZone?.zone_id === z.zone_id ? 3 : 1,
              }}
              eventHandlers={{
                click: () => handleZoneClick(z),
              }}
            >
              <LeafletTooltip direction="top" offset={[0, -5]} opacity={1}>
                <div className="text-xs font-semibold">{z.zone} ({z.borough})</div>
              </LeafletTooltip>
            </CircleMarker>
          ))}
        </MapContainer>
      </div>

      {/* Side Panel: Zone Inspector */}
      {selectedZone ? (
        <aside className="w-full lg:w-96 bg-slate-900 border-l border-slate-800 p-5 flex flex-col justify-between overflow-y-auto z-20 shadow-2xl">
          <div>
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center space-x-2">
                <div
                  className="w-3.5 h-3.5 rounded-full"
                  style={{ backgroundColor: BOROUGH_COLORS[selectedZone.borough] || "#64748b" }}
                />
                <span className="text-xs uppercase font-bold text-slate-400 font-mono">{selectedZone.borough}</span>
              </div>
              <button
                onClick={() => setSelectedZone(null)}
                className="p-1 rounded-md text-slate-400 hover:text-white hover:bg-slate-800"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="mt-4">
              <h2 className="text-lg font-bold text-slate-100">{selectedZone.zone}</h2>
              <p className="text-xs text-slate-400 font-mono mt-0.5">Zone ID: #{selectedZone.zone_id}</p>
            </div>

            {/* Coordinates & KD-Tree Centroid */}
            <div className="mt-4 p-3 rounded-xl bg-slate-950 border border-slate-800 space-y-2 text-xs">
              <div className="flex justify-between text-slate-400 font-mono">
                <span>Centroid Latitude:</span>
                <span className="font-mono text-slate-200">{selectedZone.latitude.toFixed(5)}</span>
              </div>
              <div className="flex justify-between text-slate-400 font-mono">
                <span>Centroid Longitude:</span>
                <span className="font-mono text-slate-200">{selectedZone.longitude.toFixed(5)}</span>
              </div>
              <div className="flex justify-between text-slate-400 font-mono">
                <span>Lookup Engine:</span>
                <span className="text-brand-400 font-medium">KD-Tree 2D Mapped</span>
              </div>
            </div>

            {/* Live Model Prediction */}
            <div className="mt-4 p-4 rounded-xl bg-slate-950 border border-slate-800">
              <div className="flex items-center justify-between">
                <span className="text-xs font-medium text-slate-400">Model Demand Forecast</span>
                <span className="px-2 py-0.5 rounded text-[10px] bg-brand-500/20 text-brand-400 border border-brand-500/30 font-mono">
                  {prediction ? prediction.model : "XGBoost"}
                </span>
              </div>

              {loadingPred ? (
                <div className="mt-3 py-4 text-center text-xs text-slate-500 animate-pulse font-mono">
                  Querying backend model service...
                </div>
              ) : prediction ? (
                <div className="mt-3">
                  <div className="text-3xl font-extrabold text-slate-100 font-mono">
                    {Math.round(prediction.predicted_demand)}{" "}
                    <span className="text-xs font-normal text-slate-400">trips/hr</span>
                  </div>
                  <p className="text-[11px] text-slate-400 mt-1 font-mono">
                    At {selectedHour.toString().padStart(2, "0")}:00 on Day {selectedDay}
                  </p>
                </div>
              ) : (
                <div className="mt-3 text-xs text-slate-400 font-mono">Select parameters to re-predict.</div>
              )}
            </div>

            {/* Generated Insights */}
            <div className="mt-4 p-4 rounded-xl bg-slate-950 border border-slate-800">
              <div className="flex items-center space-x-1.5 text-xs font-semibold text-slate-200 mb-2">
                <Sparkles className="w-3.5 h-3.5 text-brand-400" />
                <span>Zone RAG Insight</span>
              </div>
              {loadingInsight ? (
                <p className="text-xs text-slate-500 font-mono animate-pulse">Querying hybrid RAG pipeline...</p>
              ) : insightError ? (
                <p className="text-xs text-red-400">Unavailable -- RAG backend did not respond.</p>
              ) : insight ? (
                <p className="text-xs text-slate-300 leading-relaxed">{insight}</p>
              ) : (
                <p className="text-xs text-slate-500">No insight generated yet.</p>
              )}
            </div>
          </div>

          <div>
            <div className="mt-4 pt-3 border-t border-slate-800">
              <a
                href={`/analyst`}
                className="w-full py-2 px-3 rounded-lg bg-brand-500 hover:bg-brand-400 text-slate-950 text-xs font-semibold flex items-center justify-center space-x-1.5 transition-colors"
              >
                <Sparkles className="w-3.5 h-3.5" />
                <span>Ask AI Analyst About Zone #{selectedZone.zone_id}</span>
              </a>
            </div>

            <Provenance type="live" source="GET /zones" />
          </div>
        </aside>
      ) : (
        <div className="hidden lg:flex w-80 bg-slate-900 border-l border-slate-800 p-6 flex-col items-center justify-center text-center">
          <MapPin className="w-10 h-10 text-slate-600 mb-3" />
          <h3 className="text-sm font-semibold text-slate-300">Select a TLC Zone</h3>
          <p className="text-xs text-slate-500 mt-1">
            Click any zone marker on the NYC map to inspect centroid spatial data and demand forecast.
          </p>
        </div>
      )}
    </div>
  );
};

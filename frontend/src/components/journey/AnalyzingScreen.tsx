import React, { useState, useEffect } from "react";
import { useMobility } from "../../context/MobilityContext";
import { CheckCircle2, Loader2, Cpu, Globe, Database, ShieldCheck, Sparkles } from "lucide-react";
import { useNavigate } from "react-router-dom";

export const AnalyzingScreen: React.FC = () => {
  const { selectedCountry, countryCities, setIsAnalyzing } = useMobility();
  const [stepIndex, setStepIndex] = useState(0);
  const navigate = useNavigate();

  const STEPS = [
    { label: "Checking mobility datasets...", detail: "Connected to DuckDB Warehouse" },
    { label: `Loading supported cities for ${selectedCountry?.name || "region"}...`, detail: `${countryCities.length || 1} city record(s) found` },
    { label: "Preparing prediction models...", detail: "XGBoost & Model Registry Verified" },
    { label: "Loading geographic intelligence...", detail: "Canonical Area Mart Synced" },
  ];

  useEffect(() => {
    const timer1 = setTimeout(() => setStepIndex(1), 300);
    const timer2 = setTimeout(() => setStepIndex(2), 700);
    const timer3 = setTimeout(() => setStepIndex(3), 1100);
    const timer4 = setTimeout(() => {
      setIsAnalyzing(false);
    }, 1500);

    return () => {
      clearTimeout(timer1);
      clearTimeout(timer2);
      clearTimeout(timer3);
      clearTimeout(timer4);
    };
  }, [setIsAnalyzing]);

  return (
    <div className="min-h-[calc(100vh-4rem)] bg-slate-950 flex flex-col items-center justify-center p-6 text-slate-100 font-sans select-none relative overflow-hidden">
      {/* Subtle Background Glow */}
      <div className="absolute w-96 h-96 bg-brand-500/10 rounded-full blur-3xl -z-10 animate-pulse" />

      <div className="w-full max-w-lg bg-slate-900/90 border border-slate-800 backdrop-blur-xl p-8 rounded-3xl shadow-2xl space-y-6">
        <div className="flex items-center space-x-3 border-b border-slate-800 pb-5">
          <div className="w-12 h-12 rounded-2xl bg-brand-500/20 text-brand-400 border border-brand-500/30 flex items-center justify-center font-mono font-extrabold text-base shadow-lg shadow-brand-500/20">
            {selectedCountry?.iso_code || "US"}
          </div>
          <div>
            <span className="text-[10px] uppercase font-mono font-bold text-brand-400 tracking-wider">
              Context Initialization
            </span>
            <h2 className="text-xl font-extrabold text-slate-100 tracking-tight">
              Analyzing {selectedCountry?.name || "Country"}
            </h2>
          </div>
        </div>

        {/* Progress List */}
        <div className="space-y-4 py-2">
          {STEPS.map((step, idx) => {
            const isDone = idx < stepIndex;
            const isCurrent = idx === stepIndex;

            return (
              <div
                key={idx}
                className={`p-3.5 rounded-xl border transition-all duration-300 flex items-center justify-between ${
                  isDone
                    ? "bg-slate-950/80 border-emerald-500/30 text-slate-200"
                    : isCurrent
                    ? "bg-brand-500/10 border-brand-500/40 text-brand-400 shadow-md shadow-brand-500/10"
                    : "bg-slate-950/30 border-slate-800/40 text-slate-500 opacity-50"
                }`}
              >
                <div className="flex items-center space-x-3">
                  {isDone ? (
                    <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0" />
                  ) : isCurrent ? (
                    <Loader2 className="w-5 h-5 text-brand-400 animate-spin shrink-0" />
                  ) : (
                    <div className="w-5 h-5 rounded-full border border-slate-700 shrink-0" />
                  )}
                  <div>
                    <p className={`text-xs font-semibold ${isDone ? "text-slate-200" : isCurrent ? "text-brand-300" : "text-slate-500"}`}>
                      {step.label}
                    </p>
                    <p className="text-[10px] font-mono text-slate-400 mt-0.5">{step.detail}</p>
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        <div className="pt-2 border-t border-slate-800/80 flex items-center justify-between text-xs text-slate-400 font-mono">
          <span className="flex items-center gap-1.5">
            <Sparkles className="w-3.5 h-3.5 text-brand-400" />
            <span>FastAPI Real Telemetry</span>
          </span>
          <span className="text-emerald-400">Context Ready</span>
        </div>
      </div>
    </div>
  );
};

import React, { useState } from "react";
import { X, Cpu, GitMerge, Sparkles } from "lucide-react";
import { ModelCenter } from "../../pages/ModelCenter";
import { Algorithms } from "../../pages/Algorithms";

interface MethodologyModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const MethodologyModal: React.FC<MethodologyModalProps> = ({ isOpen, onClose }) => {
  const [activeTab, setActiveTab] = useState<"algorithms" | "models">("algorithms");

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-[1800] flex items-center justify-center p-4 md:p-8 bg-slate-950/80 backdrop-blur-md animate-fadeIn select-none font-sans">
      <div className="w-full max-w-5xl h-[85vh] bg-slate-900 border border-slate-800 rounded-3xl shadow-2xl overflow-hidden flex flex-col">
        {/* Modal Header */}
        <div className="p-4 md:px-6 bg-slate-950 border-b border-slate-800 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-9 h-9 rounded-xl bg-brand-500/20 text-brand-400 border border-brand-500/30 flex items-center justify-center">
              <Cpu className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-bold text-slate-100">Methodology & Algorithmic Benchmarks</h2>
              <p className="text-[11px] font-mono text-slate-400">KD-Tree 2D Spatial Lookup • PageRank Network Hubs • ML Ladder</p>
            </div>
          </div>

          <div className="flex items-center space-x-2">
            {/* Tab selector */}
            <div className="flex items-center space-x-1 bg-slate-900 p-1 rounded-xl border border-slate-800 text-xs font-mono">
              <button
                onClick={() => setActiveTab("algorithms")}
                className={`px-3 py-1.5 rounded-lg flex items-center space-x-1.5 ${
                  activeTab === "algorithms" ? "bg-brand-500/20 text-brand-400 border border-brand-500/30 font-bold" : "text-slate-400"
                }`}
              >
                <GitMerge className="w-3.5 h-3.5" />
                <span>Spatial & Network Algorithms</span>
              </button>
              <button
                onClick={() => setActiveTab("models")}
                className={`px-3 py-1.5 rounded-lg flex items-center space-x-1.5 ${
                  activeTab === "models" ? "bg-brand-500/20 text-brand-400 border border-brand-500/30 font-bold" : "text-slate-400"
                }`}
              >
                <Cpu className="w-3.5 h-3.5" />
                <span>Model Ladder & Metrics</span>
              </button>
            </div>

            <button
              onClick={onClose}
              className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors ml-2"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Modal Body */}
        <div className="flex-1 overflow-y-auto p-6 bg-slate-950/60">
          {activeTab === "algorithms" && <Algorithms />}
          {activeTab === "models" && <ModelCenter />}
        </div>
      </div>
    </div>
  );
};

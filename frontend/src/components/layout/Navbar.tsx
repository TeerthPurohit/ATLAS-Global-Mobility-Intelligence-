import React, { useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  Globe,
  Search,
  Database,
  Cpu,
  FileText,
  RefreshCw,
  Layers,
  Sparkles,
  ChevronRight,
  Command,
} from "lucide-react";
import { fetchHealth } from "../../api/client";
import { useMobility } from "../../context/MobilityContext";
import { CommandPalette } from "../navigation/CommandPalette";
import { DataTransparencyModal } from "../modals/DataTransparencyModal";
import { MethodologyModal } from "../modals/MethodologyModal";

interface NavbarProps {
  onRefresh?: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({ onRefresh }) => {
  const location = useLocation();
  const navigate = useNavigate();
  const { selectedCountry, selectedCity, resetToWorld } = useMobility();
  const [refreshing, setRefreshing] = useState(false);

  const [commandPaletteOpen, setCommandPaletteOpen] = useState(false);
  const [dataModalOpen, setDataModalOpen] = useState(false);
  const [methodologyModalOpen, setMethodologyModalOpen] = useState(false);

  const { data: health } = useQuery({
    queryKey: ["health"],
    queryFn: fetchHealth,
    refetchInterval: 30_000,
  });

  const handleRefreshClick = () => {
    setRefreshing(true);
    onRefresh?.();
    setTimeout(() => setRefreshing(false), 800);
  };

  return (
    <header className="h-16 bg-slate-900 border-b border-slate-800 px-4 md:px-6 flex items-center justify-between shrink-0 z-30 select-none font-sans">
      {/* Left: Product Brand Identity & Spatial Breadcrumbs */}
      <div className="flex items-center space-x-4">
        <Link to="/" onClick={resetToWorld} className="flex items-center space-x-2.5 group">
          <div className="h-9 w-9 rounded-xl bg-brand-500 flex items-center justify-center text-slate-950 font-bold shadow-lg shadow-brand-500/20 group-hover:scale-105 transition-transform">
            <Globe className="w-5 h-5" />
          </div>
          <div>
            <h1 className="text-sm font-extrabold text-slate-100 tracking-tight leading-none flex items-center gap-1.5">
              ATLAS <span className="text-brand-400 font-mono text-xs font-semibold">MOBILITY</span>
            </h1>
            <p className="text-[10px] uppercase font-mono font-semibold text-slate-400 mt-0.5 tracking-wider">
              Global Mobility Intelligence
            </p>
          </div>
        </Link>

        {/* Global Location Breadcrumb */}
        <div className="hidden sm:flex items-center space-x-2 pl-4 border-l border-slate-800 text-xs">
          <button
            onClick={() => {
              resetToWorld();
              navigate("/");
            }}
            className={`font-semibold transition-colors ${
              !selectedCountry ? "text-brand-400" : "text-slate-400 hover:text-slate-200"
            }`}
          >
            World
          </button>

          {selectedCountry && (
            <>
              <ChevronRight className="w-3.5 h-3.5 text-slate-600" />
              <span className="font-mono text-slate-300 bg-slate-800 px-2 py-0.5 rounded text-[11px]">
                {selectedCountry.iso_code}
              </span>
            </>
          )}

          {selectedCity && (
            <>
              <ChevronRight className="w-3.5 h-3.5 text-slate-600" />
              <span className="font-bold text-slate-100">{selectedCity.name}</span>
            </>
          )}
        </div>
      </div>

      {/* Center: Command Palette Trigger */}
      <div className="hidden md:flex items-center">
        <button
          onClick={() => setCommandPaletteOpen(true)}
          className="flex items-center space-x-3 px-4 py-2 rounded-xl bg-slate-950 border border-slate-800 hover:border-slate-700 text-xs text-slate-400 hover:text-slate-200 transition-all shadow-inner w-64 lg:w-80 justify-between"
        >
          <div className="flex items-center space-x-2">
            <Search className="w-4 h-4 text-brand-400" />
            <span>Search country or city...</span>
          </div>
          <kbd className="px-1.5 py-0.5 text-[10px] font-mono bg-slate-900 rounded text-slate-400 border border-slate-800 flex items-center gap-0.5">
            <Command className="w-3 h-3" />K
          </kbd>
        </button>
      </div>

      {/* Right: Modals & Documentation Destinations */}
      <div className="flex items-center space-x-2 sm:space-x-3">
        {/* Search button mobile */}
        <button
          onClick={() => setCommandPaletteOpen(true)}
          className="md:hidden p-2 rounded-lg bg-slate-800 text-slate-300 hover:text-white"
        >
          <Search className="w-4 h-4" />
        </button>

        {/* Data Engineering Modal Trigger */}
        <button
          onClick={() => setDataModalOpen(true)}
          className="p-2 md:px-3 md:py-1.5 rounded-xl bg-slate-800/80 hover:bg-slate-800 border border-slate-700/50 text-slate-300 hover:text-slate-100 text-xs font-semibold flex items-center space-x-1.5 transition-colors"
          title="Data Pipeline & DuckDB Warehouse"
        >
          <Database className="w-4 h-4 text-brand-400" />
          <span className="hidden lg:inline">Data</span>
        </button>

        {/* Methodology & Algorithms Modal Trigger */}
        <button
          onClick={() => setMethodologyModalOpen(true)}
          className="p-2 md:px-3 md:py-1.5 rounded-xl bg-slate-800/80 hover:bg-slate-800 border border-slate-700/50 text-slate-300 hover:text-slate-100 text-xs font-semibold flex items-center space-x-1.5 transition-colors"
          title="Methodology & Algorithmic Benchmarks"
        >
          <Cpu className="w-4 h-4 text-emerald-400" />
          <span className="hidden lg:inline">Methodology</span>
        </button>

        {/* Developer Documentation Portal Link */}
        <Link
          to="/docs"
          className={`p-2 md:px-3 md:py-1.5 rounded-xl border text-xs font-semibold flex items-center space-x-1.5 transition-colors ${
            location.pathname === "/docs"
              ? "bg-brand-500/20 text-brand-400 border-brand-500/30"
              : "bg-slate-800/80 hover:bg-slate-800 border-slate-700/50 text-slate-300 hover:text-slate-100"
          }`}
        >
          <FileText className="w-4 h-4 text-teal-400" />
          <span className="hidden lg:inline">Docs</span>
        </Link>

        {/* Backend Health Telemetry Pill */}
        <div className="hidden xl:flex items-center space-x-2 px-3 py-1 rounded-full bg-slate-950 border border-slate-800 text-[11px] font-mono">
          <span
            className={`h-2 w-2 rounded-full ${
              health?.status === "healthy" ? "bg-emerald-400 animate-pulse" : "bg-slate-600"
            }`}
          />
          <span className="text-slate-400">{health?.status === "healthy" ? "Backend Online" : "Connecting..."}</span>
        </div>

        {/* Refresh Queries */}
        <button
          onClick={handleRefreshClick}
          className="p-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white transition-colors"
          title="Refresh Data Queries"
        >
          <RefreshCw className={`w-4 h-4 ${refreshing ? "animate-spin text-brand-400" : ""}`} />
        </button>
      </div>

      {/* Command Palette Modal */}
      <CommandPalette isOpen={commandPaletteOpen} onClose={() => setCommandPaletteOpen(false)} />

      {/* Modals */}
      <DataTransparencyModal isOpen={dataModalOpen} onClose={() => setDataModalOpen(false)} />
      <MethodologyModal isOpen={methodologyModalOpen} onClose={() => setMethodologyModalOpen(false)} />
    </header>
  );
};

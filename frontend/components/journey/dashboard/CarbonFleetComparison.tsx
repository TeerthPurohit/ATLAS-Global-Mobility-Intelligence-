"use client";

import React from "react";
import { motion } from "framer-motion";
import { Leaf, ShieldCheck } from "lucide-react";

interface CarbonFleetComparisonProps {
  distanceMiles: number;
  currentVehicle: string;
  currentCarbon: number;
  confidence?: number;
}

export function CarbonFleetComparison({
  distanceMiles,
  currentVehicle,
  currentCarbon,
  confidence = 0.98,
}: CarbonFleetComparisonProps) {
  // Emission factors from seeds/vehicle_profiles.csv:
  // ev: 0.0, bike: 0.02, auto: 0.20, mini: 0.35, sedan: 0.40, premium: 0.50, suv: 0.55
  const fleetProfiles = [
    { name: "Zero-Emission EV", class: "ev", factor: 0.0, color: "#10b981", badge: "Zero Emissions" },
    { name: "Standard Sedan", class: "sedan", factor: 0.40, color: "#c49752", badge: "Selected" },
    { name: "Executive Luxury", class: "premium", factor: 0.50, color: "#6366f1", badge: "Premium" },
    { name: "Full-Size SUV", class: "suv", factor: 0.55, color: "#c85a48", badge: "High Footprint" },
  ];

  const maxCarbon = Math.max(1, distanceMiles * 0.55);

  return (
    <div className="flex flex-col gap-4 rounded-2xl border border-surface-border bg-surface-1/90 p-5 shadow-xs">
      <div className="flex items-center justify-between border-b border-surface-border/60 pb-3">
        <div className="flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-teal-500/10 text-teal-600">
            <Leaf className="h-4 w-4" />
          </div>
          <div>
            <h3 className="font-section-md text-sm font-bold text-ink-primary">
              Modeled Tailpipe CO₂ Footprint
            </h3>
            <p className="text-xs text-ink-muted">
              Calculated footprint across {distanceMiles.toFixed(1)} route miles (Distance × Vehicle Factor)
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <span className="flex items-center gap-1 rounded bg-teal-500/10 px-2.5 py-1 font-mono text-xs font-semibold text-teal-700 dark:text-teal-400">
            <ShieldCheck className="h-3.5 w-3.5" />
            Calculated
          </span>
        </div>
      </div>

      <div className="flex flex-col gap-3">
        {fleetProfiles.map((fleet) => {
          const emissionKg = Number((distanceMiles * fleet.factor).toFixed(2));
          const pct = Math.max(fleet.factor === 0 ? 3 : 8, (emissionKg / maxCarbon) * 100);
          const isCurrent = fleet.class.toLowerCase() === currentVehicle.toLowerCase();

          return (
            <div
              key={fleet.class}
              className={`flex flex-col gap-1 rounded-xl p-2.5 transition-all ${
                isCurrent ? "bg-brass/10 border border-brass/30 shadow-xs" : "bg-surface-2/40 hover:bg-surface-2/70"
              }`}
            >
              <div className="flex items-center justify-between text-xs">
                <div className="flex items-center gap-2">
                  <span className="font-semibold text-ink-primary">{fleet.name}</span>
                  {isCurrent && (
                    <span className="rounded bg-brass/20 px-1.5 py-0.2 text-[10px] font-mono font-bold text-brass uppercase">
                      Current Fleet
                    </span>
                  )}
                </div>
                <div className="flex items-center gap-2 font-mono">
                  <span className="font-bold text-ink-primary">
                    {emissionKg === 0 ? "0.00 kg CO₂" : `${emissionKg.toFixed(2)} kg CO₂`}
                  </span>
                  <span className="text-[11px] text-ink-muted">
                    ({(fleet.factor * 1000).toFixed(0)} g/mi)
                  </span>
                </div>
              </div>

              {/* Comparative Progress bar */}
              <div className="h-2 w-full overflow-hidden rounded-full bg-surface-border/40">
                <motion.div
                  className="h-full rounded-full"
                  style={{ backgroundColor: fleet.color }}
                  initial={{ width: 0 }}
                  animate={{ width: `${pct}%` }}
                  transition={{ duration: 0.8, ease: "easeOut" }}
                />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

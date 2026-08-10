"use client";

import { Card, CardTitle } from "@/components/ui/Card";
import type { Capabilities } from "@/lib/api";
import { cn } from "@/lib/utils";
import {
  TrendingUp,
  Zap,
  MapPin,
  MessageSquare,
  Layers,
  Navigation,
  Activity,
  CheckCircle2,
  Clock,
  Leaf,
  Calendar,
  AlertCircle,
} from "lucide-react";

interface CapabilityMatrixProps {
  capabilities: Capabilities;
  className?: string;
}

const CAPABILITIES_LIST = [
  { key: "demand", label: "Demand Prediction", icon: TrendingUp, desc: "Pickup demand estimation by zone/area" },
  { key: "fare", label: "Fare Estimation", icon: Zap, desc: "Predictive & tariff fare computation" },
  { key: "journey", label: "Journey Intelligence", icon: MapPin, desc: "Full route, fare, ETA & risk pipeline" },
  { key: "chat", label: "AI Analyst Chat", icon: MessageSquare, desc: "Grounded LLM mobility queries" },
  { key: "area_analysis", label: "Area Analytics", icon: Layers, desc: "Spatial area metrics & choropleth maps" },
  { key: "routing", label: "OSRM Routing", icon: Navigation, desc: "Deterministic route geometry & duration" },
  { key: "congestion", label: "Congestion Score", icon: Activity, desc: "Traffic flow & delay indexing" },
  { key: "availability", label: "Ride Availability", icon: CheckCircle2, desc: "Vehicle dispatch & wait-time modeling" },
  { key: "surge", label: "Surge Risk", icon: Activity, desc: "Multiplier surge likelihood estimation" },
  { key: "carbon", label: "Carbon Emissions", icon: Leaf, desc: "CO2e footprint calculation" },
  { key: "best_departure", label: "Best Departure Time", icon: Clock, desc: "Optimal departure window recommendation" },
] as const;

export function CapabilityMatrix({ capabilities, className }: CapabilityMatrixProps) {
  const activeCount = CAPABILITIES_LIST.filter(
    (cap) => capabilities[cap.key as keyof Capabilities]
  ).length;

  return (
    <Card className={cn("p-6", className)}>
      <div className="flex items-center justify-between border-b border-surface-border pb-4">
        <div>
          <CardTitle className="font-display text-base font-semibold text-ink-primary">
            Capability Matrix
          </CardTitle>
          <p className="mt-0.5 text-xs text-ink-muted">
            {activeCount} of {CAPABILITIES_LIST.length} capabilities active for this city
          </p>
        </div>
        <span className="font-mono text-xs font-semibold px-2.5 py-1 rounded-full bg-surface-1 text-brass border border-surface-border">
          {Math.round((activeCount / CAPABILITIES_LIST.length) * 100)}% COVERAGE
        </span>
      </div>

      <div className="mt-4 grid grid-cols-1 gap-2.5 sm:grid-cols-2 lg:grid-cols-3">
        {CAPABILITIES_LIST.map((cap) => {
          const isEnabled = Boolean(capabilities[cap.key as keyof Capabilities]);
          const Icon = cap.icon;

          return (
            <div
              key={cap.key}
              className={cn(
                "group relative flex items-start gap-3 rounded-xl border p-3.5 transition-all duration-200",
                isEnabled
                  ? "border-surface-border bg-surface-1/40 hover:border-brass/40 hover:bg-surface-1"
                  : "border-dashed border-surface-border/60 bg-surface-0/40 opacity-60"
              )}
              title={cap.desc}
            >
              <div
                className={cn(
                  "flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border text-xs",
                  isEnabled
                    ? "border-brass/30 bg-brass/10 text-brass"
                    : "border-surface-border bg-surface-1 text-ink-muted"
                )}
              >
                <Icon className="h-4 w-4" />
              </div>

              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between gap-1">
                  <span
                    className={cn(
                      "text-xs font-semibold truncate",
                      isEnabled ? "text-ink-primary" : "text-ink-muted"
                    )}
                  >
                    {cap.label}
                  </span>

                  {isEnabled ? (
                    <span className="flex h-1.5 w-1.5 rounded-full bg-brass shrink-0" />
                  ) : (
                    <AlertCircle className="h-3 w-3 text-oxide shrink-0" />
                  )}
                </div>

                <p className="mt-0.5 text-[11px] leading-tight text-ink-muted line-clamp-1">
                  {cap.desc}
                </p>
              </div>
            </div>
          );
        })}
      </div>
    </Card>
  );
}

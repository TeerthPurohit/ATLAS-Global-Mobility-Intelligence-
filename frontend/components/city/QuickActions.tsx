"use client";

import { Card, CardTitle } from "@/components/ui/Card";
import { useRouter } from "next/navigation";
import { MapPin, BarChart2, Search, MessageSquare, ArrowRight } from "lucide-react";
import { cn } from "@/lib/utils";

interface QuickActionsProps {
  hasCapabilities: boolean;
  className?: string;
}

export function QuickActions({ hasCapabilities, className }: QuickActionsProps) {
  const router = useRouter();

  const actions = [
    {
      label: "Plan Journey",
      desc: "Plot origin & destination",
      icon: MapPin,
      href: "/journey",
      disabled: false,
      color: "text-brass border-brass/30 bg-brass/10",
    },
    {
      label: "Compare Vehicles",
      desc: "Multi-vehicle matrix",
      icon: BarChart2,
      href: "/compare",
      disabled: !hasCapabilities,
      color: "text-verdigris border-verdigris/30 bg-verdigris/10",
    },
    {
      label: "City Insights",
      desc: "Demand & flow analytics",
      icon: Search,
      href: "/insights",
      disabled: !hasCapabilities,
      color: "text-brass border-brass/30 bg-brass/10",
    },
    {
      label: "AI Analyst",
      desc: "Interactive intelligence",
      icon: MessageSquare,
      href: "/ask-ai",
      disabled: false,
      color: "text-verdigris border-verdigris/30 bg-verdigris/10",
    },
  ];

  return (
    <Card className={cn("p-6 flex flex-col gap-4", className)}>
      <CardTitle className="font-display text-base font-semibold text-ink-primary">
        Quick Actions
      </CardTitle>

      <div className="grid grid-cols-1 gap-2.5 sm:grid-cols-2">
        {actions.map((action) => {
          const Icon = action.icon;

          return (
            <button
              key={action.label}
              onClick={() => !action.disabled && router.push(action.href)}
              disabled={action.disabled}
              className={cn(
                "group flex items-center justify-between rounded-xl border p-3.5 text-left transition-all duration-200",
                action.disabled
                  ? "border-surface-border bg-surface-0/40 text-ink-muted cursor-not-allowed opacity-50"
                  : "border-surface-border bg-surface-1/40 hover:border-brass/40 hover:bg-surface-1 text-ink-primary"
              )}
            >
              <div className="flex items-center gap-3">
                <div
                  className={cn(
                    "flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border",
                    action.disabled ? "border-surface-border bg-surface-1 text-ink-muted" : action.color
                  )}
                >
                  <Icon className="h-4 w-4" />
                </div>
                <div>
                  <p className="text-xs font-semibold">{action.label}</p>
                  <p className="text-[11px] text-ink-muted">{action.desc}</p>
                </div>
              </div>

              {!action.disabled && (
                <ArrowRight className="h-4 w-4 text-ink-muted transition-transform group-hover:translate-x-0.5 group-hover:text-brass" />
              )}
            </button>
          );
        })}
      </div>
    </Card>
  );
}

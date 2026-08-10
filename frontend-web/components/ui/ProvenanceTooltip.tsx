"use client";

import { cn } from "@/lib/utils";
import { type PredictionOut } from "@/lib/api";
import { ExternalLink, Info } from "lucide-react";

interface ProvenanceTooltipProps {
  prediction: PredictionOut;
  label?: string;
  className?: string;
}

export function ProvenanceTooltip({ prediction, label, className }: ProvenanceTooltipProps) {
  const { source, method, confidence, data_vintage, model_version, reason, value_usd } = prediction;

  if (!source && !method && !confidence && !data_vintage && !model_version && !reason && !value_usd) {
    return null;
  }

  return (
    <div className={cn("relative inline-flex", className)}>
      <Info
        className="cursor-help text-ink-muted/50 hover:text-ink-primary transition-colors ml-1 shrink-0"
        size={12}
        aria-label={`Show provenance for ${label || "prediction"}`}
      />
      <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-80 opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-200 z-50 pointer-events-none group-hover:pointer-events-auto">
        <div className="bg-surface-0 border border-surface-border rounded-lg shadow-xl p-3 text-xs">
          <div className="flex items-center justify-between mb-2">
            <span className="font-display font-semibold text-ink-primary">Provenance</span>
            <span className="text-ink-muted">Source details</span>
          </div>
          <div className="space-y-1.5 font-mono">
            {source && (
              <div className="flex justify-between gap-2">
                <span className="text-ink-muted">Source</span>
                <span className="text-ink-primary truncate max-w-[60%] text-right">{source}</span>
              </div>
            )}
            {method && (
              <div className="flex justify-between gap-2">
                <span className="text-ink-muted">Method</span>
                <span className="text-ink-primary truncate max-w-[60%] text-right">{method}</span>
              </div>
            )}
            {confidence !== undefined && confidence !== null && (
              <div className="flex justify-between gap-2">
                <span className="text-ink-muted">Confidence</span>
                <span className="text-ink-primary">{Math.round(confidence * 100)}%</span>
              </div>
            )}
            {data_vintage && (
              <div className="flex justify-between gap-2">
                <span className="text-ink-muted">Data vintage</span>
                <span className="text-ink-primary">{data_vintage}</span>
              </div>
            )}
            {model_version && (
              <div className="flex justify-between gap-2">
                <span className="text-ink-muted">Model version</span>
                <span className="text-ink-primary truncate max-w-[60%] text-right">{model_version}</span>
              </div>
            )}
            {value_usd !== undefined && value_usd !== null && (
              <div className="flex justify-between gap-2 border-t border-surface-border pt-1.5">
                <span className="text-ink-muted">USD equivalent</span>
                <span className="text-ink-primary font-medium">${value_usd.toFixed(2)}</span>
              </div>
            )}
            {reason && (
              <div className="border-t border-surface-border pt-1.5">
                <span className="text-ink-muted block mb-0.5">Reason</span>
                <span className="text-ink-secondary whitespace-pre-wrap">{reason}</span>
              </div>
            )}
          </div>
        </div>
        <div className="absolute top-full left-1/2 -translate-x-1/2 w-0 h-0 border-4 border-transparent border-t-surface-0" />
      </div>
    </div>
  );
}

/**
 * ProvenanceSummary - aggregates provenance from multiple predictions
 * Used at journey level to show overall data lineage
 */
export function ProvenanceSummary({ predictions }: { predictions: Record<string, PredictionOut> }) {
  const entries = Object.entries(predictions).filter(([, pred]) => pred.source || pred.method || pred.data_vintage || pred.model_version);

  if (entries.length === 0) return null;

  // Collect unique sources/methods
  const sources = new Set<string>();
  const methods = new Set<string>();
  const vintages = new Set<string>();
  const models = new Set<string>();

  entries.forEach(([, pred]) => {
    if (pred.source) sources.add(pred.source);
    if (pred.method) methods.add(pred.method);
    if (pred.data_vintage) vintages.add(pred.data_vintage);
    if (pred.model_version) models.add(pred.model_version);
  });

  return (
    <div className="rounded-lg border border-surface-border bg-surface-1 p-4">
      <h4 className="font-display text-sm tracking-wide text-ink-secondary mb-3 flex items-center gap-2">
        <ExternalLink className="h-4 w-4 text-brass" />
        Provenance Summary
      </h4>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
        {sources.size > 0 && (
          <div>
            <p className="text-ink-muted mb-1">Sources</p>
            <p className="font-mono text-ink-primary">{Array.from(sources).join(", ")}</p>
          </div>
        )}
        {methods.size > 0 && (
          <div>
            <p className="text-ink-muted mb-1">Methods</p>
            <p className="font-mono text-ink-primary">{Array.from(methods).join(", ")}</p>
          </div>
        )}
        {vintages.size > 0 && (
          <div>
            <p className="text-ink-muted mb-1">Data vintages</p>
            <p className="font-mono text-ink-primary">{Array.from(vintages).join(", ")}</p>
          </div>
        )}
        {models.size > 0 && (
          <div>
            <p className="text-ink-muted mb-1">Model versions</p>
            <p className="font-mono text-ink-primary">{Array.from(models).join(", ")}</p>
          </div>
        )}
      </div>
      <p className="mt-3 text-xs text-ink-muted">
        Each prediction field above shows its individual basis ring:{" "}
        <span className="inline-flex items-center gap-1"><span className="w-3 h-3 rounded-full border-2 border-brass" /> computed</span>{" "}
        <span className="inline-flex items-center gap-1 ml-2"><span className="w-3 h-3 rounded-full border-2 border-verdigris border-dashed" /> modeled estimate</span>{" "}
        <span className="inline-flex items-center gap-1 ml-2"><span className="w-3 h-3 rounded-full border-2 border-oxide border-dashed" /> unavailable</span>
      </p>
    </div>
  );
}
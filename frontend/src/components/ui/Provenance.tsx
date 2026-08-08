import React from "react";

export type ProvenanceType = "live" | "mart" | "artifact" | "duckdb" | "derived";

const TYPE_META: Record<ProvenanceType, { label: string; color: string }> = {
  live: { label: "Live API Response", color: "text-emerald-400" },
  mart: { label: "Materialized dbt Mart", color: "text-brand-400" },
  artifact: { label: "Precomputed Model Artifact", color: "text-amber-400" },
  duckdb: { label: "DuckDB Warehouse", color: "text-indigo-400" },
  derived: { label: "Derived Client-Side", color: "text-slate-400" },
};

interface ProvenanceProps {
  type: ProvenanceType;
  /** The specific table, artifact path, or endpoint backing this widget. */
  source: string;
  /** Optional right-aligned detail, e.g. row count or split name. */
  detail?: string;
}

/**
 * The app's one recurring signature device: every metric card ends in a
 * torn-receipt stub stating exactly what produced the number above it,
 * the same way a TLC trip receipt itemizes its own fare. Per DESIGN.md's
 * "Total Provenance" rule — this makes that rule visually distinct instead
 * of a plain text footer indistinguishable from any other dashboard.
 */
export const Provenance: React.FC<ProvenanceProps> = ({ type, source, detail }) => {
  const meta = TYPE_META[type];
  return (
    <div className="provenance-tear mt-3 pt-2.5 flex items-center justify-between gap-3 text-[10px] font-mono text-slate-500">
      <span className="truncate">
        <span className={`font-semibold ${meta.color}`}>{meta.label}</span>
        <span className="text-slate-600"> · </span>
        <span className="text-slate-400">{source}</span>
      </span>
      {detail && <span className="shrink-0 text-slate-500">{detail}</span>}
    </div>
  );
};

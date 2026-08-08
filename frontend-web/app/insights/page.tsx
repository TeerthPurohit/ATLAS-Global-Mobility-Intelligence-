"use client";

import { useQuery } from "@tanstack/react-query";
import { Card, CardTitle } from "@/components/ui/Card";
import { Skeleton } from "@/components/ui/Skeleton";
import { Badge } from "@/components/ui/Badge";
import { getInsights, type InsightDoc } from "@/lib/api";

// The Compass Log: real per-zone insight paragraphs from
// rag/insight_generation/generate_insight_docs.py, grounded in mart data
// (validate_grounding() rejects anything the LLM invents). Every card here
// is one line from insight_docs.jsonl -- no fabricated copy.

const SOURCE_LABELS: Record<string, string> = {
  demand: "mart:zone_hourly_demand",
  flows: "mart:zone_pair_flows",
  hub_rank: "PageRank hub importance",
};

function InsightCard({ doc }: { doc: InsightDoc }) {
  return (
    <Card className="flex flex-col gap-3">
      <div className="flex items-start justify-between gap-3">
        <span className="font-mono text-xs uppercase tracking-wider text-ink-muted">
          {doc.zone_name} &middot; {doc.borough}
        </span>
        {doc.pagerank_rank && doc.pagerank_total_zones && (
          <Badge title="Ranked by algorithms/graph/pagerank_hubs.py">
            #{doc.pagerank_rank} busiest of {doc.pagerank_total_zones}
          </Badge>
        )}
      </div>

      <p className="font-display text-lg leading-snug text-ink-primary">{doc.text}</p>

      <div className="flex flex-wrap gap-x-4 gap-y-1 border-t border-surface-border pt-3 text-xs text-ink-muted">
        {Object.entries(doc.sources).map(([key, value]) => (
          <span key={key} title={value} className="font-mono">
            {SOURCE_LABELS[key] ?? key}: {value}
          </span>
        ))}
        <span className="ml-auto italic">{doc.phrased_by === "llm" ? "LLM-phrased, grounding-checked" : "template"}</span>
      </div>
    </Card>
  );
}

function InsightsSkeleton() {
  return (
    <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
      {Array.from({ length: 6 }).map((_, i) => (
        <Skeleton key={i} className="h-40 rounded-2xl" />
      ))}
    </div>
  );
}

export default function InsightsPage() {
  const { data, isLoading, isError, error } = useQuery({
    queryKey: ["insights"],
    queryFn: () => getInsights(20),
  });

  return (
    <div className="flex flex-col gap-6">
      <div>
        <CardTitle className="font-display text-2xl font-normal tracking-wide">The compass log</CardTitle>
        <p className="mt-1 text-sm text-ink-muted">
          Generated per-zone stories, grounded in real trip data and PageRank hub ranking -- busiest zones first.
        </p>
      </div>

      {isLoading && <InsightsSkeleton />}

      {isError && (
        <div className="rounded-2xl border border-dashed border-oxide/40 p-8 text-center text-sm text-ink-muted">
          Couldn&apos;t load insights: {error instanceof Error ? error.message : "unknown error"}
        </div>
      )}

      {data && data.length === 0 && (
        <div className="rounded-2xl border border-dashed border-surface-border p-8 text-center text-sm text-ink-muted">
          No insights generated yet — run <code className="font-mono text-ink-secondary">rag/insight_generation/generate_insight_docs.py</code>.
        </div>
      )}

      {data && data.length > 0 && (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          {data.map((doc) => (
            <InsightCard key={doc.zone_id} doc={doc} />
          ))}
        </div>
      )}
    </div>
  );
}

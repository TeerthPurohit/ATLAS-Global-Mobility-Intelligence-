"use client";

import { useQuery } from "@tanstack/react-query";
import { Card, CardTitle } from "@/components/ui/Card";
import { Skeleton } from "@/components/ui/Skeleton";
import { Badge } from "@/components/ui/Badge";
import { getInsights, type InsightDoc } from "@/lib/api";
import { BookOpen } from "lucide-react";

const SOURCE_LABELS: Record<string, string> = {
  demand: "Zone Demand",
  flows: "Flow Patterns",
  hub_rank: "Hub Ranking",
};

function InsightCard({ doc }: { doc: InsightDoc }) {
  return (
    <Card className="flex flex-col gap-4 hover:border-brass/40 transition-colors">
      <div className="flex items-start justify-between gap-3">
        <div className="flex flex-col gap-1">
          <span className="font-label-sm text-brass">{doc.zone_name}</span>
          <span className="font-body-sm text-ink-secondary">{doc.borough}</span>
        </div>
        {doc.pagerank_rank && doc.pagerank_total_zones && (
          <Badge title="Ranked by PageRank algorithm">
            #{doc.pagerank_rank} of {doc.pagerank_total_zones}
          </Badge>
        )}
      </div>

      <p className="font-section-md leading-relaxed text-ink-primary">{doc.text}</p>

      <div className="flex flex-wrap gap-x-4 gap-y-2 border-t border-surface-border pt-4 text-xs text-ink-muted">
        {Object.entries(doc.sources).map(([key, value]) => (
          <span key={key} title={value} className="font-mono">
            {SOURCE_LABELS[key] ?? key}: <span className="text-brass">{value}</span>
          </span>
        ))}
        <span className="ml-auto italic text-ink-muted">
          {doc.phrased_by === "llm" ? "LLM-verified" : "template"}
        </span>
      </div>
    </Card>
  );
}

function InsightsSkeleton() {
  return (
    <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
      {Array.from({ length: 6 }).map((_, i) => (
        <Skeleton key={i} className="h-48 rounded-sm" />
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
    <div className="flex flex-col gap-12">
      {/* Header */}
      <section className="flex flex-col gap-3">
        <span className="font-label-sm text-brass tracking-wider">
          Data Intelligence
        </span>
        <h1 className="font-display-lg text-ink-primary">
          The Compass Log
        </h1>
        <p className="font-body-md max-w-2xl text-ink-secondary">
          Generated zone stories grounded in real trip data and hub ranking. Busiest zones first.
        </p>
      </section>

      {/* Divider */}
      <div className="separator-line" />

      {/* Content */}
      {isLoading && <InsightsSkeleton />}

      {isError && (
        <div className="flex items-center justify-center border border-surface-border bg-surface-1 p-12 text-center rounded-sm">
          <div className="max-w-md space-y-3">
            <div className="flex justify-center">
              <div className="p-3 bg-oxide/10 rounded-sm">
                <BookOpen className="h-6 w-6 text-oxide" />
              </div>
            </div>
            <h3 className="font-section-md text-ink-primary">Unable to Load Insights</h3>
            <p className="font-body-sm text-ink-secondary">
              {error instanceof Error ? error.message : "Unknown error occurred"}
            </p>
          </div>
        </div>
      )}

      {data && data.length === 0 && (
        <div className="flex items-center justify-center border border-surface-border bg-surface-1 p-12 text-center rounded-sm">
          <div className="max-w-md space-y-3">
            <div className="flex justify-center">
              <div className="p-3 bg-verdigris/10 rounded-sm">
                <BookOpen className="h-6 w-6 text-verdigris" />
              </div>
            </div>
            <h3 className="font-section-md text-ink-primary">No Insights Yet</h3>
            <p className="font-body-sm text-ink-secondary">
              Run the insight generation pipeline to populate zone stories.
            </p>
          </div>
        </div>
      )}

      {data && data.length > 0 && (
        <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
          {data.map((doc) => (
            <InsightCard key={doc.zone_id} doc={doc} />
          ))}
        </div>
      )}
    </div>
  );
}

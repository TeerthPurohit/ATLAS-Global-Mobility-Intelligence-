"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Card, CardTitle } from "@/components/ui/Card";
import { Skeleton } from "@/components/ui/Skeleton";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/Tabs";
import { Badge } from "@/components/ui/Badge";
import { getAnalyticsSummary, getAnalyticsInsights, getAnalyticsHistory, getAnalyticsTrends } from "@/lib/api";
import { cn } from "@/lib/utils";
import { formatCurrency } from "@/lib/api";
import { TrendingUp, TrendingDown, Minus, Target, BarChart2, History, Lightbulb } from "lucide-react";

export default function AnalyticsPage() {
  const [period, setPeriod] = useState<"7d" | "30d" | "90d">("30d");

  const { data: summary, isLoading: summaryLoading } = useQuery({
    queryKey: ["analytics", "summary"],
    queryFn: getAnalyticsSummary,
    staleTime: 5 * 60_000,
  });

  const { data: insights, isLoading: insightsLoading } = useQuery({
    queryKey: ["analytics", "insights"],
    queryFn: getAnalyticsInsights,
    staleTime: 5 * 60_000,
  });

  const { data: history, isLoading: historyLoading } = useQuery({
    queryKey: ["analytics", "history", 100, 0],
    queryFn: () => getAnalyticsHistory(100, 0),
    staleTime: 5 * 60_000,
  });

  const { data: trends, isLoading: trendsLoading } = useQuery({
    queryKey: ["analytics", "trends", period],
    queryFn: () => getAnalyticsTrends(period),
    staleTime: 5 * 60_000,
  });

  function MetricCard({ label, value, change, icon: Icon }: { label: string; value: string | number; change?: number; icon: React.ComponentType<{ className?: string }> }) {
    const changeColor = change === undefined ? "text-ink-muted" : change > 0 ? "text-verdigris" : change < 0 ? "text-oxide" : "text-ink-muted";
    const ChangeIcon = change === undefined ? Minus : change > 0 ? TrendingUp : change < 0 ? TrendingDown : Minus;

    return (
      <Card className="p-4">
        <div className="flex items-start justify-between">
          <div>
            <p className="text-xs uppercase tracking-wider text-ink-muted">{label}</p>
            <p className="mt-1 font-display text-2xl font-semibold text-ink-primary">{value}</p>
            {change !== undefined && (
              <p className={cn("mt-1 flex items-center gap-1 text-xs font-medium", changeColor)}>
                <ChangeIcon className="h-3 w-3" />
                {change > 0 ? "+" : ""}{change.toFixed(1)}%
              </p>
            )}
          </div>
          <div className="p-2 rounded-lg bg-brass/10 text-brass">
            <Icon className="h-5 w-5" />
          </div>
        </div>
      </Card>
    );
  }

  function SkeletonMetricCard() {
    return (
      <Card className="p-4 animate-pulse">
        <div className="flex items-start justify-between">
          <div>
            <Skeleton className="h-3 w-24" />
            <Skeleton className="mt-2 h-8 w-32" />
            <Skeleton className="mt-2 h-3 w-20" />
          </div>
          <Skeleton className="h-9 w-9 rounded-lg" />
        </div>
      </Card>
    );
  }

  function InsightCard({ insight }: { insight: Record<string, unknown> }) {
    const titleText =
      (typeof insight.title === "string" && insight.title) ||
      (typeof insight.metric === "string" && insight.metric) ||
      "Insight";

    const descText =
      (typeof insight.description === "string" && insight.description) ||
      (typeof insight.text === "string" && insight.text) ||
      "No description";

    const changeVal = typeof insight.change === "number" ? insight.change : undefined;

    return (
      <Card className="p-4 hover:border-brass/30 transition-colors">
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1 min-w-0">
            <p className="font-medium text-ink-primary truncate">{titleText}</p>
            <p className="mt-1 text-sm text-ink-muted line-clamp-2">{descText}</p>
            <div className="mt-2 flex flex-wrap gap-1">
              {typeof insight.city === "string" && <Badge className="border border-surface-border bg-surface-1 text-xs">{insight.city}</Badge>}
              {typeof insight.borough === "string" && <Badge className="border border-surface-border bg-surface-1 text-xs">{insight.borough}</Badge>}
              {typeof insight.source === "string" && <Badge className="border border-surface-border bg-surface-1 text-xs text-ink-muted">{insight.source}</Badge>}
            </div>
          </div>
          {insight.value !== undefined && (
            <div className="text-right shrink-0">
              <p className="font-display text-lg font-semibold text-brass">
                {typeof insight.value === "number" ? (insight.unit === "currency" ? formatCurrency(insight.value, "USD") : insight.value.toLocaleString()) : String(insight.value)}
              </p>
              {changeVal !== undefined && (
                <p className={cn("text-xs font-medium", changeVal > 0 ? "text-verdigris" : "text-oxide")}>
                  {changeVal > 0 ? "+" : ""}{changeVal.toFixed(1)}%
                </p>
              )}
            </div>
          )}
        </div>
      </Card>
    );
  }

  function TrendSparkline({ data, color }: { data: number[]; color: string }) {
    if (!data.length) return <span className="text-ink-muted">No data</span>;
    const max = Math.max(...data);
    const min = Math.min(...data);
    const range = max - min || 1;
    const points = data.map((v, i) => `${(i / (data.length - 1)) * 100}%,${100 - ((v - min) / range) * 90}%`).join(" ");
    return (
      <svg viewBox="0 0 100 100" className="h-12 w-full" preserveAspectRatio="none">
        <polyline fill="none" stroke={color} strokeWidth="1.5" points={points} />
        <circle cx={points.split(" ")[points.split(" ").length - 1].split(",")[0].replace("%", "")} cy={points.split(" ")[points.split(" ").length - 1].split(",")[1].replace("%", "")} r="2" fill={color} />
      </svg>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="font-display text-2xl font-semibold text-ink-primary">Analytics & Intelligence</h1>
          <p className="mt-1 text-sm text-ink-muted">System health, insights, trends, and prediction history</p>
        </div>
        <div className="flex items-center gap-2">
          <label className="text-xs text-ink-muted">Period:</label>
          <select
            value={period}
            onChange={(e) => setPeriod(e.target.value as "7d" | "30d" | "90d")}
            className="px-3 py-1.5 text-sm bg-surface-1 border border-surface-border rounded-lg text-ink-primary focus:outline-none focus:ring-2 focus:ring-brass/50"
          >
            <option value="7d">7 days</option>
            <option value="30d">30 days</option>
            <option value="90d">90 days</option>
          </select>
        </div>
      </div>

      {/* Tabs */}
      <Tabs defaultValue="overview" className="space-y-4">
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="overview"><Target className="h-4 w-4 mr-2" /> Overview</TabsTrigger>
          <TabsTrigger value="insights"><Lightbulb className="h-4 w-4 mr-2" /> Insights</TabsTrigger>
          <TabsTrigger value="trends"><BarChart2 className="h-4 w-4 mr-2" /> Trends</TabsTrigger>
          <TabsTrigger value="history"><History className="h-4 w-4 mr-2" /> History</TabsTrigger>
        </TabsList>

        {/* Overview Tab */}
        <TabsContent value="overview">
          {summaryLoading ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              {[0, 1, 2, 3].map((i) => <SkeletonMetricCard key={i} />)}
            </div>
          ) : summary ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              <MetricCard
                label="Total Predictions"
                value={summary.total_predictions?.toLocaleString() || "—"}
                icon={Target}
              />
              <MetricCard
                label="Cities Served"
                value={summary.cities_served || "—"}
                icon={TrendingUp}
              />
              <MetricCard
                label="Avg Confidence"
                value={`${(
                  (typeof (summary.top_cities?.[0] as Record<string, unknown> | undefined)?.confidence === "number"
                    ? ((summary.top_cities?.[0] as Record<string, unknown>).confidence as number)
                    : 0.85) * 100
                ).toFixed(0)}%`}
                icon={TrendingUp}
              />
              <MetricCard
                label="Date Range"
                value={
                  summary.date_range && typeof summary.date_range.start === "string" && typeof summary.date_range.end === "string"
                    ? `${new Date(summary.date_range.start).toLocaleDateString()} – ${new Date(summary.date_range.end).toLocaleDateString()}`
                    : "Last 30 Days"
                }
                icon={History}
              />
            </div>
          ) : (
            <Card className="p-8 text-center text-ink-muted">No summary data available</Card>
          )}

          {/* Top Cities */}
          {summary?.top_cities && (
            <div className="mt-6">
              <h3 className="font-display text-lg font-semibold text-ink-primary mb-4">Top Cities by Volume</h3>
              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                {summary.top_cities.slice(0, 6).map((city: Record<string, unknown>, i: number) => (
                  <Card key={i} className="p-4 flex items-center justify-between">
                    <div>
                      <p className="font-medium text-ink-primary">{city.city_name || city.city || `City ${i + 1}`}</p>
                      <p className="text-xs text-ink-muted">{city.country || "—"}</p>
                    </div>
                    <div className="text-right">
                      <p className="font-display text-lg font-semibold text-brass">{city.predictions?.toLocaleString() || "—"}</p>
                      <p className="text-xs text-ink-muted">predictions</p>
                    </div>
                  </Card>
                ))}
              </div>
            </div>
          )}
        </TabsContent>

        {/* Insights Tab */}
        <TabsContent value="insights">
          {insightsLoading ? (
            <div className="space-y-3">
              {[0, 1, 2].map((i) => <Card key={i} className="p-4 animate-pulse"><Skeleton className="h-4 w-1/3" /><Skeleton className="mt-2 h-3 w-full" /></Card>)}
            </div>
          ) : insights?.insights?.length ? (
            <div className="space-y-3">
              {insights.insights.map((insight: Record<string, unknown>, i: number) => (
                <InsightCard key={i} insight={insight} />
              ))}
            </div>
          ) : (
            <Card className="p-8 text-center text-ink-muted">No insights available</Card>
          )}
        </TabsContent>

        {/* Trends Tab */}
        <TabsContent value="trends">
          {trendsLoading ? (
            <div className="space-y-3">
              {[0, 1, 2, 3].map((i) => <Card key={i} className="p-4 animate-pulse"><Skeleton className="h-4 w-1/3" /><Skeleton className="mt-3 h-12 w-full" /></Card>)}
            </div>
          ) : trends?.trends ? (
            <div className="space-y-4">
              {Object.entries(trends.trends).map(([metric, data]) => (
                <Card key={metric} className="p-4">
                  <div className="flex items-center justify-between mb-3">
                    <h4 className="font-display text-base font-semibold capitalize">{metric.replace(/_/g, " ")}</h4>
                    <span className="text-xs text-ink-muted">{period}</span>
                  </div>
                  <TrendSparkline data={data as number[]} color="#c9922a" />
                  <div className="mt-2 flex justify-between text-xs text-ink-muted">
                    <span>{(data as number[])[0]?.toFixed(1) || "—"}</span>
                    <span>{(data as number[])[(data as number[]).length - 1]?.toFixed(1) || "—"}</span>
                  </div>
                </Card>
              ))}
            </div>
          ) : (
            <Card className="p-8 text-center text-ink-muted">No trend data available for this period</Card>
          )}
        </TabsContent>

        {/* History Tab */}
        <TabsContent value="history">
          {historyLoading ? (
            <div className="space-y-3">
              {[0, 1, 2, 3, 4].map((i) => <Card key={i} className="p-4 animate-pulse"><Skeleton className="h-4 w-1/2" /><Skeleton className="mt-2 h-3 w-1/3" /></Card>)}
            </div>
          ) : history?.history?.length ? (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-surface-border text-left text-xs uppercase tracking-wider text-ink-muted">
                    <th className="pb-2 pr-4">Timestamp</th>
                    <th className="pb-2 pr-4">City</th>
                    <th className="pb-2 pr-4">Journey</th>
                    <th className="pb-2 pr-4">Fare</th>
                    <th className="pb-2 pr-4">Basis</th>
                    <th className="pb-2 pr-4">Confidence</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-surface-border/50">
                  {history.history.slice(0, 50).map((entry: Record<string, unknown>, i: number) => (
                    <tr key={i} className="hover:bg-surface-1/50 transition-colors">
                      <td className="py-2 pr-4 font-mono text-ink-secondary">{entry.requested_at ? new Date(entry.requested_at as string).toLocaleString() : "—"}</td>
                      <td className="py-2 pr-4 text-ink-primary">{entry.city_id as string || "—"}</td>
                      <td className="py-2 pr-4 text-ink-muted">
                        {entry.pickup_lat && entry.dropoff_lat
                          ? `(${Number(entry.pickup_lat).toFixed(3)}, ${Number(entry.pickup_lon).toFixed(3)}) → (${Number(entry.dropoff_lat).toFixed(3)}, ${Number(entry.dropoff_lon).toFixed(3)})`
                          : "—"}
                      </td>
                      <td className="py-2 pr-4 font-mono text-brass">{entry.fare_value ? formatCurrency(Number(entry.fare_value), "USD") : "—"}</td>
                      <td className="py-2 pr-4">
                        <Badge variant={entry.fare_basis === "computed" ? "default" : entry.fare_basis === "modeled_estimate" ? "outline" : "secondary"} className="text-[10px]">
                          {entry.fare_basis as string || "—"}
                        </Badge>
                      </td>
                      <td className="py-2 pr-4 text-ink-muted">{entry.confidence_value ? `${Math.round(Number(entry.confidence_value) * 100)}%` : "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <Card className="p-8 text-center text-ink-muted">No history available</Card>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}
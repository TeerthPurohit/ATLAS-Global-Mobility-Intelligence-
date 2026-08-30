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
      <Card className="p-6 flex flex-col gap-4">
        <div className="flex items-start justify-between">
          <div className="flex flex-col gap-2">
            <span className="font-label-sm text-ink-muted">{label}</span>
            <p className="font-data-lg text-brass">{value}</p>
          </div>
          <div className="p-2 rounded-sm bg-brass/10 text-brass">
            <Icon className="h-5 w-5" />
          </div>
        </div>
        {change !== undefined && (
          <div className={cn("flex items-center gap-1 font-label-sm", changeColor)}>
            <ChangeIcon className="h-3 w-3" />
            {change > 0 ? "+" : ""}{change.toFixed(1)}%
          </div>
        )}
      </Card>
    );
  }

  function SkeletonMetricCard() {
    return (
      <Card className="p-6 animate-pulse">
        <div className="flex items-start justify-between">
          <div className="flex flex-col gap-2 flex-1">
            <Skeleton className="h-3 w-24" />
            <Skeleton className="h-8 w-32" />
          </div>
          <Skeleton className="h-9 w-9 rounded-sm" />
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
      <Card className="p-6 hover:border-brass/40 transition-colors">
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1 min-w-0">
            <p className="font-section-md text-ink-primary">{titleText}</p>
            <p className="mt-2 font-body-sm text-ink-secondary">{descText}</p>
            <div className="mt-3 flex flex-wrap gap-2">
              {typeof insight.city === "string" && <Badge className="border border-surface-border bg-surface-1 text-xs">{insight.city}</Badge>}
              {typeof insight.borough === "string" && <Badge className="border border-surface-border bg-surface-1 text-xs">{insight.borough}</Badge>}
              {typeof insight.source === "string" && <Badge className="border border-surface-border bg-surface-1 text-xs text-ink-muted">{insight.source}</Badge>}
            </div>
          </div>
          {insight.value !== undefined && (
            <div className="text-right shrink-0">
              <p className="font-data-md text-brass">
                {typeof insight.value === "number" ? (insight.unit === "currency" ? formatCurrency(insight.value, "USD") : insight.value.toLocaleString()) : String(insight.value)}
              </p>
              {changeVal !== undefined && (
                <p className={cn("text-xs font-medium mt-1", changeVal > 0 ? "text-verdigris" : "text-oxide")}>
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
    if (!data.length) return <span className="font-body-sm text-ink-muted">No data</span>;
    const max = Math.max(...data);
    const min = Math.min(...data);
    const range = max - min || 1;
    const points = data.map((v, i) => `${(i / (data.length - 1)) * 100}%,${100 - ((v - min) / range) * 90}%`).join(" ");
    return (
      <svg viewBox="0 0 100 100" className="h-16 w-full" preserveAspectRatio="none">
        <polyline fill="none" stroke={color} strokeWidth="1.5" points={points} />
        <circle cx={points.split(" ")[points.split(" ").length - 1].split(",")[0].replace("%", "")} cy={points.split(" ")[points.split(" ").length - 1].split(",")[1].replace("%", "")} r="2" fill={color} />
      </svg>
    );
  }

  return (
    <div className="flex flex-col gap-12">
      {/* Header */}
      <section className="flex flex-col gap-3">
        <span className="font-label-sm text-brass tracking-wider">
          System Intelligence
        </span>
        <h1 className="font-display-lg text-ink-primary">
          Analytics & Performance
        </h1>
        <p className="font-body-md max-w-2xl text-ink-secondary">
          System health, insights, trends, and prediction history across all cities and vehicle classes.
        </p>
      </section>

      {/* Period Selector */}
      <div className="flex items-center gap-3 border-b border-surface-border pb-6">
        <span className="font-label-sm text-ink-muted">Time Period:</span>
        <select
          value={period}
          onChange={(e) => setPeriod(e.target.value as "7d" | "30d" | "90d")}
          className="px-4 py-2 font-body-sm bg-surface-1 border border-surface-border rounded-sm text-ink-primary focus:outline-none focus:ring-2 focus:ring-brass/50"
        >
          <option value="7d">Last 7 days</option>
          <option value="30d">Last 30 days</option>
          <option value="90d">Last 90 days</option>
        </select>
      </div>

      {/* Tabs */}
      <Tabs defaultValue="overview" className="space-y-8">
        <TabsList className="grid w-full grid-cols-4 bg-transparent border-b border-surface-border p-0 h-auto gap-6">
          <TabsTrigger value="overview" className="bg-transparent border-b-2 border-transparent data-[state=active]:border-brass data-[state=active]:bg-transparent rounded-none px-0 py-2 font-section-md">
            <Target className="h-4 w-4 mr-2" /> Overview
          </TabsTrigger>
          <TabsTrigger value="insights" className="bg-transparent border-b-2 border-transparent data-[state=active]:border-brass data-[state=active]:bg-transparent rounded-none px-0 py-2 font-section-md">
            <Lightbulb className="h-4 w-4 mr-2" /> Insights
          </TabsTrigger>
          <TabsTrigger value="trends" className="bg-transparent border-b-2 border-transparent data-[state=active]:border-brass data-[state=active]:bg-transparent rounded-none px-0 py-2 font-section-md">
            <BarChart2 className="h-4 w-4 mr-2" /> Trends
          </TabsTrigger>
          <TabsTrigger value="history" className="bg-transparent border-b-2 border-transparent data-[state=active]:border-brass data-[state=active]:bg-transparent rounded-none px-0 py-2 font-section-md">
            <History className="h-4 w-4 mr-2" /> History
          </TabsTrigger>
        </TabsList>

        {/* Overview Tab */}
        <TabsContent value="overview" className="space-y-8">
          {summaryLoading ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
              {[0, 1, 2, 3].map((i) => <SkeletonMetricCard key={i} />)}
            </div>
          ) : summary ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
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
                value="—"
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
            <Card className="p-8 text-center font-body-sm text-ink-muted">No summary data available</Card>
          )}

          {/* Top Cities */}
          {summary?.top_cities && (
            <div className="space-y-6">
              <div className="separator-line" />
              <div>
                <h3 className="font-section-lg text-ink-primary mb-6">Top Cities by Volume</h3>
                <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                  {summary.top_cities.slice(0, 6).map((city: Record<string, unknown>, i: number) => {
                    const cityName =
                      (typeof city.city_name === "string" && city.city_name) ||
                      (typeof city.city_id === "string" && city.city_id) ||
                      (typeof city.city === "string" && city.city) ||
                      `City ${i + 1}`;
                    const countryName = typeof city.country === "string" ? city.country : "—";
                    const predictionsText = typeof city.predictions === "number" ? city.predictions.toLocaleString() : "—";

                    return (
                      <Card key={i} className="p-6 flex items-center justify-between hover:border-brass/40 transition-colors">
                        <div>
                          <p className="font-section-md text-ink-primary">{cityName}</p>
                          <p className="font-body-sm text-ink-secondary mt-1">{countryName}</p>
                        </div>
                        <div className="text-right">
                          <p className="font-data-md text-brass">{predictionsText}</p>
                          <p className="font-label-sm text-ink-muted mt-1">predictions</p>
                        </div>
                      </Card>
                    );
                  })}
                </div>
              </div>
            </div>
          )}
        </TabsContent>

        {/* Insights Tab */}
        <TabsContent value="insights" className="space-y-4">
          {insightsLoading ? (
            <div className="space-y-4">
              {[0, 1, 2].map((i) => <Card key={i} className="p-6 animate-pulse"><Skeleton className="h-4 w-1/3" /><Skeleton className="mt-3 h-3 w-full" /></Card>)}
            </div>
          ) : insights?.insights?.length ? (
            <div className="space-y-4">
              {insights.insights.map((insight: Record<string, unknown>, i: number) => (
                <InsightCard key={i} insight={insight} />
              ))}
            </div>
          ) : (
            <Card className="p-8 text-center font-body-sm text-ink-muted">No insights available</Card>
          )}
        </TabsContent>

        {/* Trends Tab */}
        <TabsContent value="trends" className="space-y-6">
          {trendsLoading ? (
            <div className="space-y-4">
              {[0, 1, 2, 3].map((i) => <Card key={i} className="p-6 animate-pulse"><Skeleton className="h-4 w-1/3" /><Skeleton className="mt-4 h-16 w-full" /></Card>)}
            </div>
          ) : trends?.trends ? (
            <div className="space-y-6">
              {Object.entries(trends.trends).map(([metric, data]) => (
                <Card key={metric} className="p-6">
                  <div className="flex items-center justify-between mb-6">
                    <h4 className="font-section-md capitalize">{metric.replace(/_/g, " ")}</h4>
                    <span className="font-label-sm text-ink-muted">{period}</span>
                  </div>
                  <TrendSparkline data={data as number[]} color="#6c5ce7" />
                  <div className="mt-4 flex justify-between font-body-sm text-ink-muted">
                    <span>{(data as number[])[0]?.toFixed(1) || "—"}</span>
                    <span>{(data as number[])[(data as number[]).length - 1]?.toFixed(1) || "—"}</span>
                  </div>
                </Card>
              ))}
            </div>
          ) : (
            <Card className="p-8 text-center font-body-sm text-ink-muted">No trend data available for this period</Card>
          )}
        </TabsContent>

        {/* History Tab */}
        <TabsContent value="history" className="space-y-4">
          {historyLoading ? (
            <div className="space-y-3">
              {[0, 1, 2, 3, 4].map((i) => <Card key={i} className="p-4 animate-pulse"><Skeleton className="h-4 w-1/2" /><Skeleton className="mt-2 h-3 w-1/3" /></Card>)}
            </div>
          ) : history?.history?.length ? (
            <div className="overflow-x-auto border border-surface-border rounded-sm">
              <table className="w-full font-body-sm">
                <thead>
                  <tr className="border-b border-surface-border bg-surface-1 text-left">
                    <th className="px-6 py-4 font-label-sm text-ink-muted">Timestamp</th>
                    <th className="px-6 py-4 font-label-sm text-ink-muted">City</th>
                    <th className="px-6 py-4 font-label-sm text-ink-muted">Journey</th>
                    <th className="px-6 py-4 font-label-sm text-ink-muted">Fare</th>
                    <th className="px-6 py-4 font-label-sm text-ink-muted">Basis</th>
                    <th className="px-6 py-4 font-label-sm text-ink-muted">Confidence</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-surface-border">
                  {history.history.slice(0, 50).map((entry: Record<string, unknown>, i: number) => (
                    <tr key={i} className="hover:bg-surface-1/50 transition-colors">
                      <td className="px-6 py-4 font-mono text-ink-secondary">{entry.requested_at ? new Date(entry.requested_at as string).toLocaleString() : "—"}</td>
                      <td className="px-6 py-4 text-ink-primary">{(entry.city_id as string) || "—"}</td>
                      <td className="px-6 py-4 text-ink-muted text-xs">
                        {entry.pickup_lat && entry.dropoff_lat
                          ? `(${Number(entry.pickup_lat).toFixed(3)}, ${Number(entry.pickup_lon).toFixed(3)}) → (${Number(entry.dropoff_lat).toFixed(3)}, ${Number(entry.dropoff_lon).toFixed(3)})`
                          : "—"}
                      </td>
                      <td className="px-6 py-4 font-mono text-brass">{entry.fare_value ? formatCurrency(Number(entry.fare_value), "USD") : "—"}</td>
                      <td className="px-6 py-4">
                        <Badge basis={(entry.fare_basis as any) || "unavailable"} className="text-[10px]">
                          {String(entry.fare_basis || "—")}
                        </Badge>
                      </td>
                      <td className="px-6 py-4 text-ink-muted">{entry.confidence_value ? `${Math.round(Number(entry.confidence_value) * 100)}%` : "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <Card className="p-8 text-center font-body-sm text-ink-muted">No history available</Card>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}

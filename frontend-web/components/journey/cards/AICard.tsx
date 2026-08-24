"use client";

import { Card, CardTitle } from "@/components/ui/Card";
import { Skeleton } from "@/components/ui/Skeleton";
import { useQuery } from "@tanstack/react-query";
import { sendChatMessage, type ChatRequest, type ChatResponse } from "@/lib/api";
import { queryKeys } from "@/lib/queryKeys";
import { CapabilityGate } from "@/components/capability/CapabilityGate";
import { Brain, Sparkles } from "lucide-react";
import { useState } from "react";

interface AICardProps {
  journeyRequest: {
    pickup_lat: number;
    pickup_lon: number;
    dropoff_lat: number;
    dropoff_lon: number;
    departure_time: string;
    vehicle_type: string;
  };
  fare?: string;
  duration?: string;
  demand?: string;
  surge?: string;
}

function AICardSkeleton() {
  return (
    <Card>
      <CardTitle className="font-display text-base tracking-wide flex items-center gap-2">
        <Brain className="h-4 w-4 text-brass" />
        AI Recommendation
      </CardTitle>
      <div className="mt-3 space-y-3">
        <Skeleton className="h-12 w-full" />
        <Skeleton className="h-8 w-3/4" />
      </div>
    </Card>
  );
}

function AICardContent({ data, isStreaming }: { data: ChatResponse | null; isStreaming: boolean }) {
  if (!data) return null;

  return (
    <Card className="relative overflow-hidden">
      <div className="absolute inset-0 bg-gradient-to-r from-brass/5 via-transparent to-verdigris/5" />
      <CardTitle className="font-display text-base tracking-wide flex items-center gap-2 relative z-10">
        <Sparkles className="h-4 w-4 text-brass" />
        AI Recommendation
        <span className="ml-auto flex items-center gap-1.5 text-xs px-2 py-0.5 rounded-full bg-brass/10 text-brass border border-brass/30">
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-brass opacity-75" />
            <span className="relative inline-flex rounded-full h-2 w-2 bg-brass" />
          </span>
          {data.route === "numeric" ? "SQL grounded" : "Retrieval grounded"}
        </span>
      </CardTitle>
      <div className="mt-3 relative z-10">
        <p className="text-ink-primary whitespace-pre-wrap leading-relaxed">
          {data.answer}
        </p>
        {data.sql && (
          <details className="mt-3 group">
            <summary className="flex items-center gap-2 text-xs text-ink-muted cursor-pointer hover:text-ink-primary">
              <span className="font-mono">SQL</span>
              <span className="text-[10px] text-ink-muted/70">(click to expand)</span>
            </summary>
            <pre className="mt-2 p-3 text-xs font-mono text-ink-secondary bg-surface-1 rounded-lg overflow-x-auto border border-surface-border">
              {data.sql}
            </pre>
          </details>
        )}
      </div>
    </Card>
  );
}

export function AICard({
  journeyRequest,
  fare,
  duration,
  demand,
  surge
}: AICardProps) {
  const [recommendation, setRecommendation] = useState<ChatResponse | null>(null);
  const [isStreaming, setIsStreaming] = useState(false);

  const prompt = `Given a journey from (${journeyRequest.pickup_lat.toFixed(4)}, ${journeyRequest.pickup_lon.toFixed(4)}) to (${journeyRequest.dropoff_lat.toFixed(4)}, ${journeyRequest.dropoff_lon.toFixed(4)}) at ${journeyRequest.departure_time}, vehicle: ${journeyRequest.vehicle_type}${fare ? `, fare: ${fare}` : ""}${duration ? `, duration: ${duration}` : ""}${demand ? `, demand: ${demand}` : ""}${surge ? `, surge: ${surge}` : ""}. Provide a 2-sentence recommendation.`;

  const { data: chatData, isLoading, refetch } = useQuery({
    queryKey: queryKeys.chatHistory("journey-ai-card"), // stable key; manually triggered
    queryFn: async () => {
      setIsStreaming(true);
      try {
        const resp = await sendChatMessage({ question: prompt });
        setRecommendation(resp);
        return resp;
      } finally {
        setIsStreaming(false);
      }
    },
    enabled: false, // Manual trigger
    staleTime: 5 * 60_000,
  });

  // Auto-fetch on mount when we have the data context
  // In a real app, this would be triggered by the parent when all predictions are ready

  return (
    <CapabilityGate capability="chat" fallback={<AICardSkeleton />}>
      {isLoading || isStreaming ? <AICardSkeleton /> : recommendation ? (
        <AICardContent data={recommendation} isStreaming={isStreaming} />
      ) : (
        <Card>
          <CardTitle className="font-display text-base tracking-wide flex items-center gap-2">
            <Brain className="h-4 w-4 text-brass" />
            AI Recommendation
          </CardTitle>
          <div className="mt-3">
            <button
              onClick={() => refetch()}
              className="w-full py-2 px-4 text-sm font-medium text-ink-primary bg-brass/10 border border-brass/30 rounded-lg hover:bg-brass/20 transition-colors"
            >
              Generate Recommendation
            </button>
            <p className="mt-2 text-xs text-ink-muted text-center">
              AI analyzes fare, demand, surge, and context to recommend optimal departure
            </p>
          </div>
        </Card>
      )}
    </CapabilityGate>
  );
}
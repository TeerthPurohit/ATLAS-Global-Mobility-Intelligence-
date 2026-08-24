// Query key factories for TanStack Query - consistent invalidation and caching
// All keys are tuples for proper serialization and partial matching

export const queryKeys = {
  // Countries & Cities
  cities: (params?: Record<string, unknown>) => ["cities", params] as const,
  zoneDemandTotals: () => ["zone-demand-totals"] as const,
  zones: () => ["zones"] as const,
  cityProfile: () => ["city", "profile"] as const,
  cityCapabilities: () => ["city", "capabilities"] as const,
  cityTariff: () => ["city", "tariff"] as const,

  // Journey
  journeyEstimate: (req: unknown) => ["journey", "estimate", req] as const,
  journeyHistory: (limit: number) => ["journey", "history", limit] as const,

  // Mobility (granular)
  route: (req: unknown) => ["mobility", "route", req] as const,
  fare: (req: unknown) => ["mobility", "fare", req] as const,
  demand: (req: unknown) => ["mobility", "demand", req] as const,
  congestion: (req: unknown) => ["mobility", "congestion", req] as const,
  availability: (req: unknown) => ["mobility", "availability", req] as const,
  surge: (req: unknown) => ["mobility", "surge", req] as const,
  carbon: (req: unknown) => ["mobility", "carbon", req] as const,
  bestDeparture: (req: unknown) => ["mobility", "bestDeparture", req] as const,

  // Context
  weather: (params?: Record<string, unknown>) => ["context", "weather", params] as const,
  holiday: (params?: Record<string, unknown>) => ["context", "holiday", params] as const,
  traffic: (params?: Record<string, unknown>) => ["context", "traffic", params] as const,

  // Chat
  chatHistory: (sessionId: string) => ["chat", "history", sessionId] as const,

  // Insights
  insights: (limit: number) => ["insights", limit] as const,

  // Analytics
  analyticsSummary: () => ["analytics", "summary"] as const,
  analyticsInsights: () => ["analytics", "insights"] as const,
  analyticsHistory: (limit: number, offset: number) => ["analytics", "history", limit, offset] as const,
  analyticsTrends: (period: string) => ["analytics", "trends", period] as const,
} as const;

// Helper to create a stable key from a request object
export function createRequestKey(req: Record<string, unknown>): string {
  return JSON.stringify(req, Object.keys(req).sort());
}
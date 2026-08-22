// Query key factories for TanStack Query - consistent invalidation and caching
// All keys are tuples for proper serialization and partial matching

export const queryKeys = {
  // Countries & Cities
  cities: (params?: Record<string, unknown>) => ["cities", params] as const,
  zoneDemandTotals: () => ["zone-demand-totals"] as const,
  cityProfile: (cityId: string) => ["city", "profile", cityId] as const,
  cityCapabilities: (cityId: string) => ["city", "capabilities", cityId] as const,
  cityTariff: (cityId: string) => ["city", "tariff", cityId] as const,
  cityZones: (cityId: string) => ["city", "zones", cityId] as const,

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
  weather: (cityId: string, params?: Record<string, unknown>) => ["context", "weather", cityId, params] as const,
  holiday: (cityId: string, params?: Record<string, unknown>) => ["context", "holiday", cityId, params] as const,
  traffic: (cityId: string, params?: Record<string, unknown>) => ["context", "traffic", cityId, params] as const,

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
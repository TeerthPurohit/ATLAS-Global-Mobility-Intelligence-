// Typed client for the Journey Intelligence Engine API (backend/routers/journey.py).
// Mirrors backend/schemas.py exactly -- basis is structural (ADR-007), never
// optional: every field on JourneyEstimate is a PredictionOut, and UI code
// must branch on `basis`, never assume `value` is present/trustworthy.

export const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export type Basis = "computed" | "modeled_estimate" | "unavailable";

export interface PredictionOut {
  value: number | string | null;
  unit: string | null;
  basis: Basis;
  source: string;
  reason: string | null;
  data_vintage: string | null;
  value_usd: number | null;
}

export interface JourneyEstimate {
  city_id: string;
  distance: PredictionOut;
  duration: PredictionOut;
  fare: PredictionOut;
  fare_range: PredictionOut;
  demand: PredictionOut;
  carbon_emissions: PredictionOut;
  congestion: PredictionOut;
  ride_availability: PredictionOut;
  surge_risk: PredictionOut;
  best_departure_time: PredictionOut;
  confidence: PredictionOut;
  fare_breakdown: Record<string, PredictionOut>;
  ai_recommendation: PredictionOut;
}

export interface JourneyRequest {
  pickup_lat: number;
  pickup_lon: number;
  dropoff_lat: number;
  dropoff_lon: number;
  departure_time: string; // ISO 8601
  vehicle_type: string;
  // Explicit city (registered id, GeoNames id, or free-text place name).
  // Optional only for NYC/London -- auto-detected from pickup coordinates;
  // every other city must be named explicitly or every city-scoped field
  // (fare, demand, surge, availability) degrades to "unavailable".
  city_id?: string;
}

// A fare's `unit` is its ISO 4217 currency code ("USD", "INR", "JPY", ...).
// Intl.NumberFormat handles symbol, digit grouping, and decimal precision
// per currency -- no symbol table or formatting library needed.
export function formatCurrency(value: number, currencyCode: string, locale = "en-US"): string {
  try {
    return new Intl.NumberFormat(locale, { style: "currency", currency: currencyCode }).format(value);
  } catch {
    return `${value.toFixed(2)} ${currencyCode}`;
  }
}

export async function estimateJourney(req: JourneyRequest): Promise<JourneyEstimate> {
  const resp = await fetch(`${API_BASE_URL}/journey/estimate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
  if (!resp.ok) {
    throw new Error(`journey/estimate failed: ${resp.status} ${await resp.text()}`);
  }
  return resp.json();
}

export const VEHICLE_CLASSES = ["bike", "auto", "mini", "sedan", "suv", "ev", "premium"] as const;
export type VehicleClass = (typeof VEHICLE_CLASSES)[number];

export interface JourneyHistoryEntry {
  id: number;
  requested_at: string;
  pickup_lat: number;
  pickup_lon: number;
  dropoff_lat: number;
  dropoff_lon: number;
  departure_time: string;
  vehicle_type: string;
  fare_value: string | null;
  fare_basis: Basis | null;
  confidence_value: number | null;
  response_json: string;
}

export async function getJourneyHistory(limit = 50): Promise<JourneyHistoryEntry[]> {
  const resp = await fetch(`${API_BASE_URL}/journey/history?limit=${limit}`);
  if (!resp.ok) {
    throw new Error(`journey/history failed: ${resp.status} ${await resp.text()}`);
  }
  return resp.json();
}

// --- Chat / AI Analyst (backend/routers/chat.py) ---

export type ChatRoute = "sql" | "retrieval";

export interface ChatRequest {
  question: string;
  session_id?: string;
}

export interface ChatResponse {
  answer: string;
  route: ChatRoute;
  sql?: string | null;
  session_id: string;
}

export interface ChatMessage {
  role: string;
  content: string;
  route?: ChatRoute | null;
  sql?: string | null;
  timestamp: string;
}

export async function sendChatMessage(req: ChatRequest): Promise<ChatResponse> {
  const resp = await fetch(`${API_BASE_URL}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
  if (!resp.ok) {
    throw new Error(`chat failed: ${resp.status} ${await resp.text()}`);
  }
  return resp.json();
}

export async function getChatHistory(sessionId: string): Promise<ChatMessage[]> {
  const resp = await fetch(`${API_BASE_URL}/chat/history/${sessionId}`);
  if (!resp.ok) {
    throw new Error(`chat/history failed: ${resp.status} ${await resp.text()}`);
  }
  return resp.json();
}

// Frame shapes yielded by WS /chat/stream (backend/routers/chat.py, rag/rag_pipeline.py):
// {type: "chunk", text} zero or more times, then one {type: "done", payload: ChatResponse-ish},
// or {error: string} on failure.
export interface ChatStreamChunk {
  type: "chunk";
  text: string;
}
export interface ChatStreamDone {
  type: "done";
  payload: ChatResponse;
}
export interface ChatStreamError {
  error: string;
}
export type ChatStreamFrame = ChatStreamChunk | ChatStreamDone | ChatStreamError;

// --- Insights (backend/routers/platform.py -> rag/insight_generation) ---
// Real per-zone paragraphs grounded in mart data (see generate_insight_docs.py's
// validate_grounding()) -- never fabricated copy on this page.

export interface InsightTopHour {
  hour: number;
  total_trips: number;
  share_pct: number;
}

export interface InsightTopDestination {
  zone: string;
  trip_count: number;
}

export interface InsightDoc {
  zone_id: number;
  zone_name: string;
  borough: string;
  total_trips: number;
  avg_fare: number | null;
  avg_distance_miles: number | null;
  top_hours: InsightTopHour[];
  top_destination: InsightTopDestination | null;
  pagerank_rank: number | null;
  pagerank_score: number | null;
  pagerank_total_zones: number | null;
  sources: Record<string, string>;
  text: string;
  phrased_by: string;
}

export async function getInsights(limit = 20): Promise<InsightDoc[]> {
  const resp = await fetch(`${API_BASE_URL}/insights?limit=${limit}`);
  if (!resp.ok) {
    throw new Error(`insights failed: ${resp.status} ${await resp.text()}`);
  }
  return resp.json();
}

export function streamChat(
  req: ChatRequest,
  handlers: { onFrame: (frame: ChatStreamFrame) => void; onError?: (err: Event) => void; onClose?: () => void }
): () => void {
  const wsUrl = `${API_BASE_URL.replace(/^http/, "ws")}/chat/stream`;
  const ws = new WebSocket(wsUrl);
  ws.onopen = () => ws.send(JSON.stringify(req));
  ws.onmessage = (evt) => handlers.onFrame(JSON.parse(evt.data));
  ws.onerror = (evt) => handlers.onError?.(evt);
  ws.onclose = () => handlers.onClose?.();
  return () => ws.close();
}

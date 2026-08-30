// Typed client for the Journey Intelligence Engine API (backend/routers/journey.py).
// Mirrors backend/schemas.py exactly -- basis is structural (ADR-007), never
// optional: every field on JourneyEstimate is a PredictionOut, and UI code
// must branch on `basis`, never assume `value` is present/trustworthy.

// Same-origin, relative -- every call in this file is proxied server-side to
// the FastAPI backend by next.config.js's rewrites(). The browser never sees
// the backend's real host/port (no NEXT_PUBLIC_* env var here on purpose).
export const API_BASE_URL = "/api";

export type Basis = "computed" | "modeled_estimate" | "unavailable";

export interface PredictionOut {
  value: number | string | null;
  unit: string | null;
  basis: Basis;
  source: string;
  reason: string | null;
  data_vintage: string | null;
  value_usd: number | null;
  confidence?: number | null;
  method?: string | null;
  ui_label?: string | null;
  model_version?: string | null;
}

export interface MobilityResponse {
  value: number | null;
  unit: string | null;
  status: Basis;
  method: string;
  source: string;
  confidence: number;
  reason: string | null;
}

export function mobilityToPrediction(mob: MobilityResponse): PredictionOut {
  return {
    value: mob.value,
    unit: mob.unit,
    basis: mob.status || "unavailable",
    source: mob.source || "mobility/engine",
    reason: mob.reason || null,
    data_vintage: null,
    value_usd: null,
    confidence: mob.confidence ?? null,
    method: mob.method ?? null,
  };
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
  city_id?: string;
}

export async function getJourneyHistory(limit = 50): Promise<JourneyHistoryEntry[]> {
  const resp = await fetch(`${API_BASE_URL}/journey/history?limit=${limit}`);
  if (!resp.ok) {
    throw new Error(`journey/history failed: ${resp.status} ${await resp.text()}`);
  }
  return resp.json();
}

// --- Chat / AI Analyst (backend/routers/chat.py) ---

export type ChatRoute = "numeric" | "explanatory";

export interface ChatRequest {
  question: string;
  session_id?: string;
  area_id?: number;
}

export interface ChatResponse {
  answer: string;
  route: ChatRoute;
  sql?: string | null;
  session_id: string;
  city_id?: string | null;
  area_id?: number | null;
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
    credentials: "include",
    body: JSON.stringify(req),
  });
  if (!resp.ok) {
    throw new Error(`chat failed: ${resp.status} ${await resp.text()}`);
  }
  return resp.json();
}

export async function getChatHistory(sessionId: string): Promise<ChatMessage[]> {
  const resp = await fetch(`${API_BASE_URL}/chat/history/${sessionId}`, { credentials: "include" });
  if (!resp.ok) {
    throw new Error(`chat/history failed: ${resp.status} ${await resp.text()}`);
  }
  return resp.json();
}

export interface ChatSessionSummary {
  session_id: string;
  title: string | null;
  last_activity: string;
  message_count: number;
}

// Creates a new chat session, or reuses the caller's existing empty one --
// mirrors ChatGPT/Claude's "New Chat" not piling up blank conversations.
export async function createChatSession(): Promise<{ session_id: string }> {
  const resp = await fetch(`${API_BASE_URL}/chat/sessions`, { method: "POST", credentials: "include" });
  if (!resp.ok) {
    throw new Error(`chat/sessions create failed: ${resp.status} ${await resp.text()}`);
  }
  return resp.json();
}

export async function listChatSessions(): Promise<ChatSessionSummary[]> {
  const resp = await fetch(`${API_BASE_URL}/chat/sessions`, { credentials: "include" });
  if (!resp.ok) {
    throw new Error(`chat/sessions list failed: ${resp.status} ${await resp.text()}`);
  }
  return resp.json();
}

export async function deleteChatSession(sessionId: string): Promise<void> {
  const resp = await fetch(`${API_BASE_URL}/chat/sessions/${sessionId}`, { method: "DELETE", credentials: "include" });
  if (!resp.ok) {
    throw new Error(`chat/sessions delete failed: ${resp.status} ${await resp.text()}`);
  }
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
  // API_BASE_URL is a relative path now (proxied), so build the ws(s):// URL
  // from the current page's own origin instead of string-swapping http->ws.
  const wsProtocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const wsUrl = `${wsProtocol}//${window.location.host}${API_BASE_URL}/chat/stream`;
  const ws = new WebSocket(wsUrl);
  ws.onopen = () => ws.send(JSON.stringify(req));
  ws.onmessage = (evt) => handlers.onFrame(JSON.parse(evt.data));
  ws.onerror = (evt) => handlers.onError?.(evt);
  ws.onclose = () => handlers.onClose?.();
  return () => ws.close();
}

// ============================================================================
// Cities (backend/routers/cities.py)
// ============================================================================

export interface City {
  id: string;
  name: string;
  country_code: string;
  latitude: number;
  longitude: number;
  timezone: string;
  currency: string;
  model_status: string;
  data_source: string;
  geography_type: string;
  mobility_mode: string;
}

export interface Capabilities {
  demand: boolean;
  fare: boolean;
  journey: boolean;
  chat: boolean;
  area_analysis: boolean;
  routing: boolean;
  congestion: boolean;
  availability: boolean;
  surge: boolean;
  carbon: boolean;
  best_departure: boolean;
  chat_tier: "full_rag" | "sql_only";
  mobility_mode: string;
  area_type: string;
  forecast: boolean;
  transit_coverage: boolean;
}

export interface CityProfileResponse {
  id: string;
  name: string;
  country_code: string;
  country: string;
  latitude: number;
  longitude: number;
  timezone: string;
  currency: string;
  tier: string;
  population: number | null;
  model_status: string;
  data_source: string;
  geography_type: string;
  mobility_mode: string;
  confidence: number;
  data_availability: Record<string, boolean>;
}

export interface CityTariffResponse {
  available: boolean;
  city_id: string;
  reason: string | null;
  currency: string | null;
  base_fare: number | null;
  per_km: number | null;
  per_min: number | null;
  min_fare: number | null;
  night_multiplier: number | null;
  airport_surcharge: number | null;
  booking_fee: number | null;
  platform_fee: number | null;
  tolls: number | null;
  peak_multiplier: number | null;
  vehicle_multiplier: number | null;
  surge_multiplier: number | null;
  effective_from: string | null;
  version: string | null;
  source_type: string | null;
  confidence: number | null;
  notes: string | null;
  generated_at: string | null;
  model_id: string | null;
  // null = never evidence/analytically validated.
  validation_method: string | null;
  evidence_sources: string | null;
  validated_at: string | null;
}

// ============================================================================
// Mobility API (backend/routers/mobility.py)
// ============================================================================

export interface Coordinates {
  lat: number;
  lon: number;
}

export interface JourneyContextRequest {
  pickup: Coordinates;
  dropoff: Coordinates;
  departure_time: string;
  vehicle_type: string;
}

export interface RouteRequest extends JourneyContextRequest {}

export interface PredictionRequest extends JourneyContextRequest {
  distance_km?: number | null;
  duration_min?: number | null;
}

export interface RouteResponse {
  distance: MobilityResponse;
  duration: MobilityResponse;
  request_id: string | null;
  timestamp: string | null;
}

export interface FareBreakdown {
  base: number | null;
  vehicle: number | null;
  traffic: number | null;
  weather: number | null;
  demand: number | null;
  total: number | null;
}

export interface FareResponse {
  fare: MobilityResponse;
  breakdown: FareBreakdown;
  currency: string;
  request_id: string | null;
  timestamp: string | null;
}

export interface DemandResponse {
  demand: MobilityResponse;
  request_id: string | null;
  timestamp: string | null;
}

export interface CongestionResponse {
  congestion: MobilityResponse;
  request_id: string | null;
  timestamp: string | null;
}

export interface AvailabilityResponse {
  availability: MobilityResponse;
  request_id: string | null;
  timestamp: string | null;
}

export interface SurgeResponse {
  surge: MobilityResponse;
  request_id: string | null;
  timestamp: string | null;
}

export interface CarbonResponse {
  carbon: MobilityResponse;
  request_id: string | null;
  timestamp: string | null;
}

export interface DepartureTimeResponse {
  recommended_departure: string | null;
  reason: string | null;
  confidence: number;
  status: Basis;
  request_id: string | null;
  timestamp: string | null;
}

// ============================================================================
// Context API (backend/routers/context.py)
// ============================================================================

export interface WeatherResponse {
  temperature: number | null;
  humidity: number | null;
  precipitation: number | null;
  wind_speed: number | null;
  weather_condition: string | null;
  severity: number | null;
  source: string;
  timestamp: string;
  city_id: string;
}

export interface HolidayResponse {
  is_holiday: boolean;
  holiday_name: string | null;
  country: string;
  date: string;
  source: string;
}

export interface TrafficResponse {
  congestion_level: number | null;
  source: string;
  is_live: boolean;
  timestamp: string;
  city_id: string;
  note: string | null;
}

// ============================================================================
// Analytics API (backend/routers/analytics.py)
// ============================================================================

export interface AnalyticsSummaryResponse {
  total_predictions: number;
  cities_served: number;
  date_range: { start: string | null; end: string | null };
  top_cities: Record<string, unknown>[];
}

export interface AnalyticsInsightsResponse {
  insights: Record<string, unknown>[];
}

export interface AnalyticsHistoryResponse {
  history: Record<string, unknown>[];
  limit: number;
  offset: number;
}

export interface AnalyticsTrendsResponse {
  trends: Record<string, number[]>;
  period: string;
}

// ============================================================================
// API Functions
// ============================================================================

async function fetchJson<T>(path: string, init?: RequestInit): Promise<T> {
  const resp = await fetch(`${API_BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json", ...init?.headers },
    credentials: "include",
    ...init,
  });
  if (!resp.ok) {
    throw new Error(`${path} failed: ${resp.status} ${await resp.text()}`);
  }
  return resp.json();
}

// --- Auth (backend/routers/auth.py) ---

export interface AuthUser {
  id: number;
  email: string;
  created_at: string;
}

// backend/errors.py's DomainError handler always returns {"error": {"code", "message"}} --
// surface .message directly rather than the generic fetchJson error text, so
// the login/signup forms can show "Invalid email or password" instead of a raw HTTP error.
async function postAuth(path: "/auth/signup" | "/auth/login", email: string, password: string): Promise<AuthUser> {
  const resp = await fetch(`${API_BASE_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({ email, password }),
  });
  if (!resp.ok) {
    const body = await resp.json().catch(() => null);
    throw new Error(body?.error?.message ?? `${path} failed: ${resp.status}`);
  }
  return resp.json();
}

export async function signup(email: string, password: string): Promise<AuthUser> {
  return postAuth("/auth/signup", email, password);
}

export async function login(email: string, password: string): Promise<AuthUser> {
  return postAuth("/auth/login", email, password);
}

export async function loginAsDemo(): Promise<AuthUser> {
  const demoEmail = "analyst@atlas.nyc";
  const demoPassword = "atlas_demo_pass_2026";
  try {
    return await login(demoEmail, demoPassword);
  } catch {
    // If demo user does not exist in fresh DB, auto-register it
    try {
      return await signup(demoEmail, demoPassword);
    } catch {
      return await login(demoEmail, demoPassword);
    }
  }
}

export async function logout(): Promise<void> {
  await fetchJson("/auth/logout", { method: "POST" });
}

// Returns null if not logged in (401) rather than throwing -- that's the
// expected, non-error state on first load / after logout.
export async function getMe(): Promise<AuthUser | null> {
  const resp = await fetch(`${API_BASE_URL}/auth/me`, { credentials: "include" });
  if (resp.status === 401) return null;
  if (!resp.ok) {
    throw new Error(`auth/me failed: ${resp.status} ${await resp.text()}`);
  }
  return resp.json();
}

// The served city's real zone bbox -- mirrors backend/services/
// geography_service.py's _NYC_BBOX exactly, so a pickup inside the city
// resolves the same way client-side (avoiding a network round trip) as it
// would server-side.
const CITY_BBOX = { minLat: 40.49, minLon: -74.26, maxLat: 40.92, maxLon: -73.68 };

/**
 * Whether a picked point is inside the served city's zone coverage.
 *
 * This was `resolveCityId(lat, lon): "nyc" | null` before ADR-013. No call
 * needs a city id any more, but the *coverage* half of that answer is still
 * real: outside the bbox, every zone-keyed field (fare, demand, surge,
 * availability) degrades to "unavailable", and callers must show that rather
 * than silently pretending the point is in the city.
 */
export function isInCoverage(lat: number, lon: number): boolean {
  return lat >= CITY_BBOX.minLat && lat <= CITY_BBOX.maxLat
    && lon >= CITY_BBOX.minLon && lon <= CITY_BBOX.maxLon;
}

export async function getCityProfile(): Promise<CityProfileResponse> {
  return fetchJson<CityProfileResponse>("/api/profile");
}

export async function getCapabilities(): Promise<Capabilities> {
  return fetchJson<Capabilities>("/api/capabilities");
}

export async function getTariff(): Promise<CityTariffResponse> {
  return fetchJson<CityTariffResponse>("/api/tariff");
}

export interface Zone {
  zone_id: number;
  zone: string;
  borough: string;
  service_zone: string | null;
  latitude: number;
  longitude: number;
}

// The city-scoped /api/cities/{id}/zones wrapper was deleted in ADR-013 --
// it only ever re-served this route's rows inside an availability envelope.
export async function getZones(): Promise<Zone[]> {
  return fetchJson<Zone[]>("/zones");
}

// Per-zone measured trip totals backing the landing map's choropleth.
// Precomputed at backend startup from zone_hourly_demand.
export interface ZoneDemandTotal {
  location_id: number;
  zone: string;
  borough: string;
  total_trips: number;
  avg_fare: number | null;
}

export async function getZoneDemandTotals(): Promise<ZoneDemandTotal[]> {
  return fetchJson<ZoneDemandTotal[]>("/marts/zone_demand_totals");
}

// Mobility
export async function getRoute(req: RouteRequest): Promise<RouteResponse> {
  return fetchJson<RouteResponse>("/api/mobility/route", { method: "POST", body: JSON.stringify(req) });
}

export async function getFare(req: PredictionRequest): Promise<FareResponse> {
  return fetchJson<FareResponse>("/api/mobility/fare", { method: "POST", body: JSON.stringify(req) });
}

export async function getDemand(req: PredictionRequest): Promise<DemandResponse> {
  return fetchJson<DemandResponse>("/api/mobility/demand", { method: "POST", body: JSON.stringify(req) });
}

export async function getCongestion(req: PredictionRequest): Promise<CongestionResponse> {
  return fetchJson<CongestionResponse>("/api/mobility/congestion", { method: "POST", body: JSON.stringify(req) });
}

export async function getAvailability(req: PredictionRequest): Promise<AvailabilityResponse> {
  return fetchJson<AvailabilityResponse>("/api/mobility/availability", { method: "POST", body: JSON.stringify(req) });
}

export async function getSurge(req: PredictionRequest): Promise<SurgeResponse> {
  return fetchJson<SurgeResponse>("/api/mobility/surge", { method: "POST", body: JSON.stringify(req) });
}

export async function getCarbon(req: PredictionRequest): Promise<CarbonResponse> {
  return fetchJson<CarbonResponse>("/api/mobility/carbon", { method: "POST", body: JSON.stringify(req) });
}

export async function getBestDeparture(req: PredictionRequest): Promise<DepartureTimeResponse> {
  return fetchJson<DepartureTimeResponse>("/api/mobility/departure-time", { method: "POST", body: JSON.stringify(req) });
}

// Context
export async function getWeather(lat?: number, lon?: number, timestamp?: string): Promise<WeatherResponse> {
  const params = new URLSearchParams();
  if (lat !== undefined) params.set("lat", String(lat));
  if (lon !== undefined) params.set("lon", String(lon));
  if (timestamp) params.set("timestamp", timestamp);
  return fetchJson<WeatherResponse>(`/api/context/weather?${params.toString()}`);
}

export async function getHoliday(lat?: number, lon?: number, date?: string): Promise<HolidayResponse> {
  const params = new URLSearchParams();
  if (lat !== undefined) params.set("lat", String(lat));
  if (lon !== undefined) params.set("lon", String(lon));
  if (date) params.set("date", date);
  return fetchJson<HolidayResponse>(`/api/context/holiday?${params.toString()}`);
}

export async function getTraffic(lat?: number, lon?: number): Promise<TrafficResponse> {
  const params = new URLSearchParams();
  if (lat !== undefined) params.set("lat", String(lat));
  if (lon !== undefined) params.set("lon", String(lon));
  return fetchJson<TrafficResponse>(`/api/context/traffic?${params.toString()}`);
}

// Analytics
export async function getAnalyticsSummary(): Promise<AnalyticsSummaryResponse> {
  return fetchJson<AnalyticsSummaryResponse>("/api/analytics/summary");
}

export async function getAnalyticsInsights(): Promise<AnalyticsInsightsResponse> {
  return fetchJson<AnalyticsInsightsResponse>("/api/analytics/insights");
}

export async function getAnalyticsHistory(limit = 100, offset = 0): Promise<AnalyticsHistoryResponse> {
  return fetchJson<AnalyticsHistoryResponse>(`/api/analytics/history?limit=${limit}&offset=${offset}`);
}

export async function getAnalyticsTrends(period = "30d"): Promise<AnalyticsTrendsResponse> {
  return fetchJson<AnalyticsTrendsResponse>(`/api/analytics/trends?period=${period}`);
}

export async function getDocsSpec(): Promise<any> {
  return fetchJson<any>("/api/docs/spec");
}


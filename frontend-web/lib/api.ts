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
  city_id?: string;
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

// --- Tariff enrichment (WS /api/cities/{city_id}/tariff/enrich, backend/routers/cities.py) ---
// Fires once per city, the first time its page is opened with a never-validated
// tariff profile (validation_method === null) -- see tariff_enrichment.py.

export interface TariffEnrichStatusFrame {
  type: "status";
  message: string;
}
export interface TariffEnrichResultFrame {
  type: "result";
  profile: TariffProfilePayload;
  cached?: boolean;
}
export interface TariffEnrichErrorFrame {
  type: "error";
  message: string;
}
export type TariffEnrichFrame = TariffEnrichStatusFrame | TariffEnrichResultFrame | TariffEnrichErrorFrame;

// Raw shape of the backend TariffProfile dataclass (backend/services/tariff_profiles.py),
// sent as-is in the WS result frame. Overlaps CityTariffResponse but adds `source`
// ("measured" | "llm_anchored") and `extras_backfilled_at`, which mergeTariffProfile drops.
export interface TariffProfilePayload {
  city_id: string;
  currency: string;
  base_fare: number;
  per_km: number;
  per_min: number;
  min_fare: number;
  night_multiplier: number;
  airport_surcharge: number;
  source: string;
  generated_at: string;
  model_id: string;
  confidence: number;
  notes: string;
  booking_fee: number | null;
  platform_fee: number | null;
  tolls: number | null;
  peak_multiplier: number | null;
  vehicle_multiplier: number | null;
  surge_multiplier: number | null;
  effective_from: string | null;
  version: string | null;
  source_type: string | null;
  extras_backfilled_at: string | null;
  evidence_sources: string | null;
  validation_method: string | null;
  validated_at: string | null;
}

// Merges a WS result frame's profile into the displayed CityTariffResponse without
// a refetch -- fields not present on TariffProfilePayload (available, reason) are
// set explicitly rather than assumed.
export function mergeTariffProfile(base: CityTariffResponse, profile: TariffProfilePayload): CityTariffResponse {
  return {
    ...base,
    available: true,
    city_id: profile.city_id,
    reason: null,
    currency: profile.currency,
    base_fare: profile.base_fare,
    per_km: profile.per_km,
    per_min: profile.per_min,
    min_fare: profile.min_fare,
    night_multiplier: profile.night_multiplier,
    airport_surcharge: profile.airport_surcharge,
    booking_fee: profile.booking_fee,
    platform_fee: profile.platform_fee,
    tolls: profile.tolls,
    peak_multiplier: profile.peak_multiplier,
    vehicle_multiplier: profile.vehicle_multiplier,
    surge_multiplier: profile.surge_multiplier,
    effective_from: profile.effective_from,
    version: profile.version,
    source_type: profile.source_type,
    confidence: profile.confidence,
    notes: profile.notes,
    generated_at: profile.generated_at,
    model_id: profile.model_id,
    validation_method: profile.validation_method,
    evidence_sources: profile.evidence_sources,
    validated_at: profile.validated_at,
  };
}

export function streamTariffEnrichment(
  cityId: string,
  handlers: { onFrame: (frame: TariffEnrichFrame) => void; onError?: (err: Event) => void; onClose?: () => void }
): () => void {
  const wsUrl = `${API_BASE_URL.replace(/^http/, "ws")}/api/cities/${cityId}/tariff/enrich`;
  const ws = new WebSocket(wsUrl);
  ws.onmessage = (evt) => handlers.onFrame(JSON.parse(evt.data));
  ws.onerror = (evt) => handlers.onError?.(evt);
  ws.onclose = () => handlers.onClose?.();
  return () => ws.close();
}

// ============================================================================
// Countries & Cities (backend/routers/cities.py, countries registry)
// ============================================================================

export interface Country {
  iso_code: string;
  name: string;
  supported: boolean;
  supported_city_count: number;
}

export interface City {
  id: string;
  name: string;
  country_code: string;
  latitude: number;
  longitude: number;
  timezone: string;
  currency: string;
  model_status: "OBSERVED" | "TRANSFER" | "NONE";
  data_source: string;
  geography_type: string;
  mobility_mode: string;
}

export interface CitySearchParams {
  q?: string;
  country?: string;
  tier?: string;
  supported?: boolean;
  page?: number;
  limit?: number;
}

export interface CitySearchResponse {
  results: City[];
  total: number;
  page: number;
  limit: number;
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
  chat_tier: "full_rag" | "sql_only" | "context_only";
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
  // null = never evidence/analytically validated -- see WS /api/cities/{city_id}/tariff/enrich.
  validation_method: string | null;
  evidence_sources: string | null;
  validated_at: string | null;
}

export interface CityZone {
  zone_id: number;
  zone: string;
  borough: string;
  service_zone: string | null;
  latitude: number;
  longitude: number;
}

export interface CityZonesResponse {
  available: boolean;
  city_id: string;
  reason: string | null;
  zones: CityZone[] | null;
}

// ============================================================================
// Mobility API (backend/routers/mobility.py)
// ============================================================================

export interface Coordinates {
  lat: number;
  lon: number;
}

export interface JourneyContextRequest {
  city_id: string;
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
    ...init,
  });
  if (!resp.ok) {
    throw new Error(`${path} failed: ${resp.status} ${await resp.text()}`);
  }
  return resp.json();
}

// Countries & Cities
export async function getCountries(): Promise<Country[]> {
  const resp = await fetchJson<Country[] | { countries: Country[] }>("/api/countries");
  return Array.isArray(resp) ? resp : resp.countries || [];
}

export async function searchCities(params: CitySearchParams = {}): Promise<CitySearchResponse> {
  const searchParams = new URLSearchParams();
  if (params.q) searchParams.set("q", params.q);
  if (params.country) searchParams.set("country", params.country);
  if (params.tier) searchParams.set("tier", params.tier);
  if (params.supported !== undefined) searchParams.set("supported", String(params.supported));
  if (params.page) searchParams.set("page", String(params.page));
  if (params.limit) searchParams.set("limit", String(params.limit));
  return fetchJson<CitySearchResponse>(`/api/cities?${searchParams.toString()}`);
}

// NYC/London's real zone/station bbox coverage -- mirrors backend/services/
// geography_service.py's _NYC_BBOX/_LONDON_BBOX exactly, so a pickup inside
// either city resolves the same way client-side (avoiding a network round
// trip for the two cities that don't need one) as it would server-side.
const NYC_BBOX = { minLat: 40.49, minLon: -74.26, maxLat: 40.92, maxLon: -73.68 };
const LONDON_BBOX = { minLat: 51.28, minLon: -0.51, maxLat: 51.70, maxLon: 0.33 };

function detectRegisteredCity(lat: number, lon: number): "nyc" | "london" | null {
  if (lat >= NYC_BBOX.minLat && lat <= NYC_BBOX.maxLat && lon >= NYC_BBOX.minLon && lon <= NYC_BBOX.maxLon) return "nyc";
  if (lat >= LONDON_BBOX.minLat && lat <= LONDON_BBOX.maxLat && lon >= LONDON_BBOX.minLon && lon <= LONDON_BBOX.maxLon) return "london";
  return null;
}

/**
 * Resolves a picked address to the real backend city_id that every
 * /api/mobility/* call needs -- NYC/London by bbox (no request needed),
 * anything else via /api/cities?q= (the mobility/WorldMove city registry --
 * same one City/capabilities/profile endpoints key off). Previously this
 * queried /api/geography/search/global, a broader any-place-on-earth
 * GeoNames search whose `id` is a GeoNames id, not a mobility-registry
 * city_id -- every /api/cities/{city_id}/profile|capabilities call for a
 * non-NYC/London address then 404'd (CITY_NOT_FOUND), silently breaking the
 * tier/capability-gated honest messaging for exactly the cities it exists to
 * describe. Returns null if nothing resolves (e.g. open ocean, or Nominatim
 * gave no city name to search on, or the place has no mobility coverage) --
 * callers should treat that as "unavailable", not silently fall back to nyc.
 */
export async function resolveCityId(lat: number, lon: number, city?: string, countryCode?: string): Promise<string | null> {
  const registered = detectRegisteredCity(lat, lon);
  if (registered) return registered;
  if (!city) return null;
  const params = new URLSearchParams({ q: city, limit: "1" });
  if (countryCode) params.set("country", countryCode.toUpperCase());
  try {
    const resp = await fetchJson<{ results: { id: string }[] }>(`/api/cities?${params.toString()}`);
    return resp.results[0]?.id ?? null;
  } catch {
    return null;
  }
}

export async function getCityProfile(cityId: string): Promise<CityProfileResponse> {
  return fetchJson<CityProfileResponse>(`/api/cities/${cityId}/profile`);
}

export async function getCityCapabilities(cityId: string): Promise<Capabilities> {
  return fetchJson<Capabilities>(`/api/cities/${cityId}/capabilities`);
}

export async function getCityTariff(cityId: string): Promise<CityTariffResponse> {
  return fetchJson<CityTariffResponse>(`/api/cities/${cityId}/tariff`);
}

export async function getCityZones(cityId: string): Promise<CityZonesResponse> {
  return fetchJson<CityZonesResponse>(`/api/cities/${cityId}/zones`);
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
export async function getWeather(cityId: string, lat?: number, lon?: number, timestamp?: string): Promise<WeatherResponse> {
  const params = new URLSearchParams({ city_id: cityId });
  if (lat !== undefined) params.set("lat", String(lat));
  if (lon !== undefined) params.set("lon", String(lon));
  if (timestamp) params.set("timestamp", timestamp);
  return fetchJson<WeatherResponse>(`/api/context/weather?${params.toString()}`);
}

export async function getHoliday(cityId: string, lat?: number, lon?: number, date?: string): Promise<HolidayResponse> {
  const params = new URLSearchParams({ city_id: cityId });
  if (lat !== undefined) params.set("lat", String(lat));
  if (lon !== undefined) params.set("lon", String(lon));
  if (date) params.set("date", date);
  return fetchJson<HolidayResponse>(`/api/context/holiday?${params.toString()}`);
}

export async function getTraffic(cityId: string, lat?: number, lon?: number): Promise<TrafficResponse> {
  const params = new URLSearchParams({ city_id: cityId });
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

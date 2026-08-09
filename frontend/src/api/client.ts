export const API_BASE_URL =
  localStorage.getItem("app_api_base_url") || import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export interface Zone {
  zone_id: number;
  zone: string;
  borough: string;
  service_zone?: string;
  latitude: number;
  longitude: number;
}

export interface DemandPrediction {
  zone_id: number;
  hour: number;
  day_of_week: number;
  predicted_demand: number;
  model: string;
}

export interface FarePrediction {
  pickup_zone: number;
  dropoff_zone: number;
  hour: number;
  predicted_fare: number;
  model: string;
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  route?: string;
  sql?: string;
  timestamp: string;
}

export interface ChatResponse {
  answer: string;
  route: string;
  sql?: string;
  session_id: string;
}

export async function fetchZones(): Promise<Zone[]> {
  const res = await fetch(`${API_BASE_URL}/zones`);
  if (!res.ok) throw new Error(`Failed to fetch zones: ${res.statusText}`);
  return res.json();
}

export async function fetchZone(zoneId: number): Promise<Zone> {
  const res = await fetch(`${API_BASE_URL}/zones/${zoneId}`);
  if (!res.ok) throw new Error(`Failed to fetch zone ${zoneId}`);
  return res.json();
}

export async function predictDemand(zoneId: number, hour: number, dayOfWeek: number): Promise<DemandPrediction> {
  const url = new URL(`${API_BASE_URL}/predict/demand`);
  url.searchParams.set("zone_id", zoneId.toString());
  url.searchParams.set("hour", hour.toString());
  url.searchParams.set("day_of_week", dayOfWeek.toString());
  const res = await fetch(url.toString());
  if (!res.ok) throw new Error(`Demand prediction failed: ${res.statusText}`);
  return res.json();
}

export async function predictFare(pickupZone: number, dropoffZone: number, hour: number): Promise<FarePrediction> {
  const url = new URL(`${API_BASE_URL}/predict/fare`);
  url.searchParams.set("pickup_zone", pickupZone.toString());
  url.searchParams.set("dropoff_zone", dropoffZone.toString());
  url.searchParams.set("hour", hour.toString());
  const res = await fetch(url.toString());
  if (!res.ok) throw new Error(`Fare prediction failed: ${res.statusText}`);
  return res.json();
}

export async function sendChatMessage(question: string, sessionId?: string): Promise<ChatResponse> {
  const res = await fetch(`${API_BASE_URL}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, session_id: sessionId }),
  });
  if (!res.ok) throw new Error(`Chat request failed: ${res.statusText}`);
  return res.json();
}

export async function fetchChatHistory(sessionId: string): Promise<ChatMessage[]> {
  const res = await fetch(`${API_BASE_URL}/chat/history/${sessionId}`);
  if (!res.ok) {
    if (res.status === 404) return [];
    throw new Error(`Failed to fetch chat history: ${res.statusText}`);
  }
  return res.json();
}

export interface HealthStatus {
  duckdb: "online" | "unavailable";
  qdrant: "online" | "unavailable";
  status: "healthy" | "degraded";
}

export interface DashboardSummary {
  total_trips: number;
  avg_fare: number;
  active_zones: number;
}

export interface HourlyDemandPoint {
  hour: number;
  demand: number;
  fare: number;
}

export interface WarehouseStats {
  row_counts: Record<string, number>;
  total_rows: number;
  warehouse_file_bytes: number;
  warehouse_last_modified: number;
}

export interface WarehouseTable {
  table: string;
  row_count: number;
  columns: { column_name: string; column_type: string; null: string }[];
}

export interface DemandModelMetrics {
  rmse: number;
  mae: number;
  latency_ms_per_row: number;
  n_rows: number;
  hyperparameters: Record<string, unknown> | null;
  feature_importances: Record<string, number> | null;
}

export interface ModelMetrics {
  demand: Record<string, DemandModelMetrics>;
  fare: {
    hyperparameters: Record<string, unknown>;
    feature_importances?: Record<string, number>;
    metrics: { val_rmse: number; val_mae: number; test_rmse: number; test_mae: number };
  } | null;
}

export interface AlgorithmBenchmarks {
  kdtree: {
    n_zones: number;
    tree_depth: number;
    n_queries: number;
    linear_scan_us_per_query: number;
    kdtree_us_per_query: number;
    speedup_x: number;
  } | null;
  pagerank: {
    damping: number;
    n_zones: number;
    n_edges: number;
    top_hubs: { rank: number; zone: string; pagerank_score: number; raw_weighted_degree: number }[];
  } | null;
}

export interface PipelineStatus {
  available: boolean;
  generated_at?: string;
  dbt_version?: string;
  elapsed_time_seconds?: number;
  stages: { unique_id: string; status: string; execution_time_seconds: number; rows_affected: number | null }[];
}

export async function fetchHealth(): Promise<HealthStatus> {
  const res = await fetch(`${API_BASE_URL}/health`);
  if (!res.ok) throw new Error(`Failed to fetch health: ${res.statusText}`);
  return res.json();
}

export async function fetchDashboardSummary(): Promise<DashboardSummary> {
  const res = await fetch(`${API_BASE_URL}/dashboard/summary`);
  if (!res.ok) throw new Error(`Failed to fetch dashboard summary: ${res.statusText}`);
  return res.json();
}

export async function fetchHourlyDemandProfile(): Promise<HourlyDemandPoint[]> {
  const res = await fetch(`${API_BASE_URL}/marts/zone_hourly_demand`);
  if (!res.ok) throw new Error(`Failed to fetch hourly demand mart: ${res.statusText}`);
  return res.json();
}

export async function fetchWarehouseStats(): Promise<WarehouseStats> {
  const res = await fetch(`${API_BASE_URL}/warehouse/stats`);
  if (!res.ok) throw new Error(`Failed to fetch warehouse stats: ${res.statusText}`);
  return res.json();
}

export async function fetchWarehouseTables(): Promise<WarehouseTable[]> {
  const res = await fetch(`${API_BASE_URL}/warehouse/tables`);
  if (!res.ok) throw new Error(`Failed to fetch warehouse tables: ${res.statusText}`);
  return res.json();
}

export async function fetchModelMetrics(): Promise<ModelMetrics> {
  const res = await fetch(`${API_BASE_URL}/models/metrics`);
  if (!res.ok) throw new Error(`Failed to fetch model metrics: ${res.statusText}`);
  return res.json();
}

export async function fetchAlgorithmBenchmarks(): Promise<AlgorithmBenchmarks> {
  const res = await fetch(`${API_BASE_URL}/algorithms/benchmarks`);
  if (!res.ok) throw new Error(`Failed to fetch algorithm benchmarks: ${res.statusText}`);
  return res.json();
}

export async function fetchPipelineStatus(): Promise<PipelineStatus> {
  const res = await fetch(`${API_BASE_URL}/pipeline/status`);
  if (!res.ok) throw new Error(`Failed to fetch pipeline status: ${res.statusText}`);
  return res.json();
}

// ── Global Mobility Domain Model API Extensions ──────────────────────────────

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
  status: string;
  data_source: string;
  geography_type: string;
  model_status: string;
  last_updated: string;
}

export interface Capabilities {
  demand: boolean;
  fare: boolean;
  journey: boolean;
  chat: boolean;
  area_analysis: boolean;
}

export interface Area {
  area_id: number;
  city_id: string;
  name: string;
  area_type: string;
  parent_area_id?: string | null;
  latitude?: number | null;
  longitude?: number | null;
}

export interface CapabilityUnavailable {
  available: false;
  capability: string;
  reason: string;
}

export interface PredictionEnvelope {
  city_id: string;
  area_id?: number | null;
  dropoff_area_id?: number | null;
  metric: string;
  prediction: number;
  model: string;
  model_version?: string | null;
  generated_at: string;
  data_timestamp?: string | null;
  source: string;
  basis: "computed" | "modeled_estimate";
  reason?: string | null;
}

export interface ForecastPoint {
  hour: number;
  value: number;
}

export interface ForecastEnvelope {
  city_id: string;
  metric: string;
  model: string;
  model_version?: string | null;
  generated_at: string;
  source: string;
  series: ForecastPoint[];
}

export async function fetchCountries(): Promise<Country[]> {
  const res = await fetch(`${API_BASE_URL}/api/countries`);
  if (!res.ok) throw new Error(`Failed to fetch countries: ${res.statusText}`);
  const data = await res.json();
  return data.countries || [];
}

export async function fetchCountry(code: string): Promise<Country> {
  const res = await fetch(`${API_BASE_URL}/api/countries/${code.toUpperCase()}`);
  if (!res.ok) throw new Error(`Failed to fetch country ${code}`);
  return res.json();
}

export async function fetchCountryCities(code: string): Promise<City[]> {
  const res = await fetch(`${API_BASE_URL}/api/countries/${code.toUpperCase()}/cities`);
  if (!res.ok) throw new Error(`Failed to fetch cities for ${code}`);
  return res.json();
}

export async function fetchCity(cityId: string): Promise<City> {
  const res = await fetch(`${API_BASE_URL}/api/cities/${cityId}`);
  if (!res.ok) throw new Error(`Failed to fetch city ${cityId}`);
  return res.json();
}

export async function fetchCityCapabilities(cityId: string): Promise<Capabilities> {
  const res = await fetch(`${API_BASE_URL}/api/cities/${cityId}/capabilities`);
  if (!res.ok) throw new Error(`Failed to fetch capabilities for ${cityId}`);
  return res.json();
}

export async function fetchCityAreas(cityId: string): Promise<Area[]> {
  const res = await fetch(`${API_BASE_URL}/api/cities/${cityId}/areas`);
  if (!res.ok) throw new Error(`Failed to fetch areas for ${cityId}`);
  return res.json();
}

export async function fetchCityArea(cityId: string, areaId: number): Promise<Area> {
  const res = await fetch(`${API_BASE_URL}/api/cities/${cityId}/areas/${areaId}`);
  if (!res.ok) throw new Error(`Failed to fetch area ${areaId} for ${cityId}`);
  return res.json();
}

export async function fetchCityMetrics(cityId: string): Promise<string[]> {
  const res = await fetch(`${API_BASE_URL}/api/cities/${cityId}/metrics`);
  if (!res.ok) throw new Error(`Failed to fetch metrics for ${cityId}`);
  return res.json();
}

export async function predictCityDemand(
  cityId: string,
  areaId: number,
  hour: number,
  dayOfWeek: number
): Promise<PredictionEnvelope | CapabilityUnavailable> {
  const res = await fetch(`${API_BASE_URL}/api/cities/${cityId}/predict/demand`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ area_id: areaId, hour, day_of_week: dayOfWeek }),
  });
  if (!res.ok) throw new Error(`City demand prediction failed: ${res.statusText}`);
  return res.json();
}

export async function predictCityFare(
  cityId: string,
  pickupAreaId: number,
  dropoffAreaId: number,
  hour: number
): Promise<PredictionEnvelope | CapabilityUnavailable> {
  const res = await fetch(`${API_BASE_URL}/api/cities/${cityId}/predict/fare`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ pickup_area_id: pickupAreaId, dropoff_area_id: dropoffAreaId, hour }),
  });
  if (!res.ok) throw new Error(`City fare prediction failed: ${res.statusText}`);
  return res.json();
}

export interface PredictionOut {
  value: number | string | null;
  unit: string | null;
  basis: "computed" | "modeled_estimate" | "unavailable";
  source: string;
  reason?: string | null;
  ui_label?: string | null;
}

export interface CityJourneyEstimate {
  city_id: string;
  distance: PredictionOut;
  duration: PredictionOut;
  demand: PredictionOut;
  fare: PredictionOut;
  mode: "zone_enriched" | "osrm_only";
}

// Works for ANY resolvable city -- computed where a real model exists
// (NYC/London), an honestly-labeled modeled_estimate everywhere else.
export async function fetchCityJourneyEstimate(
  cityId: string,
  pickupLat: number,
  pickupLon: number,
  dropoffLat: number,
  dropoffLon: number,
  departureTime: string = new Date().toISOString()
): Promise<CityJourneyEstimate> {
  const res = await fetch(`${API_BASE_URL}/api/cities/${cityId}/journey/estimate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      pickup_lat: pickupLat,
      pickup_lon: pickupLon,
      dropoff_lat: dropoffLat,
      dropoff_lon: dropoffLon,
      departure_time: departureTime,
    }),
  });
  if (!res.ok) throw new Error(`City journey estimate failed: ${res.statusText}`);
  return res.json();
}

export async function fetchCityForecast(
  cityId: string,
  metric: string = "demand",
  hours: number = 24
): Promise<ForecastEnvelope | CapabilityUnavailable> {
  const res = await fetch(`${API_BASE_URL}/api/cities/${cityId}/forecast?metric=${metric}&hours=${hours}`);
  if (!res.ok) throw new Error(`City forecast failed: ${res.statusText}`);
  return res.json();
}

export async function sendCityChatMessage(
  cityId: string,
  question: string,
  areaId?: number,
  sessionId?: string
): Promise<ChatResponse> {
  const res = await fetch(`${API_BASE_URL}/api/cities/${cityId}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, area_id: areaId, session_id: sessionId }),
  });
  if (!res.ok) throw new Error(`City chat failed: ${res.statusText}`);
  return res.json();
}

// ── Global Geography Discovery API Extensions ────────────────────────────────

export interface GlobalCitySearchResult {
  id: string;
  name: string;
  country?: string | null;
  country_code?: string | null;
  latitude?: number | null;
  longitude?: number | null;
  timezone?: string | null;
  population?: number | null;
  place_type: string;
  mobility_available: boolean;
  modeling_available: boolean;
}

export interface GlobalCitySearchResponse {
  results: GlobalCitySearchResult[];
}

export interface CityCoordinates {
  latitude?: number | null;
  longitude?: number | null;
}

export interface CityProfileCapabilities {
  geographic: boolean;
  context: boolean;
  observed_mobility: boolean;
  cross_city_model: boolean;
}

export interface CityProfileResponse {
  city_id: string;
  city: string;
  country?: string | null;
  country_code?: string | null;
  coordinates: CityCoordinates;
  timezone?: string | null;
  currency?: string | null;
  population?: number | null;
  administrative_hierarchy?: Record<string, string | number | null>[];
  alternate_names?: string[];
  geographic_classification?: { feature_class?: string | null; feature_code?: string | null; place_type: string };
  capabilities: CityProfileCapabilities;
}

export interface ContextSourceEnvelope {
  status: "available" | "unavailable";
  data?: any;
  source: string;
  timestamp: string;
  freshness?: string | null;
  coverage?: string | null;
  reason?: string | null;
}

export interface CityContextResponse {
  city_id: string;
  city_name: string;
  generated_at: string;
  context: Record<string, ContextSourceEnvelope>;
}

export interface GeographyCountry {
  geoname_id?: number | null;
  iso2?: string | null;
  iso3?: string | null;
  name?: string | null;
  capital?: string | null;
  continent?: string | null;
  latitude?: number | null;
  longitude?: number | null;
  supported: boolean;
}

export interface GeographyCountriesResponse {
  countries: GeographyCountry[];
}

export interface MobilitySupport {
  supported: boolean;
  city_id?: string | null;
}

export interface PlaceSearchResult {
  geoname_id?: number | null;
  name?: string | null;
  country_code?: string | null;
  country_name?: string | null;
  admin1_code?: string | null;
  admin1_name?: string | null;
  feature_class?: string | null;
  feature_code?: string | null;
  latitude?: number | null;
  longitude?: number | null;
  source: string;
  mobility_support: MobilitySupport;
}

export interface SearchResponse {
  results: PlaceSearchResult[];
}

export async function searchGlobalCities(
  query: string,
  limit: number = 10,
  country?: string
): Promise<GlobalCitySearchResult[]> {
  const url = new URL(`${API_BASE_URL}/api/geography/search/global`);
  url.searchParams.set("q", query);
  url.searchParams.set("limit", limit.toString());
  if (country) url.searchParams.set("country", country);
  const res = await fetch(url.toString());
  if (!res.ok) throw new Error(`Global city search failed: ${res.statusText}`);
  const data: GlobalCitySearchResponse = await res.json();
  return data.results || [];
}

export async function fetchCityProfile(cityId: string): Promise<CityProfileResponse> {
  const res = await fetch(`${API_BASE_URL}/api/geography/${cityId}`);
  if (!res.ok) throw new Error(`Failed to fetch profile for ${cityId}: ${res.statusText}`);
  return res.json();
}

export async function fetchCityContext(cityId: string): Promise<CityContextResponse> {
  const res = await fetch(`${API_BASE_URL}/api/geography/${cityId}/context`);
  if (!res.ok) throw new Error(`Failed to fetch context for ${cityId}: ${res.statusText}`);
  return res.json();
}

export async function fetchGeographyCountries(): Promise<GeographyCountry[]> {
  const res = await fetch(`${API_BASE_URL}/api/geography/countries`);
  if (!res.ok) throw new Error(`Failed to fetch geography countries: ${res.statusText}`);
  const data: GeographyCountriesResponse = await res.json();
  return data.countries || [];
}

export async function searchGeographyPlaces(query: string, country?: string): Promise<PlaceSearchResult[]> {
  const url = new URL(`${API_BASE_URL}/api/geography/search`);
  url.searchParams.set("q", query);
  if (country) url.searchParams.set("country", country);
  const res = await fetch(url.toString());
  if (!res.ok) throw new Error(`Search geography places failed: ${res.statusText}`);
  const data: SearchResponse = await res.json();
  return data.results || [];
}



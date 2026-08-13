# Graph Report - ..  (2026-08-13)

## Corpus Check
- 406 files · ~202,327 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 2667 nodes · 5313 edges · 195 communities (144 shown, 51 thin omitted)
- Extraction: 98% EXTRACTED · 2% INFERRED · 0% AMBIGUOUS · INFERRED: 117 edges (avg confidence: 0.79)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- Backend Schemas
- Frontend Web Components Journey Cards
- Models Global Transfer
- Frontend Web Components Ui
- Frontend Web Lib Api
- Specs
- Docs
- Backend Routers Analytics
- Frontend Web Components
- Tests Test Api Test
- Models Congestion
- Backend Routers Cities
- Backend
- Backend Routers Mobility
- Frontend Web Components
- Frontend Web Components City
- Backend Adapters
- Backend Services Global Geography Service
- Frontend Src Api Client
- Frontend Web
- Tests Test Geonames Test
- Backend Datasources
- Backend
- Tests Test Model Service
- Backend Schemas Geography
- Cross City Estimation Calibration Eval
- Backend Registry Cities
- Frontend Src Pages
- Scripts Services Tariff Profiles
- Frontend Src
- Frontend Src Components
- Rag Rag Pipeline
- Docs
- Backend Routers Chat
- Frontend Web Tsconfig Compileroptions
- Backend
- Backend Services Platform Service
- Tests Test Prep Split
- Scripts Load Worldmove Mobility
- Frontend Tsconfig Compileroptions
- Models Data Baseline Build Features
- Algorithms Timeseries Ewma Smoothing
- Frontend Web Hooks Usereversegeocode
- Nl To Sql Query Plan
- Backend Services Model Service
- Backend Predictors Journey Predictors
- Algorithms Graph Pagerank Hubs
- Implementation
- Models London Demand Build Features
- Nl To Sql Training Data
- Algorithms Spatial Kdtree Zone Lookup
- Backend Services Pricing Engine
- Backend Services Geonames Service
- Test Fare Provenance Capabilities Test
- Frontend Src Api Client
- Algorithms Graph Shortest Path Eta
- Backend Routers Geography
- Frontend Web Package Dependencies
- Frontend Package Dependencies
- Frontend Package Devdependencies
- Opencode
- Backend Services Geography Service
- Tests Test Geography Generalized Test
- Models Lstm Model Train Lstm
- Tests Test Rag Test
- Backend Registry Transit Registry
- Scripts
- Frontend Src Api Client
- Frontend Web Package Devdependencies
- Tests Test Global Cities Table
- Tests Test Registry Test
- Docs
- Backend Datasources Base Mobilitydatasource
- Backend Routers Context
- Tests Test Query Plan Test
- Backend Registry Global Cities Registry
- Backend Services City Journey Service
- Fare Prediction Train Fare Xgb
- Models Query Plan Finetune Evaluate
- Tests Test London Pipeline Test
- Nl To Sql Query Plan
- London Demand Train London Xgb
- Scripts Refresh Model Registry
- Backend Routers Zones
- Backend Adapters Routing Osrm
- Tests Test Tariff Profiles
- Models Xgboost Model Feature Importance
- Scripts Download Worldmove
- Rag Embeddings Build Vector Store
- Insight Generation Generate Insight Docs
- Nl To Sql Sql Agent
- Test Training Data Gen Data
- Specs
- Algorithms Timeseries Seasonality Decompose
- Architecture
- Package Dependencies
- Nl To Sql Query Plan
- Rag Journey Narrative
- Test Journey Test Journey Estimate
- Algorithms Spatial Geohash Grid
- Frontend Package Scripts
- Frontend Web Package Scripts
- Rag Session Store
- Scripts Ingest Gtfs Feeds
- Scripts Ingest Tfl Cycle Hire
- Backend Services Vehicle Profiles
- Web Components Journey Cards Aicard
- Models Xgboost Model Train Xgboost
- Tests Test Chronological Split Dedup
- Test Sql Agent Query Plan
- Scripts Extract Fixed Holidays
- Backend Errors Geography
- Backend Services Platform Service
- Frontend Web App History Page
- Models Lstm Model Loss Curve
- Scripts Calibrate Tariff Nyc
- Specs Journey Intelligence Spec
- Skills Design Taste Frontend Skill
- Algorithms Timeseries
- Timeseries Output Park Slope Decomp
- Backend Routers Platform Service
- Infra Cdk Stack Dbtbuildstack
- Scripts Backfill Weather Openmeteo
- Test Build Global Cities Test
- Algorithms Timeseries
- Scripts Load Worldmove To Duckdb
- Specs Query Plan Finetuning Spec
- Github
- Scripts Verify Ingestion
- Specs Hybrid Rag Spec
- Backend Routers Init
- Backend Services Init
- Claude Rules Rule7 Minimal Infra
- Data Ingestion Report
- Gl Layers Dependencies Deck Gl
- Frontend Package Dependencies Framer Motion
- Frontend Package Dependencies Lucide React
- Package Dependencies Tanstack React Query
- Frontend Package Devdependencies Typescript
- Frontend Package Devdependencies Vite
- Frontend Web Next Config Nextconfig
- Frontend Web Next Env D
- Frontend Web Package Dependencies Animejs
- Web Package Dependencies Framer Motion
- Frontend Web Package Dependencies Lenis
- Web Package Dependencies Lucide React
- Web Package Dependencies Maplibre Gl
- Frontend Web Package Dependencies Next
- Frontend Web Package Dependencies React
- Web Package Dependencies React Dom
- Web Package Dependencies Tailwind Merge
- Web Package Dependencies Tanstack React
- Web Package Dependencies Types Animejs
- Frontend Web Tailwind Config Config
- Global Mobility Domain Model Spec
- Tests Test Dbt Marts
- Docs Architecture Image
- Seeds Taxi Zone Lookup
- Skill Observations Cross Cutting Principles
- Skill Observations Last Review Date
- Skill Observations Log
- Model Ladder Demand Spec Build
- Model Ladder Demand Spec Train
- Backend Api Spec Routers Predictions
- Backend Api Spec Routers Zones
- Specs Backend Api Spec Schemas
- Specs Frontend Spec App Tsx
- Specs Frontend Spec Zonemap Tsx
- Specs Deployment Devops Spec Ci
- Specs Journey Intelligence Spec Adapters
- Journey Intelligence Spec Geography Service
- Journey Intelligence Spec Pricing Engine
- Journey Intelligence Spec Vehicle Profiles
- Global Mobility Domain Model Spec
- Global Mobility Domain Model Spec
- Global Mobility Domain Model Spec
- Global Mobility Domain Model Spec
- Global Mobility Domain Model Spec
- Global Mobility Domain Model Spec
- Second Real City Estimation Spec

## God Nodes (most connected - your core abstractions)
1. `cn()` - 78 edges
2. `PredictionResult` - 72 edges
3. `QueryPlan` - 34 edges
4. `CityMobilitySchema` - 33 edges
5. `Card()` - 32 edges
6. `get_city_profile()` - 31 edges
7. `CardTitle()` - 27 edges
8. `JourneyFeatures` - 26 edges
9. `DomainError` - 25 edges
10. `JourneyContext` - 23 edges

## Surprising Connections (you probably didn't know these)
- `Anti-Slop Frontend Skill` --semantically_similar_to--> `DESIGN.md Enterprise Product Spec`  [INFERRED] [semantically similar]
  .agents/skills/design-taste-frontend/SKILL.md → DESIGN.md
- `PredictionResult` --shares_data_with--> `POST /journey/estimate`  [EXTRACTED]
  backend/predictors/base.py → docs/adr/ADR-007-predictor-basis-field.md
- `ADR-007: Structural basis Field on Every Journey Prediction` --references--> `PredictionResult`  [EXTRACTED]
  docs/adr/ADR-007-predictor-basis-field.md → backend/predictors/base.py
- `Chat tiers (full_rag / sql_only / context_only)` --implements--> `get_chat_tier()`  [EXTRACTED]
  docs/reference/capabilities.md → backend/registry/cities.py
- `get_capabilities()` --references--> `Chat tiers (full_rag / sql_only / context_only)`  [EXTRACTED]
  backend/registry/cities.py → docs/reference/capabilities.md

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **ADR Documentation Set** — docs_readme_md, docs_adr_adr_001_duckdb_over_postgres_md, docs_adr_adr_002_dbt_layering_md, docs_adr_adr_003_chronological_split_md [EXTRACTED 1.00]
- **dbt Project Configuration Files** — dbt_project_dbt_project_yml, dbt_project_profiles_yml, dbt_project_packages_yml, dbt_project_package_lock_yml, dbt_project_models_intermediate_schema_yml, dbt_project_models_marts_schema_yml, dbt_project_models_staging_schema_yml, dbt_project_seeds_schema_yml [INFERRED 0.85]
- **Zero-Fabrication / Total-Provenance Discipline** — architecture_audit_md, design_md, implementation_audit_md, claude_rules_md_zero_fabrication_rule [INFERRED 0.85]
- **Hybrid RAG Numeric/Explanatory Routing Flow** — rag_router_query_classifier, rag_nl_to_sql_sql_agent, rag_insight_generation [EXTRACTED 0.95]
- **Journey Prediction Honesty via basis/adapter Pattern** — backend_predictors_base_predictionresult, backend_adapters_base, docs_adr_adr_007_predictor_basis_field [INFERRED 0.90]
- **AWS On-Demand dbt Build Pipeline** — github_workflows_dbt_build_aws, scripts_aws_dbt_build_userdata, infra_cdk_stack [EXTRACTED 0.90]
- **Product Documentation Set (Vision/PRD/Personas/Roadmap/Use-Cases/Success-Metrics)** — docs_product_vision, docs_product_prd, docs_product_personas, docs_product_roadmap, docs_product_use_cases, docs_product_success_metrics [INFERRED 0.85]
- **Honest-Data Adapters implementing the basis contract** — basis_contract, backend_adapters_routing_osrm, backend_adapters_weather_openmeteo [INFERRED 0.75]
- **Model Ladder Evaluation Suite** — fare_prediction_model, demand_forecasting_ladder, congestion_model, quantile_eta_model [INFERRED 0.75]
- **Algorithms + Model Ladder Layer (Specs 003-007)** — specs_003_spatial_algorithms_spec, specs_004_graph_algorithms_spec, specs_005_timeseries_algorithms_spec, specs_006_model_ladder_demand_spec, specs_007_fare_prediction_spec [INFERRED 0.85]
- **Serving & Presentation Layer (Specs 009-011)** — specs_009_backend_api_spec, specs_010_frontend_spec, specs_011_deployment_devops_spec [INFERRED 0.85]
- **Global Mobility Generalization Phase (Specs 012-015)** — specs_012_journey_intelligence_spec, specs_013_global_mobility_domain_model_spec, specs_014_query_plan_finetuning_spec, specs_015_second_real_city_and_estimation_spec [INFERRED 0.85]

## Communities (195 total, 51 thin omitted)

### Community 0 - "Backend Schemas"
Cohesion: 0.04
Nodes (70): POST /journey/estimate -- the Journey Intelligence Engine endpoint (ADR-007).…, GET /predict/demand, GET /predict/fare (FR-2). Thin: validates input, delegates…, AnalyticsHistoryResponse, AnalyticsInsightsResponse, AnalyticsSummaryResponse, AnalyticsTrendsResponse, AvailabilityResponse, CarbonResponse (+62 more)

### Community 1 - "Frontend Web Components Journey Cards"
Cohesion: 0.06
Nodes (45): CapabilityGate(), useCapability(), AvailabilityCard(), AvailabilityCardContent(), AvailabilityCardProps, BestDepartureCard(), BestDepartureCardProps, CarbonCard() (+37 more)

### Community 2 - "Models Global Transfer"
Cohesion: 0.06
Nodes (59): apply_scaler(), build_city_feature_table(), demo(), fit_scaler(), load_scaler(), DataFrame, DuckDBPyConnection, Path (+51 more)

### Community 3 - "Frontend Web Components Ui"
Cohesion: 0.07
Nodes (37): InsightsPage(), SOURCE_LABELS, CapabilityUnavailable(), CapabilityUnavailableProps, CertaintyRing(), CertaintyRingProps, ADR-0007, commands (+29 more)

### Community 4 - "Frontend Web Lib Api"
Cohesion: 0.06
Nodes (46): AnalyticsPage(), CityProfile(), ContextCard(), ContextCardProps, DemandCard(), RouteCard(), RouteCardContent(), RouteCardProps (+38 more)

### Community 5 - "Specs"
Cohesion: 0.06
Nodes (50): SPEC-001: Data Foundation, scripts/load_raw_to_duckdb.py, data/warehouse/nyc_rides.duckdb, scripts/spot_check.py, scripts/verify_ingestion.py, SPEC-002: dbt Transformation Layer, ADR-007 (incremental vs full-refresh), int_trips_enriched.sql (+42 more)

### Community 6 - "Docs"
Cohesion: 0.06
Nodes (46): ADR-003 Chronological Split, ADR-007 Predictor basis field, ADR-008 Adapter Pattern Zero Budget, basis field contract (computed/modeled_estimate/unavailable), Chat tiers (full_rag / sql_only / context_only), Congestion Model (Phase 6), Demand Forecasting Model Ladder (SPEC-006), Personas (+38 more)

### Community 7 - "Backend Routers Analytics"
Cohesion: 0.06
Nodes (40): AnalyticsHistoryResponse, AnalyticsInsightsResponse, AnalyticsSummaryResponse, AnalyticsTrendsResponse, history(), insights(), _parse_requested_at(), datetime (+32 more)

### Community 8 - "Frontend Web Components"
Cohesion: 0.07
Nodes (36): AnalystPage(), EXAMPLE_PROMPTS, looksNumeric(), Turn, TurnBubble(), ComparePage(), BasisBadge(), CompareCard() (+28 more)

### Community 9 - "Tests Test Api Test"
Cohesion: 0.04
Nodes (3): client(), fixture, One happy-path test per backend route (standards.md testing bar).

### Community 10 - "Models Congestion"
Cohesion: 0.08
Nodes (35): _bucket(), build_features(), build_free_flow_lookup(), demo(), _holiday_flags(), load_raw_trips(), DataFrame, DuckDBPyConnection (+27 more)

### Community 11 - "Backend Routers Cities"
Cohesion: 0.08
Nodes (41): Area, city_chat(), city_journey_estimate(), forecast(), get_area(), get_capabilities(), get_city(), get_city_tariff() (+33 more)

### Community 12 - "Backend"
Cohesion: 0.08
Nodes (34): demo(), _extended_fixed_holidays(), fetch(), datetime, Real public-holiday lookup via Nager.Date -- free, global, no API key required…, Real holiday dates (ISO strings) for a (year, country), or None if the lookup…, _year_holidays(), _cached_fetch() (+26 more)

### Community 13 - "Backend Routers Mobility"
Cohesion: 0.09
Nodes (37): AvailabilityResponse, features(), datetime, availability(), carbon(), congestion(), demand(), departure_time() (+29 more)

### Community 14 - "Frontend Web Components"
Cohesion: 0.11
Nodes (28): defaultDropoff, defaultPickup, JourneyPage(), CityPage(), CountryPage(), WorldPage(), CityCard(), CityCardProps (+20 more)

### Community 15 - "Frontend Web Components City"
Cohesion: 0.11
Nodes (25): Theme, Units, CapabilityGateProps, TIER_COLORS, TierBadge(), TierBadgeProps, TierNotice(), TierNoticeProps (+17 more)

### Community 16 - "Backend Adapters"
Cohesion: 0.10
Nodes (27): DataSourceAdapter, datetime, Protocol, External data-source adapter contract (ADR-008). One method, not…, _cached_fetch(), demo(), fetch(), Real purchasing-power lookup via the World Bank Open Data API -- free, no API… (+19 more)

### Community 17 - "Backend Services Global Geography Service"
Cohesion: 0.08
Nodes (26): _classify_place_type(), _country_currencies(), get_city_profile(), get_currency_for_country(), get_worldmove_population(), Global Geography Registry Service (Phase 1). Resolves arbitrary global places…, True iff cross-city modeling estimates are actually possible.…, (model_status, confidence). Checks the 524-city global_cities registry first… (+18 more)

### Community 18 - "Frontend Src Api Client"
Cohesion: 0.06
Nodes (26): AlgorithmBenchmarks, API_BASE_URL, Capabilities, CapabilityUnavailable, ChatResponse, CityCoordinates, CityJourneyEstimate, CityProfileCapabilities (+18 more)

### Community 19 - "Frontend Web"
Cohesion: 0.09
Nodes (22): metadata, makeClient(), Providers(), JourneyResultsProps, CommandPalette(), NavBar(), navLinks, SmoothScrollProvider() (+14 more)

### Community 20 - "Tests Test Geonames Test"
Cohesion: 0.09
Nodes (24): _hierarchy_type(), get_all_countries(), client(), _fake_response(), _isolated_service_state(), fixture, skipif, Correctness tests for the geography-discovery layer (GeoNames client, Google… (+16 more)

### Community 21 - "Backend Datasources"
Cohesion: 0.09
Nodes (12): get_datasource(), Per-city mobility data source registry (SPEC-013 FR-6). Each city registers…, LondonCyclesDataSource, `LondonCyclesDataSource` -- mirrors `nyc_tlc.py`'s shape exactly, reading…, _rows(), NYCTLCDataSource, `NYCTLCDataSource` (SPEC-013 FR-6) -- thin read wrappers over the existing NYC…, _rows() (+4 more)

### Community 22 - "Backend"
Cohesion: 0.12
Nodes (29): DomainError, Exception, Exception type for the Global Mobility Domain Model routes (SPEC-013 FR-8).…, CapabilityUnavailable, ErrorCode, ForecastEnvelope, ForecastPoint, PredictionEnvelope (+21 more)

### Community 23 - "Tests Test Model Service"
Cohesion: 0.09
Nodes (31): predict_demand(), predict_fare(), get, load(), _load_fare_categories(), _load_worldmove_hourly_shapes(), _load_zone_centroids(), _load_zone_demand_artifacts() (+23 more)

### Community 24 - "Backend Schemas Geography"
Cohesion: 0.15
Nodes (30): _find_country_name(), _mobility_support(), place_hierarchy(), Geography Discovery API -- world -> country -> city search -> place hierarchy,…, search_places(), ChildPlace, CityContextResponse, CityCoordinates (+22 more)

### Community 25 - "Cross City Estimation Calibration Eval"
Cohesion: 0.10
Nodes (28): compute_metrics(), demo(), load_city_daily_demand(), load_population(), main(), DataFrame, ndarray, Path (+20 more)

### Community 26 - "Backend Registry Cities"
Cohesion: 0.11
Nodes (27): _area_count(), capability_matrix(), _effective_model_status(), get_capabilities(), get_city(), list_cities(), list_metrics(), load() (+19 more)

### Community 27 - "Frontend Src Pages"
Cohesion: 0.12
Nodes (22): FarePrediction, fetchAlgorithmBenchmarks(), fetchModelMetrics(), fetchPipelineStatus(), fetchWarehouseStats(), fetchWarehouseTables(), fetchZones(), predictFare() (+14 more)

### Community 28 - "Scripts Services Tariff Profiles"
Cohesion: 0.11
Nodes (25): city_ids(), ensure_table(), load(), _present_columns(), DuckDBPyConnection, Validation at construction, so it holds on BOTH paths -- the offline upsert and…, Called only from the offline generation/calibration scripts (they hold the sole…, Read-only at startup (rule 8: no write lock ever taken by the live server). A… (+17 more)

### Community 29 - "Frontend Src"
Cohesion: 0.12
Nodes (23): Area, ChatMessage, DemandPrediction, predictCityDemand(), predictCityFare(), predictDemand(), sendChatMessage(), sendCityChatMessage() (+15 more)

### Community 30 - "Frontend Src Components"
Cohesion: 0.14
Nodes (20): fetchHealth(), GlobalCitySearchResult, searchGlobalCities(), App(), CityRouteController(), CountryRouteController(), queryClient, AnalyzingScreen() (+12 more)

### Community 31 - "Rag Rag Pipeline"
Cohesion: 0.12
Nodes (25): Rule 8: No Reprocessing on Request Path, data/warehouse/nyc_rides.duckdb, Data Flow, System Design, rag/embeddings, rag/insight_generation docs, chat_completion(), demo() (+17 more)

### Community 32 - "Docs"
Cohesion: 0.11
Nodes (21): ADR-009 (CDK deploy / RDS Postgres), backend/Dockerfile, Rule 2: Never Fabricate Results, Rule 7: Prune Scaffolding That Stops Earning Its Keep, ADR-001: DuckDB over Postgres, ADR-002: dbt Layering, ADR-004: NL-to-SQL as Separate Path from RAG-over-text, ADR-005: Precompute for Deployment, Never Run Full Pipeline Live (+13 more)

### Community 33 - "Backend Routers Chat"
Cohesion: 0.11
Nodes (25): get_chat_tier(), get_chat_history(), _normalize_route(), post_chat(), ChatRequest, ChatResponse, get, post (+17 more)

### Community 34 - "Frontend Web Tsconfig Compileroptions"
Cohesion: 0.07
Nodes (26): compilerOptions, allowJs, esModuleInterop, incremental, isolatedModules, jsx, lib, module (+18 more)

### Community 35 - "Backend"
Cohesion: 0.11
Nodes (21): domain_error_handler(), geography_error_handler(), lifespan(), FastAPI app (FR-1). Mounts routers; loads model artifacts once at startup (rule…, get_country(), list_countries(), Country registry (SPEC-013 FR-4) -- thin query module over the seeded…, _with_support() (+13 more)

### Community 36 - "Backend Services Platform Service"
Cohesion: 0.14
Nodes (23): algorithm_benchmarks(), dashboard_summary(), health(), insights(), mart_zone_hourly_demand(), model_metrics(), pipeline_status(), get (+15 more)

### Community 37 - "Tests Test Prep Split"
Cohesion: 0.13
Nodes (19): chronological_split(), demo(), _latest_month_start(), DataFrame, Chronological train/validation/test split (ADR-003). Never random-split time-…, train/val = every month before the latest one (chronological 85/15), test = the…, Sort `df` by `ts_col` and slice into len(fracs) chunks, in the given…, split_demand_blocks() (+11 more)

### Community 38 - "Scripts Load Worldmove Mobility"
Cohesion: 0.14
Nodes (22): Client, _fix_population(), flush(), geocode(), get_tz(), main(), DuckDBPyConnection, scripts/geocode_global_cities.py Geocoding backfill using GeoNames free API.… (+14 more)

### Community 39 - "Frontend Tsconfig Compileroptions"
Cohesion: 0.08
Nodes (23): compilerOptions, allowImportingTsExtensions, baseUrl, isolatedModules, jsx, lib, module, moduleResolution (+15 more)

### Community 40 - "Models Data Baseline Build Features"
Cohesion: 0.13
Nodes (20): _block_features(), build_features(), demo(), _load_weather_lookup(), DataFrame, DuckDBPyConnection, Series, Feature table for zone-hourly demand forecasting (SPEC-006). Reuses… (+12 more)

### Community 41 - "Algorithms Timeseries Ewma Smoothing"
Cohesion: 0.13
Nodes (20): _best_alpha(), ewma(), ewma_blocks(), load_zone_hourly_blocks(), DuckDBPyConnection, ndarray, Series, EWMA smoothing over zone_hourly_demand, implemented from scratch. S_t = alpha *… (+12 more)

### Community 42 - "Frontend Web Hooks Usereversegeocode"
Cohesion: 0.14
Nodes (17): AddressSearch(), AddressSearchProps, JourneyMap(), JourneyMapProps, MAP_STYLE, ROUTE_LINE_LAYER, cache, formatPlaceName() (+9 more)

### Community 43 - "Nl To Sql Query Plan"
Cohesion: 0.15
Nodes (12): POST /chat, London's real CityMobilitySchema -- demand (bike-share departures) only. No…, The one real CityMobilitySchema, for NYC's actual marts (FR-3). Column/table…, demo(), FieldMapping, MetricSchema, Schema-agnostic QueryPlan + per-city schema resolver (FR-1, spec-014). Today's…, A canonical metric's backing table, its own value column, and every other… (+4 more)

### Community 44 - "Backend Services Model Service"
Cohesion: 0.11
Nodes (19): data_vintage(), get_zone_momentum(), _haversine_miles(), predict_fare(), Loads precomputed model artifacts once at startup (rule 8 — no training or raw-…, Last-known-row demand-momentum snapshot for a zone, loaded once at startup.…, Real min/max date range this city's demand mart actually covers -- surfaced on…, _base_fare_nyc() (+11 more)

### Community 45 - "Backend Predictors Journey Predictors"
Cohesion: 0.18
Nodes (19): effective_confidence(), JourneyContext, A component's own measured/derived confidence when it has one, the basis…, Raw inputs plus whatever the adapters (backend/adapters/) returned,…, _demand_pressure(), predict_availability(), predict_carbon(), predict_confidence() (+11 more)

### Community 46 - "Algorithms Graph Pagerank Hubs"
Cohesion: 0.19
Nodes (16): build_zone_graph(), demo(), DiGraph, Path, Build a weighted directed zone-to-zone trip-flow graph from the…, Return a directed graph of zones with edge attribute `weight` = total trip…, demo(), hub_summary() (+8 more)

### Community 47 - "Implementation"
Cohesion: 0.12
Nodes (19): Intermediate Models Schema, Marts Models Schema, Staging Models & Sources Schema, Seeds Schema, DuckDB over Postgres Decision, dbt Staging/Intermediate/Marts Layering Decision, Chronological Train/Val/Test Split Decision, Docs Index (+11 more)

### Community 48 - "Models London Demand Build Features"
Cohesion: 0.18
Nodes (17): _block_features(), build_features(), demo(), load_station_hourly_blocks(), _load_weather_lookup(), DataFrame, DuckDBPyConnection, Series (+9 more)

### Community 49 - "Nl To Sql Training Data"
Cohesion: 0.17
Nodes (14): CityMobilitySchema, QueryFilters, Canonical field name -> real (table, column), scoped per metric since the same…, Compact `TABLE <name> (<column> -- <canonical>: <meaning>, ...)` text for LLM…, Only the filters actually set, as canonical-name -> value., _area_value(), _gen_area_ranking(), _gen_comparison() (+6 more)

### Community 50 - "Algorithms Spatial Kdtree Zone Lookup"
Cohesion: 0.22
Nodes (12): _benchmark(), benchmark_summary(), _coord(), KDNode, KDTree, linear_nearest(), From-scratch KD-tree over NYC TLC zone centroids for nearest-neighbor lookup.…, Run the linear-scan-vs-KD-tree benchmark and return measured results (used both… (+4 more)

### Community 51 - "Backend Services Pricing Engine"
Cohesion: 0.20
Nodes (16): JourneyFeatures, Derived, named scores every predictor actually consumes. Adding a new…, fare(), Granular Mobility APIs (Part 2 of API Decomposition). Each endpoint exposes one…, Get fare estimate for a journey. Uses trained model (NYC) or tariff profile…, compute_fare(), _demand_adjustment(), estimate_tariff_base_fare() (+8 more)

### Community 52 - "Backend Services Geonames Service"
Cohesion: 0.20
Nodes (16): _get(), get_children(), get_hierarchy(), get_timezone(), _get_timezone_cached(), _normalize_place(), _num(), GeoNames JSON web services client -- the geography-discovery layer's source of… (+8 more)

### Community 53 - "Test Fare Provenance Capabilities Test"
Cohesion: 0.24
Nodes (16): _base_fare(), NYC (a real trained model) or a `TariffProfile` (ADR-011) everywhere else --…, _ctx(), _features(), parametrize, Provenance + capability-truthfulness tests for the extended tariff engine.…, NYC prices from the trained fare model, never from a tariff profile. The model…, A model artifact that won't score must never fabricate a fare or blow up the… (+8 more)

### Community 54 - "Frontend Src Api Client"
Cohesion: 0.19
Nodes (15): fetchCityAreas(), fetchCityCapabilities(), fetchCityForecast(), fetchCityJourneyEstimate(), fetchDashboardSummary(), fetchHourlyDemandProfile(), ForecastEnvelope, Zone (+7 more)

### Community 55 - "Algorithms Graph Shortest Path Eta"
Cohesion: 0.20
Nodes (15): build_eta_graph(), demo(), dijkstra(), DiGraph, Path, Dijkstra's shortest path from scratch (FR-4), used as a graph-path ETA sanity…, Directed graph of zones with edge attribute `weight` = average trip duration in…, Return (path, total_weight) for the shortest path from source to target. Raises… (+7 more)

### Community 56 - "Backend Routers Geography"
Cohesion: 0.13
Nodes (17): GeographyError, Exception, _classify_feature(), country_places(), get_city_context(), get_city_profile(), list_countries(), CityProfileResponse (+9 more)

### Community 57 - "Frontend Web Package Dependencies"
Cohesion: 0.12
Nodes (17): @deck.gl/core, @deck.gl/react, dependencies, clsx, @deck.gl/core, @deck.gl/react, gsap, @gsap/react (+9 more)

### Community 58 - "Frontend Package Dependencies"
Cohesion: 0.12
Nodes (17): dependencies, clsx, leaflet, react, react-dom, react-leaflet, react-router-dom, recharts (+9 more)

### Community 59 - "Frontend Package Devdependencies"
Cohesion: 0.12
Nodes (17): devDependencies, autoprefixer, postcss, tailwindcss, @types/leaflet, @types/node, @types/react, @types/react-dom (+9 more)

### Community 60 - "Opencode"
Cohesion: 0.12
Nodes (16): limit, name, tool_call, context, output, models, name, npm (+8 more)

### Community 61 - "Backend Services Geography Service"
Cohesion: 0.19
Nodes (15): detect_city_from_coords(), _get_london_tree(), _get_tree(), in_coverage(), _in_london_coverage(), load_london_station_points(), Geography domain (ADR-007 candidate for Phase 2's Region generalization; Phase…, Same ZonePoint shape as NYC's zone_centroids loader, sourced from the… (+7 more)

### Community 62 - "Tests Test Geography Generalized Test"
Cohesion: 0.14
Nodes (12): get_area(), list_areas(), Real rows from the `canonical_areas` mart -- a small (~265 for NYC) dimension…, client(), fixture, Correctness tests for geography_service.py's SPEC-013 FR-5 additions…, The pre-existing KD-tree resolve() -- a distinct concern from…, test_get_area_known_zone() (+4 more)

### Community 63 - "Models Lstm Model Train Lstm"
Cohesion: 0.17
Nodes (12): evaluate_all(), _measure_latency(), Evaluate all 4 demand models on one shared test set (SPEC-006, FR-7). The…, probe() runs the model once on a small batch and returns the batch size;…, rmse_mae(), DemandLSTM, _epoch(), plot_loss_curve() (+4 more)

### Community 64 - "Tests Test Rag Test"
Cohesion: 0.16
Nodes (15): True iff every number in `text` is either a small connective number…, validate_grounding(), _heuristic_classify(), parametrize, skipif, RAG layer: the non-trivial, LLM-independent logic gets a real test…, test_heuristic_classify_ambiguous_defaults_numeric(), test_heuristic_classify_explanatory() (+7 more)

### Community 65 - "Backend Registry Transit Registry"
Cohesion: 0.23
Nodes (12): get_feed(), has_feed(), load(), GTFS transit feed registry -- exact mirror of backend/registry/models.py's…, True only once a real feed is both configured (not the unverified placeholder)…, count_stops_near(), Real transit-stop-density signal from ingested GTFS static feeds…, demo() (+4 more)

### Community 66 - "Scripts"
Cohesion: 0.13
Nodes (12): int_trips_enriched.sql, dbt_project/models/staging/schema.yml, dbt_project/models/staging/stg_trips.sql, ADR-003: Chronological Split, Data Source and Transformation, zone_fare_stats mart, zone_hourly_demand mart, zone_pair_flows mart (+4 more)

### Community 67 - "Frontend Src Api Client"
Cohesion: 0.23
Nodes (14): City, CityContextResponse, CityProfileResponse, Country, fetchCityContext(), fetchCityProfile(), fetchCountries(), fetchCountryCities() (+6 more)

### Community 68 - "Frontend Web Package Devdependencies"
Cohesion: 0.13
Nodes (15): devDependencies, autoprefixer, postcss, tailwindcss, @types/node, @types/react, @types/react-dom, typescript (+7 more)

### Community 69 - "Tests Test Global Cities Table"
Cohesion: 0.15
Nodes (9): global_cities DuckDB table, Global City Registry and Model Tiers Implementation Plan, main(), Build global_cities: the stable, honest registry of every city this platform…, _slug(), con(), fixture, _table_exists() (+1 more)

### Community 70 - "Tests Test Registry Test"
Cohesion: 0.14
Nodes (8): client(), fixture, Correctness tests for the Global Mobility Domain Model registry (SPEC-013…, No capability is hand-authored true -- every True demand/fare/journey flag…, Flat set of every registered path. Recent FastAPI wraps…, _route_paths(), test_capabilities_backed_by_real_model_registry_rows(), test_capabilities_match_what_is_actually_wired()

### Community 71 - "Docs"
Cohesion: 0.16
Nodes (14): /api/countries/*, /api/cities/* (Global Mobility Domain Model), GET /predict/demand, GET /predict/fare, backend/registry/*.py, journey_narrative.py, ADR-007: Structural basis Field on Every Journey Prediction, ADR-008: External Data-Source Adapters Under $0 Budget, API Reference (+6 more)

### Community 72 - "Backend Datasources Base Mobilitydatasource"
Cohesion: 0.14
Nodes (8): MobilityDataSource, Protocol, `MobilityDataSource` protocol (SPEC-013 FR-6) -- the shape every city's data…, Every area (zone/station/etc.) for this city, from its canonical area mart., Aggregated demand rows, optionally filtered by area/hour., Aggregated fare-stat rows, optionally filtered by pickup/dropoff area., Aggregated origin-destination flow rows, optionally filtered by origin., A citywide hourly series for `metric` (e.g. "demand"), for /forecast.

### Community 73 - "Backend Routers Context"
Cohesion: 0.19
Nodes (13): holiday(), get, Context APIs - Weather, Holiday, Traffic (Part 3 of API Decomposition).…, Get traffic/congestion information for a city. Returns historical traffic score…, Resolve a city to (lat, lon). Raises 400 -- not a bare 500 -- when the city is…, Get weather for a city at a specific time. Accepts either city_id or lat/lon…, Check if a date is a holiday in the city's country., _resolve_coords() (+5 more)

### Community 74 - "Tests Test Query Plan Test"
Cohesion: 0.21
Nodes (10): QueryPlan, parametrize, Compiler correctness per canonical intent against nyc_schema.py, and the "raise…, test_area_ranking_compiles(), test_bad_aggregation_raises(), test_comparison_compiles(), test_hourly_pattern_compiles(), test_metric_lookup_compiles() (+2 more)

### Community 75 - "Backend Registry Global Cities Registry"
Cohesion: 0.32
Nodes (11): backend/main.py, find_by_name(), get_city(), list_cities(), load(), Registry for global_cities (docs/superpowers/plans/2026-08-09-global-city-…, test_find_by_name_case_insensitive(), test_get_city_registered() (+3 more)

### Community 76 - "Backend Services City Journey Service"
Cohesion: 0.21
Nodes (11): CityJourneyEstimate, PredictionOut, Any, Deliberately a 4-field subset of JourneyEstimate: distance/duration (real, via…, Every journey field carries `basis` structurally (ADR-007) -- never a bare…, estimate(), CityJourneyEstimate, datetime (+3 more)

### Community 77 - "Fare Prediction Train Fare Xgb"
Cohesion: 0.26
Nodes (11): load_data(), main(), DataFrame, Path, Train a single tuned XGBoost fare-prediction model (SPEC-007). Deliberately not…, Small manual grid, selected by validation RMSE. Not a full ladder or CV search…, rmse_mae(), split_data() (+3 more)

### Community 78 - "Models Query Plan Finetune Evaluate"
Cohesion: 0.26
Nodes (10): call_base_model(), demo(), evaluate_file(), _parse_model_plan(), Path, Scores the base model's QueryPlan-JSON output against the known-correct plan on…, Structural match on intent/metric/filters/aggregation (FR-8) -- not…, run() (+2 more)

### Community 79 - "Tests Test London Pipeline Test"
Cohesion: 0.15
Nodes (9): con(), fixture, Correctness tests for the London (Santander Cycle Hire) dbt pipeline (SPEC-015…, The actual dbt test suite for the four London models -- pass or warn, never a…, station_id, trip_date, hour, day_of_week, total_trips, avg_duration_min -- real…, rule 6 / spec-015 ground rule: London is additive-only, NYC's warehouse file…, test_dbt_test_passes_for_london_models(), test_mart_shape_mirrors_zone_hourly_demand() (+1 more)

### Community 80 - "Nl To Sql Query Plan"
Cohesion: 0.24
Nodes (11): ADR-010: Query-Plan Fine-Tuning Budget Exception, models/query_plan_finetune/eval_report.json, evaluate.py, compile(), demo(), _group_by_name(), Deterministic QueryPlan -> SQL compiler (FR-2, spec-014). The LLM (base or,…, Resolve every field the plan references against `schema`; raises before any SQL… (+3 more)

### Community 81 - "London Demand Train London Xgb"
Cohesion: 0.29
Nodes (10): DataFrame, ndarray, Series, Tuned XGBoost regressor for London station-hourly bike-share demand (SPEC-015…, rmse_mae(), split_london_demand_blocks(), train_and_save(), tune() (+2 more)

### Community 82 - "Scripts Refresh Model Registry"
Cohesion: 0.23
Nodes (8): demo(), DataFrame, Path, Phase 4: regenerate `dbt_project/seeds/model_registry.csv`'s `training_period`…, Self-check on a throwaway copy: a metadata file with a later date_range must…, refresh(), _training_period_from_metadata(), Phase 4: refresh_model_registry.py must update training_period from real…

### Community 83 - "Backend Routers Zones"
Cohesion: 0.33
Nodes (10): load_zone_points(), Path, get_zone(), _get_zones(), list_zones(), _load_zones(), get, GET /zones (list), GET /zones/{zone_id} (detail) (FR-3). Zone metadata is… (+2 more)

### Community 84 - "Backend Adapters Routing Osrm"
Cohesion: 0.25
Nodes (10): _cached_route(), fetch(), fetch_distance(), fetch_duration(), datetime, Real road-network routing via OSRM (ADR-008). Defaults to OSRM's public demo…, _historical_pair(), Real historical (avg_duration_min, avg_speed_mph) for this exact zone-name pair… (+2 more)

### Community 85 - "Tests Test Tariff Profiles"
Cohesion: 0.44
Nodes (10): _base_fare_tariff(), _ctx(), demo(), _features(), Correctness tests for the tariff-profile fare engine (ADR-011): the LLM never…, FX is never on the fare path -- forcing it to fail must not change the result…, test_fare_monotonic_in_distance(), test_fx_unavailable_does_not_break_local_currency_fare() (+2 more)

### Community 86 - "Models Xgboost Model Feature Importance"
Cohesion: 0.24
Nodes (11): day_of_week, ewma, hour, XGBoost Feature Importance Chart, is_weekend, lag_168h, lag_1h, lag_24h (+3 more)

### Community 87 - "Scripts Download Worldmove"
Cohesion: 0.31
Nodes (10): Namespace, city_keys_from_disk(), city_keys_from_site(), download_key(), main(), output_dir(), parse_args(), Path (+2 more)

### Community 88 - "Rag Embeddings Build Vector Store"
Cohesion: 0.29
Nodes (10): Qdrant Vector Store, build_vector_store(), demo(), _embed(), _get_client(), Path, Embed insight docs into Qdrant (FR-2). Uses OpenAI's `text-embedding-3-small`…, OpenAI embeddings are already unit-normalized, so cosine distance in Qdrant… (+2 more)

### Community 89 - "Insight Generation Generate Insight Docs"
Cohesion: 0.31
Nodes (10): _allowed_numbers(), demo(), _facts_for_zone(), generate_all(), load_insight_docs(), _phrase_with_llm(), DataFrame, Path (+2 more)

### Community 90 - "Nl To Sql Sql Agent"
Cohesion: 0.27
Nodes (10): answer(), demo(), generate_plan(), Path, NL-to-SQL over the mart schema only (FR-3, ADR-004; restructured for SPEC-013…, Question -> QueryPlan -> deterministically compiled SQL -> real, read-only…, Defense-in-depth guard (ADR-004): compile_plan() only ever emits schema-…, The one place an LLM is called on the numeric-question path -- its entire… (+2 more)

### Community 91 - "Test Training Data Gen Data"
Cohesion: 0.27
Nodes (10): build_splits(), demo(), generate_examples(), Path, write_splits(), Every generated training/eval label is correct by construction (rule 2 -- no…, test_every_label_round_trips_through_the_compiler(), test_held_out_schema_absent_from_train_split() (+2 more)

### Community 92 - "Specs"
Cohesion: 0.18
Nodes (11): query_classifier.py, rag_pipeline.py, session_store.py, sql_agent.py, services/rag_service.py, routers/chat.py, ChatPanel.tsx, rag/nl_to_sql/nyc_schema.py (+3 more)

### Community 93 - "Algorithms Timeseries Seasonality Decompose"
Cohesion: 0.29
Nodes (9): _centered_moving_average(), decompose(), Decomposition, _plot_zone(), ndarray, Series, Trend + daily-seasonal + weekly-seasonal + residual decomposition, from…, Centered MA via convolution; edges (window//2 on each side) are NaN, same… (+1 more)

### Community 94 - "Architecture"
Cohesion: 0.22
Nodes (10): Frontend Architecture Audit, DemandForecast.tsx Fabricated Comparison Chart, pagerank_hubs.json Missing Artifact, backend/routers/platform.py, No Fabricated Metrics Rule, Dashboard Widget Fabrication Audit Finding, DESIGN.md Enterprise Product Spec, Enterprise Quality Checklist (+2 more)

### Community 95 - "Package Dependencies"
Cohesion: 0.20
Nodes (9): dependencies, animejs, gsap, @gsap/react, lenis, animejs, gsap, @gsap/react (+1 more)

### Community 96 - "Nl To Sql Query Plan"
Cohesion: 0.27
Nodes (8): Shared config for the RAG layer -- one place for the LLM model id and warehouse…, answer(), demo(), generate_plan(), Path, NL question -> QueryPlan (fine-tuned model) -> compiled SQL -> executed read-…, System prompt is `schema.describe()` alone -- exactly the training format…, _strip_fences()

### Community 97 - "Rag Journey Narrative"
Cohesion: 0.31
Nodes (9): extract_numbers(), _allowed_numbers(), _facts_from_components(), generate(), _phrase_with_llm(), AI Recommendations for a journey estimate (ADR-007). Reuses…, `components` is the dict[str, PredictionResult] journey_service.estimate()…, Returns (text, basis) -- basis is "modeled_estimate" for any LLM- phrased text… (+1 more)

### Community 98 - "Test Journey Test Journey Estimate"
Cohesion: 0.31
Nodes (9): _body(), client(), fixture, Correctness tests for POST /journey/estimate (ADR-007)., test_journey_estimate_happy_path(), test_journey_estimate_outside_coverage_degrades_honestly(), test_journey_estimate_unknown_vehicle_type_is_unavailable_not_default(), test_journey_estimate_vehicle_type_changes_fare_and_carbon() (+1 more)

### Community 99 - "Algorithms Spatial Geohash Grid"
Cohesion: 0.25
Nodes (8): load_zone_geohashes(), nearby_zones(), DataFrame, Path, Geohash encoding of zone centroids + prefix-matching for "nearby zones."…, Zones sharing a geohash prefix of length `prefix_len` with `location_id`., Rule 0: From-Scratch Must Still Be Verified, Algorithms Overview

### Community 100 - "Frontend Package Scripts"
Cohesion: 0.22
Nodes (8): name, private, scripts, build, dev, preview, type, version

### Community 101 - "Frontend Web Package Scripts"
Cohesion: 0.22
Nodes (8): name, private, scripts, build, dev, lint, start, version

### Community 102 - "Rag Session Store"
Cohesion: 0.42
Nodes (8): get_connection(), get_session_history(), init_db(), Any, Connection, Postgres-backed conversation history store (FR-7), migrated off SQLite per…, save_message(), session_exists()

### Community 103 - "Scripts Ingest Gtfs Feeds"
Cohesion: 0.39
Nodes (8): _download(), _fetch_and_extract_stops(), load_stops(), main(), Path, Download, unzip, and load GTFS static feeds' stops.txt into each city's own…, _read_feeds(), dbt_project/seeds/gtfs_feeds.csv

### Community 104 - "Scripts Ingest Tfl Cycle Hire"
Cohesion: 0.36
Nodes (8): _download(), fetch_journeys(), fetch_stations(), load_duckdb(), main(), Path, Download and load TfL Santander Cycle Hire journey data into DuckDB. Mirrors…, Pull live BikePoint locations and write the same station_id/name/lat/lon shape…

### Community 105 - "Backend Services Vehicle Profiles"
Cohesion: 0.32
Nodes (6): VehicleProfile, load(), load(), Path, Vehicle profiles -- data, not conditionals (ADR-007). Loads…, resolve()

### Community 106 - "Web Components Journey Cards Aicard"
Cohesion: 0.29
Nodes (5): AICard(), AICardProps, ChatRequest, ChatResponse, sendChatMessage()

### Community 107 - "Models Xgboost Model Train Xgboost"
Cohesion: 0.39
Nodes (7): plot_feature_importance(), DataFrame, Path, Tuned XGBoost regressor for zone-hourly demand (SPEC-006, FR-5). Same manual-…, rmse_mae(), train_and_save(), tune()

### Community 108 - "Tests Test Chronological Split Dedup"
Cohesion: 0.36
Nodes (6): _old_split_data(), DataFrame, Phase 2 dedup proof: `train_fare_xgb.split_data()` (now delegating to the…, The exact logic train_fare_xgb.split_data() used to inline, before Phase 2…, _synthetic_gapped_df(), test_new_split_data_matches_old_inline_logic_exactly()

### Community 109 - "Test Sql Agent Query Plan"
Cohesion: 0.25
Nodes (7): sql_agent.py-specific coverage for SPEC-013 FR-10: the LIVE `/chat` numeric-…, generate_sql() (the old LLM-writes-SQL-text function) must be gone;…, Patching generate_plan to return a known QueryPlan proves answer()'s executed…, _validate_sql() is kept as a second layer over the compiler's output (ADR-004…, test_sql_agent_answer_routes_through_the_compiler_not_raw_text(), test_sql_agent_has_no_raw_sql_generation_path(), test_validate_sql_still_rejects_disallowed_sql_defense_in_depth()

### Community 110 - "Scripts Extract Fixed Holidays"
Cohesion: 0.43
Nodes (6): demo(), extract(), _iso3_to_iso2_map(), _nager_covered_iso2(), DataFrame, Extends holiday coverage past Nager.Date's 204 countries (notably: no India)…

### Community 111 - "Backend Errors Geography"
Cohesion: 0.40
Nodes (4): GeographyErrorCode, Enum, str, Error taxonomy for the geography-discovery layer (GeoNames + Google Places…

### Community 112 - "Backend Services Platform Service"
Cohesion: 0.33
Nodes (6): load(), _load_insight_docs(), Path, Import the generator once and read the doc file once (at startup), so a request…, Read every artifact file once. Call from FastAPI's startup hook., _read_json()

### Community 113 - "Frontend Web App History Page"
Cohesion: 0.47
Nodes (5): coordLabel(), HistoryEntryCard(), HistoryPage(), getJourneyHistory(), JourneyHistoryEntry

### Community 114 - "Models Lstm Model Loss Curve"
Cohesion: 0.47
Nodes (6): LSTM Loss Curve (Zone-Hourly Demand), Train MSE (normalized), Validation MSE (normalized), LSTM Demand Forecast Model, Model Ladder (linear -> EWMA -> XGBoost -> LSTM), Zone-Hourly Demand Target

### Community 115 - "Scripts Calibrate Tariff Nyc"
Cohesion: 0.53
Nodes (5): blind_guess(), main(), measure_mape(), _parse_json_response(), Credibility anchor for the LLM-tariff methodology (ADR-011). Prompts the LLM…

### Community 116 - "Specs Journey Intelligence Spec"
Cohesion: 0.33
Nodes (6): services/model_service.py, backend/predictors/journey_predictors.py, backend/services/journey_service.py, backend/predictors/base.py, backend/routers/journey.py, backend/services/prediction_service.py

### Community 117 - "Skills Design Taste Frontend Skill"
Cohesion: 0.50
Nodes (5): Anti-Default Discipline, Anti-Slop Frontend Skill, Brief Inference / Design Read, Premium-Consumer Palette Ban, Three Dials (Variance/Motion/Density)

### Community 118 - "Algorithms Timeseries"
Cohesion: 0.50
Nodes (5): Daily and Weekly Seasonality Pattern, East Village (NYC Zone), Multiplicative Time-Series Decomposition (Trend/Seasonal/Residual), East Village Multiplicative Decomposition (Jan 2024), Ride Demand Time Series

### Community 119 - "Timeseries Output Park Slope Decomp"
Cohesion: 0.70
Nodes (5): Daily*Weekly Seasonality Component, Park Slope Multiplicative Decomposition Chart, Multiplicative Time-Series Decomposition, Park Slope Zone, Ride Demand Time Series (Jan 2024)

### Community 120 - "Backend Routers Platform Service"
Cohesion: 0.40
Nodes (5): capability_summary(), Per-capability supported/unsupported counts across every registered city,…, get_capability_summary(), Real coverage report over every registered city in BOTH registries (the…, test_capability_summary_counts_come_from_the_registries()

### Community 121 - "Infra Cdk Stack Dbtbuildstack"
Cohesion: 0.50
Nodes (3): Construct, DbtBuildStack, Stack

### Community 122 - "Scripts Backfill Weather Openmeteo"
Cohesion: 0.60
Nodes (4): fetch_city_weather(), main(), Backfill real historical hourly weather (temperature + precipitation) for every…, _real_dates_needed()

### Community 123 - "Test Build Global Cities Test"
Cohesion: 0.60
Nodes (4): _build(), Unit tests for scripts/build_global_cities.py's two correctness rules: a…, test_registered_city_without_active_model_is_transfer(), test_worldmove_row_colliding_with_registered_city_is_skipped()

### Community 124 - "Algorithms Timeseries"
Cohesion: 0.67
Nodes (4): algorithms/timeseries Module, JFK Airport Multiplicative Decomposition (Jan 2024), JFK Airport Ride Demand Time Series, Multiplicative Time-Series Decomposition (Trend/Seasonal/Residual)

### Community 125 - "Scripts Load Worldmove To Duckdb"
Cohesion: 0.67
Nodes (3): main(), parse_rows(), Load WorldMove population-mobility grids (data/raw/worldmove_data/*.npy) into…

### Community 126 - "Specs Query Plan Finetuning Spec"
Cohesion: 0.50
Nodes (4): models/query_plan_finetune/evaluate.py, rag/nl_to_sql/synthetic_schemas.py, models/query_plan_finetune/train.py, rag/nl_to_sql/training_data_gen.py

### Community 127 - "Github"
Cohesion: 0.67
Nodes (3): dbt Build AWS Workflow, infra/cdk/stack.py, scripts/aws_dbt_build_userdata.sh

### Community 129 - "Specs Hybrid Rag Spec"
Cohesion: 0.67
Nodes (3): build_vector_store.py, generate_insight_docs.py, rag/journey_narrative.py

## Knowledge Gaps
- **360 isolated node(s):** `EXAMPLE_PROMPTS`, `SOURCE_LABELS`, `defaultPickup`, `defaultDropoff`, `metadata` (+355 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **51 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `PredictionResult` connect `Backend Adapters` to `Backend Schemas`, `Docs`, `Backend Routers Analytics`, `Backend Routers Context`, `Backend`, `Backend Predictors Journey Predictors`, `Backend Routers Mobility`, `Backend Services City Journey Service`, `Backend Services Model Service`, `Backend Services Pricing Engine`, `Backend Adapters Routing Osrm`, `Test Fare Provenance Capabilities Test`, `Tests Test Tariff Profiles`?**
  _High betweenness centrality (0.033) - this node is a cross-community bridge._
- **Why does `Settings()` connect `Frontend Src Api Client` to `Frontend Web Components Ui`, `Frontend Src Components`?**
  _High betweenness centrality (0.020) - this node is a cross-community bridge._
- **Why does `Data Flow` connect `Rag Rag Pipeline` to `Docs`, `Scripts`, `Tests Test Prep Split`, `Models Data Baseline Build Features`, `Nl To Sql Sql Agent`?**
  _High betweenness centrality (0.018) - this node is a cross-community bridge._
- **Are the 7 inferred relationships involving `QueryPlan` (e.g. with `test_area_ranking_compiles()` and `test_bad_aggregation_raises()`) actually correct?**
  _`QueryPlan` has 7 INFERRED edges - model-reasoned connections that need verification._
- **What connects `EXAMPLE_PROMPTS`, `SOURCE_LABELS`, `defaultPickup` to the rest of the system?**
  _360 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Backend Schemas` be split into smaller, more focused modules?**
  _Cohesion score 0.04337899543378995 - nodes in this community are weakly interconnected._
- **Should `Frontend Web Components Journey Cards` be split into smaller, more focused modules?**
  _Cohesion score 0.06196291270918137 - nodes in this community are weakly interconnected._
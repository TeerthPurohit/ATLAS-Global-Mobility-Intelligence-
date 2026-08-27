# Graph Report - Uber nyc TLC Dataset  (2026-08-27)

## Corpus Check
- 284 files · ~159,375 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 2015 nodes · 3980 edges · 167 communities (118 shown, 49 thin omitted)
- Extraction: 95% EXTRACTED · 5% INFERRED · 0% AMBIGUOUS · INFERRED: 216 edges (avg confidence: 0.91)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `9d7db7d2`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- test_algorithms.py
- mobility.py
- PredictionField.tsx
- main.py
- kdtree_zone_lookup.py
- cn
- layout.tsx
- schemas.py
- PredictionResult
- api.ts
- test_fare_provenance_and_capabilities.py
- prediction_service.py
- test_api.py
- model_service.py
- Product Requirements Document
- ADR-011: Retreat from global coverage to NYC + London
- JourneyResults.tsx
- CapabilityGate.tsx
- compilerOptions
- analytics.py
- test_datasource_nyc.py
- requirements.txt (Full Project Deps)
- compare_models.py
- analyst/page.tsx
- cities.py
- Architecture Overview
- CompareForm.tsx
- JourneyMap.tsx
- dependencies
- predictions.py
- get_city_context
- Frontend Architecture Audit
- ADR-012: NYC Only
- city.py
- SPEC-008: Hybrid RAG Chat Layer
- BestDepartureCard.tsx
- rag_pipeline.py
- holiday
- journey.py
- session_store.py
- linear_regression_model.py
- modal-kimi
- chat.py
- split_demand_blocks
- test_rag.py
- build_zone_graph
- devDependencies
- route
- train_quantile_eta.py
- test_geography_generalized.py
- config.py
- CityMobilitySchema
- history/page.tsx
- build_vector_store.py
- QueryPlan
- data_prep/build_features.py
- congestion/build_features.py
- train_fare_xgb.py
- evaluate.py
- semantic_cache.py
- refresh_model_registry.py
- Implementation Audit
- query_plan_compiler.py
- dependencies
- zones.py
- test_registry.py
- journey_service.py
- models.py
- pagerank
- _base_fare_tariff
- XGBoost Feature Importance Chart
- generate_insight_docs.py
- sql_agent.py
- training_data_gen.py
- test_zone_geojson.py
- External Data Adapters Reference
- Demand Forecasting Model Ladder Comparison
- get
- seasonality_decompose.py
- ADR-010: Query-Plan Fine-Tuning Budget Exception
- NYC Ride Intelligence README
- frontend-web/package.json
- SettingsPage
- East Village Multiplicative Decomposition (Jan 2024)
- holidays_nager.py
- train_xgboost.py
- @deck.gl/core
- ingest_gtfs_feeds.py
- @deck.gl/layers
- test_sql_agent_query_plan.py
- geohash_grid.py
- @deck.gl/react
- weather_openmeteo.py
- ADR-012: NYC only — removing London
- ADR-013: Collapsing `city_id`
- @gsap/react
- extract_fixed_holidays.py
- train_congestion_xgb.py
- lucide-react
- LSTM Loss Curve (Zone-Hourly Demand)
- react
- chat_completion
- Park Slope Multiplicative Decomposition Chart
- backfill_weather_openmeteo.py
- nyc_fare_anchor.py
- SPEC-001: Data Foundation
- test_feature_gap_safety.py
- Local dev setup and warehouse build
- backend/predictors/journey_predictors.py
- react-dom
- dbt Project Config (nyc_tlc_rides)
- dbt Build AWS Workflow
- build_zone_geojson.py
- dump_countries_seed.py
- verify_ingestion.py
- registry/__init__.py
- backend/registry/*.py
- routers/__init__.py
- services/__init__.py
- Rule 7: No Speculative Infra
- Data Ingestion Verification Report
- @tanstack/react-query
- next.config.js
- next-env.d.ts
- gsap
- lenis
- maplibre-gl
- react-hook-form
- tailwind.config.ts
- test_dbt_marts.py
- int_trips_enriched dbt model
- Intermediate Models Schema
- Marts Models Schema
- zone_fare_stats dbt model
- zone_hourly_demand dbt model
- Staging Models Schema
- stg_trips dbt model
- Seeds Schema
- vehicle_profiles seed
- dbt Project User Config
- Nager.Date IsTodayPublicHoliday silent-wrongness fix
- architecture.png (placeholder)
- FastAPI lifespan preload of models and registries
- Getting the DuckDB File Into Colab (Drive mount or GCS, GLOBAL_MOBILITY_DATA_ROOT env var)
- taxi_zone_lookup.csv
- Cross-Cutting Principles (skill observations)
- Skill Observations Last Review Date
- Skill Observation Log
- backend/adapters/ (DataSourceAdapter)
- backend/services/geography_service.py
- rag/journey_narrative.py
- backend/services/pricing_engine.py
- backend/services/vehicle_profiles.py

## God Nodes (most connected - your core abstractions)
1. `cn()` - 60 edges
2. `PredictionResult` - 50 edges
3. `QueryPlan` - 36 edges
4. `CityMobilitySchema` - 32 edges
5. `Card()` - 27 edges
6. `JourneyFeatures` - 26 edges
7. `requirements.txt (Full Project Deps)` - 25 edges
8. `CardTitle()` - 24 edges
9. `JourneyContext` - 23 edges
10. `fetchJson()` - 21 edges

## Surprising Connections (you probably didn't know these)
- `PageRank Hub Ranking` --shares_data_with--> `build_zone_graph()`  [INFERRED]
  docs/algorithms/README.md → algorithms/graph/build_zone_graph.py
- `build_zone_graph()` --shares_data_with--> `zone_pair_flows dbt model`  [EXTRACTED]
  algorithms/graph/build_zone_graph.py → dbt_project/models/marts/schema.yml
- `Dijkstra / A* Shortest Path ETA` --shares_data_with--> `build_zone_graph()`  [INFERRED]
  docs/algorithms/README.md → algorithms/graph/build_zone_graph.py
- `test_compare_models_uses_identical_test_rows()` --calls--> `evaluate_all()`  [INFERRED]
  tests/test_demand_split_no_leakage.py → models/evaluation/compare_models.py
- `test_sql_agent_accepts_wellformed_mart_query()` --calls--> `_validate_sql()`  [INFERRED]
  tests/test_rag.py → rag/nl_to_sql/sql_agent.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Adding a City Onboarding Workflow** — docs_guides_adding_a_city, dbt_project_seeds_cities_cities, dbt_project_seeds_model_registry_model_registry, docs_reference_capabilities_chat_tiers [EXTRACTED 0.90]
- **AWS On-Demand dbt Build Pipeline** — github_workflows_dbt_build_aws, scripts_aws_dbt_build_userdata, infra_cdk_stack [EXTRACTED 0.90]
- **Four-Model Demand Ladder Compared on One Shared Chronological Test Set** — models_evaluation_metrics_report_ewma_baseline, models_evaluation_metrics_report_linear_regression, models_evaluation_metrics_report_xgboost_demand, models_evaluation_metrics_report_lstm_demand, specs_006_model_ladder_demand_spec [EXTRACTED 0.95]
- **Global Mobility Coverage Attempted Then Reverted to NYC-Only** — specs_013_global_mobility_domain_model_spec, specs_015_second_real_city_and_estimation_spec, docs_adr_adr_011_retreat_from_global_coverage, docs_adr_adr_012_nyc_only [EXTRACTED 0.95]
- **Hybrid RAG Numeric/Explanatory Routing Flow** — rag_router_query_classifier, rag_nl_to_sql_sql_agent, rag_insight_generation [EXTRACTED 0.95]
- **ADR Documentation Set** — docs_readme_md, docs_adr_adr_001_duckdb_over_postgres_md, docs_adr_adr_002_dbt_layering_md, docs_adr_adr_003_chronological_split_md [EXTRACTED 1.00]
- **OpenAI Embedding + Qdrant Vector Store Pipeline** — pkg_openai, pkg_qdrant_client, rag_embeddings_build_vector_store, docker_compose_qdrant_service [EXTRACTED 1.00]
- **Rise and retreat of the 519-city global coverage layer** — specs_015_second_real_city_and_estimation_spec_estimation_service, docs_superpowers_plans_2026_08_09_global_city_registry_global_cities_registry, docs_adr_adr_011_retreat_from_global_coverage_worldmove_data_quality, docs_adr_adr_011_retreat_from_global_coverage_retreat_decision, docs_superpowers_specs_2026_08_23_nyc_refocus_design_nyc_refocus_plan [EXTRACTED 1.00]
- **RDS TLS CA Bundle Fix for sslmode=verify-full (ADR-009)** — docker_compose_backend_service, rag_session_store, backend_services_prediction_log, certs_global_bundle_pem, docs_adr_adr_009_aws_cloud_dbt_build [EXTRACTED 1.00]
- **basis Field Honesty Discipline Across Docs** — docs_reference_capabilities, docs_api_readme, docs_reference_capabilities_basis_contract [INFERRED 0.80]
- **NL-to-SQL Evolution: Raw SQL Agent → Canonical Query Plan → Schema-Agnostic Fine-Tuned Query Plan** — specs_008_hybrid_rag_spec, specs_013_global_mobility_domain_model_spec, specs_014_query_plan_finetuning_spec [INFERRED 0.85]
- **NYC-Only Scope Narrowing (ADR-011 to ADR-012 to ADR-013)** — docs_adr_adr_012_nyc_only, docs_adr_adr_013_collapse_city_id, dbt_project_models_marts_canonical_areas_canonical_areas, dbt_project_seeds_cities_cities [INFERRED 0.85]
- **Product Documentation Set (Vision/PRD/Personas/Roadmap/Use-Cases/Success-Metrics)** — docs_product_vision, docs_product_prd, docs_product_personas, docs_product_use_cases, docs_product_success_metrics [INFERRED 0.85]
- **Zero-Fabrication / Total-Provenance Discipline** — architecture_audit_md, design_md, implementation_audit_md, claude_rules_md_zero_fabrication_rule [INFERRED 0.85]

## Communities (167 total, 49 thin omitted)

### Community 0 - "test_algorithms.py"
Cohesion: 0.14
Nodes (32): astar(), benchmark_astar_vs_dijkstra(), build_eta_graph(), demo(), dijkstra(), haversine_km(), load_zone_coords(), DiGraph (+24 more)

### Community 1 - "mobility.py"
Cohesion: 0.13
Nodes (33): AvailabilityResponse, availability(), carbon(), congestion(), demand(), departure_time(), fare(), _make_mobility_response() (+25 more)

### Community 2 - "PredictionField.tsx"
Cohesion: 0.07
Nodes (38): InsightCard(), AvailabilityCard(), AvailabilityCardContent(), AvailabilityCardProps, CarbonCard(), CarbonCardContent(), CarbonCardProps, CongestionCard() (+30 more)

### Community 3 - "main.py"
Cohesion: 0.05
Nodes (57): domain_error_handler(), lifespan(), log_requests(), openapi_explorer_docs(), get, rapidoc_docs(), FastAPI app (FR-1). Mounts routers; loads model artifacts once at startup (rule…, Every API request/response/failure logs through here (logging rule: log the… (+49 more)

### Community 4 - "kdtree_zone_lookup.py"
Cohesion: 0.15
Nodes (20): _benchmark(), benchmark_summary(), _coord(), KDNode, KDTree, linear_nearest(), load_zone_points(), Path (+12 more)

### Community 5 - "cn"
Cohesion: 0.10
Nodes (39): Theme, Units, CapabilityGateProps, CAPABILITIES_LIST, CapabilityMatrix(), CapabilityMatrixProps, CityHero(), CityHeroProps (+31 more)

### Community 6 - "layout.tsx"
Cohesion: 0.07
Nodes (27): ADR-0011, JourneyPageContent(), metadata, makeClient(), Providers(), HomePage(), CommandPalette(), NavBar() (+19 more)

### Community 7 - "schemas.py"
Cohesion: 0.08
Nodes (39): AvailabilityResponse, Capabilities, CityProfileResponse, ContextSourceEnvelope, Coordinates, CountriesResponse, Country, DemandResponse (+31 more)

### Community 8 - "PredictionResult"
Cohesion: 0.14
Nodes (35): effective_confidence(), JourneyContext, JourneyFeatures, PredictionResult, Derived, named scores every predictor actually consumes. Adding a new…, A component's own measured/derived confidence when it has one, the basis…, Raw inputs plus whatever the adapters (backend/adapters/) returned,…, _demand_pressure() (+27 more)

### Community 9 - "api.ts"
Cohesion: 0.08
Nodes (32): AnalyticsPage(), MetricCard(), ContextCard(), ContextCardProps, AnalyticsHistoryResponse, AnalyticsInsightsResponse, AnalyticsSummaryResponse, AnalyticsTrendsResponse (+24 more)

### Community 10 - "test_fare_provenance_and_capabilities.py"
Cohesion: 0.12
Nodes (27): ensure_table(), load(), Table, Cached per-city fare-structure profiles. A `TariffProfile` is a small set of…, Validation at construction, so it holds on BOTH paths -- the offline upsert and…, Idempotent create -- called from load() and upsert() the same way…, Startup read (rule 8: no work on the request path -- this is called once at app…, Offline-only write path (scripts/generate_tariff_profile.py,… (+19 more)

### Community 11 - "prediction_service.py"
Cohesion: 0.16
Nodes (28): DomainError, Exception type for the city-scoped routes. Routers/services raise…, forecast(), CapabilityUnavailable, ErrorCode, ForecastEnvelope, ForecastPoint, PredictionEnvelope (+20 more)

### Community 12 - "test_api.py"
Cohesion: 0.06
Nodes (5): client(), fixture, One happy-path test per backend route (standards.md testing bar)., With no city_id parameter left, omitting lat/lon must fall back to the seeded…, test_context_endpoints_default_to_the_city_centroid()

### Community 13 - "model_service.py"
Cohesion: 0.09
Nodes (31): data_vintage(), get_zone_momentum(), _haversine_miles(), hourly_shape_fraction(), load(), _load_fare_categories(), _load_zone_centroids(), _load_zone_demand_artifacts() (+23 more)

### Community 14 - "Product Requirements Document"
Cohesion: 0.08
Nodes (30): Personas, Secondary Persona: Future-You, Interviewer / Hiring Manager Persona, Product Requirements Document, PRD Functional Requirements (FR-1..FR-6), PRD Non-Goals, PRD Problem Statement, Success Metrics (+22 more)

### Community 15 - "ADR-011: Retreat from global coverage to NYC + London"
Cohesion: 0.08
Nodes (30): Structural `basis` field on every prediction, Confidence as a deterministic function of the basis mix, PredictionResult dataclass contract, Qualitative buckets over false precision (Surge Risk / Ride Availability), Single-method fetch() adapter pattern, Honest stubs for paid data sources, Cacheable point lookups with stdlib lru_cache, Open-Meteo historical backfill lifts the weather ceiling (+22 more)

### Community 16 - "JourneyResults.tsx"
Cohesion: 0.13
Nodes (13): defaultDropoff, defaultPickup, FormValues, JourneyForm(), JourneyFormProps, NYC_DROPOFF, NYC_PICKUP, schema (+5 more)

### Community 17 - "CapabilityGate.tsx"
Cohesion: 0.10
Nodes (21): CapabilityGate(), useCapability(), CapabilityUnavailable(), CapabilityUnavailableProps, AICard(), AICardProps, FareCard(), FareCardContent() (+13 more)

### Community 18 - "compilerOptions"
Cohesion: 0.07
Nodes (26): compilerOptions, allowJs, esModuleInterop, incremental, isolatedModules, jsx, lib, module (+18 more)

### Community 19 - "analytics.py"
Cohesion: 0.10
Nodes (27): AnalyticsHistoryResponse, AnalyticsInsightsResponse, AnalyticsSummaryResponse, AnalyticsTrendsResponse, history(), insights(), _parse_requested_at(), datetime (+19 more)

### Community 20 - "test_datasource_nyc.py"
Cohesion: 0.12
Nodes (9): get_datasource(), Mobility data source. One implementation, for the one city this platform serves…, NYCTLCDataSource, `NYCTLCDataSource` (SPEC-013 FR-6) -- thin read wrappers over the existing NYC…, _rows(), ds(), fixture, Correctness tests for NYCTLCDataSource (SPEC-013 FR-6): every method returns… (+1 more)

### Community 21 - "requirements.txt (Full Project Deps)"
Cohesion: 0.08
Nodes (27): qdrant Service (docker-compose), qdrant_storage Volume, KD-tree correctness test (scipy reference implementation), dbt-core, dbt-duckdb, duckdb, fastapi, geohash2 (+19 more)

### Community 22 - "compare_models.py"
Cohesion: 0.13
Nodes (19): evaluate_all(), _measure_latency(), Evaluate all 4 demand models on one shared test set (SPEC-006, FR-7). The…, probe() runs the model once on a small batch and returns the batch size;…, rmse_mae(), build_sequences(), demo(), DataFrame (+11 more)

### Community 23 - "analyst/page.tsx"
Cohesion: 0.12
Nodes (19): AnalystPage(), ask(), handleSubmit(), EXAMPLE_PROMPTS, looksNumeric(), Turn, TurnBubble(), CityPage() (+11 more)

### Community 24 - "cities.py"
Cohesion: 0.13
Nodes (22): _area_count(), capability_matrix(), _effective_model_status(), get_capabilities(), get_city(), get_city_profile(), list_metrics(), load() (+14 more)

### Community 25 - "Architecture Overview"
Cohesion: 0.05
Nodes (46): backend/Dockerfile, certs/global-bundle.pem (RDS TLS CA Bundle), Rule 2: Never Fabricate Results, Rule 7: Prune Scaffolding That Stops Earning Its Keep, Rule 8: No Reprocessing on Request Path, Construct, data/warehouse/nyc_rides.duckdb, int_trips_enriched.sql (+38 more)

### Community 26 - "CompareForm.tsx"
Cohesion: 0.08
Nodes (27): ComparePage(), BasisBadge(), CompareCard(), CompareCardProps, ComparisonCell(), VEHICLE_ICONS, CompareForm(), CompareFormProps (+19 more)

### Community 27 - "JourneyMap.tsx"
Cohesion: 0.15
Nodes (16): AddressSearchProps, JourneyMap(), JourneyMapProps, MAP_STYLE, ROUTE_LINE_LAYER, cache, formatPlaceName(), forwardGeocode() (+8 more)

### Community 28 - "dependencies"
Cohesion: 0.12
Nodes (17): clsx, framer-motion, dependencies, animejs, clsx, framer-motion, next, react-map-gl (+9 more)

### Community 29 - "predictions.py"
Cohesion: 0.43
Nodes (6): predict_demand(), predict_fare(), get, GET /predict/demand, GET /predict/fare (FR-2). Thin: validates input, delegates…, DemandPrediction, FarePrediction

### Community 30 - "get_city_context"
Cohesion: 0.18
Nodes (16): get_feed(), has_feed(), load(), GTFS transit feed registry -- exact mirror of backend/registry/models.py's…, True only once a real feed is both configured (not the unverified placeholder)…, get_city_context(), _now_iso(), Backend Context Orchestrator Service (Phase 4). Orchestrates environmental,… (+8 more)

### Community 31 - "Frontend Architecture Audit"
Cohesion: 0.12
Nodes (19): Anti-Default Discipline, Anti-Slop Frontend Skill, Brief Inference / Design Read, Premium-Consumer Palette Ban, Three Dials (Variance/Motion/Density), Frontend Architecture Audit, DemandForecast.tsx Fabricated Comparison Chart, pagerank_hubs.json Missing Artifact (+11 more)

### Community 32 - "ADR-012: NYC Only"
Cohesion: 0.16
Nodes (19): NYC-Only Scope Decision, Collapse city_id Decision, KD-Tree Zone Lookup, Cities Registry Module, City Router, canonical_areas dbt model, stg_zones dbt model, cities seed (+11 more)

### Community 33 - "city.py"
Cohesion: 0.21
Nodes (17): get_area(), get_capabilities(), get_city_context(), get_city_profile(), get_city_tariff(), list_areas(), list_metrics(), get (+9 more)

### Community 34 - "SPEC-008: Hybrid RAG Chat Layer"
Cohesion: 0.20
Nodes (21): ADR-003: Chronological Split, Fare Prediction XGBoost Model, SPEC-002: dbt Transformation Layer, SPEC-003: Spatial Algorithms — KD-Tree + Geohash, SPEC-004: Graph Algorithms — PageRank + Dijkstra, SPEC-005: Time-Series Algorithms — EWMA + Seasonality, SPEC-006: Model Ladder — Zone-Hourly Demand Forecasting, SPEC-007: Fare Prediction Model (+13 more)

### Community 35 - "BestDepartureCard.tsx"
Cohesion: 0.16
Nodes (9): InsightsPage(), SOURCE_LABELS, BestDepartureCard(), BestDepartureCardProps, Skeleton(), DepartureTimeResponse, getBestDeparture(), getInsights() (+1 more)

### Community 36 - "rag_pipeline.py"
Cohesion: 0.23
Nodes (16): extract_numbers(), answer(), _answer_explanatory(), _answer_numeric(), answer_stream(), demo(), _format_label(), _format_numeric_answer() (+8 more)

### Community 37 - "holiday"
Cohesion: 0.20
Nodes (12): _city_coords(), holiday(), get, Check if a date is a holiday in the city's country., Get traffic/congestion information. Returns a historical traffic score where…, The served city's seeded (lat, lon). Raises 400 -- not a bare 500 -- when the…, Get weather at a specific time. Reports the adapter's real 0-1 weather severity…, traffic() (+4 more)

### Community 38 - "journey.py"
Cohesion: 0.14
Nodes (19): estimate(), features(), history(), datetime, get, post, POST /journey/estimate -- the Journey Intelligence Engine endpoint (ADR-007).…, _to_out() (+11 more)

### Community 39 - "session_store.py"
Cohesion: 0.08
Nodes (35): ADR-009 (CDK deploy / RDS Postgres), get_recent_predictions(), init_db(), JourneyPrediction, log_prediction(), Table, Postgres-backed prediction log (ADR-007 follow-up, migrated off SQLite per…, _table_for() (+27 more)

### Community 40 - "linear_regression_model.py"
Cohesion: 0.40
Nodes (4): DataFrame, Linear regression baseline for zone-hourly demand (SPEC-006, FR-3). Uses the…, rmse_mae(), train_and_save()

### Community 41 - "modal-kimi"
Cohesion: 0.12
Nodes (16): limit, name, tool_call, context, output, models, name, npm (+8 more)

### Community 42 - "chat.py"
Cohesion: 0.08
Nodes (39): get_chat_tier(), `full_rag` with both a warehouse and an insight corpus, `sql_only` with a…, get_chat_history(), _normalize_route(), post_chat(), get, post, Chat router endpoints: POST /chat, GET /chat/history/{session_id}, and WS… (+31 more)

### Community 43 - "split_demand_blocks"
Cohesion: 0.15
Nodes (17): chronological_split(), demo(), _latest_month_start(), DataFrame, Chronological train/validation/test split (ADR-003). Never random-split time-…, train/val = every month before the latest one (chronological 85/15), test = the…, Sort `df` by `ts_col` and slice into len(fracs) chunks, in the given…, split_demand_blocks() (+9 more)

### Community 44 - "test_rag.py"
Cohesion: 0.16
Nodes (15): True iff every number in `text` is either a small connective number…, validate_grounding(), _heuristic_classify(), parametrize, skipif, RAG layer: the non-trivial, LLM-independent logic gets a real test…, test_heuristic_classify_ambiguous_defaults_numeric(), test_heuristic_classify_explanatory() (+7 more)

### Community 45 - "build_zone_graph"
Cohesion: 0.16
Nodes (14): build_zone_graph(), demo(), DiGraph, Path, Build a weighted directed zone-to-zone trip-flow graph from the…, Return a directed graph of zones with edge attribute `weight` = total trip…, PageRank Hub Ranking, Dijkstra / A* Shortest Path ETA (+6 more)

### Community 46 - "devDependencies"
Cohesion: 0.13
Nodes (15): autoprefixer, devDependencies, autoprefixer, postcss, tailwindcss, @types/node, @types/react, @types/react-dom (+7 more)

### Community 47 - "route"
Cohesion: 0.20
Nodes (12): _predict_route(), Shared route prediction - returns (distance, duration)., Get route distance and duration for a city. Uses OSRM with haversine fallback.…, route(), JourneyContextRequest, Shared context for all mobility predictions - coordinates, time, vehicle., Request for routing - inherits all context fields., Route response with distance and duration. (+4 more)

### Community 48 - "train_quantile_eta.py"
Cohesion: 0.16
Nodes (10): pinball_loss(), DataFrame, ndarray, XGBRegressor, Quantile ETA models (Phase 7): eta_p10/p50/p90 via XGBoost's native…, train_and_save(), train_quantile(), metadata() (+2 more)

### Community 49 - "test_geography_generalized.py"
Cohesion: 0.20
Nodes (8): get_area(), client(), fixture, Correctness tests for geography_service.py's SPEC-013 FR-5 additions…, The pre-existing KD-tree resolve() -- a distinct concern from…, test_get_area_known_zone(), test_get_area_unknown_area_id_is_none(), test_resolve_still_works_unchanged()

### Community 50 - "config.py"
Cohesion: 0.23
Nodes (10): python-dotenv, Shared config for the RAG layer -- one place for the LLM model id and warehouse…, _allowed_numbers(), _facts_from_components(), generate(), _phrase_with_llm(), AI Recommendations for a journey estimate (ADR-007). Reuses…, `components` is the dict[str, PredictionResult] journey_service.estimate()… (+2 more)

### Community 51 - "CityMobilitySchema"
Cohesion: 0.15
Nodes (13): The one real CityMobilitySchema, for NYC's actual marts (FR-3). Column/table…, CityMobilitySchema, demo(), FieldMapping, MetricSchema, Schema-agnostic QueryPlan + per-city schema resolver (FR-1, spec-014). Today's…, A canonical metric's backing table, its own value column, and every other…, Canonical field name -> real (table, column), scoped per metric since the same… (+5 more)

### Community 52 - "history/page.tsx"
Cohesion: 0.25
Nodes (8): coordLabel(), HistoryEntryCard(), HistoryPage(), commands, Dialog(), DialogProps, getJourneyHistory(), JourneyHistoryEntry

### Community 53 - "build_vector_store.py"
Cohesion: 0.23
Nodes (13): build_vector_store(), demo(), _embed(), _get_client(), _point_id(), Path, Embed insight docs into Qdrant (FR-2). Uses OpenAI's `text-embedding-3-small`…, Hybrid rerank: blend each candidate's real embedding cosine score (already in… (+5 more)

### Community 54 - "QueryPlan"
Cohesion: 0.16
Nodes (13): QueryPlan, _gen_area_ranking(), _gen_comparison(), _gen_top_n(), parametrize, Compiler correctness per canonical intent against nyc_schema.py, and the "raise…, test_area_ranking_compiles(), test_bad_aggregation_raises() (+5 more)

### Community 55 - "data_prep/build_features.py"
Cohesion: 0.10
Nodes (29): _best_alpha(), ewma(), ewma_blocks(), load_zone_hourly_blocks(), DuckDBPyConnection, ndarray, Series, EWMA smoothing over zone_hourly_demand, implemented from scratch. S_t = alpha *… (+21 more)

### Community 56 - "congestion/build_features.py"
Cohesion: 0.16
Nodes (20): _bucket(), build_features(), build_free_flow_lookup(), demo(), _holiday_flags(), load_raw_trips(), DataFrame, DuckDBPyConnection (+12 more)

### Community 57 - "train_fare_xgb.py"
Cohesion: 0.15
Nodes (17): load_data(), main(), DataFrame, Path, Train a single tuned XGBoost fare-prediction model (SPEC-007). Deliberately not…, Small manual grid, selected by validation RMSE. Not a full ladder or CV search…, rmse_mae(), split_data() (+9 more)

### Community 58 - "evaluate.py"
Cohesion: 0.26
Nodes (10): call_base_model(), demo(), evaluate_file(), _parse_model_plan(), Path, Scores the base model's QueryPlan-JSON output against the known-correct plan on…, Structural match on intent/metric/filters/aggregation (FR-8) -- not…, run() (+2 more)

### Community 59 - "semantic_cache.py"
Cohesion: 0.28
Nodes (12): demo(), _embed(), _ensure_collection(), get(), _get_client(), _point_id(), put(), Any (+4 more)

### Community 60 - "refresh_model_registry.py"
Cohesion: 0.23
Nodes (8): demo(), DataFrame, Path, Phase 4: regenerate `dbt_project/seeds/model_registry.csv`'s `training_period`…, Self-check on a throwaway copy: a metadata file with a later date_range must…, refresh(), _training_period_from_metadata(), Phase 4: refresh_model_registry.py must update training_period from real…

### Community 61 - "Implementation Audit"
Cohesion: 0.18
Nodes (12): DuckDB over Postgres Decision, dbt Staging/Intermediate/Marts Layering Decision, Chronological Train/Val/Test Split Decision, Docs Index, Implementation Audit, Chronological Split Discipline (Implementation Audit), city_tariff_profiles Table, global_cities Table (+4 more)

### Community 62 - "query_plan_compiler.py"
Cohesion: 0.21
Nodes (14): answer(), demo(), generate_plan(), Path, NL question -> QueryPlan (fine-tuned model) -> compiled SQL -> executed read-…, System prompt is `schema.describe()` alone -- exactly the training format…, _strip_fences(), compile() (+6 more)

### Community 63 - "dependencies"
Cohesion: 0.20
Nodes (9): dependencies, animejs, gsap, @gsap/react, lenis, animejs, gsap, @gsap/react (+1 more)

### Community 64 - "zones.py"
Cohesion: 0.44
Nodes (9): get_zone(), _get_zones(), list_zones(), _load_zones(), get, GET /zones (list), GET /zones/{zone_id} (detail) (FR-3). Zone metadata is…, Lazily build the zone table on first request. Loaded once and cached…, Zone (+1 more)

### Community 65 - "test_registry.py"
Cohesion: 0.18
Nodes (10): client(), fixture, Correctness tests for the city registry (SPEC-013 FR-4/FR-9): profile…, Flat set of every registered path. Recent FastAPI wraps…, ADR-011/013: this platform serves the one city it has real trip data for, and…, No capability is hand-authored true -- every True demand/fare/journey flag…, _route_paths(), test_capabilities_backed_by_real_model_registry_rows() (+2 more)

### Community 66 - "journey_service.py"
Cohesion: 0.11
Nodes (23): backend/adapters/ (weather/holiday/routing HTTP adapters), _cached_route(), fetch(), fetch_distance(), fetch_duration(), datetime, Real road-network routing via OSRM (ADR-008). Defaults to OSRM's public demo…, Predictor (+15 more)

### Community 67 - "models.py"
Cohesion: 0.25
Nodes (10): get_model(), has_active_model(), list_models_for(), load(), Model registry (SPEC-013 FR-4) -- thin query module over the seeded…, The active model backing `metric`, or None if the capability isn't really wired…, resolve_model(), Operations (+2 more)

### Community 68 - "pagerank"
Cohesion: 0.39
Nodes (8): demo(), hub_summary(), pagerank(), DiGraph, PageRank from scratch via power iteration (FR-2). PR(p) = (1-d)/N + d *…, Top-k hubs with rank/score/raw-degree, for persisting as a real artifact…, top_hubs(), test_pagerank_matches_networkx_small_synthetic_graph()

### Community 69 - "_base_fare_tariff"
Cohesion: 0.44
Nodes (10): _base_fare_tariff(), _ctx(), demo(), _features(), Correctness tests for the tariff-profile fare engine (ADR-011): the LLM never…, A tariff fare is denominated in the city's own currency and is never FX-…, test_fare_monotonic_in_distance(), test_fare_stays_in_the_profiles_own_currency_never_converted() (+2 more)

### Community 70 - "XGBoost Feature Importance Chart"
Cohesion: 0.24
Nodes (11): day_of_week, ewma, hour, XGBoost Feature Importance Chart, is_weekend, lag_168h, lag_1h, lag_24h (+3 more)

### Community 71 - "generate_insight_docs.py"
Cohesion: 0.31
Nodes (10): _allowed_numbers(), demo(), _facts_for_zone(), generate_all(), load_insight_docs(), _phrase_with_llm(), DataFrame, Path (+2 more)

### Community 72 - "sql_agent.py"
Cohesion: 0.27
Nodes (10): answer(), demo(), generate_plan(), Path, NL-to-SQL over the mart schema only (FR-3, ADR-004; restructured for SPEC-013…, The one place an LLM is called on the numeric-question path -- its entire…, Question -> QueryPlan -> deterministically compiled SQL -> real, read-only…, Defense-in-depth guard (ADR-004): compile_plan() only ever emits schema-… (+2 more)

### Community 73 - "training_data_gen.py"
Cohesion: 0.16
Nodes (18): QueryFilters, Only the filters actually set, as canonical-name -> value., _area_value(), build_splits(), demo(), _gen_hourly_pattern(), _gen_metric_lookup(), generate_examples() (+10 more)

### Community 74 - "test_zone_geojson.py"
Cohesion: 0.20
Nodes (9): _coords(), fixture, Correctness checks for the map hero's zone geometry (ADR-011 phase 7). The bug…, Walk an arbitrarily nested GeoJSON coordinate array down to positions., Catches the axis-order bug: (lat, lon) puts NYC at ~(40, -74) read as lon=40,…, The choropleth joins these to zone_hourly_demand on location_id -- a drifted or…, test_every_zone_position_is_lon_lat_inside_nyc(), test_location_ids_join_to_the_zone_lookup() (+1 more)

### Community 75 - "External Data Adapters Reference"
Cohesion: 0.40
Nodes (6): Nager.Date Holidays Adapter, Open-Meteo Weather Adapter, GTFS Transit Registry, Adding a City - Step 3: Transit Context, External Data Adapters Reference, GTFS Feed Ingestion Script

### Community 76 - "Demand Forecasting Model Ladder Comparison"
Cohesion: 0.25
Nodes (8): Block-Gap-Aware Chronological Split (rationale: disjoint monthly warehouse blocks require boundary-snapped cutoffs, not row-count splits), Demand Forecasting Model Ladder Comparison, EWMA Baseline Model, Linear Regression Baseline Model, LSTM Demand Model, LSTM Stale Artifact (rationale: saved weights/scaling fit on old 2024 warehouse, de-normalizes 2026-04 predictions with wrong constants — 96.9 RMSE is not a real finding), RMSE Chosen Over MAE as Primary Metric (rationale: squared-error term penalizes costly under-provisioned surge hours harder than MAE does), Train/Eval Split by Schema Family, Not Randomly (held-out synthetic schema never seen in training)

### Community 77 - "get"
Cohesion: 0.50
Nodes (4): get(), has_profile(), The cached profile for the one city this platform serves (ADR-013). The…, Whether a real cached profile backs the fare estimate -- read from the loaded…

### Community 78 - "seasonality_decompose.py"
Cohesion: 0.29
Nodes (9): _centered_moving_average(), decompose(), Decomposition, _plot_zone(), ndarray, Series, Trend + daily-seasonal + weekly-seasonal + residual decomposition, from…, Centered MA via convolution; edges (window//2 on each side) are NaN, same… (+1 more)

### Community 79 - "ADR-010: Query-Plan Fine-Tuning Budget Exception"
Cohesion: 0.50
Nodes (4): ADR-010: Query-Plan Fine-Tuning Budget Exception, models/query_plan_finetune/eval_report.json, evaluate.py, SPEC-014 (RAG Fine-Tuning Track)

### Community 80 - "NYC Ride Intelligence README"
Cohesion: 0.42
Nodes (9): ADR-011: Retreat From Global Coverage, Product Roadmap, Layer 0: Data Foundation, Layer 1: dbt Transformation, Layer 2: Algorithms, Layer 3: Model Ladder, Layer 4: Hybrid RAG, Layer 5: Serving & Presentation (+1 more)

### Community 81 - "frontend-web/package.json"
Cohesion: 0.22
Nodes (8): name, private, scripts, build, dev, lint, start, version

### Community 83 - "East Village Multiplicative Decomposition (Jan 2024)"
Cohesion: 0.32
Nodes (8): Daily and Weekly Seasonality Pattern, East Village (NYC Zone), algorithms/timeseries Module, East Village Multiplicative Decomposition (Jan 2024), JFK Airport Multiplicative Decomposition (Jan 2024), Ride Demand Time Series, JFK Airport Ride Demand Time Series, Multiplicative Time-Series Decomposition (Trend/Seasonal/Residual)

### Community 84 - "holidays_nager.py"
Cohesion: 0.43
Nodes (7): demo(), _extended_fixed_holidays(), fetch(), datetime, Real public-holiday lookup via Nager.Date -- free, global, no API key required…, Real holiday dates (ISO strings) for a (year, country), or None if the lookup…, _year_holidays()

### Community 85 - "train_xgboost.py"
Cohesion: 0.39
Nodes (7): plot_feature_importance(), DataFrame, Path, Tuned XGBoost regressor for zone-hourly demand (SPEC-006, FR-5). Same manual-…, rmse_mae(), train_and_save(), tune()

### Community 87 - "ingest_gtfs_feeds.py"
Cohesion: 0.46
Nodes (7): _download(), _fetch_and_extract_stops(), load_stops(), main(), Path, Download, unzip, and load GTFS static feeds' stops.txt into each city's own…, _read_feeds()

### Community 89 - "test_sql_agent_query_plan.py"
Cohesion: 0.25
Nodes (7): sql_agent.py-specific coverage for SPEC-013 FR-10: the LIVE `/chat` numeric-…, generate_sql() (the old LLM-writes-SQL-text function) must be gone;…, Patching generate_plan to return a known QueryPlan proves answer()'s executed…, _validate_sql() is kept as a second layer over the compiler's output (ADR-004…, test_sql_agent_answer_routes_through_the_compiler_not_raw_text(), test_sql_agent_has_no_raw_sql_generation_path(), test_validate_sql_still_rejects_disallowed_sql_defense_in_depth()

### Community 90 - "geohash_grid.py"
Cohesion: 0.33
Nodes (6): load_zone_geohashes(), nearby_zones(), DataFrame, Path, Geohash encoding of zone centroids + prefix-matching for "nearby zones."…, Zones sharing a geohash prefix of length `prefix_len` with `location_id`.

### Community 92 - "weather_openmeteo.py"
Cohesion: 0.52
Nodes (6): _cached_fetch(), demo(), fetch(), datetime, Real weather adjustment via Open-Meteo's free forecast API (ADR-008 update,…, _severity_from_conditions()

### Community 93 - "ADR-012: NYC only — removing London"
Cohesion: 0.29
Nodes (7): ADR-012: NYC only — removing London, Alternatives considered, Collapsing `city_id`, Consequence: a test got stronger, Context, Decision, Reversibility

### Community 94 - "ADR-013: Collapsing `city_id`"
Cohesion: 0.29
Nodes (7): ADR-013: Collapsing `city_id`, Alternatives considered, Consequence: two latent bugs surfaced, Context, Decision, The seam that replaces it, What this bought, honestly

### Community 96 - "extract_fixed_holidays.py"
Cohesion: 0.43
Nodes (6): demo(), extract(), _iso3_to_iso2_map(), _nager_covered_iso2(), DataFrame, Extends holiday coverage past Nager.Date's 204 countries (notably: no India)…

### Community 97 - "train_congestion_xgb.py"
Cohesion: 0.60
Nodes (5): DataFrame, Train the congestion-multiplier XGBoost regressor (Phase 6). Same tuned-grid-…, rmse_mae(), train_and_save(), tune()

### Community 99 - "LSTM Loss Curve (Zone-Hourly Demand)"
Cohesion: 0.47
Nodes (6): LSTM Loss Curve (Zone-Hourly Demand), Train MSE (normalized), Validation MSE (normalized), LSTM Demand Forecast Model, Model Ladder (linear -> EWMA -> XGBoost -> LSTM), Zone-Hourly Demand Target

### Community 101 - "chat_completion"
Cohesion: 0.20
Nodes (12): chat_completion(), demo(), Shared DeepSeek-primary / OpenAI-fallback chat completion helper. DeepSeek's…, Same call shape as `OpenAI().chat.completions.create(...)`. Tries DeepSeek…, classify(), demo(), Numeric vs explanatory intent router (FR-4, ADR-004). A short LLM…, blind_guess() (+4 more)

### Community 102 - "Park Slope Multiplicative Decomposition Chart"
Cohesion: 0.70
Nodes (5): Daily*Weekly Seasonality Component, Park Slope Multiplicative Decomposition Chart, Multiplicative Time-Series Decomposition, Park Slope Zone, Ride Demand Time Series (Jan 2024)

### Community 103 - "backfill_weather_openmeteo.py"
Cohesion: 0.60
Nodes (4): fetch_city_weather(), main(), Backfill real historical hourly weather (temperature + precipitation) for every…, _real_dates_needed()

### Community 104 - "nyc_fare_anchor.py"
Cohesion: 0.50
Nodes (4): demo(), fit_nyc_fare_anchor(), DuckDBPyConnection, Real, measured NYC fare anchor shared by generate_tariff_profile.py and…

### Community 105 - "SPEC-001: Data Foundation"
Cohesion: 0.40
Nodes (5): SPEC-001: Data Foundation, scripts/load_raw_to_duckdb.py, data/warehouse/nyc_rides.duckdb, scripts/spot_check.py, scripts/verify_ingestion.py

### Community 106 - "test_feature_gap_safety.py"
Cohesion: 0.60
Nodes (4): _assert_no_cross_block_leakage(), _make_gapped_blocks(), Phase 3 gap-safety proof: lag_1h/lag_24h/lag_168h/ewma/rolling_7d_avg must…, test_nyc_build_features_gap_safe()

### Community 107 - "Local dev setup and warehouse build"
Cohesion: 0.50
Nodes (4): Local dev setup and warehouse build, Tests skip when the warehouse is unbuilt, NYC zone geometry and choropleth hero, Serving-only backend dependency split

### Community 108 - "backend/predictors/journey_predictors.py"
Cohesion: 0.50
Nodes (4): backend/predictors/journey_predictors.py, backend/services/journey_service.py, backend/predictors/base.py, backend/routers/journey.py

### Community 110 - "dbt Project Config (nyc_tlc_rides)"
Cohesion: 0.67
Nodes (3): dbt Project Config (nyc_tlc_rides), dbt Profiles Config, taxi_zone_lookup seed

### Community 111 - "dbt Build AWS Workflow"
Cohesion: 0.67
Nodes (3): dbt Build AWS Workflow, infra/cdk/stack.py, scripts/aws_dbt_build_userdata.sh

## Knowledge Gaps
- **272 isolated node(s):** `ADR-0013`, `EXAMPLE_PROMPTS`, `SOURCE_LABELS`, `defaultPickup`, `defaultDropoff` (+267 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **49 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Operations` connect `models.py` to `cities.py`, `prediction_service.py`, `rag_pipeline.py`, `query_plan_compiler.py`?**
  _High betweenness centrality (0.047) - this node is a cross-community bridge._
- **Why does `Data Flow` connect `Architecture Overview` to `sql_agent.py`, `split_demand_blocks`, `chat_completion`, `data_prep/build_features.py`?**
  _High betweenness centrality (0.045) - this node is a cross-community bridge._
- **Why does `Models Overview` connect `model_service.py` to `SPEC-008: Hybrid RAG Chat Layer`, `Product Requirements Document`?**
  _High betweenness centrality (0.030) - this node is a cross-community bridge._
- **Are the 7 inferred relationships involving `PredictionResult` (e.g. with `fetch()` and `fetch()`) actually correct?**
  _`PredictionResult` has 7 INFERRED edges - model-reasoned connections that need verification._
- **Are the 19 inferred relationships involving `QueryPlan` (e.g. with `call_base_model()` and `demo()`) actually correct?**
  _`QueryPlan` has 19 INFERRED edges - model-reasoned connections that need verification._
- **Are the 16 inferred relationships involving `CityMobilitySchema` (e.g. with `answer()` and `generate_plan()`) actually correct?**
  _`CityMobilitySchema` has 16 INFERRED edges - model-reasoned connections that need verification._
- **What connects `ADR-0013`, `EXAMPLE_PROMPTS`, `SOURCE_LABELS` to the rest of the system?**
  _272 weakly-connected nodes found - possible documentation gaps or missing edges._
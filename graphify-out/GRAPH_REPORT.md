# Graph Report - Uber nyc TLC Dataset  (2026-08-28)

## Corpus Check
- 112 files · ~2,903,637 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 2079 nodes · 3874 edges · 210 communities (133 shown, 77 thin omitted)
- Extraction: 96% EXTRACTED · 4% INFERRED · 0% AMBIGUOUS · INFERRED: 168 edges (avg confidence: 0.9)
- Token cost: 140,000 input · 12,768 output

## Community Hubs (Navigation)
- Journey History & Capability Gates
- Fare Pricing Engine
- Journey Predictors Base
- Frontend Design & Audit Docs
- Insights & Context Cards
- Compare & Journey Pages
- App Layout & Compare Card
- Backend Schemas
- Chat Router & History
- Mobility Router
- Backend API Tests
- Domain Errors & City Router
- Product Docs (PRD/Personas)
- Capability Matrix & City Hero
- Infra Adapters & Dependencies
- Frontend TS Config
- City Registry & Capabilities
- NYC TLC Data Source
- Home & Journey Page
- Local QueryPlan Model Decision & Design
- train_lstm
- page
- Tabs
- test_registry
- spec
- useReverseGeocode
- analytics
- package
- context
- city
- QueryPlan Training Data & LoRA Script
- training_data_gen
- test_geography_generalized
- test_algorithms
- shortest_path_eta
- kdtree_zone_lookup
- journey_service
- capabilities
- schemas
- tariff_profiles
- build_features
- opencode
- query_plan
- chronological_split
- LLM Client Fallback Chain
- RAG Pipeline Answer Routing
- test_rag
- README
- package
- transit
- schema
- motion
- build_vector_store
- journey_narrative
- test_query_plan
- ewma_smoothing
- main
- compose_eta
- train_fare_xgb
- semantic_cache
- README
- IMPLEMENTATION_AUDIT
- Fine-Tuned QueryPlan Agent
- package
- test_analytics
- prediction_log
- session_store
- README
- feature_importance
- generate_insight_docs
- SQL Agent QueryPlan Generation
- test_training_data_gen
- test_zone_geojson
- Architecture
- metrics_report
- test_journey
- seasonality_decompose
- holidays_nager
- aws_dbt_build_userdata
- package
- Oracle VM Deployment Scripts
- build_features
- pagerank_hubs
- East_Village_decomp
- zones
- db
- schema
- Roadmap
- train_quantile_eta
- metrics_report
- train_xgboost
- query_plan_compiler
- ingest_gtfs_feeds
- test_chronological_split_dedup
- test_sql_agent_query_plan
- geohash_grid
- generate_algorithm_artifacts
- docker-compose
- ADR-012-nyc-only
- ADR-013-collapse-city-id
- ewma_forecast
- extract_fixed_holidays
- test_quantile_eta_ordering_and_coverage
- predictions
- app
- train_congestion_xgb
- test_demand_split_no_leakage
- loss_curve
- Park_Slope_decomp
- adapters
- 2026-08-09-global-city-registry
- backfill_weather_openmeteo
- nyc_fare_anchor
- spec
- test_feature_gap_safety
- schema
- README
- spec
- requirements
- dbt-build-aws
- build_zone_geojson
- verify_ingestion
- __init__
- README
- __init__
- __init__
- ci
- ingestion_report
- dbt_project
- package
- ADR-010-query-plan-finetuning-budget-exception
- package
- next.config
- next-env.d
- package
- package
- package
- package
- package
- package
- tailwind.config
- test_dbt_marts
- AnalyticsHistoryResponse
- AnalyticsInsightsResponse
- AnalyticsSummaryResponse
- AnalyticsTrendsResponse
- AvailabilityResponse
- get
- get
- get
- get
- get
- get
- get
- Capabilities
- CarbonResponse
- ChatMessage
- ChatRequest
- ChatResponse
- CityProfileResponse
- CityTariffResponse
- CongestionResponse
- schema
- schema
- schema
- .user
- DemandResponse
- DepartureTimeResponse
- architecture
- README
- 2026-08-23-nyc-refocus-design
- FareResponse
- HolidayResponse
- JourneyEstimate
- JourneyHistoryEntry
- JourneyRequest
- MobilityResponse
- README
- PredictionOut
- PredictionRequest
- Table
- RouteRequest
- RouteResponse
- README
- cross-cutting-principles
- last-review-date
- log
- spec
- spec
- spec
- spec
- spec
- SurgeResponse
- TrafficResponse
- WeatherResponse
- Zone

## God Nodes (most connected - your core abstractions)
1. `cn()` - 60 edges
2. `QueryPlan` - 37 edges
3. `CityMobilitySchema` - 32 edges
4. `get()` - 30 edges
5. `Card()` - 27 edges
6. `requirements.txt (Full Project Deps)` - 25 edges
7. `CardTitle()` - 24 edges
8. `chat_completion()` - 23 edges
9. `fetchJson()` - 21 edges
10. `ErrorCode` - 19 edges

## Surprising Connections (you probably didn't know these)
- `PageRank Hub Ranking` --shares_data_with--> `build_zone_graph()`  [INFERRED]
  docs/algorithms/README.md → algorithms/graph/build_zone_graph.py
- `test_demand_chronological_split_no_leakage()` --calls--> `split_demand_blocks()`  [INFERRED]
  tests/test_demand_split_no_leakage.py → models/data_prep/chronological_split.py
- `test_compare_models_uses_identical_test_rows()` --calls--> `evaluate_all()`  [INFERRED]
  tests/test_demand_split_no_leakage.py → models/evaluation/compare_models.py
- `Dijkstra / A* Shortest Path ETA` --shares_data_with--> `build_zone_graph()`  [INFERRED]
  docs/algorithms/README.md → algorithms/graph/build_zone_graph.py
- `Three-Tier Honesty Model: Real / Estimated / Unavailable (never a silent zero)` --semantically_similar_to--> `Measured Prediction Interval Coverage (78.9% vs nominal 80%, reported honestly rather than rounded up)`  [INFERRED] [semantically similar]
  specs/015-second-real-city-and-estimation/spec.md → models/evaluation/metrics_report.md

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **QueryPlan local fine-tuning + serving pipeline** — rag_nl_to_sql_augment_training_data_augment_split, models_query_plan_finetune_train_lora_train, models_query_plan_finetune_quantize, infra_local_model_vm_setup, rag_llm_client_chat_completion, models_query_plan_finetune_evaluate_comparison_run [EXTRACTED 0.90]
- **Rollout gated on real, honestly-reported eval numbers** — docs_adr_adr_010_query_plan_finetuning_budget_exception, docs_superpowers_specs_2026_08_27_local_queryplan_model_design_rollout_decision, _claude_rules_no_fabricated_metrics [INFERRED 0.85]
- **Adding a City Onboarding Workflow** — docs_guides_adding_a_city, docs_reference_capabilities_chat_tiers [EXTRACTED 0.90]
- **AWS On-Demand dbt Build Pipeline** — github_workflows_dbt_build_aws, scripts_aws_dbt_build_userdata, infra_cdk_stack [EXTRACTED 0.90]
- **Four-Model Demand Ladder Compared on One Shared Chronological Test Set** — models_evaluation_metrics_report_ewma_baseline, models_evaluation_metrics_report_linear_regression, models_evaluation_metrics_report_xgboost_demand, models_evaluation_metrics_report_lstm_demand, specs_006_model_ladder_demand_spec [EXTRACTED 0.95]
- **Global Mobility Coverage Attempted Then Reverted to NYC-Only** — specs_013_global_mobility_domain_model_spec, specs_015_second_real_city_and_estimation_spec, docs_adr_adr_011_retreat_from_global_coverage, docs_adr_adr_012_nyc_only [EXTRACTED 0.95]
- **Hybrid RAG Numeric/Explanatory Routing Flow** — rag_router_query_classifier, rag_nl_to_sql_sql_agent, rag_insight_generation [EXTRACTED 0.95]
- **ADR Documentation Set** — docs_readme_md, docs_adr_adr_001_duckdb_over_postgres_md, docs_adr_adr_002_dbt_layering_md, docs_adr_adr_003_chronological_split_md [EXTRACTED 1.00]
- **OpenAI Embedding + Qdrant Vector Store Pipeline** — pkg_openai, pkg_qdrant_client, rag_embeddings_build_vector_store, docker_compose_qdrant_service [EXTRACTED 1.00]
- **RDS TLS CA Bundle Fix for sslmode=verify-full (ADR-009)** — docker_compose_backend_service, rag_session_store, backend_services_prediction_log, certs_global_bundle_pem, docs_adr_adr_009_aws_cloud_dbt_build [EXTRACTED 1.00]
- **basis Field Honesty Discipline Across Docs** — docs_reference_capabilities, docs_api_readme, docs_reference_capabilities_basis_contract [INFERRED 0.80]
- **NL-to-SQL Evolution: Raw SQL Agent → Canonical Query Plan → Schema-Agnostic Fine-Tuned Query Plan** — specs_008_hybrid_rag_spec, specs_013_global_mobility_domain_model_spec, specs_014_query_plan_finetuning_spec [INFERRED 0.85]
- **Product Documentation Set (Vision/PRD/Personas/Roadmap/Use-Cases/Success-Metrics)** — docs_product_vision, docs_product_prd, docs_product_personas, docs_product_use_cases, docs_product_success_metrics [INFERRED 0.85]
- **Zero-Fabrication / Total-Provenance Discipline** — architecture_audit_md, design_md, implementation_audit_md, claude_rules_md_zero_fabrication_rule [INFERRED 0.85]

## Communities (210 total, 77 thin omitted)

### Community 0 - "Journey History & Capability Gates"
Cohesion: 0.05
Nodes (55): coordLabel(), HistoryEntryCard(), HistoryPage(), CapabilityGate(), useCapability(), CapabilityUnavailable(), CapabilityUnavailableProps, AvailabilityCard() (+47 more)

### Community 1 - "Fare Pricing Engine"
Cohesion: 0.06
Nodes (61): _base_fare(), _base_fare_nyc(), _base_fare_tariff(), compute_fare(), _demand_adjustment(), estimate_tariff_base_fare(), _load_calibration(), JourneyContext (+53 more)

### Community 2 - "Journey Predictors Base"
Cohesion: 0.05
Nodes (58): effective_confidence(), JourneyContext, JourneyFeatures, PredictionResult, Predictor, Shared types for the journey predictor pipeline (ADR-007). `basis` is…, Derived, named scores every predictor actually consumes. Adding a new…, A component's own measured/derived confidence when it has one, the basis… (+50 more)

### Community 3 - "Frontend Design & Audit Docs"
Cohesion: 0.05
Nodes (54): Anti-Default Discipline, Anti-Slop Frontend Skill, Brief Inference / Design Read, Premium-Consumer Palette Ban, Three Dials (Variance/Motion/Density), Frontend Architecture Audit, DemandForecast.tsx Fabricated Comparison Chart, pagerank_hubs.json Missing Artifact (+46 more)

### Community 4 - "Insights & Context Cards"
Cohesion: 0.06
Nodes (34): InsightsPage(), SOURCE_LABELS, ContextCard(), ContextCardProps, RouteCard(), RouteCardProps, AnalyticsHistoryResponse, AnalyticsInsightsResponse (+26 more)

### Community 5 - "Compare & Journey Pages"
Cohesion: 0.06
Nodes (31): ComparePage(), defaultDropoff, defaultPickup, SettingsPage(), Theme, Units, CompareCard(), CompareForm() (+23 more)

### Community 6 - "App Layout & Compare Card"
Cohesion: 0.09
Nodes (28): metadata, makeClient(), Providers(), BasisBadge(), CompareCardProps, ComparisonCell(), VEHICLE_ICONS, CertaintyRing() (+20 more)

### Community 7 - "Backend Schemas"
Cohesion: 0.08
Nodes (39): AnalyticsHistoryResponse, CarbonResponse, CongestionResponse, ContextSourceEnvelope, Coordinates, CountriesResponse, Country, DemandPrediction (+31 more)

### Community 8 - "Chat Router & History"
Cohesion: 0.09
Nodes (33): get_chat_history(), _normalize_route(), post_chat(), post, Chat router endpoints: POST /chat, GET /chat/history/{session_id}, and WS…, Frontend ChatRoute contract is numeric | explanatory. The context-only tier's…, websocket_chat_stream(), ChatMessage (+25 more)

### Community 9 - "Mobility Router"
Cohesion: 0.12
Nodes (35): availability(), carbon(), congestion(), demand(), departure_time(), fare(), _make_mobility_response(), _predict_route() (+27 more)

### Community 10 - "Backend API Tests"
Cohesion: 0.06
Nodes (5): client(), fixture, One happy-path test per backend route (standards.md testing bar)., With no city_id parameter left, omitting lat/lon must fall back to the seeded…, test_context_endpoints_default_to_the_city_centroid()

### Community 11 - "Domain Errors & City Router"
Cohesion: 0.14
Nodes (29): DomainError, Exception type for the city-scoped routes. Routers/services raise…, forecast(), CapabilityUnavailable, ErrorCode, ForecastEnvelope, ForecastPoint, PredictionEnvelope (+21 more)

### Community 12 - "Product Docs (PRD/Personas)"
Cohesion: 0.08
Nodes (30): Personas, Secondary Persona: Future-You, Interviewer / Hiring Manager Persona, Product Requirements Document, PRD Functional Requirements (FR-1..FR-6), PRD Non-Goals, PRD Problem Statement, Success Metrics (+22 more)

### Community 13 - "Capability Matrix & City Hero"
Cohesion: 0.14
Nodes (23): CapabilityGateProps, CAPABILITIES_LIST, CapabilityMatrix(), CapabilityMatrixProps, CityHero(), CityHeroProps, CityProfile(), ModelStatus() (+15 more)

### Community 14 - "Infra Adapters & Dependencies"
Cohesion: 0.07
Nodes (29): backend/adapters/ (weather/holiday/routing HTTP adapters), qdrant Service (docker-compose), qdrant_storage Volume, KD-tree correctness test (scipy reference implementation), dbt-core, dbt-duckdb, duckdb, fastapi (+21 more)

### Community 15 - "Frontend TS Config"
Cohesion: 0.07
Nodes (26): compilerOptions, allowJs, esModuleInterop, incremental, isolatedModules, jsx, lib, module (+18 more)

### Community 16 - "City Registry & Capabilities"
Cohesion: 0.12
Nodes (24): _area_count(), capability_matrix(), _effective_model_status(), get_capabilities(), get_chat_tier(), get_city(), get_city_profile(), list_metrics() (+16 more)

### Community 17 - "NYC TLC Data Source"
Cohesion: 0.12
Nodes (9): get_datasource(), Mobility data source. One implementation, for the one city this platform serves…, NYCTLCDataSource, `NYCTLCDataSource` (SPEC-013 FR-6) -- thin read wrappers over the existing NYC…, _rows(), ds(), fixture, Correctness tests for NYCTLCDataSource (SPEC-013 FR-6): every method returns… (+1 more)

### Community 18 - "Home & Journey Page"
Cohesion: 0.12
Nodes (15): ADR-0011, JourneyPageContent(), HomePage(), AICard(), AICardProps, HoveredZone, NYC_VIEW, ZoneMap() (+7 more)

### Community 19 - "Local QueryPlan Model Decision & Design"
Cohesion: 0.14
Nodes (20): ADR-008: adapter pattern zero budget, Local fine-tuning supersedes paid OpenAI path, ADR-010: QueryPlan Fine-Tuning Budget Exception, QueryPlan intermediate representation, Local Fine-Tuned QueryPlan Model Design, 3-tier local/DeepSeek/OpenAI fallback architecture, API-key-only security, no TLS / no IP allowlist, call_base_model() (+12 more)

### Community 20 - "train_lstm"
Cohesion: 0.13
Nodes (19): evaluate_all(), _measure_latency(), Evaluate all 4 demand models on one shared test set (SPEC-006, FR-7). The…, probe() runs the model once on a small batch and returns the batch size;…, rmse_mae(), build_sequences(), demo(), DataFrame (+11 more)

### Community 21 - "page"
Cohesion: 0.13
Nodes (18): AnalystPage(), ask(), handleSubmit(), EXAMPLE_PROMPTS, looksNumeric(), Turn, TurnBubble(), CityPage() (+10 more)

### Community 22 - "Tabs"
Cohesion: 0.14
Nodes (19): AnalyticsPage(), InsightCard(), MetricCard(), Tabs(), TabsContent(), TabsContentProps, TabsContext, TabsContextType (+11 more)

### Community 23 - "test_registry"
Cohesion: 0.12
Nodes (19): get_model(), has_active_model(), list_models_for(), load(), Model registry (SPEC-013 FR-4) -- thin query module over the seeded…, The active model backing `metric`, or None if the capability isn't really wired…, resolve_model(), model_registry seed (+11 more)

### Community 24 - "spec"
Cohesion: 0.19
Nodes (22): ADR-003: Chronological Split, ADR-011: retreat from global coverage, Fare Prediction XGBoost Model, SPEC-002: dbt Transformation Layer, SPEC-003: Spatial Algorithms — KD-Tree + Geohash, SPEC-004: Graph Algorithms — PageRank + Dijkstra, SPEC-005: Time-Series Algorithms — EWMA + Seasonality, SPEC-006: Model Ladder — Zone-Hourly Demand Forecasting (+14 more)

### Community 25 - "useReverseGeocode"
Cohesion: 0.14
Nodes (17): AddressSearch(), AddressSearchProps, JourneyMap(), JourneyMapProps, MAP_STYLE, ROUTE_LINE_LAYER, cache, formatPlaceName() (+9 more)

### Community 26 - "analytics"
Cohesion: 0.13
Nodes (20): history(), insights(), _parse_requested_at(), datetime, Analytics APIs (Part 13 of API Decomposition). Frontend dashboard analytics…, Get insight documents from the RAG pipeline., Get recent prediction history., Real trend series bucketed from log timestamps and response payloads. `now` and… (+12 more)

### Community 27 - "package"
Cohesion: 0.10
Nodes (21): clsx, @deck.gl/core, @deck.gl/react, dependencies, clsx, @deck.gl/core, @deck.gl/react, lucide-react (+13 more)

### Community 28 - "context"
Cohesion: 0.16
Nodes (18): _cached_fetch(), demo(), fetch(), datetime, PredictionResult, Real weather adjustment via Open-Meteo's free forecast API (ADR-008 update,…, _severity_from_conditions(), _city_coords() (+10 more)

### Community 29 - "city"
Cohesion: 0.16
Nodes (19): get_area(), get_capabilities(), get_city_context(), get_city_profile(), get_city_tariff(), list_areas(), list_metrics(), City capability routes (ADR-013). One city is served (ADR-012), so these no… (+11 more)

### Community 30 - "QueryPlan Training Data & LoRA Script"
Cohesion: 0.15
Nodes (16): rules.md: no fabricated metrics rule, Local Fine-Tuned QueryPlan Model Implementation Plan, QueryPlan LoRA fine-tune README, load_jsonl(), Path, train(), augment_split(), demo() (+8 more)

### Community 31 - "training_data_gen"
Cohesion: 0.17
Nodes (14): CityMobilitySchema, QueryFilters, Canonical field name -> real (table, column), scoped per metric since the same…, Compact `TABLE <name> (<column> -- <canonical>: <meaning> [type], ...)` text…, Only the filters actually set, as canonical-name -> value., _area_value(), _gen_area_ranking(), _gen_comparison() (+6 more)

### Community 32 - "test_geography_generalized"
Cohesion: 0.14
Nodes (14): get_area(), _get_tree(), in_coverage(), Geography domain (ADR-007 candidate for Phase 2's Region generalization; Phase…, resolve(), canonical_areas mart, zone_centroids.csv, client() (+6 more)

### Community 33 - "test_algorithms"
Cohesion: 0.17
Nodes (12): requires_warehouse, _nx_heuristic(), Correctness tests: from-scratch algorithms vs. reference libraries. Per…, _synthetic_graph_and_coords(), test_astar_matches_dijkstra_cost_on_zone_graph(), test_astar_matches_networkx_on_zone_graph(), test_astar_matches_networkx_small_synthetic_graph(), test_astar_no_path_raises_like_networkx() (+4 more)

### Community 34 - "shortest_path_eta"
Cohesion: 0.20
Nodes (16): astar(), benchmark_astar_vs_dijkstra(), build_eta_graph(), demo(), dijkstra(), haversine_km(), load_zone_coords(), DiGraph (+8 more)

### Community 35 - "kdtree_zone_lookup"
Cohesion: 0.24
Nodes (11): _benchmark(), benchmark_summary(), _coord(), KDNode, KDTree, linear_nearest(), From-scratch KD-tree over NYC TLC zone centroids for nearest-neighbor lookup.…, Run the linear-scan-vs-KD-tree benchmark and return measured results (used both… (+3 more)

### Community 36 - "journey_service"
Cohesion: 0.19
Nodes (15): _cached_route(), fetch(), fetch_distance(), fetch_duration(), datetime, PredictionResult, Real road-network routing via OSRM (ADR-008). Defaults to OSRM's public demo…, estimate() (+7 more)

### Community 37 - "capabilities"
Cohesion: 0.16
Nodes (16): Cities Registry Module, City Router, area_id, area_type, canonical_areas, zone_centroids seed, ADR-012: NYC-only, ADR-013: collapse city_id (+8 more)

### Community 38 - "schemas"
Cohesion: 0.18
Nodes (15): estimate(), features(), history(), datetime, post, PredictionResult, POST /journey/estimate -- the Journey Intelligence Engine endpoint (ADR-007).…, _to_out() (+7 more)

### Community 39 - "tariff_profiles"
Cohesion: 0.19
Nodes (15): ensure_table(), get(), has_profile(), load(), Table, Cached per-city fare-structure profiles. A `TariffProfile` is a small set of…, Validation at construction, so it holds on BOTH paths -- the offline upsert and…, Idempotent create -- called from load() and upsert() the same way… (+7 more)

### Community 40 - "build_features"
Cohesion: 0.18
Nodes (14): _block_features(), build_features(), demo(), _load_weather_lookup(), DataFrame, DuckDBPyConnection, Series, Feature table for zone-hourly demand forecasting (SPEC-006). Reuses… (+6 more)

### Community 41 - "opencode"
Cohesion: 0.12
Nodes (16): limit, name, tool_call, context, output, models, name, npm (+8 more)

### Community 42 - "query_plan"
Cohesion: 0.18
Nodes (10): The one real CityMobilitySchema, for NYC's actual marts (FR-3). Column/table…, demo(), FieldMapping, MetricSchema, Schema-agnostic QueryPlan + per-city schema resolver (FR-1, spec-014). Today's…, A canonical metric's backing table, its own value column, and every other…, One canonical concept's real column, plus whether it needs SQL string quoting…, _full_coverage_schema() (+2 more)

### Community 43 - "chronological_split"
Cohesion: 0.19
Nodes (13): chronological_split(), demo(), _latest_month_start(), DataFrame, Chronological train/validation/test split (ADR-003). Never random-split time-…, train/val = every month before the latest one (chronological 85/15), test = the…, Sort `df` by `ts_col` and slice into len(fracs) chunks, in the given…, split_demand_blocks() (+5 more)

### Community 44 - "LLM Client Fallback Chain"
Cohesion: 0.20
Nodes (13): chat_completion(), demo(), Shared local-model-primary / DeepSeek-secondary / OpenAI-fallback chat…, Same call shape as `OpenAI().chat.completions.create(...)`. Tries the local…, blind_guess(), main(), measure_mape(), _parse_json_response() (+5 more)

### Community 45 - "RAG Pipeline Answer Routing"
Cohesion: 0.23
Nodes (15): answer(), _answer_explanatory(), _answer_numeric(), answer_stream(), demo(), _format_label(), _format_numeric_answer(), _format_value() (+7 more)

### Community 46 - "test_rag"
Cohesion: 0.17
Nodes (14): classify(), demo(), _heuristic_classify(), Numeric vs explanatory intent router (FR-4, ADR-004). A short LLM…, parametrize, skipif, RAG layer: the non-trivial, LLM-independent logic gets a real test…, test_heuristic_classify_ambiguous_defaults_numeric() (+6 more)

### Community 47 - "README"
Cohesion: 0.16
Nodes (14): build_zone_graph(), demo(), DiGraph, Path, Build a weighted directed zone-to-zone trip-flow graph from the…, Return a directed graph of zones with edge attribute `weight` = total trip…, PageRank Hub Ranking, Dijkstra / A* Shortest Path ETA (+6 more)

### Community 48 - "package"
Cohesion: 0.13
Nodes (15): autoprefixer, devDependencies, autoprefixer, postcss, tailwindcss, @types/node, @types/react, @types/react-dom (+7 more)

### Community 49 - "transit"
Cohesion: 0.23
Nodes (12): get_feed(), has_feed(), load(), GTFS transit feed registry -- exact mirror of backend/registry/models.py's…, True only once a real feed is both configured (not the unverified placeholder)…, count_stops_near(), Real transit-stop-density signal from ingested GTFS static feeds…, demo() (+4 more)

### Community 50 - "schema"
Cohesion: 0.15
Nodes (15): avg_speed_mph, int_trips_enriched, pickup_at (int_trips_enriched), trip_id (int_trips_enriched), borough, dropoff_at, dropoff_location_id, location_id (+7 more)

### Community 51 - "motion"
Cohesion: 0.23
Nodes (9): SmoothScrollProvider(), NumberTicker(), NumberTickerProps, useAnimePulse(), EntranceOptions, useLenis(), checkReducedMotion(), DURATIONS (+1 more)

### Community 52 - "build_vector_store"
Cohesion: 0.23
Nodes (13): build_vector_store(), demo(), _embed(), _get_client(), _point_id(), Path, Embed insight docs into Qdrant (FR-2). Uses OpenAI's `text-embedding-3-small`…, Hybrid rerank: blend each candidate's real embedding cosine score (already in… (+5 more)

### Community 53 - "journey_narrative"
Cohesion: 0.22
Nodes (13): extract_numbers(), True iff every number in `text` is either a small connective number…, validate_grounding(), _allowed_numbers(), _facts_from_components(), generate(), _phrase_with_llm(), AI Recommendations for a journey estimate (ADR-007). Reuses… (+5 more)

### Community 54 - "test_query_plan"
Cohesion: 0.21
Nodes (10): QueryPlan, parametrize, Compiler correctness per canonical intent against nyc_schema.py, and the "raise…, test_area_ranking_compiles(), test_bad_aggregation_raises(), test_comparison_compiles(), test_hourly_pattern_compiles(), test_metric_lookup_compiles() (+2 more)

### Community 55 - "ewma_smoothing"
Cohesion: 0.22
Nodes (12): _best_alpha(), ewma(), ewma_blocks(), load_zone_hourly_blocks(), DuckDBPyConnection, ndarray, Series, EWMA smoothing over zone_hourly_demand, implemented from scratch. S_t = alpha *… (+4 more)

### Community 56 - "main"
Cohesion: 0.17
Nodes (12): domain_error_handler(), lifespan(), log_requests(), openapi_explorer_docs(), rapidoc_docs(), FastAPI app (FR-1). Mounts routers; loads model artifacts once at startup (rule…, Every API request/response/failure logs through here (logging rule: log the…, scalar_docs() (+4 more)

### Community 57 - "compose_eta"
Cohesion: 0.21
Nodes (12): _bucket(), demo(), Series, Synthetic sanity check: a slower-than-bucket-freeflow trip must score…, demo(), free_flow_duration_min(), predict_eta(), DataFrame (+4 more)

### Community 58 - "train_fare_xgb"
Cohesion: 0.26
Nodes (11): load_data(), main(), DataFrame, Path, Train a single tuned XGBoost fare-prediction model (SPEC-007). Deliberately not…, Small manual grid, selected by validation RMSE. Not a full ladder or CV search…, rmse_mae(), split_data() (+3 more)

### Community 59 - "semantic_cache"
Cohesion: 0.28
Nodes (12): demo(), _embed(), _ensure_collection(), get(), _get_client(), _point_id(), put(), Any (+4 more)

### Community 60 - "README"
Cohesion: 0.21
Nodes (11): Rule 7: Prune Scaffolding That Stops Earning Its Keep, docker-compose.yml, ADR-006: Full .claude/ Engineering-Process Scaffolding Despite Solo Scope, Deployment Plan, Infrastructure, Deployment Short Reference, frontend/Dockerfile, .github/workflows/dbt-build-aws.yml (+3 more)

### Community 61 - "IMPLEMENTATION_AUDIT"
Cohesion: 0.18
Nodes (12): DuckDB over Postgres Decision, dbt Staging/Intermediate/Marts Layering Decision, Chronological Train/Val/Test Split Decision, Docs Index, Implementation Audit, Chronological Split Discipline (Implementation Audit), city_tariff_profiles Table, global_cities Table (+4 more)

### Community 62 - "Fine-Tuned QueryPlan Agent"
Cohesion: 0.21
Nodes (10): Q4_K_M quantization caused the accuracy collapse, f16 fixed it, USE_FINETUNED_QUERY_PLAN rollout decision, Shared config for the RAG layer -- one place for the LLM model id and warehouse…, answer(), demo(), generate_plan(), Path, NL question -> QueryPlan (fine-tuned model) -> compiled SQL -> executed read-… (+2 more)

### Community 63 - "package"
Cohesion: 0.17
Nodes (11): animejs, @gsap/react, dependencies, animejs, gsap, @gsap/react, lenis, animejs (+3 more)

### Community 64 - "test_analytics"
Cohesion: 0.21
Nodes (7): client(), fixture, Analytics endpoints -- no warehouse required. `/api/analytics/*` must never 500…, _row(), test_history_respects_limit_and_offset(), test_summary_derives_cities_dates_and_top(), test_trends_buckets_aware_timestamps()

### Community 65 - "prediction_log"
Cohesion: 0.29
Nodes (10): get_recent_predictions(), init_db(), JourneyPrediction, log_prediction(), Table, Postgres-backed prediction log (ADR-007 follow-up, migrated off SQLite per…, _table_for(), CityTariffProfile (+2 more)

### Community 66 - "session_store"
Cohesion: 0.31
Nodes (10): Base, get_session_history(), init_db(), Message, Any, Postgres-backed conversation history store (FR-7), migrated off SQLite per…, save_message(), session_exists() (+2 more)

### Community 67 - "README"
Cohesion: 0.18
Nodes (11): Rule 8: No Reprocessing on Request Path, int_trips_enriched.sql, dbt_project/models/staging/stg_trips.sql, Data Flow, Data Source and Transformation, zone_fare_stats mart, zone_hourly_demand mart, zone_pair_flows mart (+3 more)

### Community 68 - "feature_importance"
Cohesion: 0.24
Nodes (11): day_of_week, ewma, hour, XGBoost Feature Importance Chart, is_weekend, lag_168h, lag_1h, lag_24h (+3 more)

### Community 69 - "generate_insight_docs"
Cohesion: 0.31
Nodes (10): _allowed_numbers(), demo(), _facts_for_zone(), generate_all(), load_insight_docs(), _phrase_with_llm(), DataFrame, Path (+2 more)

### Community 70 - "SQL Agent QueryPlan Generation"
Cohesion: 0.27
Nodes (10): answer(), demo(), generate_plan(), Path, NL-to-SQL over the mart schema only (FR-3, ADR-004; restructured for SPEC-013…, The one place an LLM is called on the numeric-question path -- its entire…, Question -> QueryPlan -> deterministically compiled SQL -> real, read-only…, Defense-in-depth guard (ADR-004): compile_plan() only ever emits schema-… (+2 more)

### Community 71 - "test_training_data_gen"
Cohesion: 0.27
Nodes (10): build_splits(), demo(), generate_examples(), Path, write_splits(), Every generated training/eval label is correct by construction (rule 2 -- no…, test_every_label_round_trips_through_the_compiler(), test_held_out_schema_absent_from_train_split() (+2 more)

### Community 72 - "test_zone_geojson"
Cohesion: 0.20
Nodes (9): _coords(), fixture, Correctness checks for the map hero's zone geometry (ADR-011 phase 7). The bug…, Walk an arbitrarily nested GeoJSON coordinate array down to positions., Catches the axis-order bug: (lat, lon) puts NYC at ~(40, -74) read as lon=40,…, The choropleth joins these to zone_hourly_demand on location_id -- a drifted or…, test_every_zone_position_is_lon_lat_inside_nyc(), test_location_ids_join_to_the_zone_lookup() (+1 more)

### Community 73 - "Architecture"
Cohesion: 0.27
Nodes (10): Rule 2: Never Fabricate Results, data/warehouse/nyc_rides.duckdb, ADR-001: DuckDB over Postgres, ADR-002: dbt Layering, ADR-004: NL-to-SQL as Separate Path from RAG-over-text, ADR-005: Precompute for Deployment, Never Run Full Pipeline Live, ADR-009: AWS Cloud dbt Build, Architecture Overview (+2 more)

### Community 74 - "metrics_report"
Cohesion: 0.20
Nodes (10): Congestion Multiplier Model (Phase 6), ETA = T_freeflow × Congestion Multiplier Composition (explicit, not an opaque end-to-end model), Free-Flow Duration Estimate (rationale: no road-graph data exists, so free-flow speed is approximated as 85th percentile observed speed per distance bucket; corrects the original brief's backwards p10/p15 instruction), Measured Prediction Interval Coverage (78.9% vs nominal 80%, reported honestly rather than rounded up), Quantile ETA Model (Phase 7), XGBoost Demand Model, Colab Training Notebooks README, Progressive-Sampling Workflow (1M → 5M → ... → ALL, stop when held-out metric stops improving) (+2 more)

### Community 75 - "test_journey"
Cohesion: 0.31
Nodes (9): _body(), client(), fixture, Correctness tests for POST /journey/estimate (ADR-007)., test_journey_estimate_happy_path(), test_journey_estimate_outside_coverage_degrades_honestly(), test_journey_estimate_unknown_vehicle_type_is_unavailable_not_default(), test_journey_estimate_vehicle_type_changes_fare_and_carbon() (+1 more)

### Community 76 - "seasonality_decompose"
Cohesion: 0.33
Nodes (8): _centered_moving_average(), decompose(), Decomposition, _plot_zone(), ndarray, Series, Trend + daily-seasonal + weekly-seasonal + residual decomposition, from…, Centered MA via convolution; edges (window//2 on each side) are NaN, same…

### Community 77 - "holidays_nager"
Cohesion: 0.36
Nodes (8): demo(), _extended_fixed_holidays(), fetch(), datetime, PredictionResult, Real public-holiday lookup via Nager.Date -- free, global, no API key required…, Real holiday dates (ISO strings) for a (year, country), or None if the lookup…, _year_holidays()

### Community 78 - "aws_dbt_build_userdata"
Cohesion: 0.22
Nodes (6): nyc_tlc source, raw_trips, dbt_project/models/staging/schema.yml, DBT_PROFILES_DIR, DBT_PROJECT_DIR, aws_dbt_build_userdata.sh script

### Community 79 - "package"
Cohesion: 0.22
Nodes (8): name, private, scripts, build, dev, lint, start, version

### Community 80 - "Oracle VM Deployment Scripts"
Cohesion: 0.25
Nodes (5): Local QueryPlan model VM README, setup.sh script, merge(), Path, quantize.sh script

### Community 81 - "build_features"
Cohesion: 0.42
Nodes (8): build_features(), build_free_flow_lookup(), _holiday_flags(), load_raw_trips(), DataFrame, DuckDBPyConnection, Feature table for the congestion-multiplier model (Phase 6). Target: C =…, One row per distance bucket: estimated free-flow speed (p85 of observed speed…

### Community 82 - "pagerank_hubs"
Cohesion: 0.46
Nodes (7): demo(), hub_summary(), pagerank(), DiGraph, PageRank from scratch via power iteration (FR-2). PR(p) = (1-d)/N + d *…, Top-k hubs with rank/score/raw-degree, for persisting as a real artifact…, top_hubs()

### Community 83 - "East_Village_decomp"
Cohesion: 0.32
Nodes (8): Daily and Weekly Seasonality Pattern, East Village (NYC Zone), algorithms/timeseries Module, East Village Multiplicative Decomposition (Jan 2024), JFK Airport Multiplicative Decomposition (Jan 2024), Ride Demand Time Series, JFK Airport Ride Demand Time Series, Multiplicative Time-Series Decomposition (Trend/Seasonal/Residual)

### Community 84 - "zones"
Cohesion: 0.50
Nodes (7): get_zone(), _get_zones(), list_zones(), _load_zones(), GET /zones (list), GET /zones/{zone_id} (detail) (FR-3). Zone metadata is…, Lazily build the zone table on first request. Loaded once and cached…, Zone

### Community 85 - "db"
Cohesion: 0.39
Nodes (7): Connection, Engine, build_engine(), get_connection(), get_engine(), Shared SQLAlchemy engine for the Postgres operational store (ADR-009).…, _to_sqlalchemy_dsn()

### Community 86 - "schema"
Cohesion: 0.25
Nodes (6): cities seed, countries seed, country_code, iso_code, status (cities), Regenerates dbt_project/seeds/countries.csv from GeoNames' countryInfoJSON --…

### Community 87 - "Roadmap"
Cohesion: 0.46
Nodes (8): Product Roadmap, Layer 0: Data Foundation, Layer 1: dbt Transformation, Layer 2: Algorithms, Layer 3: Model Ladder, Layer 4: Hybrid RAG, Layer 5: Serving & Presentation, NYC Ride Intelligence README

### Community 88 - "train_quantile_eta"
Cohesion: 0.36
Nodes (7): pinball_loss(), DataFrame, ndarray, XGBRegressor, Quantile ETA models (Phase 7): eta_p10/p50/p90 via XGBoost's native…, train_and_save(), train_quantile()

### Community 89 - "metrics_report"
Cohesion: 0.25
Nodes (8): Block-Gap-Aware Chronological Split (rationale: disjoint monthly warehouse blocks require boundary-snapped cutoffs, not row-count splits), Demand Forecasting Model Ladder Comparison, EWMA Baseline Model, Linear Regression Baseline Model, LSTM Demand Model, LSTM Stale Artifact (rationale: saved weights/scaling fit on old 2024 warehouse, de-normalizes 2026-04 predictions with wrong constants — 96.9 RMSE is not a real finding), RMSE Chosen Over MAE as Primary Metric (rationale: squared-error term penalizes costly under-provisioned surge hours harder than MAE does), Train/Eval Split by Schema Family, Not Randomly (held-out synthetic schema never seen in training)

### Community 90 - "train_xgboost"
Cohesion: 0.39
Nodes (7): plot_feature_importance(), DataFrame, Path, Tuned XGBoost regressor for zone-hourly demand (SPEC-006, FR-5). Same manual-…, rmse_mae(), train_and_save(), tune()

### Community 91 - "query_plan_compiler"
Cohesion: 0.43
Nodes (7): compile(), demo(), _group_by_name(), Deterministic QueryPlan -> SQL compiler (FR-2, spec-014). The LLM (base or,…, Resolve every field the plan references against `schema`; raises before any SQL…, _sql_literal(), validate_plan()

### Community 92 - "ingest_gtfs_feeds"
Cohesion: 0.46
Nodes (7): _download(), _fetch_and_extract_stops(), load_stops(), main(), Path, Download, unzip, and load GTFS static feeds' stops.txt into each city's own…, _read_feeds()

### Community 93 - "test_chronological_split_dedup"
Cohesion: 0.36
Nodes (6): _old_split_data(), DataFrame, Phase 2 dedup proof: `train_fare_xgb.split_data()` (now delegating to the…, The exact logic train_fare_xgb.split_data() used to inline, before Phase 2…, _synthetic_gapped_df(), test_new_split_data_matches_old_inline_logic_exactly()

### Community 94 - "test_sql_agent_query_plan"
Cohesion: 0.25
Nodes (7): sql_agent.py-specific coverage for SPEC-013 FR-10: the LIVE `/chat` numeric-…, generate_sql() (the old LLM-writes-SQL-text function) must be gone;…, Patching generate_plan to return a known QueryPlan proves answer()'s executed…, _validate_sql() is kept as a second layer over the compiler's output (ADR-004…, test_sql_agent_answer_routes_through_the_compiler_not_raw_text(), test_sql_agent_has_no_raw_sql_generation_path(), test_validate_sql_still_rejects_disallowed_sql_defense_in_depth()

### Community 95 - "geohash_grid"
Cohesion: 0.33
Nodes (6): load_zone_geohashes(), nearby_zones(), DataFrame, Path, Geohash encoding of zone centroids + prefix-matching for "nearby zones."…, Zones sharing a geohash prefix of length `prefix_len` with `location_id`.

### Community 96 - "generate_algorithm_artifacts"
Cohesion: 0.33
Nodes (6): load_zone_points(), Path, load(), main(), Persist real measured output for algorithms/ so the Algorithms page can read…, test_kdtree_matches_scipy_nearest_neighbor()

### Community 97 - "docker-compose"
Cohesion: 0.33
Nodes (7): backend/Dockerfile, certs/global-bundle.pem (RDS TLS CA Bundle), backend Service (docker-compose), frontend-web Service (docker-compose), NEXT_PUBLIC_API_BASE_URL Must Be Host-Published Address (rationale), RDS TLS CA Bundle Mount for sslmode=verify-full (rationale), frontend-web/Dockerfile

### Community 98 - "ADR-012-nyc-only"
Cohesion: 0.29
Nodes (7): ADR-012: NYC only — removing London, Alternatives considered, Collapsing `city_id`, Consequence: a test got stronger, Context, Decision, Reversibility

### Community 99 - "ADR-013-collapse-city-id"
Cohesion: 0.29
Nodes (7): ADR-013: Collapsing `city_id`, Alternatives considered, Consequence: two latent bugs surfaced, Context, Decision, The seam that replaces it, What this bought, honestly

### Community 100 - "ewma_forecast"
Cohesion: 0.38
Nodes (6): evaluate_and_save(), predict(), DataFrame, Series, EWMA baseline for zone-hourly demand (SPEC-006, FR-4): no training. The…, Forecast for each row = its own `ewma` feature column (S_(t-1)).

### Community 101 - "extract_fixed_holidays"
Cohesion: 0.43
Nodes (6): demo(), extract(), _iso3_to_iso2_map(), _nager_covered_iso2(), DataFrame, Extends holiday coverage past Nager.Date's 204 countries (notably: no India)…

### Community 102 - "test_quantile_eta_ordering_and_coverage"
Cohesion: 0.29
Nodes (3): metadata(), fixture, Phase 7 test: p10 <= p50 <= p90 ordering (mostly) holds, and prediction…

### Community 103 - "predictions"
Cohesion: 0.47
Nodes (5): predict_demand(), predict_fare(), get, GET /predict/demand, GET /predict/fare (FR-2). Thin: validates input, delegates…, FarePrediction

### Community 104 - "app"
Cohesion: 0.40
Nodes (4): Construct, Entry point for `cdk deploy` / `cdk synth`. See stack.py for what this actually…, DbtBuildStack, Stack

### Community 105 - "train_congestion_xgb"
Cohesion: 0.60
Nodes (5): DataFrame, Train the congestion-multiplier XGBoost regressor (Phase 6). Same tuned-grid-…, rmse_mae(), train_and_save(), tune()

### Community 106 - "test_demand_split_no_leakage"
Cohesion: 0.33
Nodes (4): Backward-compatible re-export. The actual implementation moved to…, Leakage-guard + identical-test-set tests for the demand model ladder (SPEC-006,…, test_compare_models_uses_identical_test_rows(), test_demand_chronological_split_no_leakage()

### Community 107 - "loss_curve"
Cohesion: 0.47
Nodes (6): LSTM Loss Curve (Zone-Hourly Demand), Train MSE (normalized), Validation MSE (normalized), LSTM Demand Forecast Model, Model Ladder (linear -> EWMA -> XGBoost -> LSTM), Zone-Hourly Demand Target

### Community 108 - "Park_Slope_decomp"
Cohesion: 0.70
Nodes (5): Daily*Weekly Seasonality Component, Park Slope Multiplicative Decomposition Chart, Multiplicative Time-Series Decomposition, Park Slope Zone, Ride Demand Time Series (Jan 2024)

### Community 109 - "adapters"
Cohesion: 0.50
Nodes (5): Nager.Date Holidays Adapter, Open-Meteo Weather Adapter, GTFS Transit Registry, External Data Adapters Reference, GTFS Feed Ingestion Script

### Community 110 - "2026-08-09-global-city-registry"
Cohesion: 0.50
Nodes (5): global_cities registry (524-city table) — superseded, resolve_city_tier (model_status + confidence resolution) — superseded, Two-signal confidence heuristic (deliberately reduced), get_city_profile as the single global seam, NYC refocus implementation design (9 phases)

### Community 111 - "backfill_weather_openmeteo"
Cohesion: 0.60
Nodes (4): fetch_city_weather(), main(), Backfill real historical hourly weather (temperature + precipitation) for every…, _real_dates_needed()

### Community 112 - "nyc_fare_anchor"
Cohesion: 0.50
Nodes (4): demo(), fit_nyc_fare_anchor(), DuckDBPyConnection, Real, measured NYC fare anchor shared by generate_tariff_profile.py and…

### Community 113 - "spec"
Cohesion: 0.40
Nodes (5): SPEC-001: Data Foundation, scripts/load_raw_to_duckdb.py, data/warehouse/nyc_rides.duckdb, scripts/spot_check.py, scripts/verify_ingestion.py

### Community 114 - "test_feature_gap_safety"
Cohesion: 0.60
Nodes (4): _assert_no_cross_block_leakage(), _make_gapped_blocks(), Phase 3 gap-safety proof: lag_1h/lag_24h/lag_168h/ewma/rolling_7d_avg must…, test_nyc_build_features_gap_safe()

### Community 115 - "schema"
Cohesion: 0.50
Nodes (4): pickup_date, pickup_hour, pickup_location_id (zone_hourly_demand), zone_hourly_demand

### Community 116 - "README"
Cohesion: 0.50
Nodes (4): Local dev setup and warehouse build, Tests skip when the warehouse is unbuilt, NYC zone geometry and choropleth hero, Serving-only backend dependency split

### Community 117 - "spec"
Cohesion: 0.50
Nodes (4): backend/predictors/journey_predictors.py, backend/services/journey_service.py, backend/predictors/base.py, backend/routers/journey.py

### Community 119 - "dbt-build-aws"
Cohesion: 0.67
Nodes (3): dbt Build AWS Workflow, infra/cdk/stack.py, scripts/aws_dbt_build_userdata.sh

## Knowledge Gaps
- **277 isolated node(s):** `FormValues`, `CapabilityUnavailableProps`, `AICardProps`, `CompareFormProps`, `ButtonProps` (+272 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **77 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Data Flow` connect `README` to `SQL Agent QueryPlan Generation`, `build_features`, `Architecture`, `test_demand_split_no_leakage`, `test_rag`, `aws_dbt_build_userdata`?**
  _High betweenness centrality (0.054) - this node is a cross-community bridge._
- **Why does `ADR-012: NYC-only` connect `capabilities` to `spec`, `ADR-012-nyc-only`, `schema`, `Roadmap`?**
  _High betweenness centrality (0.042) - this node is a cross-community bridge._
- **Why does `Operations` connect `test_registry` to `City Registry & Capabilities`, `query_plan_compiler`, `Domain Errors & City Router`, `RAG Pipeline Answer Routing`?**
  _High betweenness centrality (0.037) - this node is a cross-community bridge._
- **Are the 20 inferred relationships involving `QueryPlan` (e.g. with `call_base_model()` and `score()`) actually correct?**
  _`QueryPlan` has 20 INFERRED edges - model-reasoned connections that need verification._
- **Are the 16 inferred relationships involving `CityMobilitySchema` (e.g. with `answer()` and `generate_plan()`) actually correct?**
  _`CityMobilitySchema` has 16 INFERRED edges - model-reasoned connections that need verification._
- **What connects `FormValues`, `CapabilityUnavailableProps`, `AICardProps` to the rest of the system?**
  _277 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Journey History & Capability Gates` be split into smaller, more focused modules?**
  _Cohesion score 0.05154320987654321 - nodes in this community are weakly interconnected._
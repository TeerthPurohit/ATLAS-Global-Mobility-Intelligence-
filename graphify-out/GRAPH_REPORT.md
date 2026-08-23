# Graph Report - Uber nyc TLC Dataset  (2026-08-23)

## Corpus Check
- 324 files · ~167,525 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 2166 nodes · 4262 edges · 179 communities (135 shown, 44 thin omitted)
- Extraction: 94% EXTRACTED · 6% INFERRED · 0% AMBIGUOUS · INFERRED: 242 edges (avg confidence: 0.91)
- Token cost: 151,013 input · 0 output

## Community Hubs (Navigation)
- Transit & City Context
- Journey Result Cards
- Frontend Design Audit
- Settings & Capability Matrix
- Analytics Dashboard UI
- API Schemas
- App Shell & Journey Page
- Mobility Endpoints
- ADRs & Product Personas
- Prediction Log (Postgres)
- Vehicle Class Compare
- Backend API Tests
- Data Foundation & dbt
- Predictor Contract & Basis
- Per-City Data Sources
- Domain Errors & Capability Gating
- Geography & Zone Lookup
- London Demand Features
- Analytics Router
- TypeScript Config
- OSRM Routing Adapter
- NL-to-SQL City Schemas
- City Router
- Python Dependencies
- NYC Demand Features
- Model Comparison & LSTM
- History & Journey Pages
- Congestion Features
- FastAPI App Startup
- Journey Router
- Tariff Profiles & Fare Provenance
- Zone Graph & PageRank
- Geohash & Seasonality
- Weather/Holiday Adapters
- Community 34
- Community 35
- Community 36
- Community 37
- Community 38
- Community 39
- Community 40
- Community 41
- Community 42
- Community 43
- Community 44
- Community 45
- Community 46
- Community 47
- Community 48
- Community 49
- Community 50
- Community 51
- Community 52
- Community 53
- Community 54
- Community 55
- Community 56
- Community 57
- Community 58
- Community 59
- Community 60
- Community 61
- Community 62
- Community 63
- Community 64
- Community 65
- Community 66
- Community 67
- Community 68
- Community 69
- Community 70
- Community 71
- Community 72
- Community 73
- Community 74
- Community 75
- Community 76
- Community 77
- Community 78
- Community 79
- Community 80
- Community 81
- Community 82
- Community 83
- Community 84
- Community 85
- Community 86
- Community 87
- Community 88
- Community 89
- Community 90
- Community 91
- Community 92
- Community 93
- Community 94
- Community 95
- Community 96
- Community 97
- Community 98
- Community 99
- Community 100
- Community 101
- Community 102
- Community 103
- Community 104
- Community 105
- Community 106
- Community 107
- Community 108
- Community 109
- Community 110
- Community 111
- Community 112
- Community 113
- Community 114
- Community 115
- Community 116
- Community 117
- Community 118
- Community 119
- Community 120
- Community 121
- Community 122
- Community 123
- Community 124
- Community 126
- Community 127
- Community 128
- Community 129
- Community 130
- Community 131
- Community 132
- Community 133
- Community 134
- Community 135
- Community 136
- Community 137
- Community 138
- Community 139
- Community 140
- Community 141
- Community 158
- Community 159
- Community 162
- Community 163
- Community 164
- Community 165
- Community 166
- Community 167
- Community 168
- Community 169
- Community 170
- Community 171
- Community 172
- Community 173
- Community 174
- Community 175
- Community 176
- Community 177
- Community 178

## God Nodes (most connected - your core abstractions)
1. `cn()` - 60 edges
2. `PredictionResult` - 52 edges
3. `QueryPlan` - 36 edges
4. `CityMobilitySchema` - 33 edges
5. `Card()` - 27 edges
6. `JourneyFeatures` - 26 edges
7. `requirements.txt (Full Project Deps)` - 25 edges
8. `CardTitle()` - 24 edges
9. `DomainError` - 23 edges
10. `JourneyContext` - 23 edges

## Surprising Connections (you probably didn't know these)
- `Real / Estimated / Unavailable three-tier honesty model` --semantically_similar_to--> `OBSERVED / TRANSFER / NONE model_status tier system`  [INFERRED] [semantically similar]
  specs/015-second-real-city-and-estimation/spec.md → docs/adr/ADR-011-retreat-from-global-coverage.md
- `Chat tiers (full_rag / sql_only / context_only)` --implements--> `get_chat_tier()`  [EXTRACTED]
  docs/reference/capabilities.md → backend/registry/cities.py
- `get_capabilities()` --references--> `Chat tiers (full_rag / sql_only / context_only)`  [EXTRACTED]
  backend/registry/cities.py → docs/reference/capabilities.md
- `test_congestion_chronological_split_no_leakage()` --calls--> `split_demand_blocks()`  [INFERRED]
  tests/test_congestion_split_and_labeling.py → models/data_prep/chronological_split.py
- `test_compare_models_uses_identical_test_rows()` --calls--> `evaluate_all()`  [INFERRED]
  tests/test_demand_split_no_leakage.py → models/evaluation/compare_models.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Zero-Fabrication / Total-Provenance Discipline** — architecture_audit_md, design_md, implementation_audit_md, claude_rules_md_zero_fabrication_rule [INFERRED 0.85]
- **dbt Project Configuration Files** — dbt_project_dbt_project_yml, dbt_project_profiles_yml, dbt_project_packages_yml, dbt_project_package_lock_yml, dbt_project_models_intermediate_schema_yml [INFERRED 0.85]
- **RDS TLS CA Bundle Fix for sslmode=verify-full (ADR-009)** — docker_compose_backend_service, rag_session_store, backend_services_prediction_log, certs_global_bundle_pem, docs_adr_adr_009_aws_cloud_dbt_build [EXTRACTED 1.00]
- **ADR Documentation Set** — docs_readme_md, docs_adr_adr_001_duckdb_over_postgres_md, docs_adr_adr_002_dbt_layering_md, docs_adr_adr_003_chronological_split_md [EXTRACTED 1.00]
- **Hybrid RAG Numeric/Explanatory Routing Flow** — rag_router_query_classifier, rag_nl_to_sql_sql_agent, rag_insight_generation [EXTRACTED 0.95]
- **AWS On-Demand dbt Build Pipeline** — github_workflows_dbt_build_aws, scripts_aws_dbt_build_userdata, infra_cdk_stack [EXTRACTED 0.90]
- **Product Documentation Set (Vision/PRD/Personas/Roadmap/Use-Cases/Success-Metrics)** — docs_product_vision, docs_product_prd, docs_product_personas, docs_product_use_cases, docs_product_success_metrics [INFERRED 0.85]
- **Model Ladder Evaluation Suite** — fare_prediction_model, demand_forecasting_ladder, congestion_model, quantile_eta_model [INFERRED 0.75]
- **OpenAI Embedding + Qdrant Vector Store Pipeline** — pkg_openai, pkg_qdrant_client, rag_embeddings_build_vector_store, docker_compose_qdrant_service [EXTRACTED 1.00]
- **Algorithms + Model Ladder Layer (Specs 003-007)** — specs_003_spatial_algorithms_spec, specs_004_graph_algorithms_spec, specs_005_timeseries_algorithms_spec, specs_006_model_ladder_demand_spec, specs_007_fare_prediction_spec [INFERRED 0.85]
- **Serving & Presentation Layer (Specs 009-011)** — specs_009_backend_api_spec, specs_010_frontend_spec, specs_011_deployment_devops_spec [INFERRED 0.85]
- **Adapters implementing the single fetch() contract under a $0 budget** — docs_adr_adr_008_adapter_pattern_zero_budget_adapter_pattern, docs_reference_adapters_osrm_routing, docs_reference_adapters_open_meteo_weather, docs_reference_adapters_nager_holidays, docs_reference_adapters_gtfs_transit, docs_adr_adr_008_adapter_pattern_zero_budget_honest_stubs [EXTRACTED 1.00]
- **London second-city pipeline: source to staging to mart to registered model** — dbt_project_models_staging_schema_tfl_cycling_source, dbt_project_models_staging_schema_stg_london_cycle_journeys, dbt_project_seeds_schema_london_stations, dbt_project_models_staging_schema_stg_london_stations, dbt_project_models_marts_schema_london_station_hourly_demand, specs_015_second_real_city_and_estimation_spec_london_onboarding, docs_guides_adding_a_city_add_city_checklist [EXTRACTED 1.00]
- **Rise and retreat of the 519-city global coverage layer** — specs_013_global_mobility_domain_model_spec_domain_model, specs_015_second_real_city_and_estimation_spec_estimation_service, docs_superpowers_plans_2026_08_09_global_city_registry_global_cities_registry, docs_adr_adr_011_retreat_from_global_coverage_worldmove_data_quality, docs_adr_adr_011_retreat_from_global_coverage_retreat_decision, docs_superpowers_specs_2026_08_23_nyc_refocus_design_nyc_refocus_plan [EXTRACTED 1.00]

## Communities (179 total, 44 thin omitted)

### Community 0 - "Transit & City Context"
Cohesion: 0.06
Nodes (52): get_feed(), has_feed(), load(), GTFS transit feed registry -- exact mirror of backend/registry/models.py's…, True only once a real feed is both configured (not the unverified placeholder)…, get_city_context(), _now_iso(), Backend Context Orchestrator Service (Phase 4). Orchestrates environmental,… (+44 more)

### Community 1 - "Journey Result Cards"
Cohesion: 0.06
Nodes (42): InsightCard(), AvailabilityCard(), AvailabilityCardContent(), AvailabilityCardProps, BestDepartureCard(), BestDepartureCardProps, CarbonCard(), CarbonCardContent() (+34 more)

### Community 2 - "Frontend Design Audit"
Cohesion: 0.05
Nodes (54): Anti-Default Discipline, Anti-Slop Frontend Skill, Brief Inference / Design Read, Premium-Consumer Palette Ban, Three Dials (Variance/Motion/Density), Frontend Architecture Audit, DemandForecast.tsx Fabricated Comparison Chart, pagerank_hubs.json Missing Artifact (+46 more)

### Community 3 - "Settings & Capability Matrix"
Cohesion: 0.08
Nodes (40): SettingsPage(), Theme, Units, CAPABILITIES_LIST, CapabilityMatrix(), QuickActions(), QuickActionsProps, TariffCard() (+32 more)

### Community 4 - "Analytics Dashboard UI"
Cohesion: 0.06
Nodes (43): AnalyticsPage(), MetricCard(), ContextCard(), ContextCardProps, RouteCard(), RouteCardProps, AnalyticsHistoryResponse, AnalyticsInsightsResponse (+35 more)

### Community 5 - "API Schemas"
Cohesion: 0.06
Nodes (50): AvailabilityResponse, Capabilities, CityCapabilitiesResponse, CityDemandPredictRequest, CityFarePredictRequest, CityJourneyRequest, CityProfileResponse, CityRequest (+42 more)

### Community 6 - "App Shell & Journey Page"
Cohesion: 0.07
Nodes (30): JourneyPageContent(), metadata, makeClient(), Providers(), HomePage(), CommandPalette(), NavBar(), navLinks (+22 more)

### Community 7 - "Mobility Endpoints"
Cohesion: 0.09
Nodes (45): AvailabilityResponse, availability(), carbon(), congestion(), demand(), departure_time(), fare(), _make_mobility_response() (+37 more)

### Community 8 - "ADRs & Product Personas"
Cohesion: 0.06
Nodes (44): ADR-003 Chronological Split, ADR-007 Predictor basis field, basis field contract (computed/modeled_estimate/unavailable), Chat tiers (full_rag / sql_only / context_only), Congestion Model (Phase 6), Demand Forecasting Model Ladder (SPEC-006), Personas, Secondary Persona: Future-You (+36 more)

### Community 9 - "Prediction Log (Postgres)"
Cohesion: 0.08
Nodes (35): ADR-009 (CDK deploy / RDS Postgres), get_recent_predictions(), init_db(), JourneyPrediction, log_prediction(), Table, Postgres-backed prediction log (ADR-007 follow-up, migrated off SQLite per…, _table_for() (+27 more)

### Community 10 - "Vehicle Class Compare"
Cohesion: 0.07
Nodes (35): ComparePage(), CompareCard(), CompareForm(), CompareFormProps, CompareRequest, FormValues, NYC_DROPOFF, NYC_PICKUP (+27 more)

### Community 11 - "Backend API Tests"
Cohesion: 0.05
Nodes (3): client(), fixture, One happy-path test per backend route (standards.md testing bar).

### Community 12 - "Data Foundation & dbt"
Cohesion: 0.06
Nodes (42): SPEC-001: Data Foundation, scripts/load_raw_to_duckdb.py, data/warehouse/nyc_rides.duckdb, scripts/spot_check.py, scripts/verify_ingestion.py, SPEC-002: dbt Transformation Layer, ADR-007 (incremental vs full-refresh), int_trips_enriched.sql (+34 more)

### Community 13 - "Predictor Contract & Basis"
Cohesion: 0.15
Nodes (35): effective_confidence(), JourneyContext, JourneyFeatures, PredictionResult, Derived, named scores every predictor actually consumes. Adding a new…, A component's own measured/derived confidence when it has one, the basis…, Raw inputs plus whatever the adapters (backend/adapters/) returned,…, _demand_pressure() (+27 more)

### Community 14 - "Per-City Data Sources"
Cohesion: 0.09
Nodes (12): get_datasource(), Per-city mobility data source registry (SPEC-013 FR-6). Each city registers…, LondonCyclesDataSource, `LondonCyclesDataSource` -- mirrors `nyc_tlc.py`'s shape exactly, reading…, _rows(), NYCTLCDataSource, `NYCTLCDataSource` (SPEC-013 FR-6) -- thin read wrappers over the existing NYC…, _rows() (+4 more)

### Community 15 - "Domain Errors & Capability Gating"
Cohesion: 0.16
Nodes (29): DomainError, Exception type for the city-scoped routes. Routers/services raise…, forecast(), predict_demand(), predict_fare(), CapabilityUnavailable, ErrorCode, ForecastEnvelope (+21 more)

### Community 16 - "Geography & Zone Lookup"
Cohesion: 0.09
Nodes (27): detect_city_from_coords(), get_area(), _get_grid_cell_tree(), _get_london_tree(), _get_tree(), in_coverage(), _in_london_coverage(), list_areas() (+19 more)

### Community 17 - "London Demand Features"
Cohesion: 0.11
Nodes (27): _block_features(), build_features(), demo(), load_station_hourly_blocks(), _load_weather_lookup(), DataFrame, DuckDBPyConnection, Series (+19 more)

### Community 18 - "Analytics Router"
Cohesion: 0.10
Nodes (27): AnalyticsHistoryResponse, AnalyticsInsightsResponse, AnalyticsSummaryResponse, AnalyticsTrendsResponse, history(), insights(), _parse_requested_at(), datetime (+19 more)

### Community 19 - "TypeScript Config"
Cohesion: 0.07
Nodes (26): compilerOptions, allowJs, esModuleInterop, incremental, isolatedModules, jsx, lib, module (+18 more)

### Community 20 - "OSRM Routing Adapter"
Cohesion: 0.11
Nodes (21): _cached_route(), fetch(), fetch_distance(), fetch_duration(), datetime, Real road-network routing via OSRM (ADR-008). Defaults to OSRM's public demo…, Predictor, Shared types for the journey predictor pipeline (ADR-007). `basis` is… (+13 more)

### Community 21 - "NL-to-SQL City Schemas"
Cohesion: 0.13
Nodes (14): London's real CityMobilitySchema -- demand (bike-share departures) only. No…, The one real CityMobilitySchema, for NYC's actual marts (FR-3). Column/table…, CityMobilitySchema, demo(), FieldMapping, MetricSchema, Schema-agnostic QueryPlan + per-city schema resolver (FR-1, spec-014). Today's…, A canonical metric's backing table, its own value column, and every other… (+6 more)

### Community 22 - "City Router"
Cohesion: 0.16
Nodes (24): get_area(), get_capabilities(), get_city(), get_city_context(), get_city_profile(), get_city_tariff(), get_city_zones(), list_areas() (+16 more)

### Community 23 - "Python Dependencies"
Cohesion: 0.09
Nodes (25): KD-tree correctness test (scipy reference implementation), dbt-core, dbt-duckdb, duckdb, fastapi, geohash2, httpx, jupyter (+17 more)

### Community 24 - "NYC Demand Features"
Cohesion: 0.13
Nodes (20): _block_features(), build_features(), demo(), _load_weather_lookup(), DataFrame, DuckDBPyConnection, Series, Feature table for zone-hourly demand forecasting (SPEC-006). Reuses… (+12 more)

### Community 25 - "Model Comparison & LSTM"
Cohesion: 0.13
Nodes (19): evaluate_all(), _measure_latency(), Evaluate all 4 demand models on one shared test set (SPEC-006, FR-7). The…, probe() runs the model once on a small batch and returns the batch size;…, rmse_mae(), build_sequences(), demo(), DataFrame (+11 more)

### Community 26 - "History & Journey Pages"
Cohesion: 0.12
Nodes (13): coordLabel(), HistoryEntryCard(), HistoryPage(), defaultDropoff, defaultPickup, CompareCardProps, JourneyFormProps, JourneyResults() (+5 more)

### Community 27 - "Congestion Features"
Cohesion: 0.16
Nodes (20): _bucket(), build_features(), build_free_flow_lookup(), demo(), _holiday_flags(), load_raw_trips(), DataFrame, DuckDBPyConnection (+12 more)

### Community 28 - "FastAPI App Startup"
Cohesion: 0.13
Nodes (19): domain_error_handler(), lifespan(), log_requests(), openapi_explorer_docs(), get, rapidoc_docs(), FastAPI app (FR-1). Mounts routers; loads model artifacts once at startup (rule…, Every API request/response/failure logs through here (logging rule: log the… (+11 more)

### Community 29 - "Journey Router"
Cohesion: 0.14
Nodes (19): estimate(), features(), history(), datetime, get, post, PredictionOut, POST /journey/estimate -- the Journey Intelligence Engine endpoint (ADR-007).… (+11 more)

### Community 30 - "Tariff Profiles & Fare Provenance"
Cohesion: 0.18
Nodes (19): get(), Validation at construction, so it holds on BOTH paths -- the offline upsert and…, TariffProfile, _ctx(), _features(), parametrize, Provenance + capability-truthfulness tests for the extended tariff engine.…, Canary. `tariff_profiles.load()` swallows a connection failure and leaves the… (+11 more)

### Community 31 - "Zone Graph & PageRank"
Cohesion: 0.19
Nodes (16): build_zone_graph(), demo(), DiGraph, Path, Build a weighted directed zone-to-zone trip-flow graph from the…, Return a directed graph of zones with edge attribute `weight` = total trip…, demo(), hub_summary() (+8 more)

### Community 32 - "Geohash & Seasonality"
Cohesion: 0.13
Nodes (17): load_zone_geohashes(), nearby_zones(), DataFrame, Path, Geohash encoding of zone centroids + prefix-matching for "nearby zones."…, Zones sharing a geohash prefix of length `prefix_len` with `location_id`., _centered_moving_average(), decompose() (+9 more)

### Community 33 - "Weather/Holiday Adapters"
Cohesion: 0.15
Nodes (17): backend/adapters/ (weather/holiday/routing HTTP adapters), _cached_fetch(), demo(), fetch(), datetime, Real weather adjustment via Open-Meteo's free forecast API (ADR-008 update,…, _severity_from_conditions(), holiday() (+9 more)

### Community 34 - "Community 34"
Cohesion: 0.22
Nodes (12): _benchmark(), benchmark_summary(), _coord(), KDNode, KDTree, linear_nearest(), From-scratch KD-tree over NYC TLC zone centroids for nearest-neighbor lookup.…, Run the linear-scan-vs-KD-tree benchmark and return measured results (used both… (+4 more)

### Community 35 - "Community 35"
Cohesion: 0.19
Nodes (17): _area_count(), capability_matrix(), _effective_model_status(), get_capabilities(), get_city(), get_city_profile(), list_cities(), list_metrics() (+9 more)

### Community 36 - "Community 36"
Cohesion: 0.18
Nodes (18): Rule 2: Never Fabricate Results, Rule 7: Prune Scaffolding That Stops Earning Its Keep, data/warehouse/nyc_rides.duckdb, docker-compose.yml, ADR-001: DuckDB over Postgres, ADR-002: dbt Layering, ADR-004: NL-to-SQL as Separate Path from RAG-over-text, ADR-005: Precompute for Deployment, Never Run Full Pipeline Live (+10 more)

### Community 37 - "Community 37"
Cohesion: 0.21
Nodes (18): canonical_areas cross-city area dimension, stg_zones staging model, cities seed (city registry), countries seed (static ISO reference), model_registry seed (model artifact catalog), taxi_zone_lookup seed (official TLC zone lookup), Real-observed-trip-data bar for adding a city, ADR-011: Retreat from global coverage to NYC + London (+10 more)

### Community 38 - "Community 38"
Cohesion: 0.21
Nodes (12): CityPage(), CityHero(), CityHeroProps, CityProfile(), ModelStatus(), ModelStatusProps, useAppContext(), CityProfileResponse (+4 more)

### Community 39 - "Community 39"
Cohesion: 0.18
Nodes (16): build_splits(), demo(), _gen_area_ranking(), _gen_comparison(), _gen_top_n(), generate_examples(), Path, Programmatic (template + correct-by-construction label) NL question ->… (+8 more)

### Community 40 - "Community 40"
Cohesion: 0.14
Nodes (16): classify(), demo(), _heuristic_classify(), Numeric vs explanatory intent router (FR-4, ADR-004). A short LLM…, skipif, parametrize, RAG layer: the non-trivial, LLM-independent logic gets a real test…, test_heuristic_classify_ambiguous_defaults_numeric() (+8 more)

### Community 41 - "Community 41"
Cohesion: 0.20
Nodes (15): build_eta_graph(), demo(), dijkstra(), DiGraph, Path, Dijkstra's shortest path from scratch (FR-4), used as a graph-path ETA sanity…, Directed graph of zones with edge attribute `weight` = average trip duration in…, Return (path, total_weight) for the shortest path from source to target. Raises… (+7 more)

### Community 42 - "Community 42"
Cohesion: 0.12
Nodes (17): clsx, framer-motion, dependencies, animejs, clsx, framer-motion, next, react-map-gl (+9 more)

### Community 43 - "Community 43"
Cohesion: 0.15
Nodes (10): InsightsPage(), SOURCE_LABELS, AICard(), AICardProps, Skeleton(), ChatRequest, ChatResponse, getInsights() (+2 more)

### Community 44 - "Community 44"
Cohesion: 0.16
Nodes (13): CapabilityGate(), CapabilityGateProps, useCapability(), CapabilityUnavailable(), CapabilityUnavailableProps, CapabilityMatrixProps, SurgeCard(), SurgeCardContent() (+5 more)

### Community 45 - "Community 45"
Cohesion: 0.12
Nodes (16): limit, name, tool_call, context, output, models, name, npm (+8 more)

### Community 46 - "Community 46"
Cohesion: 0.17
Nodes (15): get_chat_history(), _normalize_route(), post_chat(), ChatRequest, ChatResponse, get, post, Chat router endpoints: POST /chat, GET /chat/history/{session_id}, and WS… (+7 more)

### Community 47 - "Community 47"
Cohesion: 0.23
Nodes (13): chronological_split(), demo(), _latest_month_start(), DataFrame, Chronological train/validation/test split (ADR-003). Never random-split time-…, train/val = every month before the latest one (chronological 85/15), test = the…, Sort `df` by `ts_col` and slice into len(fracs) chunks, in the given…, split_demand_blocks() (+5 more)

### Community 48 - "Community 48"
Cohesion: 0.23
Nodes (15): answer(), _answer_explanatory(), _answer_numeric(), answer_stream(), demo(), _format_label(), _format_numeric_answer(), _format_value() (+7 more)

### Community 49 - "Community 49"
Cohesion: 0.13
Nodes (15): autoprefixer, devDependencies, autoprefixer, postcss, tailwindcss, @types/node, @types/react, @types/react-dom (+7 more)

### Community 50 - "Community 50"
Cohesion: 0.15
Nodes (13): Intermediate Models Schema, DuckDB over Postgres Decision, dbt Staging/Intermediate/Marts Layering Decision, Chronological Train/Val/Test Split Decision, Docs Index, Implementation Audit, Chronological Split Discipline (Implementation Audit), city_tariff_profiles Table (+5 more)

### Community 51 - "Community 51"
Cohesion: 0.16
Nodes (10): pinball_loss(), DataFrame, ndarray, XGBRegressor, Quantile ETA models (Phase 7): eta_p10/p50/p90 via XGBoost's native…, train_and_save(), train_quantile(), metadata() (+2 more)

### Community 52 - "Community 52"
Cohesion: 0.21
Nodes (14): Qdrant Vector Store, build_vector_store(), demo(), _embed(), _get_client(), _point_id(), Path, Embed insight docs into Qdrant (FR-2). Uses OpenAI's `text-embedding-3-small`… (+6 more)

### Community 53 - "Community 53"
Cohesion: 0.23
Nodes (14): check_contains(), check_numeric(), _extract_numeric(), load_golden(), _normalize(), Path, Golden-question eval runner for the RAG chat layer…, Runnable check on the comparison logic itself (no live calls). (+6 more)

### Community 54 - "Community 54"
Cohesion: 0.24
Nodes (14): True iff every number in `text` is either a small connective number…, validate_grounding(), _allowed_numbers(), _build_station_flow_graph(), demo(), _facts_for_station(), generate_all(), load_insight_docs() (+6 more)

### Community 55 - "Community 55"
Cohesion: 0.20
Nodes (13): _best_alpha(), ewma(), ewma_blocks(), load_zone_hourly_blocks(), DuckDBPyConnection, ndarray, Series, EWMA smoothing over zone_hourly_demand, implemented from scratch. S_t = alpha *… (+5 more)

### Community 56 - "Community 56"
Cohesion: 0.20
Nodes (13): get_chat_tier(), city_chat(), ChatRequest, ChatResponse, post, answer_question(), get_history(), _public_route() (+5 more)

### Community 57 - "Community 57"
Cohesion: 0.20
Nodes (11): AnalystPage(), ask(), handleSubmit(), EXAMPLE_PROMPTS, looksNumeric(), Turn, TurnBubble(), ChatMessage (+3 more)

### Community 58 - "Community 58"
Cohesion: 0.21
Nodes (10): QueryPlan, parametrize, Compiler correctness per canonical intent against nyc_schema.py, and the "raise…, test_area_ranking_compiles(), test_bad_aggregation_raises(), test_comparison_compiles(), test_hourly_pattern_compiles(), test_metric_lookup_compiles() (+2 more)

### Community 59 - "Community 59"
Cohesion: 0.15
Nodes (10): client(), fixture, Correctness tests for the Global Mobility Domain Model registry (SPEC-013…, Flat set of every registered path. Recent FastAPI wraps…, ADR-011: this platform serves the cities it has real trip data for. A city_id…, No capability is hand-authored true -- every True demand/fare/journey flag…, _route_paths(), test_capabilities_backed_by_real_model_registry_rows() (+2 more)

### Community 60 - "Community 60"
Cohesion: 0.26
Nodes (11): load_data(), main(), DataFrame, Path, Train a single tuned XGBoost fare-prediction model (SPEC-007). Deliberately not…, Small manual grid, selected by validation RMSE. Not a full ladder or CV search…, rmse_mae(), split_data() (+3 more)

### Community 61 - "Community 61"
Cohesion: 0.26
Nodes (10): call_base_model(), demo(), evaluate_file(), _parse_model_plan(), Path, Scores the base model's QueryPlan-JSON output against the known-correct plan on…, Structural match on intent/metric/filters/aggregation (FR-8) -- not…, run() (+2 more)

### Community 62 - "Community 62"
Cohesion: 0.28
Nodes (12): demo(), _embed(), _ensure_collection(), get(), _get_client(), _point_id(), put(), Any (+4 more)

### Community 63 - "Community 63"
Cohesion: 0.15
Nodes (9): con(), fixture, Correctness tests for the London (Santander Cycle Hire) dbt pipeline (SPEC-015…, The actual dbt test suite for the four London models -- pass or warn, never a…, station_id, trip_date, hour, day_of_week, total_trips, avg_duration_min -- real…, rule 6 / spec-015 ground rule: London is additive-only, NYC's warehouse file…, test_dbt_test_passes_for_london_models(), test_mart_shape_mirrors_zone_hourly_demand() (+1 more)

### Community 64 - "Community 64"
Cohesion: 0.26
Nodes (11): city_ids(), ensure_table(), load(), Table, Cached per-city fare-structure profiles. A `TariffProfile` is a small set of…, Idempotent create -- called from load() and upsert() the same way…, Startup read (rule 8: no work on the request path -- this is called once at app…, Every city_id that actually has a cached profile -- the real fare-supported… (+3 more)

### Community 65 - "Community 65"
Cohesion: 0.24
Nodes (11): ADR-010: Query-Plan Fine-Tuning Budget Exception, models/query_plan_finetune/eval_report.json, evaluate.py, compile(), demo(), _group_by_name(), Deterministic QueryPlan -> SQL compiler (FR-2, spec-014). The LLM (base or,…, Resolve every field the plan references against `schema`; raises before any SQL… (+3 more)

### Community 66 - "Community 66"
Cohesion: 0.24
Nodes (10): Shared config for the RAG layer -- one place for the LLM model id and warehouse…, extract_numbers(), _allowed_numbers(), _facts_from_components(), generate(), _phrase_with_llm(), AI Recommendations for a journey estimate (ADR-007). Reuses…, `components` is the dict[str, PredictionResult] journey_service.estimate()… (+2 more)

### Community 67 - "Community 67"
Cohesion: 0.23
Nodes (8): demo(), DataFrame, Path, Phase 4: regenerate `dbt_project/seeds/model_registry.csv`'s `training_period`…, Self-check on a throwaway copy: a metadata file with a later date_range must…, refresh(), _training_period_from_metadata(), Phase 4: refresh_model_registry.py must update training_period from real…

### Community 68 - "Community 68"
Cohesion: 0.35
Nodes (10): load_zone_points(), Path, get_zone(), _get_zones(), list_zones(), _load_zones(), get, GET /zones (list), GET /zones/{zone_id} (detail) (FR-3). Zone metadata is… (+2 more)

### Community 69 - "Community 69"
Cohesion: 0.24
Nodes (10): get_model(), has_active_model(), list_models_for(), load(), Model registry (SPEC-013 FR-4) -- thin query module over the seeded…, The active model backing `metric` for `city_id`, or None if the capability…, resolve_model(), Operations (+2 more)

### Community 70 - "Community 70"
Cohesion: 0.44
Nodes (10): _base_fare_tariff(), _ctx(), demo(), _features(), Correctness tests for the tariff-profile fare engine (ADR-011): the LLM never…, A tariff fare is denominated in the city's own currency and is never FX-…, test_fare_monotonic_in_distance(), test_fare_stays_in_the_profiles_own_currency_never_converted() (+2 more)

### Community 71 - "Community 71"
Cohesion: 0.24
Nodes (11): day_of_week, ewma, hour, XGBoost Feature Importance Chart, is_weekend, lag_168h, lag_1h, lag_24h (+3 more)

### Community 72 - "Community 72"
Cohesion: 0.31
Nodes (10): _allowed_numbers(), demo(), _facts_for_zone(), generate_all(), load_insight_docs(), _phrase_with_llm(), DataFrame, Path (+2 more)

### Community 73 - "Community 73"
Cohesion: 0.27
Nodes (9): chat_completion(), demo(), Shared DeepSeek-primary / OpenAI-fallback chat completion helper. DeepSeek's…, Same call shape as `OpenAI().chat.completions.create(...)`. Tries DeepSeek…, blind_guess(), main(), measure_mape(), _parse_json_response() (+1 more)

### Community 74 - "Community 74"
Cohesion: 0.27
Nodes (10): answer(), demo(), generate_plan(), Path, NL-to-SQL over the mart schema only (FR-3, ADR-004; restructured for SPEC-013…, The one place an LLM is called on the numeric-question path -- its entire…, Question -> QueryPlan -> deterministically compiled SQL -> real, read-only…, Defense-in-depth guard (ADR-004): compile_plan() only ever emits schema-… (+2 more)

### Community 75 - "Community 75"
Cohesion: 0.18
Nodes (11): query_classifier.py, rag_pipeline.py, session_store.py, sql_agent.py, services/rag_service.py, routers/chat.py, ChatPanel.tsx, rag/nl_to_sql/nyc_schema.py (+3 more)

### Community 76 - "Community 76"
Cohesion: 0.20
Nodes (9): _coords(), fixture, Correctness checks for the map hero's zone geometry (ADR-011 phase 7). The bug…, Walk an arbitrarily nested GeoJSON coordinate array down to positions., Catches the axis-order bug: (lat, lon) puts NYC at ~(40, -74) read as lon=40,…, The choropleth joins these to zone_hourly_demand on location_id -- a drifted or…, test_every_zone_position_is_lon_lat_inside_nyc(), test_location_ids_join_to_the_zone_lookup() (+1 more)

### Community 77 - "Community 77"
Cohesion: 0.22
Nodes (10): backend/Dockerfile, certs/global-bundle.pem (RDS TLS CA Bundle), backend Service (docker-compose), frontend-web Service (docker-compose), NEXT_PUBLIC_API_BASE_URL Must Be Host-Published Address (rationale), qdrant Service (docker-compose), qdrant_storage Volume, RDS TLS CA Bundle Mount for sslmode=verify-full (rationale) (+2 more)

### Community 78 - "Community 78"
Cohesion: 0.20
Nodes (10): Rule 8: No Reprocessing on Request Path, int_trips_enriched.sql, dbt_project/models/staging/stg_trips.sql, Data Flow, zone_fare_stats mart, zone_hourly_demand mart, zone_pair_flows mart, NYC TLC HVFHV Trip Records (+2 more)

### Community 79 - "Community 79"
Cohesion: 0.29
Nodes (10): london_station_hourly_demand mart, zone_hourly_demand mart, stg_london_stations staging model, london_stations seed (TfL BikePoint snapshot), Open-Meteo historical backfill lifts the weather ceiling, Layer 0-5 build ladder, Strict top-to-bottom layer sequencing constraint, From-Scratch Algorithms Validated Against Reference Libraries (+2 more)

### Community 80 - "Community 80"
Cohesion: 0.22
Nodes (10): Single-method fetch() adapter pattern, Honest stubs for paid data sources, Cacheable point lookups with stdlib lru_cache, Nager.Date IsTodayPublicHoliday silent-wrongness fix, GTFS transit-context onboarding with verified feed URLs, GTFS transit adapter and feed ingestion, Nager.Date holiday adapter, OSRM routing adapter (+2 more)

### Community 81 - "Community 81"
Cohesion: 0.20
Nodes (9): dependencies, animejs, gsap, @gsap/react, lenis, animejs, gsap, @gsap/react (+1 more)

### Community 82 - "Community 82"
Cohesion: 0.31
Nodes (9): _body(), client(), fixture, Correctness tests for POST /journey/estimate (ADR-007)., test_journey_estimate_happy_path(), test_journey_estimate_outside_coverage_degrades_honestly(), test_journey_estimate_unknown_vehicle_type_is_unavailable_not_default(), test_journey_estimate_vehicle_type_changes_fare_and_carbon() (+1 more)

### Community 83 - "Community 83"
Cohesion: 0.33
Nodes (8): city_journey_estimate(), CityJourneyEstimate, Deliberately a 4-field subset of JourneyEstimate: distance/duration (real, via…, estimate(), datetime, PredictionOut, City-scoped journey estimate (distance/duration/demand/fare) -- a thin 4-field…, _to_out()

### Community 84 - "Community 84"
Cohesion: 0.22
Nodes (9): stg_london_cycle_journeys staging model, tfl_cycling raw_journeys source (attached london_cycles.duckdb), Structured error envelope and ErrorCode taxonomy, PredictionEnvelope provenance wrapper, Wrapping views over renaming (backward compatibility), SPEC-013 Global Mobility Domain Model — superseded, prediction_service provenance orchestrator, SPEC-015 London onboarding (real second city) (+1 more)

### Community 85 - "Community 85"
Cohesion: 0.22
Nodes (9): vehicle_profiles seed (per-class fare/carbon factors), Structural `basis` field on every prediction, Confidence as a deterministic function of the basis mix, PredictionResult dataclass contract, Qualitative buckets over false precision (Surge Risk / Ride Availability), capability_matrix returns None for unregistered cities (404 over degraded answer), Data-unavailable is a 200 body, not a 4xx, estimation_service population-scaled demand — superseded (+1 more)

### Community 86 - "Community 86"
Cohesion: 0.22
Nodes (6): dbt_project/models/staging/schema.yml, ADR-003: Chronological Split, Data Source and Transformation, DBT_PROFILES_DIR, DBT_PROJECT_DIR, aws_dbt_build_userdata.sh script

### Community 87 - "Community 87"
Cohesion: 0.33
Nodes (6): JourneyMap(), JourneyMapProps, MAP_STYLE, ROUTE_LINE_LAYER, useReducedMotion(), useWebGLPreservation()

### Community 88 - "Community 88"
Cohesion: 0.22
Nodes (8): name, private, scripts, build, dev, lint, start, version

### Community 89 - "Community 89"
Cohesion: 0.36
Nodes (8): _download(), fetch_journeys(), fetch_stations(), load_duckdb(), main(), Path, Download and load TfL Santander Cycle Hire journey data into DuckDB. Mirrors…, Pull live BikePoint locations and write the same station_id/name/lat/lon shape…

### Community 90 - "Community 90"
Cohesion: 0.43
Nodes (7): demo(), _extended_fixed_holidays(), fetch(), datetime, Real public-holiday lookup via Nager.Date -- free, global, no API key required…, Real holiday dates (ISO strings) for a (year, country), or None if the lookup…, _year_holidays()

### Community 91 - "Community 91"
Cohesion: 0.29
Nodes (5): Construct, .github/workflows/dbt-build-aws.yml, DbtBuildStack, CDK stack for the on-demand dbt-build compute (ADR-009). Everything here exists…, Stack

### Community 92 - "Community 92"
Cohesion: 0.25
Nodes (8): zone_centroids seed (NYC TLC zone centroids), FastAPI lifespan preload of models and registries, Local dev setup and warehouse build, Tests skip when the warehouse is unbuilt, Open-Meteo weather adapter, NYC zone geometry and choropleth hero, Precompute Discipline (offline transforms, serve artifacts), Serving-only backend dependency split

### Community 93 - "Community 93"
Cohesion: 0.39
Nodes (7): plot_feature_importance(), DataFrame, Path, Tuned XGBoost regressor for zone-hourly demand (SPEC-006, FR-5). Same manual-…, rmse_mae(), train_and_save(), tune()

### Community 94 - "Community 94"
Cohesion: 0.36
Nodes (7): answer(), demo(), generate_plan(), Path, NL question -> QueryPlan (fine-tuned model) -> compiled SQL -> executed read-…, System prompt is `schema.describe()` alone -- exactly the training format…, _strip_fences()

### Community 95 - "Community 95"
Cohesion: 0.46
Nodes (7): _download(), _fetch_and_extract_stops(), load_stops(), main(), Path, Download, unzip, and load GTFS static feeds' stops.txt into each city's own…, _read_feeds()

### Community 96 - "Community 96"
Cohesion: 0.36
Nodes (6): _old_split_data(), DataFrame, Phase 2 dedup proof: `train_fare_xgb.split_data()` (now delegating to the…, The exact logic train_fare_xgb.split_data() used to inline, before Phase 2…, _synthetic_gapped_df(), test_new_split_data_matches_old_inline_logic_exactly()

### Community 97 - "Community 97"
Cohesion: 0.25
Nodes (7): sql_agent.py-specific coverage for SPEC-013 FR-10: the LIVE `/chat` numeric-…, generate_sql() (the old LLM-writes-SQL-text function) must be gone;…, Patching generate_plan to return a known QueryPlan proves answer()'s executed…, _validate_sql() is kept as a second layer over the compiler's output (ADR-004…, test_sql_agent_answer_routes_through_the_compiler_not_raw_text(), test_sql_agent_has_no_raw_sql_generation_path(), test_validate_sql_still_rejects_disallowed_sql_defense_in_depth()

### Community 98 - "Community 98"
Cohesion: 0.43
Nodes (6): demo(), extract(), _iso3_to_iso2_map(), _nager_covered_iso2(), DataFrame, Extends holiday coverage past Nager.Date's 204 countries (notably: no India)…

### Community 99 - "Community 99"
Cohesion: 0.40
Nodes (6): Chat tiers: sql_only vs full_rag, CityMobilitySchema (per-city NL-to-SQL schema declaration), Grounding Validation (no ungrounded numbers in LLM text), Hybrid RAG Pipeline (numeric vs explanatory routing), Deterministic NL to QueryPlan to SQL Path, Canonical Mobility QueryPlan intermediate representation

### Community 100 - "Community 100"
Cohesion: 0.60
Nodes (5): DataFrame, Train the congestion-multiplier XGBoost regressor (Phase 6). Same tuned-grid-…, rmse_mae(), train_and_save(), tune()

### Community 101 - "Community 101"
Cohesion: 0.47
Nodes (6): LSTM Loss Curve (Zone-Hourly Demand), Train MSE (normalized), Validation MSE (normalized), LSTM Demand Forecast Model, Model Ladder (linear -> EWMA -> XGBoost -> LSTM), Zone-Hourly Demand Target

### Community 102 - "Community 102"
Cohesion: 0.40
Nodes (5): QueryFilters, Only the filters actually set, as canonical-name -> value., _area_value(), _gen_hourly_pattern(), _gen_metric_lookup()

### Community 103 - "Community 103"
Cohesion: 0.33
Nodes (4): features_df(), fixture, Phase 6 leakage guard + honesty test for the congestion model (ADR-003 +…, test_congestion_chronological_split_no_leakage()

### Community 104 - "Community 104"
Cohesion: 0.50
Nodes (5): Daily and Weekly Seasonality Pattern, East Village (NYC Zone), Multiplicative Time-Series Decomposition (Trend/Seasonal/Residual), East Village Multiplicative Decomposition (Jan 2024), Ride Demand Time Series

### Community 105 - "Community 105"
Cohesion: 0.70
Nodes (5): Daily*Weekly Seasonality Component, Park Slope Multiplicative Decomposition Chart, Multiplicative Time-Series Decomposition, Park Slope Zone, Ride Demand Time Series (Jan 2024)

### Community 106 - "Community 106"
Cohesion: 0.40
Nodes (5): Get traffic/congestion information for a city. Returns historical traffic score…, traffic(), Traffic context response - only what's actually available., TrafficResponse, TrafficResponse

### Community 107 - "Community 107"
Cohesion: 0.60
Nodes (4): fetch_city_weather(), main(), Backfill real historical hourly weather (temperature + precipitation) for every…, _real_dates_needed()

### Community 108 - "Community 108"
Cohesion: 0.50
Nodes (4): demo(), fit_nyc_fare_anchor(), DuckDBPyConnection, Real, measured NYC fare anchor shared by generate_tariff_profile.py and…

### Community 109 - "Community 109"
Cohesion: 0.67
Nodes (4): algorithms/timeseries Module, JFK Airport Multiplicative Decomposition (Jan 2024), JFK Airport Ride Demand Time Series, Multiplicative Time-Series Decomposition (Trend/Seasonal/Residual)

### Community 110 - "Community 110"
Cohesion: 0.50
Nodes (4): JourneyContextRequest, Shared context for all mobility predictions - city, coordinates, time, vehicle., Request for routing - inherits all context fields., RouteRequest

### Community 111 - "Community 111"
Cohesion: 0.50
Nodes (4): zone_fare_stats mart, zone_pair_flows mart, nyc_tlc raw_trips source (HVFHV parquet), stg_trips staging model

### Community 112 - "Community 112"
Cohesion: 0.50
Nodes (4): backend/predictors/journey_predictors.py, backend/services/journey_service.py, backend/predictors/base.py, backend/routers/journey.py

### Community 113 - "Community 113"
Cohesion: 0.50
Nodes (4): models/query_plan_finetune/evaluate.py, rag/nl_to_sql/synthetic_schemas.py, models/query_plan_finetune/train.py, rag/nl_to_sql/training_data_gen.py

### Community 114 - "Community 114"
Cohesion: 0.67
Nodes (3): dbt Build AWS Workflow, infra/cdk/stack.py, scripts/aws_dbt_build_userdata.sh

### Community 118 - "Community 118"
Cohesion: 0.67
Nodes (3): build_vector_store.py, generate_insight_docs.py, rag/journey_narrative.py

## Knowledge Gaps
- **277 isolated node(s):** `EXAMPLE_PROMPTS`, `SOURCE_LABELS`, `defaultPickup`, `defaultDropoff`, `metadata` (+272 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **44 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Data Flow` connect `Community 78` to `Community 36`, `Community 40`, `Community 74`, `Community 47`, `Community 86`, `NYC Demand Features`?**
  _High betweenness centrality (0.040) - this node is a cross-community bridge._
- **Why does `Operations` connect `Community 69` to `Community 48`, `Community 65`, `Community 35`, `Domain Errors & Capability Gating`?**
  _High betweenness centrality (0.028) - this node is a cross-community bridge._
- **Why does `get_datasource()` connect `Per-City Data Sources` to `Domain Errors & Capability Gating`?**
  _High betweenness centrality (0.015) - this node is a cross-community bridge._
- **Are the 8 inferred relationships involving `PredictionResult` (e.g. with `fetch()` and `fetch()`) actually correct?**
  _`PredictionResult` has 8 INFERRED edges - model-reasoned connections that need verification._
- **Are the 19 inferred relationships involving `QueryPlan` (e.g. with `call_base_model()` and `demo()`) actually correct?**
  _`QueryPlan` has 19 INFERRED edges - model-reasoned connections that need verification._
- **Are the 16 inferred relationships involving `CityMobilitySchema` (e.g. with `answer()` and `generate_plan()`) actually correct?**
  _`CityMobilitySchema` has 16 INFERRED edges - model-reasoned connections that need verification._
- **What connects `EXAMPLE_PROMPTS`, `SOURCE_LABELS`, `defaultPickup` to the rest of the system?**
  _277 weakly-connected nodes found - possible documentation gaps or missing edges._
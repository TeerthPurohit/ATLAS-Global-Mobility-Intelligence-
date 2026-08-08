# Frontend Architecture Audit

> **Status: fixed, 2026-08-06.** Every finding below has been resolved —
> real backend endpoints added (`backend/routers/platform.py`), the two
> missing artifacts generated for real (`scripts/generate_algorithm_artifacts.py`),
> and the fabricated comparison chart deleted. This document is kept as the
> historical record of what was wrong and why; see `.claude/memory.md` and
> `DESIGN.md`'s audit note for the current state. Don't re-read this as
> describing the app's present behavior.

Date: 2026-08-06
Scope: `frontend/src/pages/*`, `frontend/src/components/layout/*`, cross-referenced
against `frontend/src/api/client.ts`, `backend/routers/*`, `backend/services/*`,
`dbt_project/models/marts/*`, `models/*/*.json`, and `rag/*`.

This audit was produced by reading every page component and tracing each widget
to its literal data source in code — not by re-checking a pasted summary.
Findings below diverge from the pasted "10/31 live, 18 hardcoded, 3 client-derived"
claim in one important way: several widgets aren't just static, they **fabricate**
numbers from a real API response, and two reference artifact files that do not
exist anywhere in the repo. Those are flagged separately because they're a
different severity of problem than "not wired up yet" — they violate
`.claude/rules.md`'s no-fabricated-metrics rule right now, live, in front of a
real API call.

## Classification legend

| Code | Meaning |
|---|---|
| **LIVE** | Backed by a real FastAPI call at render/interaction time |
| **DUCKDB** | Would be/is backed by a direct DuckDB query |
| **MART** | Would be/is backed by a materialized dbt mart |
| **ARTIFACT** | Would be/is backed by a trained model's metadata/metrics file |
| **SPEC** | Static documentation/config — legitimately static, not a defect |
| **DERIVED** | Computed client-side from an already-fetched real API response |
| **HARDCODED** | Literal in component code, presented as if it were data |
| **FABRICATED** | Worse than hardcoded — synthesized from a real value using invented constants, presented as if measured |
| **PLACEHOLDER** | UI element with no data or logic behind it at all (dead button, non-functional input) |
| **MISSING ARTIFACT** | References a file/endpoint that doesn't exist anywhere in the repo |

## Headline numbers (my count, not the pasted one)

Counting every distinct widget across 12 pages + 2 layout components: **~55
widgets**. Of these:

- **11 LIVE** (or LIVE+DERIVED) — genuinely hit `/zones`, `/predict/demand`,
  `/predict/fare`, or `/chat`
- **~28 HARDCODED** — literal values in component source
- **3 FABRICATED** — real API value multiplied by invented constants
  (`DemandForecast.tsx`'s model-ladder comparison chart)
- **2 MISSING ARTIFACT** — reference files that don't exist on disk at all
  (`Algorithms.tsx`'s PageRank hub list and KD-tree benchmark numbers)
- **~5 PLACEHOLDER** — decorative, non-functional (search bar, notification
  bell, refresh button, error fallback text, Settings page)
- **~6 SPEC/config** — legitimately static (nav config, docs content, form
  option lists)

So the pasted claim of "10/31 live, ~68% not backend-driven" undercounts the
problem on granularity but the direction is right: the majority of surface
area presents as live when it's compiled-in.

---

## Per-page classification

### Layout — `Sidebar.tsx`, `Navbar.tsx` (every page)

| Widget | Location | Class | Should be backed by |
|---|---|---|---|
| Nav section list | `Sidebar.tsx:38-71` | SPEC | n/a — this is routing config, correctly static |
| "RAG" nav badge | `Sidebar.tsx:51` | SPEC | n/a |
| Footer "DuckDB & Qdrant · Connected" pill | `Sidebar.tsx:146-158` | **HARDCODED** | New `GET /health` endpoint checking DuckDB file handle + Qdrant ping |
| Breadcrumb title map | `Navbar.tsx:9-22` | SPEC | n/a |
| "TLC HVFHV 2024 (Jan/Mar/Jun)" pulsing-dot pill | `Navbar.tsx:62-66` | **HARDCODED** | The pulsing dot implies liveness it doesn't have; either remove the dot or back it with the same `/health` call |
| Refresh button | `Navbar.tsx:33,68-75` | **PLACEHOLDER** | Should invalidate the active page's react-query cache; currently a 800ms `setTimeout` spinner, no `onRefresh` ever passed by any page |
| Search bar | `Navbar.tsx:46-58` | **PLACEHOLDER** | No handler wired at all — remove or implement |
| Notification bell | `Navbar.tsx:77-83` | **PLACEHOLDER** | Decorative only — remove or implement |
| User pill "Teerth Purohit / Data & ML Engineer" | `Navbar.tsx:90-93` | SPEC | Fine as static — this is a portfolio, not a multi-user app |

### `Dashboard.tsx` (`/`)

| Widget | Location | Class | Should be backed by |
|---|---|---|---|
| "Live Warehouse" title badge | L59-61 | **HARDCODED** | `/health` |
| Telemetry bar (db name, mart, row count, env, latency) | L79-103 | **HARDCODED** | Row count/latency → new `/warehouse/stats` DuckDB query; env → build-time env var, not literal |
| KPI: Total Trips "9.84 M" | L108-127 | **HARDCODED** | `MART` — `zone_hourly_demand` row-sum, needs new endpoint |
| KPI: Avg Fare "$27.14" | L130-147 | **HARDCODED** | `MART` — `zone_fare_stats`, needs new endpoint |
| KPI: Active Zones | L150-169 | **LIVE** (with hardcoded `261` fallback) | Already correct — drop the `\|\| 261` fallback, show a loading/unavailable state instead per the "never fabricate" rule |
| KPI: Demand RMSE "5.09" | L172-189 | **HARDCODED** | `ARTIFACT` — `models/evaluation/compare_results.json` exists today, just isn't read by any backend route |
| Hourly Demand & Fare chart | L194-236, data L30-37 | **HARDCODED** | `MART` — `zone_hourly_demand` |
| Model Ladder RMSE bar chart | L238-272, data L39-44 | **HARDCODED** | `ARTIFACT` — `compare_results.json` |
| 3 quick-action nav cards | L276-324 | SPEC | Fine as-is |

### `NYCMap.tsx` (`/map`)

| Widget | Location | Class | Should be backed by |
|---|---|---|---|
| Hour/day selectors | L47-76 | SPEC | Fine |
| Borough color legend | L78-90 | SPEC (mislabeled) | The legend itself is fine as config; the "Source: zone_centroids.csv" caption is misleading and should be removed — it's a color map, not derived from the CSV |
| Map + zone markers | L93-123 | **LIVE** | `GET /zones` — correct today |
| Zone inspector panel | L146-165 | **LIVE/DERIVED** | Correct — real zone data, "KD-Tree Centroid Mapped" is accurate descriptive text about the real backend algorithm |
| Model demand forecast readout | L167-193 | **LIVE** | `GET /predict/demand` — correct today |
| "Zone RAG Insight" paragraph | L195-204 | **HARDCODED**, mislabeled as RAG | This is the worst offender on this page: it's a JS template string, not a `/chat` call, but it's labeled and styled identically to genuine RAG output elsewhere in the app. Either wire it to `POST /chat` with a zone-scoped question, or rename it and drop the RAG branding |

### `DemandForecast.tsx` (`/demand`)

| Widget | Location | Class | Should be backed by |
|---|---|---|---|
| Zone/hour/day form | L57-141 | LIVE (zones) + SPEC | Fine |
| Predicted Pickup Demand KPI | L158-172 | **LIVE** | `GET /predict/demand` — correct |
| "Model Ladder Comparative Predictions" bar chart | L174-188, factors L34-41 | **FABRICATED** | Multiplies the one real XGBoost prediction by hardcoded constants (1.15, 0.92, 1.04, 1.0) to invent EWMA/Linear/LSTM numbers. This directly violates the no-fabricated-metrics rule in `.claude/rules.md` — it looks like 4 models ran, only 1 did. Needs either: (a) new backend endpoint that actually runs all 4 trained models for the given inputs, or (b) delete this chart until that exists |
| Feature store note | L198-200 | SPEC | Fine |
| Footer "models/demand/xgb_model.json" | L204 | **HARDCODED**, and factually wrong | Real path is `models/xgboost_model/xgb_model.json` per `model_service.py:23` — this caption is lying about its own backend |

### `FarePrediction.tsx` (`/fare`)

| Widget | Location | Class | Should be backed by |
|---|---|---|---|
| Pickup/dropoff/hour form | L46-129 | LIVE (zones) | Fine |
| Estimated Fare KPI | L146-156 | **LIVE** | `GET /predict/fare` — correct |
| "Evaluated on June holdout: RMSE $12.61 / MAE $6.29" | L153-155 | **HARDCODED** | `ARTIFACT` — `models/fare_prediction/fare_xgb_metadata.json` exists, unread by backend |
| Pickup/dropoff borough cards | L158-167 | **DERIVED** | Correct — legitimately computed from the real `/zones` response |
| HVFHV fare schema note | L177-179 | SPEC | Fine |

### `AIAnalyst.tsx` (`/analyst`)

| Widget | Location | Class | Should be backed by |
|---|---|---|---|
| Suggested question chips | L5-10, 101-111 | SPEC | Fine |
| Chat feed | L113-173 | **LIVE** | `POST /chat` — correct |
| Route badge (NL-to-SQL vs Vector) | L126-140 | **LIVE/DERIVED** | Correct — real `msg.route` field |
| SQL box | L146-166 | **LIVE**, but caption is off | The SQL itself is real; the caption "Engine: DuckDB v1.0 · Table: zone_hourly_demand" (L161) is a static string shown for every response regardless of which table was actually hit — should read the real table from the response or be removed |
| Session ID pill | L79-84 | **LIVE** | Correct |
| Error fallback text | L53-60 | PLACEHOLDER | Appropriate use — this is exactly the "Unavailable" pattern the provenance policy asks for, keep it |
| Footer captions | L209-212 | SPEC | Fine |

Dead code found here: `fetchChatHistory()` (`GET /chat/history/{id}`) exists in
`api/client.ts` and has a real backend route, but no page calls it — the
session-resume flow is half-built.

### `ModelCenter.tsx` (`/models`)

| Widget | Location | Class | Should be backed by |
|---|---|---|---|
| Demand models table | L5-10 | **HARDCODED** | `ARTIFACT` — `compare_results.json` |
| Feature importance chart | L12-19 | **MISSING ARTIFACT** | No gain-values JSON exists anywhere in the repo — `models/xgboost_model/feature_importance.png` is an image, not machine-readable. Needs the training script to export a JSON sidecar before this can be real |
| Fare model registry card | L145-150 | **HARDCODED** | `ARTIFACT` — `fare_xgb_metadata.json` |
| Provenance footer labels | throughout | **HARDCODED**, ironically — labeled "Registered"/"Precomputed Booster Gain Metadata" while backing no actual provenance data | Should be generated from the real metadata file's fields once wired |

### `Algorithms.tsx` (`/algorithms`)

| Widget | Location | Class | Should be backed by |
|---|---|---|---|
| KD-Tree "5.17x Measured Speedup" + latency bars | L36-63 | **MISSING ARTIFACT** | No benchmark output file exists in `algorithms/` at all. This isn't "unwired," the number was never measured and stored anywhere — needs a real benchmark run (there's a `performance-engineer` agent and `/perf` skill in this repo already set up for exactly this) |
| PageRank top-3 hub list | L99-102 | **MISSING ARTIFACT** | Footer literally claims "Precomputed JSON: pagerank_hubs.json" — that file does not exist anywhere in the repo. This is the single most misleading widget in the app: it cites a specific artifact path that was never created |
| Dijkstra tolerance badge | — | SPEC | Fine as a documented algorithm parameter |
| EWMA alpha badge | — | SPEC | Fine as a documented algorithm parameter |

### `DataPipeline.tsx` (`/pipeline`)

| Widget | Location | Class | Should be backed by |
|---|---|---|---|
| 6 pipeline-stage node cards (duration, row count, code snippet) | L25-110 | **HARDCODED** | Needs a real pipeline manifest — either dbt's own `run_results.json`/`manifest.json` (already produced by `dbt build`, currently unread) or a lightweight run-log the ingestion scripts write |
| "Run ID: 20260806_0813" | L269 | **HARDCODED**, formatted to look like a live timestamp | Same manifest fix covers this |

### `Warehouse.tsx` (`/warehouse`)

| Widget | Location | Class | Should be backed by |
|---|---|---|---|
| Table list with schema + row counts | L4-44 | **HARDCODED** | `DUCKDB` — needs a new `GET /warehouse/tables` route running `PRAGMA table_info` / `DESCRIBE` + `COUNT(*)` against `data/warehouse/nyc_rides.duckdb`. No such route exists today |

### `Experiments.tsx` (`/experiments`)

| Widget | Location | Class | Should be backed by |
|---|---|---|---|
| Experimental runs table | L4-10 | **HARDCODED**, misleadingly sourced | Footer claims "Source: MLflow Experiment Logs" — there is no MLflow anywhere in this repo. Real numbers exist in `compare_results.json` and `fare_xgb_metadata.json`; needs an endpoint that reads those, and the MLflow claim should be deleted, not implemented (adding MLflow would be scope creep for a solo project — see the "flag if this only makes sense with multiple committers" note in `.claude/CLAUDE.md`) |

### `Documentation.tsx` (`/docs`)

| Widget | Location | Class | Should be backed by |
|---|---|---|---|
| Doc body content | L37-147 | SPEC | By design — fine to keep static |
| Per-doc `lastUpdated` dates | inline | **HARDCODED** | Low priority — either drop the field or derive it from `git log -1 --format=%aI -- <path>` at build time |

### `Settings.tsx` (`/settings`)

| Widget | Location | Class | Should be backed by |
|---|---|---|---|
| Entire form (`apiBaseUrl`, theme, refresh interval) | L12-14 | **PLACEHOLDER** | Everything round-trips through `localStorage` only; `apiBaseUrl` here is disconnected from the real `VITE_API_BASE_URL` build-time env var that `api/client.ts` actually uses — editing it silently does nothing. Either wire it to actually override the API client's base URL at runtime, or relabel the field so it isn't presented as functional |

---

## What's already good (don't touch)

- `GET /zones`, `GET /predict/demand`, `GET /predict/fare`, `POST /chat` are
  real, correctly wired, and every page that claims to use them does.
- The AI Analyst's route badge and SQL box are genuinely sourced from live
  response data — the one exception is the misleading static engine caption.
- `Documentation.tsx`'s static content is static *by design* — this is not a
  defect, don't "fix" it into a CMS.
- `models/evaluation/compare_results.json`, `fare_xgb_metadata.json`, and the
  three dbt marts already exist and are correctly built — the gap is entirely
  that no backend route reads them yet, not that the artifacts are missing
  (except the two flagged MISSING ARTIFACT cases above, which need new
  measurement work, not just wiring).

## Missing API/data contracts (net-new backend work, not frontend work)

1. `GET /health` — DuckDB + Qdrant liveness, backs 3 layout/dashboard widgets currently hardcoded "Connected"
2. `GET /warehouse/stats` — row counts/latency for Dashboard telemetry bar and Warehouse page (`DUCKDB`)
3. `GET /warehouse/tables` — schema introspection for Warehouse page (`DUCKDB`)
4. `GET /models/metrics` — reads `compare_results.json` + `fare_xgb_metadata.json`, backs Dashboard KPI4, ModelCenter, FarePrediction, Experiments
5. `GET /marts/zone_hourly_demand` and `/marts/zone_fare_stats` — backs Dashboard's two hardcoded charts (`MART`)
6. `GET /pipeline/status` — reads dbt's own `run_results.json`/`manifest.json`, backs DataPipeline
7. A real multi-model comparison endpoint, or deletion of `DemandForecast.tsx`'s fabricated comparison chart — this is the one item that's a rules violation right now, not just a gap

## Missing artifacts (measurement work, not wiring work)

1. KD-tree benchmark output — no file exists; needs an actual timed run (see `/perf` skill, `performance-engineer` agent)
2. `pagerank_hubs.json` — referenced by the UI, doesn't exist; needs the PageRank algorithm to actually run over real zone-transition data and its output persisted
3. Feature-importance gain values as JSON — training script needs to export this alongside the existing `.png`

---

**No UI code has been changed as part of this audit.** Next step is a decision
on sequencing: which of the 7 missing endpoints to build first, and whether to
delete the fabricated demand-comparison chart immediately (rules violation) independent of the rest of the sequencing.

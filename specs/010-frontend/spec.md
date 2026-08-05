# SPEC-010: Frontend

Owner: solo builder · Status: not started · Layer: 5 · Depends on: SPEC-009

## Business Goal

Rescoped 2026-08-06 at the owner's explicit request: an enterprise-grade
analytics dashboard for the use cases in
[Use-Cases.md](../../docs/product/Use-Cases.md) — explore demand on a map,
compare models, ask chat questions — presented as a real internal SaaS
product (Stripe/Linear/Retool/Grafana-grade), not a 3-component demo. This
supersedes the original minimal-JSX scope below FR-1 through FR-4; those
three requirements are kept as the functional floor, everything else in
this rescoped spec is additive UI/UX scope on top of them.

Design inspiration: [awesome-design-md](https://github.com/voltagent/awesome-design-md)
(already flagged in project memory for this layer) for DESIGN.md-style
tokens — swap its placeholder palette for this project's own (neutral
grayscale + single blue accent + status colors), don't adopt it verbatim.

## Stack

React + Vite + TypeScript (migrate from JS), TailwindCSS, shadcn/ui, Framer
Motion (subtle transitions only, not decoration), Recharts, React Query,
React Router, Leaflet, Lucide icons. No Material UI or other heavy
component suites — the design must stay custom on top of shadcn primitives.

## Functional Requirements (original floor — still required)

- FR-1: `ZoneMap.tsx` — Leaflet map, zones color-coded by predicted
  demand/fare, clickable for detail (UC-1).
- FR-2: `ChatPanel.tsx` — chat UI for `/chat`, shows the SQL query when the
  answer came from the NL-to-SQL path (transparency — matches ADR-004).
- FR-3: `ModelComparisonChart.tsx` — bar/line chart of the 4-model
  RMSE/MAE from `metrics_report.md` via a backend endpoint (UC-2).
- FR-4: `App.tsx` — routed layout tying pages together (see FR-5+).

## Functional Requirements (rescoped additions)

- FR-5: Persistent collapsible sidebar (Dashboard, Demand Forecast, Fare
  Prediction, NYC Map, AI Analyst, Models, Algorithms, Data Pipeline,
  Warehouse, Experiments, Documentation, Settings) + top navbar (project
  name, search, notifications, refresh data, theme toggle, user menu,
  current dataset / last updated).
- FR-6: Dashboard landing page — KPI cards (current demand, average fare,
  active zones, trips today, prediction accuracy, data freshness, latest
  pipeline run, system health), all backed by real backend/warehouse
  values, none hardcoded.
- FR-7: Analytics charts — demand over time, fare trend, hourly
  distribution, weekday heatmap, model comparison, zone rankings, top
  routes, forecast confidence. Interactive: tooltips, legend, loading
  state per chart.
- FR-8: Zone detail side panel on map click — name, borough, current/
  predicted demand, historical trend, peak hour, avg fare, top
  destination, PageRank score, nearest zones (KD-tree/geohash), forecast,
  AI-generated insight text (from `rag/insight_generation`).
- FR-9: AI Analyst page — chat with suggested questions, conversation
  history, and per-answer transparency (generated SQL, retrieved context,
  route taken, execution time, referenced tables) — matches ADR-004's
  auditability requirement, not cosmetic.
- FR-10: Model Center — compare linear/EWMA/XGBoost/LSTM: RMSE, MAE,
  inference latency, feature importance, loss curves, prediction
  examples, all pulled from each model's real metadata JSON sidecar
  (`models/*/*.json`) — MAPE/training-time/model-size only if actually
  recorded there; do not fabricate a metric no artifact captured.
- FR-11: Algorithms page — KD-tree, PageRank, Dijkstra, EWMA,
  seasonality: explanation + the actual benchmark numbers/plots each
  algorithm module already produced (e.g. KD-tree's measured 5.17x
  speedup, PageRank's convergence-matched hub rankings).
- FR-12: Data Pipeline page — visual stage diagram (parquet → DuckDB →
  dbt → algorithms → features → models → API → frontend), each stage
  clickable showing status/duration/last-run/rows if that metadata is
  actually available; a static diagram with real per-stage facts is
  acceptable if live run telemetry doesn't exist yet — do not invent
  numbers for stages with no instrumentation.
- FR-13: Warehouse explorer — schemas/tables/views/columns/row counts via
  a real backend endpoint reading DuckDB's `information_schema` (or
  equivalent), not hardcoded. No raw SQL editor (explicitly out of scope
  per the owner).
- FR-14: Experiments page — one row per trained model run, sourced from
  each model's real metadata JSON (params, metrics, date range, seed) —
  commit hash only if actually captured by the training scripts; don't
  add new instrumentation to models/ for this (out of this spec's scope,
  flag it instead if wanted).
- FR-15: Documentation page — renders `docs/architecture/`, `docs/adr/`,
  `specs/`, `project_plan.md`, and `README.md` as in-app rendered
  markdown.
- FR-16: Settings page — theme, prediction units, map defaults, refresh
  frequency, developer mode. Local-only (localStorage), no backend
  persistence needed unless already planned elsewhere.

## UI Design

8px spacing system, neutral grayscale (white/slate/zinc) + single blue
accent + status colors (success/warning/error/info) — no gradients,
glassmorphism, or neumorphism. Desktop-first responsive, then
tablet/mobile. Every data-bearing component needs loading skeleton, empty
state, error state, and success state — no exceptions, this is the
existing floor requirement (see original UI Design section) extended to
every new page, not just the original 3 components.

## Non-Functional Requirements

Code splitting + lazy loading per route, memoization where it measurably
helps (not reflexively), React Query for all server-state caching,
virtualized tables for the warehouse/experiments pages if row counts
warrant it. No placeholder pages and no fake/mock data anywhere — every
page must read real backend or artifact data; a page whose backing data
doesn't exist yet should be visibly marked "not yet available" rather than
faked.

## Testing

Manual verification against the golden path per page (per top-level Claude
Code guidance — UI changes verified in a running browser). Golden paths:
click a zone → see prediction + insight panel; ask a numeric question →
grounded number + SQL shown; ask an explanatory question → grounded answer
with retrieved context shown; open Model Center → real metrics from JSON
sidecars; open Algorithms page → real benchmark numbers.

## Acceptance Criteria

- [ ] All components/pages render real backend or artifact data — no mock
      data left in anywhere.
- [ ] Loading/empty/error states present on every data-bearing component.
- [ ] Sidebar + navbar present and functional (collapse, theme toggle,
      search, refresh).
- [ ] Dashboard, Demand Forecast, Fare Prediction, NYC Map + zone panel,
      AI Analyst, Model Center, Algorithms, Data Pipeline, Warehouse,
      Experiments, Documentation, Settings all present and wired to real
      data (or explicitly marked unavailable where no data source exists
      yet).
- [ ] Golden paths manually verified in a running dev server.
- [ ] TypeScript migration complete, no remaining `.jsx` in `frontend/src`.

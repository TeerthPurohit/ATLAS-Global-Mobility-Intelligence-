# DESIGN.md — Enterprise Product & Design Specification

**System**: NYC Ride Intelligence Platform  
**Target Persona**: Staff Data Engineers, Principal ML Engineers, Platform Architects, Lead Analytics Engineers  
**Visual Benchmark**: Linear · Databricks · Snowflake · Stripe Dashboard · Vercel · MLflow · Weights & Biases · Palantir Foundry  
**Document Version**: 3.1.0 (Comprehensive Enterprise Product Specification)

> **2026-08-06 audit note**: A full frontend architecture audit
> (`ARCHITECTURE_AUDIT.md`) found this document's zero-fabrication and
> total-provenance principles below were, at the time, aspirational rather
> than actually enforced — roughly half the widgets across the app were
> hardcoded, three were outright fabricated from a real value, and two
> cited artifact files that didn't exist. That audit's findings have since
> been fixed (real backend endpoints added, real artifacts generated, the
> fabricated chart deleted). Sections 14 and 16 below have been corrected
> to match what's actually built — a global command-palette search was
> never implemented and has been removed from the nav bar rather than left
> as a non-functional stub; do not re-add it without also building it.

> **2026-08-30 theme note**: Sections 04 (Visual Language), 10 (Color
> Tokens), and 40 (Dark Theme) below describe a slate/obsidian dark
> enterprise palette that was never actually shipped — the real token
> system in `frontend-web/app/globals.css` was a "parchment/brass" theme,
> dark by default. Per direct user request, the app was reskinned to a
> **light-primary** theme: lavender canvas (`--surface-0`), white cards
> (`--surface-1`), and an indigo/teal/coral accent triad (`--brass`
> repurposed as the indigo primary accent `#6c5ce7`, `--verdigris` as teal
> success `#14b8a6`, `--oxide` as coral danger `#f2545b`), plus
> `--chart-sky` / `--chart-amber` / `--chart-pink` for bento-style KPI
> tiles. Dark mode still exists as an opt-in fallback via
> `data-theme="dark"`. `globals.css` is the source of truth; sections
> 04/10/40's specific hex values below are historical and not current.

---

## Table of Contents

01. [Philosophy](#01-philosophy)  
02. [Product Vision](#02-product-vision)  
03. [Design Principles](#03-design-principles)  
04. [Visual Language](#04-visual-language)  
05. [Information Density](#05-information-density)  
06. [Surface Hierarchy](#06-surface-hierarchy)  
07. [Layout Grid](#07-layout-grid)  
08. [Spacing System](#08-spacing-system)  
09. [Typography](#09-typography)  
10. [Color Tokens](#10-color-tokens)  
11. [Elevation](#11-elevation)  
12. [Motion](#12-motion)  
13. [Navigation](#13-navigation)  
14. [Search](#14-search)  
15. [Sidebar](#15-sidebar)  
16. [Top Navigation](#16-top-navigation)  
17. [Command Palette](#17-command-palette)  
18. [Documentation Reader](#18-documentation-reader)  
19. [Dashboard Rules](#19-dashboard-rules)  
20. [KPI Cards](#20-kpi-cards)  
21. [Analytics Cards](#21-analytics-cards)  
22. [Data Tables](#22-data-tables)  
23. [Charts](#23-charts)  
24. [Maps](#24-maps)  
25. [AI Chat](#25-ai-chat)  
26. [SQL Results](#26-sql-results)  
27. [Warehouse Explorer](#27-warehouse-explorer)  
28. [Pipeline Explorer](#28-pipeline-explorer)  
29. [Model Registry](#29-model-registry)  
30. [Experiment Tracking](#30-experiment-tracking)  
31. [Algorithm Visualizer](#31-algorithm-visualizer)  
32. [Feature Store](#32-feature-store)  
33. [Lineage Graph](#33-lineage-graph)  
34. [Empty States](#34-empty-states)  
35. [Loading States](#35-loading-states)  
36. [Error States](#36-error-states)  
37. [Skeletons](#37-skeletons)  
38. [Accessibility](#38-accessibility)  
39. [Mobile](#39-mobile)  
40. [Dark Theme](#40-dark-theme)  
41. [Animation](#41-animation)  
42. [Interaction Patterns](#42-interaction-patterns)  
43. [Component Catalog](#43-component-catalog)  
44. [Visual QA Checklist](#44-visual-qa-checklist)  
45. [Enterprise Quality Checklist](#45-enterprise-quality-checklist)  

---

## 01 Philosophy

The NYC Ride Intelligence Platform is an enterprise-grade data engineering, spatial graph analytics, and machine learning system. The visual and structural design must embody **uncompromising precision, radical transparency, technical authority, and dense utility**.

Enterprise software must never behave like a generic admin template, a consumer marketing page, or a superficial UI prototype. It must feel like specialized tools built for staff engineers and analytical professionals—software that treats raw code, mathematical formulas, SQL schemas, vector indices, model binaries, and telemetry lineage as first-class UI citizens.

Every visual element must answer three fundamental engineering questions:
1. **What is the exact data source of this number or visual?**
2. **What pipeline, model version, or SQL mart produced it?**
3. **What is its current execution latency and confidence state?**

---

## 02 Product Vision

To deliver a unified, interactive workspace for end-to-end data lifecycle management across NYC High Volume For-Hire Vehicle (HVFHV) trip datasets. The platform bridges raw Parquet ingestion, dbt analytical warehousing, spatial KD-Tree indexing, directed graph PageRank hub evaluation, XGBoost demand and fare modeling, and hybrid RAG conversational intelligence into a seamless, high-density dashboard experience.

---

## 03 Design Principles

1. **Enterprise Data Integrity (Zero Fabrication)**  
   No hardcoded gimmicks, fake metrics, synthetic random walk charts, or decorative approximations. If backend data is unavailable or loading, components MUST render explicit `Awaiting Backend Response` or `Telemetry Unavailable` states. Software never lies.

2. **Total Provenance & Traceability**  
   Every chart, metric card, map overlay, table, and intelligence output must contain a standardized data provenance footer identifying its origin (`Precomputed Model Artifact`, `Materialized dbt Mart`, `DuckDB Warehouse`, `Live API Response`).

3. **High Information Density with Clear Visual Hierarchy**  
   Maximize useful information density per square pixel without visual fatigue. Utilize a crisp 1px micro-border system, muted slate container fills, high-contrast semantic accents, and structured monospace data alignment.

4. **Code & Math as First-Class Citizens**  
   Monospace typography (`JetBrains Mono` / `SF Mono`) is enforced systematically for SQL statements, model hyperparameter hashes, zone LocationIDs, execution latencies, schema types, and vector similarity scores.

5. **Keyboard-First Efficiency**  
   Provide global hotkeys (`⌘K` Command Palette, `⌘B` Sidebar Toggle, `/` Search Focus) enabling power users to navigate pipelines, query schemas, and trigger model inferences without leaving the keyboard.

---

## 04 Visual Language

The visual system uses a sophisticated dark obsidian visual theme built upon deep Slate surfaces, precision 1px borders, subtle 2px accent highlights, and monospace telemetry badges.

- **Theme Baseline**: Deep Slate Canvas (`#020617` / `bg-slate-950`) paired with Surface-1 Slate (`#0f172a` / `bg-slate-900`).
- **Border Architecture**: Hairline 1px borders (`border-slate-800` / `#1e293b`) with interactive focus rings (`ring-brand-500/30`).
- **Surface Elevation**: Tiered depth model separating low-contrast background grid lines from sharp foreground cards.

---

## 05 Information Density

To accommodate complex telemetry without UI clutter, components adhere to strict density tokens:

- **Compact Grid Spacing**: 16px default container padding, 12px internal card padding.
- **Micro Typography**: 10px tracking-wide uppercase labels for metadata headers; 12px monospace for tabular values.
- **Dense Data Rows**: 36px table row height (`py-2 px-3`) for scannable data inspection.
- **Inline Badges**: Monospace status indicators with 1px border frames and 10% opacity fill tints.

---

## 06 Surface Hierarchy

A strict 4-tier surface elevation system establishes structural clarity:

| Elevation Level | Token Name | Hex Code | Tailwind Class | Usage Context |
|---|---|---|---|---|
| **Level 0 (Canvas)** | Base Background | `#020617` | `bg-slate-950` | Full-screen app canvas and main layout body |
| **Level 1 (Card Surface)** | Primary Surface | `#0f172a` | `bg-slate-900` | KPI cards, analytics panels, data tables, map sidebars |
| **Level 2 (Sub-Surface)** | Inset Container | `#090d16` | `bg-slate-950/80` | Inner metrics containers, code blocks, parameter forms |
| **Level 3 (Interactive Overlay)** | Floating Surface | `#1e293b` | `bg-slate-800` | Dropdown menus, tooltips, command palettes, modal dialogs |

---

## 07 Layout Grid

- **Global Shell**: Fixed left navigation sidebar (256px expanded, 64px collapsed) + fixed top navigation header (64px height) + flexible main viewport content area.
- **Dashboard Grid**: 12-column fluid grid system using CSS Grid (`grid-cols-1 md:grid-cols-2 lg:grid-cols-4 xl:grid-cols-12 gap-4`).
- **Max Content Width**: `max-w-7xl` for analytical dashboards; `max-w-6xl` for documentation reader views; `h-[calc(100vh-4rem)]` full-bleed overflow control for GIS maps and AI chat views.

---

## 08 Spacing System

Strict adherence to a 4px modular spacing scale:

```css
--space-1:  4px;   /* gap-1, p-1 */
--space-2:  8px;   /* gap-2, p-2 */
--space-3: 12px;   /* gap-3, p-3 */
--space-4: 16px;   /* gap-4, p-4 */
--space-6: 24px;   /* gap-6, p-6 */
--space-8: 32px;   /* gap-8, p-8 */
```

---

## 09 Typography

Dual-font stack pairing **Inter** (humanist UI sans-serif) with **JetBrains Mono** (precision monospace).

| Hierarchy Role | Font Family | Weight | Size / Line Height | Tailwind Class | Primary Usage |
|---|---|---|---|---|---|
| **Display Header** | Inter | Bold (700) | 24px / 32px | `text-2xl font-bold tracking-tight text-slate-100` | Dashboard hero title |
| **Page Header** | Inter | Bold (700) | 18px / 24px | `text-lg font-bold text-slate-100` | Section top headers |
| **Card Header** | Inter | SemiBold (600) | 14px / 20px | `text-sm font-semibold text-slate-200` | Card titles, modal headers |
| **Body Standard** | Inter | Regular (400) | 12px / 18px | `text-xs text-slate-300 leading-relaxed` | Descriptive prose, RAG answers |
| **Micro Tag** | Inter | Bold (700) | 10px / 14px | `text-[10px] font-bold uppercase tracking-wider` | Category pills, table TH |
| **Data Value (Mono)** | JetBrains Mono | Medium (500) | 12px / 16px | `font-mono text-xs text-slate-200` | Latencies, row counts, fares |
| **KPI Display (Mono)**| JetBrains Mono | ExtraBold (800)| 28px / 36px | `font-mono text-3xl font-extrabold text-slate-100`| Hero KPI numeric figures |

---

## 10 Color Tokens

### Foundational Palette (Slate)
- `bg-slate-950` (`#020617`): Primary app backdrop.
- `bg-slate-900` (`#0f172a`): Card container background.
- `bg-slate-800` (`#1e293b`): Sub-surface hover state & card borders.
- `text-slate-100` (`#f8fafc`): Primary high-contrast text.
- `text-slate-400` (`#94a3b8`): Secondary metadata labels.
- `text-slate-500` (`#64748b`): Tertiary placeholders & micro captions.

### Accent & Semantic Tokens
- **Brand Primary Blue**: `#0c93eb` (`brand-500`) / `#0074ca` (`brand-600`) — Active routes, primary CTA buttons, focus rings.
- **Success Emerald**: `#10b981` (`emerald-500`) — Online connections, passed tests, positive trend deltas, XGBoost best status.
- **Warning Amber**: `#f59e0b` (`amber-500`) — Dataset month gaps (Feb/Apr/May missing), rate limit notices.
- **Danger Red**: `#ef4444` (`red-500`) — API connection failures, SQL validation rejections, missing model artifacts.
- **Info Indigo**: `#6366f1` (`indigo-500`) — Model ladder identifiers, PageRank hub scores, spatial indexing.

---

## 11 Elevation

Depth is communicated through 1px border contrast and ambient glow shadows rather than heavy drop shadows:

- **Flat Container**: `border border-slate-800 bg-slate-900`
- **Hover Card**: `border border-slate-700 hover:border-slate-600 transition-all`
- **Active / Selected Card**: `border-brand-500 ring-2 ring-brand-500/30 shadow-lg shadow-brand-500/10`
- **Floating Modal / Palette**: `bg-slate-900/95 backdrop-blur-md border border-slate-700 shadow-2xl shadow-black/80`

---

## 12 Motion

Transitions are functional, fast, and subtle:

- **Duration Token**: `duration-150` or `duration-200` ease-in-out.
- **Sidebar Collapse**: Smooth horizontal width transition (`transition-all duration-200`).
- **Hover Micro-scaling**: Subtle transform (`hover:scale-[1.01] active:scale-[0.99]`).
- **Telemetry Pulse**: `animate-pulse` restricted exclusively to active websocket connections and live API streaming.

---

## 13 Navigation

Navigation is multi-tiered:
1. **Primary Left Sidebar**: Persistent structural view switching (Overview, AI & Intelligence, Data Engineering, Platform).
2. **Top Navigation Header**: Contextual breadcrumb path, global search input, workspace selector, and user profile pill.
3. **In-Page Sub-Tabs**: Horizontal pill tabs for view switching within complex views (e.g. Documentation, Model Center).

---

## 14 Search

**Not implemented.** The nav bar previously had a non-functional search
input with a `⌘K` hint and no handler; it has been removed rather than
left as dead chrome (see 2026-08-06 audit note above). A global search
across zones/models/SQL/docs remains a legitimate future feature, but
requires an actual search index (client-side fuzzy match over `/zones`
plus model/doc metadata) before it should reappear in the UI — don't add
the input back without the logic behind it.

---

## 15 Sidebar

- **Dimensions**: Expanded 256px (`w-64`), Collapsed 64px (`w-16`).
- **Sections**:
  - `Overview`: Dashboard, NYC Map GIS, Demand Forecast, Fare Prediction.
  - `AI & Intelligence`: Hybrid RAG Analyst, Model Center, Algorithms.
  - `Data Engineering`: Data Pipeline, Warehouse, Experiments.
  - `Platform`: Documentation, Settings.
- **Footer**: Live telemetry connection indicator showing DuckDB & Qdrant connectivity.

---

## 16 Top Navigation

- **Height**: 64px (`h-16`), sticky top, border-b `border-slate-800`.
- **Breadcrumbs**: Hierarchical section and title breadcrumb (e.g. `Overview / Executive Dashboard`).
- **Dataset Status**: Pill indicator displaying `TLC HVFHV 2024 (Jan/Mar/Jun)`; its pulse dot reflects real `GET /health` status, not a decorative always-on animation.
- **Actions**: Refresh button that calls `queryClient.invalidateQueries()` (real, refetches every active page's data). The notification bell has been removed — it was decorative chrome with no backing feature; don't re-add it without an actual notification source.

---

## 17 Command Palette

**Not implemented** — same status as section 14. This section describes a
future feature, not current behavior. Build both together if picked up.

---

## 18 Documentation Reader

Stripe/Notion-grade documentation viewer for architecture standards:
- 3-column layout: Categorized Index (left) + Article Reader (center) + Sticky Table of Contents (right).
- Features code copy blocks, syntax highlighting, and admonition callout boxes (`Note`, `Tip`, `Warning`).

---

## 19 Dashboard Rules

All dashboards MUST adhere to:
1. **No Synthetic Numbers**: Every metric must map to DuckDB tables, model files, or live API responses.
2. **Provenance Footers**: Every card must state its backing data store or model artifact in its footer.
3. **Explicit Loading**: Skeletons must be displayed while async backend queries execute.

---

## 20 KPI Cards

KPI Cards communicate high-level operational metrics:
- **Top Bar**: Category Label (12px text-slate-400) + Icon Container (28px with 10% accent tint).
- **Metric Center**: Monospace ExtraBold Value Display (28px text-slate-100).
- **Subtext / Delta**: Subtext pill indicating temporal range or model baseline.
- **Footer Provenance Tag**: Monospace micro footer stating data store (e.g. `DuckDB: stg_trips`).

---

## 21 Analytics Cards

Larger containers holding charts and comparative telemetry:
- Header with title, subtitle, and table source badge.
- Recharts visualization area.
- Monospace analytical summary footer callout.

---

## 22 Data Tables

Compact, scannable data inspection tables:
- **Header**: Sticky top, `bg-slate-950 border-b border-slate-800 text-[10px] uppercase font-bold tracking-wider text-slate-400`.
- **Rows**: 36px height (`py-2 px-3`), hover state `hover:bg-slate-800/40`.
- **Cells**: Monospace font for numerical columns, zone IDs, fares, and timestamps.

---

## 23 Charts

Built using Recharts with dark obsidian customization:
- **Grid Lines**: `stroke="#1e293b"` (1px dashed).
- **Axes**: Monospace labels `stroke="#64748b" fontSize={11}`.
- **Tooltip**: `bg-slate-900 border-slate-700 text-slate-100 rounded-lg shadow-xl`.
- **Gradients**: Area fills with 40% to 0% opacity vertical gradients.

---

## 24 Maps

NYC Leaflet GIS integration:
- **Base Tile**: Dark CARTO CartoDB map tile layer (`dark_all`).
- **Zone Markers**: Circle markers color-coded by NYC Borough (Manhattan `#0c93eb`, Queens `#10b981`, Brooklyn `#8b5cf6`, Bronx `#f59e0b`, Staten Island `#ef4444`).
- **Interactive Inspector**: Floating side drawer showing zone centroid coordinates, KD-tree status, and model forecast.

---

## 25 AI Chat

Hybrid RAG conversational interface:
- **Message Feed**: Message bubbles distinguished by role (`user` right-aligned blue bubble, `assistant` left-aligned dark card).
- **Route Badges**: Visual pill indicating intent path (`NL-to-SQL Path` vs `Vector Retrieval Path`).
- **Collapsible SQL Drawer**: Interactive drop-down displaying exact executed DuckDB SQL code.

---

## 26 SQL Results

Databricks-style SQL result renderer:
- Displays query text in syntax-highlighted code block.
- Renders row results in scrollable monospace grid.
- Includes execution latency (`34 ms`) and affected row count badges (`8,240,117 rows`).

---

## 27 Warehouse Explorer

Interactive schema browser for DuckDB analytical marts:
- Left selector list featuring dbt marts (`zone_hourly_demand`, `zone_fare_stats`, `int_trips_enriched`).
- Schema details table listing Column Name, SQL Data Type, and Business Description.

---

## 28 Pipeline Explorer

Databricks / Prefect style interactive execution DAG:
- 6-stage horizontal node flow (Raw Ingestion → dbt Cleansing → Analytics Marts → Spatial/Graph Algs → Model Training → FastAPI Serving).
- Interactive telemetry inspector showing stage duration, input/output files, and CLI execution commands.

---

## 29 Model Registry

MLflow / HuggingFace style model registry:
- Grid of trained model cards (EWMA, Linear, PyTorch LSTM, XGBoost Demand, XGBoost Fare).
- Displays holdout test set metrics (RMSE, MAE), hyperparameters, and feature importance bar charts.

---

## 30 Experiment Tracking

Comparative tabular log of model training iterations:
- Table displaying Run ID (`EXP-001` .. `EXP-005`), Architecture, Test RMSE, Test MAE, Chrono Split strategy, and Selection Status.

---

## 31 Algorithm Visualizer

Detailed benchmark cards for from-scratch algorithms:
- **KD-Tree**: Measured speedup gauge (5.17x faster than linear scan).
- **PageRank**: Top network hub score rankings (JFK, LGA, Crown Heights).
- **Dijkstra**: Priority queue travel time routing benchmark.
- **EWMA**: Multiplicative 24h seasonality decomposition.

---

## 32 Feature Store

Catalog of precomputed model features:
- Lists feature names (`lag_1h`, `lag_24h`, `rolling_7d_avg`), data types, source dbt mart, and update frequency.

---

## 33 Lineage Graph

End-to-end data provenance graph tracing data flow from raw Parquet files through dbt models and feature stores to trained XGBoost model binaries and served API endpoints.

---

## 34 Empty States

Rendered when queries return 0 results:
- Centered layout featuring muted icon, informative heading, explanatory subtext, and clear primary CTA button.

---

## 35 Loading States

Indicates background processing:
- Pulsing activity spinner (`animate-spin text-brand-400`) accompanied by explicit status message (e.g. `Querying DuckDB analytical mart...`).

---

## 36 Error States

Displayed during API or validation failures:
- Warning box tinted in Red/Amber (`bg-red-500/10 border-red-500/20 text-red-400`).
- Provides exact error details and a retry CTA trigger.

---

## 37 Skeletons

Async loading placeholder masks:
- Shimmering gradient rectangles (`bg-slate-800/60 animate-pulse rounded-lg`) mirroring exact component dimensions during data fetch.

---

## 38 Accessibility

- **Contrast Ratios**: Minimum 4.5:1 contrast for body text against dark backgrounds.
- **Focus Indicators**: 2px visible focus ring (`focus:outline-none focus:ring-2 focus:ring-brand-500/40`) on all interactive controls.
- **ARIA Attributes**: Proper `aria-expanded`, `aria-selected`, and semantic HTML headings (`h1`-`h4`).

---

## 39 Mobile

Responsive grid adapting to viewports:
- Mobile breakpoint (`<768px`) collapses sidebar into touch drawer and stacks multi-column grids into single-column layouts.

---

## 40 Dark Theme

Dedicated Enterprise Slate Dark Theme built on deep obsidian tones (`#020617`), slate surfaces (`#0f172a`), hairline borders (`#1e293b`), and vibrant brand blue accents (`#0c93eb`).

---

## 41 Animation

Restricted to high-utility micro-interactions:
- Button active scale click effect (`active:scale-[0.98]`).
- Smooth tab switching indicator transitions.
- Websocket streaming pulse animation.

---

## 42 Interaction Patterns

- **Form Submit**: Disables submit button during async execution and displays spinner.
- **Collapsible Panes**: Chevron toggle buttons preserving state.
- **Copy Buttons**: Instant visual checkmark feedback upon copying code snippets.

---

## 43 Component Catalog

Library of core reusable visual primitives:
- `MetricCard`: KPI display with subtext and provenance tag.
- `AnalyticsCard`: Container for charts with header actions.
- `ProvenanceFooter`: Standardized metadata bar stating data lineage.
- `Badge`: Status and category pills with 10% fill tints.
- `CodeBlock`: Syntax-highlighted block with copy button.

---

## 44 Visual QA Checklist

- [x] All background surfaces match 4-tier elevation tokens (`bg-slate-950`, `bg-slate-900`, `bg-slate-950/80`).
- [x] Hairline borders (`border-slate-800`) used consistently across cards and headers.
- [x] Typography strictly obeys font stack (Inter for labels, JetBrains Mono for data/code).
- [x] Focus rings display crisp 2px brand blue rings on keyboard focus.
- [x] Hover states transition smoothly within 150-200ms duration.

---

## 45 Enterprise Quality Checklist

- [x] Zero hardcoded mock metrics presented as live telemetry — verified 2026-08-06 against `ARCHITECTURE_AUDIT.md`; every KPI/chart/table now reads from `GET /health`, `/dashboard/summary`, `/warehouse/stats`, `/warehouse/tables`, `/models/metrics`, `/marts/zone_hourly_demand`, `/algorithms/benchmarks`, `/pipeline/status`, `/zones`, `/predict/*`, or `/chat`.
- [x] Every chart, card, and table includes explicit data provenance footers.
- [x] Missing backend endpoints display explicit `Awaiting Backend Response` / `Unavailable` states.
- [x] Monospace formatting enforced on all SQL, JSON, latencies, model hashes, and zone IDs.
- [x] System verified against full-viewport responsive layouts and dark theme standards.
- [ ] Global search (section 14) and command palette (section 17) remain unbuilt — don't check these off until the logic exists, not just the input box.

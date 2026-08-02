# Project Plan — NYC TLC Ride Intelligence Platform

> **Execution playbook.** This is the granular, step-by-step companion to the master
> [`/project_plan.md`](../project_plan.md) at the repo root. The root doc explains the *why*
> (concepts, math, interview framing) layer by layer; **this doc is the *how*** — exact
> commands, file targets, and a "Definition of Done" you can tick off before moving on.
>
> **Golden rule:** phases are dependencies, not parallel tracks. Do not start a phase until the
> previous phase's *Definition of Done* is fully green. Algorithms need marts; models need
> algorithm outputs; RAG needs model + mart outputs; serving needs everything.

---

## Actual Tech Stack (as pinned in this repo)

Grounded in [`requirements.txt`](../requirements.txt) and [`.env.example`](../.env.example) — use these, not substitutes:

| Layer | Technology | Package(s) |
|-------|-----------|------------|
| Warehouse | DuckDB (in-process OLAP) | `duckdb` |
| Transform | dbt | `dbt-core`, `dbt-duckdb` |
| Spatial | Shapely + geohash | `shapely`, `geohash2` |
| Time-series | statsmodels | `statsmodels`, `numpy`, `pandas` |
| ML | scikit-learn, XGBoost | `scikit-learn`, `xgboost` |
| DL | PyTorch (LSTM) | `torch` |
| RAG / NL→SQL | OpenAI + LangChain + Chroma | `openai`, `langchain`, `langchain-community`, `chromadb` |
| Backend | FastAPI + Uvicorn | `fastapi`, `uvicorn[standard]`, `pydantic` |
| Frontend | React (Vite) | see [`frontend/package.json`](../frontend/package.json) |
| Viz / Dev | matplotlib, seaborn, Jupyter, pytest | `matplotlib`, `seaborn`, `jupyter`, `pytest`, `httpx` |

> ⚠️ The root plan mentions "Gemini" for the RAG layer. **This repo is wired for OpenAI + LangChain + ChromaDB.**
> Set `OPENAI_API_KEY` in `.env`. If you deliberately switch providers, update `requirements.txt`, `.env.example`, and this table together.

---

## Phase 0 — Environment & Repository Setup

**Goal:** a reproducible local environment where every later command "just works."

### Steps
1. **Create and activate a virtual environment** (Windows PowerShell):
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   python -m pip install --upgrade pip
   ```
2. **Install dependencies:**
   ```powershell
   pip install -r requirements.txt
   ```
3. **Create your local env file** from the template and fill in `OPENAI_API_KEY`:
   ```powershell
   Copy-Item .env.example .env
   ```
4. **Confirm the folder skeleton exists** (it already does in this repo — verify, don't recreate):
   `data/{raw,lookup,warehouse}`, `dbt_project/`, `algorithms/`, `models/`, `rag/`, `backend/`, `frontend/`, `notebooks/`, `docs/`, `tests/`.
5. **Add a `scripts/` folder** for one-off ingestion utilities (not tracked in the tree yet).

### Definition of Done
- [ ] `python -c "import duckdb, dbt, xgboost, torch, fastapi, chromadb; print('ok')"` prints `ok`.
- [ ] `.env` exists locally (gitignored) with a working `OPENAI_API_KEY`.
- [ ] `dbt --version` shows `dbt-duckdb` as an installed adapter.

---

## Phase 1 — Data Ingestion

**Goal:** ~3 months (~8–10M rows) of NYC TLC **HVFHV** (High Volume For-Hire Vehicle — the Uber/Lyft dataset, *not* yellow taxi) sitting cleanly in DuckDB, joined to the zone lookup.

> A sample already exists: [`data/raw/fhvhv_tripdata_2024_8m_sample.parquet`](../data/raw/fhvhv_tripdata_2024_8m_sample.parquet). Use it to develop the pipeline before downloading the full 3 months.

### Steps
1. **Download 3 consecutive months** of `fhvhv_tripdata_YYYY-MM.parquet` from the TLC Trip Record Data page into `data/raw/`.
2. **Download the zone lookup** `taxi_zone_lookup.csv` (columns: `LocationID`, `Borough`, `Zone`, `service_zone`) into `data/lookup/` **and** copy it to `dbt_project/seeds/` for dbt.
3. **Write `scripts/load_raw_to_duckdb.py`** — let DuckDB read parquet natively (no pandas round-trip for the big load):
   ```python
   import duckdb, os
   con = duckdb.connect(os.environ.get("DUCKDB_PATH", "data/warehouse/nyc_rides.duckdb"))
   con.execute("""
       CREATE OR REPLACE TABLE raw_trips AS
       SELECT * FROM read_parquet('data/raw/fhvhv_tripdata_*.parquet');
   """)
   con.execute("""
       CREATE OR REPLACE TABLE raw_zones AS
       SELECT * FROM read_csv_auto('data/lookup/taxi_zone_lookup.csv');
   """)
   print(con.execute("SELECT COUNT(*) FROM raw_trips").fetchone())
   ```
4. **Run it** and record the row count.
5. **Spot-check known TLC data issues** with quick SQL: nulls in `PULocationID`/`DOLocationID`, negative `trip_miles`, timestamps outside the expected month range.

### Definition of Done
- [x] `raw_trips` row count is in the 8–10M target range (or matches the sample while developing).
- [x] `raw_zones` has ~265 rows with `LocationID`, `Borough`, `Zone`, `service_zone`.
- [x] DuckDB file in `data/warehouse/` is a few GB at most (laptop-manageable).
- [x] You can state in one paragraph *why DuckDB* (in-process, vectorized, reads Parquet natively — columnar OLAP vs. row-store Postgres). Draft it straight into the README.

---

## Phase 2 — dbt Transformation (staging → intermediate → marts)

**Goal:** raw rows → clean, tested, query-ready marts that every later layer reads from. Files already scaffolded under [`dbt_project/models/`](../dbt_project/models/).

### Steps
1. **Configure the DuckDB profile** in [`dbt_project/profiles.yml`](../dbt_project/profiles.yml) to point at `data/warehouse/nyc_rides.duckdb`.
2. **Seed the lookup:** `dbt seed` (loads `taxi_zone_lookup.csv`).
3. **Staging — light cleaning only** ([`stg_trips.sql`](../dbt_project/models/staging/stg_trips.sql), [`stg_zones.sql`](../dbt_project/models/staging/stg_zones.sql)): cast types, snake_case renames, drop clearly broken rows. No business logic here.
4. **Intermediate — enrichment** ([`int_trips_enriched.sql`](../dbt_project/models/intermediate/int_trips_enriched.sql)): join trips → zones; derive `hour_of_day`, `day_of_week`, `is_weekend`, `trip_duration_minutes`, `avg_speed_mph`.
5. **Marts — business questions:**
   - [`zone_hourly_demand.sql`](../dbt_project/models/marts/zone_hourly_demand.sql) — `GROUP BY zone, date, hour` → pickup counts. **This is the ML target variable — get it right; everything downstream depends on it.**
   - [`zone_fare_stats.sql`](../dbt_project/models/marts/zone_fare_stats.sql) — avg/median/percentile fares per zone-hour.
   - [`zone_pair_flows.sql`](../dbt_project/models/marts/zone_pair_flows.sql) — `GROUP BY PULocationID, DOLocationID` → trip counts. **Feeds the graph layer.**
6. **Add tests** in the `schema.yml` files + [`tests/assert_positive_fares.sql`](../dbt_project/tests/assert_positive_fares.sql): `not_null` on zone IDs, `accepted_range` on fares (>0, < sane ceiling), a relationship test from trips → zone lookup.
7. **Build & test:**
   ```powershell
   dbt build          # runs models + tests in dependency order
   dbt docs generate  # screenshot the lineage graph for the README
   ```

### Definition of Done
- [ ] `dbt build` completes with **0 failures**.
- [ ] All three marts materialize and return sane row counts.
- [ ] You can explain the staging/intermediate/marts split and justify whether `zone_hourly_demand` is incremental vs. full-refresh.
- [ ] Lineage graph screenshot saved for the README.

---

## Phase 3 — Algorithmic Showpieces (spatial + graph + time-series)

**Goal:** three *from-scratch* algorithm implementations you can fully explain — not opaque library calls. Files under [`algorithms/`](../algorithms/).

### 3A. Spatial — KD-tree nearest-zone lookup
1. [`kdtree_zone_lookup.py`](../algorithms/spatial/kdtree_zone_lookup.py): build a KD-tree from scratch over the ~265 zone centroids; implement nearest-neighbor query with branch pruning.
2. Benchmark linear scan `O(n)` vs. KD-tree `O(log n)` over repeated queries; validate against `scipy.spatial.KDTree`.
3. [`geohash_grid.py`](../algorithms/spatial/geohash_grid.py): encode centroids to geohash strings; demonstrate prefix-matching for "nearby zones" (know the boundary edge-effect limitation).

### 3B. Graph — zone network
1. [`build_zone_graph.py`](../algorithms/graph/build_zone_graph.py): read `zone_pair_flows` → weighted directed graph (networkx for structure).
2. [`pagerank_hubs.py`](../algorithms/graph/pagerank_hubs.py): implement PageRank via power iteration; validate against `nx.pagerank`.
3. [`shortest_path_eta.py`](../algorithms/graph/shortest_path_eta.py): Dijkstra with edge weight = avg trip duration between zone pairs → graph-based ETA feature.

### 3C. Time-series
1. [`ewma_smoothing.py`](../algorithms/timeseries/ewma_smoothing.py): EWMA from scratch over `zone_hourly_demand` (`S_t = α·x_t + (1−α)·S_{t−1}`).
2. [`seasonality_decompose.py`](../algorithms/timeseries/seasonality_decompose.py): decompose each zone's series into trend + daily/weekly seasonality + residual; validate against `statsmodels.seasonal_decompose`.
3. Plot decomposition for 2–3 contrasting zones (airport / nightlife / residential) → portfolio screenshot.

### Definition of Done
- [ ] Each from-scratch algorithm's output matches its library counterpart within tolerance.
- [ ] KD-tree benchmark plot shows the `O(log n)` win.
- [ ] Seasonality decomposition plots saved for 2–3 zones.
- [ ] You can explain, unprompted: KD-tree pruning, PageRank power iteration, Dijkstra's non-negative-weight assumption, EWMA's α bias-variance tradeoff.

---

## Phase 4 — Model Ladder (ML + DL)

**Goal:** four demand models of increasing complexity, compared *honestly on the same test set*, plus one fare model. The deliverable is the **comparison story**, not any single model. Files under [`models/`](../models/).

### Steps
1. **Feature build (once, reuse everywhere)** — [`build_features.py`](../models/data_prep/build_features.py): from `zone_hourly_demand` + Phase 3 EWMA/seasonality. Features: `hour`, `day_of_week`, `is_weekend`, `lag_1h`, `lag_24h`, `lag_168h`, EWMA value, rolling 7-day average.
2. **Chronological split** — [`train_test_split.py`](../models/data_prep/train_test_split.py): first ~70% train / next ~15% val / final ~15% test. **Never random-split time-series** — it leaks future into past. Document this explicitly.
3. **Model 1 — Linear Regression** ([`linear_regression_model.py`](../models/linear_baseline/linear_regression_model.py)): the naive floor; report coefficients.
4. **Model 2 — EWMA baseline** ([`ewma_forecast.py`](../models/ewma_baseline/ewma_forecast.py)): last EWMA value as next-hour forecast; the "do-nothing-fancy" floor.
5. **Model 3 — XGBoost** ([`train_xgboost.py`](../models/xgboost_model/train_xgboost.py)): tune depth/lr/n_estimators; plot feature importances; compare vs. linear coefficients. Save `xgboost_demand.pkl`.
6. **Model 4 — LSTM/GRU** ([`dataset.py`](../models/lstm_model/dataset.py) + [`train_lstm.ipynb`](../models/lstm_model/train_lstm.ipynb)): sliding-window sequences (past 24h → next hour); 1–2 layers; run on Colab/Kaggle GPU; track train/val loss curves. Save `lstm_demand.pt`.
7. **Fare model** ([`train_fare_xgb.py`](../models/fare_prediction/train_fare_xgb.py)): XGBoost predicting fare from pickup/dropoff zone, hour, day, distance. Don't over-build.
8. **Evaluation (most important file)** — [`compare_models.py`](../models/evaluation/compare_models.py): all 4 demand models on the *same* test set → RMSE, MAE, inference latency, training time. Write [`metrics_report.md`](../models/evaluation/metrics_report.md) as a comparison table + one sentence per model on what it uniquely captures.

### Definition of Done
- [ ] All four models evaluated on the identical chronological test set.
- [ ] `metrics_report.md` table filled: model | RMSE | MAE | inference time | train time.
- [ ] Feature importance (XGBoost) vs. coefficients (linear) compared in writing.
- [ ] LSTM train/val loss curve saved.
- [ ] You can explain OLS multicollinearity, RMSE-vs-MAE, gradient boosting residual-fitting, and LSTM gates.

---

## Phase 5 — Hybrid RAG Layer

**Goal:** a chat interface answering both **precise numeric** questions (→ NL→SQL against DuckDB) and **explanatory "why"** questions (→ vector retrieval over insight docs), behind one router. Files under [`rag/`](../rag/).

### Steps
1. [`generate_insight_docs.py`](../rag/insight_generation/generate_insight_docs.py): per zone/zone-hour, generate a short NL insight paragraph from marts + algorithm outputs. **Template every number from your real computed tables** — the LLM phrases, it never invents values.
2. [`build_vector_store.py`](../rag/embeddings/build_vector_store.py): embed insight docs (OpenAI embeddings or local sentence-transformer) into **ChromaDB**.
3. [`sql_agent.py`](../rag/nl_to_sql/sql_agent.py): NL→SQL path — prompt with the **mart schemas only**, generate SQL, execute against DuckDB, return the grounded number *with the query shown*.
4. [`query_classifier.py`](../rag/router/query_classifier.py): route each question as `numeric` vs. `explanatory` (a short LLM intent prompt — don't train a separate classifier).
5. [`rag_pipeline.py`](../rag/rag_pipeline.py): router → dispatch to NL→SQL or vector retrieval → grounded final answer.
6. Test with a deliberate mix; save 8–10 example Q&A pairs for the README/demo.

### Definition of Done
- [ ] Numeric questions return DuckDB-executed numbers with the SQL shown.
- [ ] Explanatory questions return vector-retrieved, grounded answers.
- [ ] Router classifies the test mix correctly.
- [ ] 8–10 example Q&A pairs documented; you can articulate *why RAG over fine-tuning* and *why NL→SQL is separated from text-RAG*.

---

## Phase 6 — Backend API (FastAPI)

**Goal:** serve predictions and chat. Files under [`backend/`](../backend/).

### Steps
1. [`schemas.py`](../backend/schemas.py): Pydantic request/response models.
2. [`services/model_service.py`](../backend/services/model_service.py): load saved `xgboost_demand.pkl` / `lstm_demand.pt`; serve predictions. **Ship precomputed predictions/tables for the live demo** — don't run the 8–10M-row pipeline on a free-tier host.
3. [`services/rag_service.py`](../backend/services/rag_service.py): wrap `rag_pipeline.py`.
4. Routers: [`predictions.py`](../backend/routers/predictions.py), [`zones.py`](../backend/routers/zones.py), [`chat.py`](../backend/routers/chat.py) exposing `/predict/demand`, `/predict/fare`, `/zones`, `/chat`.
5. [`main.py`](../backend/main.py): assemble app, CORS, include routers.
6. **Run & smoke-test:**
   ```powershell
   uvicorn backend.main:app --reload
   ```
   Open `http://localhost:8000/docs` and exercise every endpoint.

### Definition of Done
- [ ] All four endpoints return valid responses in Swagger (`/docs`).
- [ ] `model_service` loads real artifacts (no crashes on cold start).
- [ ] `/chat` round-trips through the RAG pipeline.

---

## Phase 7 — Frontend (React + Vite)

**Goal:** a clickable dashboard with map, model comparison, and chat. Files under [`frontend/`](../frontend/).

### Steps
1. `cd frontend; npm install`.
2. [`ZoneMap.jsx`](../frontend/src/components/ZoneMap.jsx): Leaflet map, zones color-coded by predicted demand/fare, clickable for detail.
3. [`ChatPanel.jsx`](../frontend/src/components/ChatPanel.jsx): RAG chat UI wired to `/chat`; seed example questions.
4. [`ModelComparisonChart.jsx`](../frontend/src/components/ModelComparisonChart.jsx): bar/line chart of the Phase 4 RMSE/MAE comparison.
5. [`App.jsx`](../frontend/src/App.jsx): layout tying the three together; read `VITE_API_BASE_URL` from env.
6. **Run:** `npm run dev` → `http://localhost:5173`.

### Definition of Done
- [ ] Map renders zones and reflects predictions from the API.
- [ ] Chat panel gets grounded answers from `/chat`.
- [ ] Comparison chart matches `metrics_report.md`.
- [ ] `docker-compose up` brings backend + frontend up together (see [`docker-compose.yml`](../docker-compose.yml)).

---

## Phase 8 — Testing, Docs & Deployment

**Goal:** a portfolio-grade repo and a deployed, clickable demo.

### Steps
1. **Tests:** flesh out [`test_dbt_marts.py`](../tests/test_dbt_marts.py), [`test_algorithms.py`](../tests/test_algorithms.py), [`test_api.py`](../tests/test_api.py). Run `pytest -q`.
2. **Docs:** finalize the root [`README.md`](../README.md) (summary, architecture diagram, model-comparison table, "why these choices", live-demo link) and [`architecture.png`](architecture.png).
3. **Deploy:** backend on Render/Railway free tier, frontend on Vercel/Netlify. Ship a lightweight DuckDB (marts + precomputed tables only).
4. **Backup:** record a short demo GIF/video in case the live deploy goes down.

### Definition of Done
- [ ] `pytest` passes green (marts, algorithms, API).
- [ ] README complete with architecture diagram + model comparison table + live-demo link.
- [ ] Live demo reachable; backup demo recording saved.

---

## Progress Tracker

| # | Phase | Status |
|---|-------|--------|
| 0 | Environment & Repo Setup | ☑ Done |
| 1 | Data Ingestion | ☑ Done |
| 2 | dbt Transformation | ☐ Not started |
| 3 | Algorithmic Showpieces | ☐ Not started |
| 4 | Model Ladder (ML + DL) | ☐ Not started |
| 5 | Hybrid RAG Layer | ☐ Not started |
| 6 | Backend API | ☐ Not started |
| 7 | Frontend | ☐ Not started |
| 8 | Testing, Docs & Deploy | ☐ Not started |

> Update the status column (`☐ Not started` → `◐ In progress` → `☑ Done`) as you clear each phase's Definition of Done. A phase is only *Done* when **every** checkbox in its DoD is ticked.

---

## Reference Map

- **Master narrative / concepts / interview framing:** [`/project_plan.md`](../project_plan.md)
- **Interactive overview page:** [`project_overview.html`](project_overview.html)
- **Architecture diagram:** [`architecture.png`](architecture.png)
- **Repo README:** [`/README.md`](../README.md)

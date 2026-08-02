# NYC Ride Intelligence Platform — Full Build Plan

A 9-week, layer-by-layer build plan. dbt + DuckDB + multi-model ML/DL + spatial/graph/time-series algorithms + hybrid RAG, served via FastAPI + React, deployed live.

**How to use this doc:** work top to bottom, layer by layer. Each layer lists exact files to create (matching the folder structure below), a checklist you can tick off, the math/CS concepts to actually understand (not just use), and study resources. Don't move to the next layer until the current layer's checklist is done — the layers are dependencies, not parallel tracks.

---

## 0. Full Folder Structure

Create this structure first (empty files are fine — you'll fill them layer by layer).

```
nyc-ride-intelligence/
├── README.md
├── .env.example
├── .gitignore
├── requirements.txt
├── docker-compose.yml
│
├── data/
│   ├── raw/                          # downloaded TLC parquet files (gitignored)
│   ├── lookup/
│   │   └── taxi_zone_lookup.csv
│   └── warehouse/
│       └── nyc_rides.duckdb          # the actual DuckDB file
│
├── dbt_project/
│   ├── dbt_project.yml
│   ├── packages.yml
│   ├── profiles.yml
│   ├── models/
│   │   ├── staging/
│   │   │   ├── stg_trips.sql
│   │   │   ├── stg_zones.sql
│   │   │   └── schema.yml
│   │   ├── intermediate/
│   │   │   ├── int_trips_enriched.sql
│   │   │   └── schema.yml
│   │   └── marts/
│   │       ├── zone_hourly_demand.sql
│   │       ├── zone_fare_stats.sql
│   │       ├── zone_pair_flows.sql
│   │       └── schema.yml
│   ├── seeds/
│   │   └── taxi_zone_lookup.csv
│   └── tests/
│       └── assert_positive_fares.sql
│
├── algorithms/
│   ├── spatial/
│   │   ├── kdtree_zone_lookup.py
│   │   └── geohash_grid.py
│   ├── graph/
│   │   ├── build_zone_graph.py
│   │   ├── pagerank_hubs.py
│   │   └── shortest_path_eta.py
│   └── timeseries/
│       ├── ewma_smoothing.py
│       └── seasonality_decompose.py
│
├── models/
│   ├── data_prep/
│   │   ├── build_features.py
│   │   └── train_test_split.py
│   ├── linear_baseline/
│   │   └── linear_regression_model.py
│   ├── ewma_baseline/
│   │   └── ewma_forecast.py
│   ├── xgboost_model/
│   │   ├── train_xgboost.py
│   │   └── xgboost_demand.pkl
│   ├── lstm_model/
│   │   ├── train_lstm.ipynb
│   │   ├── lstm_demand.pt
│   │   └── dataset.py
│   ├── fare_prediction/
│   │   └── train_fare_xgb.py
│   └── evaluation/
│       ├── compare_models.py
│       └── metrics_report.md
│
├── rag/
│   ├── insight_generation/
│   │   └── generate_insight_docs.py
│   ├── embeddings/
│   │   └── build_vector_store.py
│   ├── nl_to_sql/
│   │   └── sql_agent.py
│   ├── router/
│   │   └── query_classifier.py
│   └── rag_pipeline.py
│
├── backend/
│   ├── main.py
│   ├── routers/
│   │   ├── predictions.py
│   │   ├── zones.py
│   │   └── chat.py
│   ├── services/
│   │   ├── model_service.py
│   │   └── rag_service.py
│   └── schemas.py
│
├── frontend/
│   ├── index.html
│   ├── src/
│   │   ├── App.jsx
│   │   ├── components/
│   │   │   ├── ZoneMap.jsx
│   │   │   ├── ChatPanel.jsx
│   │   │   └── ModelComparisonChart.jsx
│   │   └── styles/
│   └── package.json
│
├── notebooks/
│   ├── 01_eda.ipynb
│   ├── 02_dbt_marts_explore.ipynb
│   └── 03_model_comparison.ipynb
│
├── docs/
│   ├── architecture.png
│   ├── project_plan.md               # this file
│   └── project_overview.html         # interactive overview
│
└── tests/
    ├── test_dbt_marts.py
    ├── test_algorithms.py
    └── test_api.py
```

---

## Layer 0 — Data Foundation

**Goal:** 3 months of NYC TLC trip data (~8-10M rows) sitting cleanly in DuckDB, joined to zone lookup.

### Files to create
- [ ] `data/raw/` — download 3 months of TLC High Volume For-Hire Vehicle (HVFHV) parquet files (this is the Uber/Lyft-equivalent dataset, NOT yellow taxi)
- [ ] `data/lookup/taxi_zone_lookup.csv` — official NYC TLC zone lookup table
- [ ] `data/warehouse/nyc_rides.duckdb` — created by your load script
- [ ] `requirements.txt` — pin: `duckdb`, `dbt-duckdb`, `pandas`, `pyarrow`
- [ ] A one-off `scripts/load_raw_to_duckdb.py` (not in the tree above — add a `scripts/` folder) that reads parquet → loads into DuckDB as a raw table

### Checklist
- [ ] Download 3 months of HVFHV parquet from the TLC trip record page
- [ ] Download and inspect the taxi zone lookup CSV (zone, borough, service_zone columns)
- [ ] Load raw parquet directly into DuckDB using `CREATE TABLE AS SELECT * FROM read_parquet(...)` — DuckDB reads parquet natively, no need to go through pandas for the big load
- [ ] Verify row count lands in your 8-10M target
- [ ] Spot-check for known TLC data issues: nulls in PULocationID/DOLocationID, negative trip distances, timestamps outside the expected month range
- [ ] Confirm DuckDB file size is manageable on your laptop (should be a few GB at this scale, well within free-tier/local limits)

### What to actually study (don't skip this — it's the "why DuckDB" interview answer)
- **Columnar storage vs row storage** — why Parquet + DuckDB is fast for analytical (OLAP) queries vs a row-store like Postgres. Be able to explain this in one paragraph in your README.
- **Why DuckDB specifically**: in-process (no server), vectorized execution, reads Parquet natively without a load step. This is your answer to "why not just use Postgres."

### Study resources
- DuckDB docs: "Why DuckDB" page (short, directly usable as README content)
- NYC TLC Trip Record Data page (data dictionary for HVFHV schema)

---

## Layer 1 — dbt Transformation Layer

**Goal:** raw trip rows → clean, tested, query-ready marts that every later layer (algorithms, ML, RAG) reads from.

### Files to create
- [ ] `dbt_project/dbt_project.yml`
- [ ] `dbt_project/profiles.yml` (DuckDB adapter config)
- [ ] `dbt_project/seeds/taxi_zone_lookup.csv`
- [ ] `dbt_project/models/staging/stg_trips.sql`
- [ ] `dbt_project/models/staging/stg_zones.sql`
- [ ] `dbt_project/models/staging/schema.yml`
- [ ] `dbt_project/models/intermediate/int_trips_enriched.sql`
- [ ] `dbt_project/models/intermediate/schema.yml`
- [ ] `dbt_project/models/marts/zone_hourly_demand.sql`
- [ ] `dbt_project/models/marts/zone_fare_stats.sql`
- [ ] `dbt_project/models/marts/zone_pair_flows.sql`
- [ ] `dbt_project/models/marts/schema.yml`
- [ ] `dbt_project/tests/assert_positive_fares.sql`

### Checklist
- [ ] `stg_trips.sql`: cast types, rename columns to consistent snake_case, filter out clearly broken rows (this is staging — light cleaning only, no business logic)
- [ ] `stg_zones.sql`: clean zone lookup, dedupe if needed
- [ ] `int_trips_enriched.sql`: join trips to zones, derive `hour_of_day`, `day_of_week`, `is_weekend`, `trip_duration_minutes`, `avg_speed_mph`
- [ ] `zone_hourly_demand.sql`: `GROUP BY` zone, date, hour → pickup counts. **This table is your ML target variable — get this right, everything downstream depends on it.**
- [ ] `zone_fare_stats.sql`: avg/median/percentile fares per zone-hour
- [ ] `zone_pair_flows.sql`: `GROUP BY` PULocationID, DOLocationID → trip counts. **This feeds your graph layer.**
- [ ] Add dbt tests: `not_null` on zone IDs, `accepted_range` on fares (e.g. fare > 0 and < some sane ceiling), relationship test from trips to zone lookup
- [ ] Run `dbt test` and get a clean pass
- [ ] Run `dbt docs generate` once — keep the generated lineage graph, it's free portfolio material (screenshot it for your README)

### What to actually study
- **Staging vs intermediate vs marts convention** — why this layering exists (each layer has one job: staging cleans, intermediate enriches, marts answer business questions). Be ready to explain this distinction, it's a common dbt interview question.
- **Incremental models** — you hit this already in your Airbnb project; here, decide explicitly whether `zone_hourly_demand` should be incremental (append new days) vs full-refresh, and be able to justify your choice.
- **Window functions in SQL** — `GROUP BY` plus the `LAG()`/`LEAD()` window functions for the lag-features you'll need in Layer 3 (e.g. demand 1 hour ago, 24 hours ago).

### Study resources
- dbt docs: "How we structure our dbt projects" (the staging/intermediate/marts guide)
- Your own Airbnb dbt+Snowflake project notes on incremental models — revisit what broke there so you don't repeat it

---

## Layer 2 — Algorithmic Showpieces (Spatial + Graph + Time-Series)

**Goal:** three real, defensible algorithm implementations — not library calls you can't explain. This is the layer that separates this project from a generic "I used pandas and XGBoost" portfolio piece.

### Files to create
- [ ] `algorithms/spatial/kdtree_zone_lookup.py`
- [ ] `algorithms/spatial/geohash_grid.py`
- [ ] `algorithms/graph/build_zone_graph.py`
- [ ] `algorithms/graph/pagerank_hubs.py`
- [ ] `algorithms/graph/shortest_path_eta.py`
- [ ] `algorithms/timeseries/ewma_smoothing.py`
- [ ] `algorithms/timeseries/seasonality_decompose.py`

### 2A. Spatial — KD-Tree for nearest-zone lookup

**What it does:** given a lat/lon (e.g. "where am I right now"), find the nearest taxi zone centroid in better than linear time.

**Checklist**
- [ ] `kdtree_zone_lookup.py`: implement a KD-tree from scratch (don't just call `scipy.spatial.KDTree` — build it yourself first, then optionally benchmark against scipy's to prove correctness)
- [ ] Build the tree over the ~260 NYC TLC zone centroids
- [ ] Implement nearest-neighbor query: given (lat, lon), return nearest zone
- [ ] Benchmark: linear scan O(n) vs KD-tree O(log n) over repeated queries, plot/print the timing difference
- [ ] `geohash_grid.py`: implement geohashing as an alternative/companion approach — encode each zone centroid to a geohash string, demonstrate prefix-matching for "nearby zones"

**Math/CS to actually understand**
- KD-tree construction: recursively partition points by alternating axis (lat, then lon, then lat...) at the median. Construction is `O(n log n)`.
- Nearest-neighbor search: traverse the tree pruning branches whose bounding region can't contain a closer point than the current best. Average case `O(log n)`, worst case `O(n)` for degenerate trees.
- Geohashing: interleaving bits of lat/lon into a base-32 string such that geographically close points often (not always) share string prefixes — useful for fast proximity bucketing but know its limitation (edge effects at boundaries).

**Study resources**
- "Introduction to Algorithms" (CLRS) — section on space-partitioning trees, or any solid KD-tree tutorial with the recursive build + nearest-neighbor-with-pruning logic
- Geohash.org explanation page for the bit-interleaving algorithm

---

### 2B. Graph — Zone network as a weighted directed graph

**What it does:** models NYC zones as nodes and trip flows as edges, then asks graph-theory questions: which zones are "hubs"? What's the shortest path (by typical travel time) between two zones?

**Checklist**
- [ ] `build_zone_graph.py`: read `zone_pair_flows` mart → build a weighted directed graph (use `networkx` for the graph structure itself, but implement the algorithms below yourself rather than calling `nx.pagerank()` directly — at least once, by hand)
- [ ] `pagerank_hubs.py`: implement PageRank from scratch (power iteration method) to rank zones by "importance" in the flow network — a zone that receives traffic from other important zones ranks higher
- [ ] Compare your hand-rolled PageRank output against `networkx`'s built-in to validate correctness
- [ ] `shortest_path_eta.py`: implement Dijkstra's algorithm where edge weights = average trip duration between zone pairs (from your enriched trips table) — this gives you an ETA-by-graph-path as a sanity-check feature, separate from your ML ETA model

**Math/CS to actually understand**
- **PageRank**: the formula is

  ```
  PR(p) = (1 - d) / N + d * Σ ( PR(q) / L(q) )
  ```

  where the sum is over all pages `q` linking to `p`, `L(q)` is the out-degree of `q`, `d` is the damping factor (~0.85), `N` is the total number of nodes. Implemented via power iteration: start with uniform rank, repeatedly apply the update until convergence (rank vector stops changing beyond some epsilon).
- **Dijkstra's algorithm**: greedy shortest-path using a min-priority-queue, relaxing edges. Time complexity `O((V + E) log V)` with a binary heap. Know why it fails with negative edge weights (it won't matter here since durations are positive, but you should know why this assumption matters).
- **Graph centrality concepts**: PageRank is one notion of "importance" (eigenvector-based); contrast briefly with degree centrality (simple in/out-degree count) so you can explain why PageRank captures something degree centrality misses.

**Study resources**
- Original PageRank paper (Brin & Page) — just the formula and power-iteration explanation, skip the search-engine framing
- Any standard Dijkstra's algorithm writeup with the priority-queue implementation (e.g. from a DSA course you've already done)

---

### 2C. Time-Series Math — EWMA + seasonality decomposition

**What it does:** smooths noisy hourly demand into a trend signal, and separates demand into trend/seasonal/residual components — this directly feeds features into your ML models in Layer 3.

**Checklist**
- [ ] `ewma_smoothing.py`: implement EWMA from scratch over `zone_hourly_demand` (you already have this exact technique from your interview platform's ability-tracking work — port the logic, adapt to this domain)
- [ ] `seasonality_decompose.py`: decompose each zone's hourly demand series into trend + daily seasonality + weekly seasonality + residual
- [ ] Visualize: pick 2-3 interesting zones (e.g. an airport zone, a nightlife zone, a residential zone) and plot their decomposition side by side — this is a great portfolio screenshot

**Math/CS to actually understand**
- **EWMA formula**:

  ```
  S_t = α * x_t + (1 - α) * S_(t-1)
  ```

  where `S_t` is the smoothed value at time `t`, `x_t` is the raw observation, and `α` (0 < α ≤ 1) is the smoothing factor — higher α weighs recent observations more heavily, lower α smooths more aggressively. Be able to explain the bias-variance tradeoff in choosing α.
- **Seasonality decomposition**: additive model `y_t = Trend_t + Seasonal_t + Residual_t` (or multiplicative if variance scales with level: `y_t = Trend_t * Seasonal_t * Residual_t`). Know when to pick additive vs multiplicative (look at whether seasonal swings grow with the overall level).
- This is the same conceptual family as your IRT/EWMA work on the interview platform — frame this explicitly as "applying smoothing/tracking techniques I built for adaptive testing to a completely different domain" in your README. That continuity is a strong narrative.

**Study resources**
- Any time-series textbook chapter on exponential smoothing (Holt-Winters is the natural next step if you want to go further, but plain EWMA + decomposition is enough here)
- `statsmodels` seasonal_decompose documentation (use it to validate your from-scratch implementation, same pattern as PageRank above)

---

## Layer 3 — Model Ladder (ML + DL)

**Goal:** four models predicting zone-hourly demand, increasing in complexity, compared honestly on the same test set. Plus one fare-prediction model. The point of this layer is the *comparison story*, not just "I trained a model."

### Files to create
- [ ] `models/data_prep/build_features.py`
- [ ] `models/data_prep/train_test_split.py`
- [ ] `models/linear_baseline/linear_regression_model.py`
- [ ] `models/ewma_baseline/ewma_forecast.py`
- [ ] `models/xgboost_model/train_xgboost.py`
- [ ] `models/lstm_model/train_lstm.ipynb`
- [ ] `models/lstm_model/dataset.py`
- [ ] `models/fare_prediction/train_fare_xgb.py`
- [ ] `models/evaluation/compare_models.py`
- [ ] `models/evaluation/metrics_report.md`

### Checklist

**Data prep (do this once, reuse everywhere)**
- [ ] `build_features.py`: pull from `zone_hourly_demand` + your EWMA/seasonality outputs from Layer 2. Features: hour, day-of-week, is_weekend, lag_1h, lag_24h, lag_168h (1 week), EWMA smoothed value, rolling 7-day average
- [ ] `train_test_split.py`: **chronological split, not random** — train on first ~70% of the date range, validate on the next ~15%, test on the final ~15%. Random splitting leaks future information into training for time-series — explain this explicitly in your evaluation report, it's a common mistake interviewers probe for

**Model 1 — Linear Regression (the naive floor)**
- [ ] `linear_regression_model.py`: plain linear regression on the engineered features
- [ ] Inspect and report the coefficients — which features matter most according to a linear model? This is genuinely useful interpretability, not just a throwaway baseline

**Model 2 — EWMA baseline (no training, pure smoothing)**
- [ ] `ewma_forecast.py`: use last known EWMA value as the forecast for the next hour — this is your "if I do nothing fancy, how good is just smoothing" floor

**Model 3 — XGBoost (tabular, feature-rich)**
- [ ] `train_xgboost.py`: train on the same engineered features, tune depth/learning_rate/n_estimators with a simple grid or `RandomizedSearchCV`
- [ ] Plot feature importances — compare against the linear model's coefficients, discuss where they agree/disagree

**Model 4 — LSTM/GRU (sequence-aware, the DL showpiece)**
- [ ] `dataset.py`: build a sliding-window sequence dataset (e.g. past 24 hours → predict next hour) per zone
- [ ] `train_lstm.ipynb`: run this on Colab/Kaggle GPU. Simple 1-2 layer LSTM or GRU is enough — don't over-architect
- [ ] Track training/validation loss curves — include the plot in your report

**Fare prediction (secondary model, XGBoost only — don't over-build this one)**
- [ ] `train_fare_xgb.py`: predict trip fare given pickup zone, dropoff zone, hour, day-of-week, distance

**Evaluation (the most important file in this layer)**
- [ ] `compare_models.py`: run all 4 demand models on the same chronological test set, compute RMSE, MAE, and measure inference latency per model
- [ ] `metrics_report.md`: write up the comparison as a table — model, RMSE, MAE, inference time, training time, one sentence on what each model seems to capture that the others don't (e.g. "LSTM picks up on multi-day momentum that XGBoost's lag features approximate but don't fully capture")

### What to actually study
- **Linear regression**: ordinary least squares, the normal equation `β = (XᵀX)⁻¹Xᵀy`, and why this becomes unstable with correlated features (multicollinearity) — relevant since lag features are correlated with each other.
- **RMSE vs MAE**: `RMSE = sqrt( (1/n) Σ (y_i - ŷ_i)² )` penalizes large errors more than `MAE = (1/n) Σ |y_i - ŷ_i|`. Know when to report which, and report both.
- **XGBoost core idea**: gradient boosting builds trees sequentially, each new tree fits the *residual error* of the ensemble so far, scaled by a learning rate. You don't need the full math derivation, but you should be able to explain "each tree corrects the previous ensemble's mistakes" clearly.
- **LSTM cell mechanics**: the forget gate, input gate, output gate, and cell state — at minimum, be able to draw the LSTM cell diagram and explain why it solves the vanishing-gradient problem that plain RNNs have over long sequences. This is the single most-asked "do you actually understand DL or just call .fit()" question.
- **Why chronological split matters for time-series**: random splitting leaks future → past information, inflating validation performance unrealistically.

### Study resources
- StatQuest's gradient boosting / XGBoost explainer videos (genuinely good for building real intuition fast)
- Christopher Olah's "Understanding LSTM Networks" blog post — the canonical clear explanation of LSTM gates with diagrams
- Any standard ML textbook chapter on bias-variance tradeoff, to frame why you're laddering model complexity at all

---

## Layer 4 — Hybrid RAG Layer

**Goal:** a chat interface that can answer both precise numeric questions ("average fare from Zone 161 around 6pm?") and explanatory "why" questions ("why does Zone 161 get busy at rush hour?"), using two different retrieval paths under one router.

### Files to create
- [ ] `rag/insight_generation/generate_insight_docs.py`
- [ ] `rag/embeddings/build_vector_store.py`
- [ ] `rag/nl_to_sql/sql_agent.py`
- [ ] `rag/router/query_classifier.py`
- [ ] `rag/rag_pipeline.py`

### Checklist
- [ ] `generate_insight_docs.py`: for each zone (or zone-hour group), generate a short natural-language insight paragraph from your marts + algorithm outputs (e.g. "Zone 161 (Midtown) sees roughly 3x baseline pickup volume between 5-7pm on weekdays, ranking in the top 10 by PageRank hub score. Demand shows strong weekly seasonality peaking Thu/Fri.") — use Gemini to help draft these from templated stats, but ground every number in your actual computed tables, don't let the LLM invent numbers
- [ ] `build_vector_store.py`: embed the insight docs (Gemini embeddings or a local sentence-transformer — either is fine, local is cheaper/faster for this volume), store in a simple vector store (FAISS or even a DuckDB table with cosine similarity — you already have DuckDB running, no need for a separate vector DB at this scale)
- [ ] `sql_agent.py`: NL-to-SQL path — prompt Gemini with your DuckDB schema (mart table structures only, not raw trip-level data) and ask it to generate a SQL query for numeric questions, execute against DuckDB, return the grounded number with the query shown (transparency matters here — show your work)
- [ ] `query_classifier.py`: simple router — classify incoming question as "numeric lookup" vs "explanatory" (a short Gemini prompt classifying intent is enough, don't over-engineer this into a separate trained classifier)
- [ ] `rag_pipeline.py`: ties it together — router → dispatch to NL-to-SQL or vector retrieval → final answer generation grounded in whichever context was retrieved
- [ ] Test with a deliberate mix of question types and write down 8-10 example Q&A pairs for your README/demo

### What to actually study
- **Why RAG over fine-tuning here**: your data changes (new months of trips), so retrieval-grounded answers stay current without retraining — a clean one-paragraph justification for your architecture choice.
- **Embeddings and cosine similarity**: `similarity(A, B) = (A · B) / (||A|| * ||B||)` — know this formula cold, you'll be asked to explain "how does retrieval actually find the relevant doc."
- **Why NL-to-SQL needs separating from RAG-over-text**: LLMs are unreliable at exact arithmetic/aggregation from retrieved text snippets — pushing numeric questions to actual SQL execution against your warehouse is the more defensible architecture, and it's a good design-judgment talking point in interviews.
- **Hallucination risk and grounding**: explicitly discuss in your README how you prevent the insight-doc generation step from inventing numbers (always template the actual computed stat into the text, use the LLM only for phrasing, not for inventing values).

### Study resources
- Any introductory RAG architecture writeup (the "retrieve-then-generate" pattern, chunking strategies)
- Gemini API docs for function-calling / structured output (useful for the NL-to-SQL agent's query generation step)

---

## Layer 5 — Serving & Presentation

**Goal:** a deployed, clickable app plus a portfolio-grade GitHub repo. Both matter equally per your call — don't shortcut either.

### Files to create
- [ ] `backend/main.py`
- [ ] `backend/routers/predictions.py`
- [ ] `backend/routers/zones.py`
- [ ] `backend/routers/chat.py`
- [ ] `backend/services/model_service.py`
- [ ] `backend/services/rag_service.py`
- [ ] `backend/schemas.py`
- [ ] `frontend/index.html`
- [ ] `frontend/src/App.jsx`
- [ ] `frontend/src/components/ZoneMap.jsx`
- [ ] `frontend/src/components/ChatPanel.jsx`
- [ ] `frontend/src/components/ModelComparisonChart.jsx`
- [ ] `README.md` (root level — this is the single most-read file in the whole project)
- [ ] `docs/architecture.png`

### Checklist
- [ ] `backend/main.py` + routers: FastAPI app exposing `/predict/demand`, `/predict/fare`, `/zones`, `/chat`
- [ ] `model_service.py`: loads your saved XGBoost/LSTM artifacts, serves predictions — **ship precomputed predictions/tables for the live demo**, don't try to serve the full 8-10M-row pipeline live on a free-tier host
- [ ] `rag_service.py`: wraps your `rag_pipeline.py` for the `/chat` endpoint
- [ ] `ZoneMap.jsx`: Leaflet-based map, color-coded zones by predicted demand or fare, clickable for detail
- [ ] `ChatPanel.jsx`: the RAG chat interface, frame the placeholder/example questions in the India-style framing you wanted ("what's the typical surge here", "how much would this ride usually cost")
- [ ] `ModelComparisonChart.jsx`: bar/line chart showing your 4-model RMSE/MAE comparison from Layer 3 — this is a great "I understand tradeoffs" visual for visitors
- [ ] Deploy backend (Render/Railway free tier) + frontend (Vercel/Netlify) — keep the deployed DuckDB file lightweight (marts + precomputed tables only)
- [ ] Write the root `README.md`: project summary, architecture diagram, the model comparison table, "why these technical choices" section, link to live demo, link to `docs/project_overview.html`
- [ ] Record a short demo video/GIF as backup in case the live deploy ever goes down

### What to actually study
- **Why precompute for deployment**: free-tier hosts can't hold 8-10M rows of live compute — explain this constraint and your workaround explicitly, it shows engineering judgment about cost/scale tradeoffs, not just "I built a demo."
- Basic REST API design conventions (resource naming, status codes) if you haven't solidified this yet — you already have FastAPI experience from the interview platform, this layer should move fast.

---

## Closing Notes

- **Order matters**: Layer 0 → 1 → 2 → 3 → 4 → 5, strictly. Algorithms (2) need the marts (1). Models (3) need algorithm outputs as features. RAG (4) needs model outputs and marts to generate insights from. Serving (5) needs everything.
- **At ~12 hrs/week**, expect roughly: Layers 0-1 in week 1-2, Layer 2 in weeks 3-4, Layer 3 in weeks 5-6, Layer 4 in weeks 7-8, Layer 5 in week 9. This is a guide, not a contract — let the checklists, not the calendar, tell you when a layer is actually done.
- **Don't skip the "study" sections** for the sake of moving faster. The entire point of this project over a generic Kaggle notebook is that you can explain *why* at every layer in an interview. A finished pipeline you can't explain is worth less than a half-finished one you understand completely.
- **Continuity story for your portfolio narrative**: this project deliberately reuses techniques from your other work — EWMA from your interview platform's ability tracking, dbt+DuckDB muscle from your Airbnb project, FastAPI+MongoDB-style service architecture from KJGSPL. Say this explicitly in your README's intro. It shows your skills compound across projects, which is a stronger signal than N disconnected projects.

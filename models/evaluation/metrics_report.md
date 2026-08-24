# Model Evaluation Report

Real numbers only (rule 2, `.claude/rules.md`) — every metric below traces
back to a training script's actual output. "Not yet measured" stands in for
anything not yet run.

## Fare Prediction (SPEC-007)

**Model:** single tuned XGBoost regressor (`models/fare_prediction/train_fare_xgb.py`).
No ladder, no LSTM variant — out of scope per spec.

**Features:** `pickup_location_id`, `dropoff_location_id`, `pickup_hour`,
`pickup_day_of_week` (all treated as native XGBoost categoricals),
`trip_distance`. **Target:** `total_amount` (`int_trips_enriched`).

**Chronological split (ADR-003), adapted for a known data gap:** the
warehouse only has trips for January, March, and June 2024 — February,
April, and May are missing, so the timeline is three disjoint monthly
blocks, not one continuous range. A plain 70/15/15 split by row count across
the concatenated blocks would put the test cutoff partway *into* June
(Jan+Mar alone is ~67% of all rows), silently mixing early-June "train" rows
with late-June "test" rows from the same block — exactly the leakage
ADR-003 exists to prevent. Instead:

- **train + val = January + March** (the two earlier blocks)
- **test = June in full** — the most recent complete block, held out
  entirely
- within Jan+Mar, the most recent 15% by `pickup_at` is validation, so the
  ordering train → val → test holds throughout, not just at the train/test
  boundary

| Split | Date range | Rows |
|---|---|---|
| train | 2024-01-01 00:00:04 → 2024-03-23 01:23:01 | 4,558,329 |
| val   | 2024-03-23 01:23:02 → 2024-03-31 23:59:59 | 804,411 |
| test  | 2024-06-01 00:00:00 → 2024-06-30 23:59:59 | 2,636,109 |

Leakage guard: `max(train.pickup_at) < min(val.pickup_at) < min(test.pickup_at)`,
enforced in code (`train_fare_xgb.py` asserts) and verified independently in
`tests/test_fare_split_no_leakage.py`.

**Hyperparameter selection:** small manual grid (4 candidates: `max_depth`
∈ {4,6,8}, `learning_rate` ∈ {0.05,0.1}, `n_estimators` ∈ {300,500}) picked
by validation RMSE, not a full CV search (out of scope). Winner:
`max_depth=6, learning_rate=0.05, n_estimators=500`. Final model refit on
train+val with these hyperparameters; test touched exactly once.

**Metrics (actual, measured 2026-08-05):**

| Split | RMSE | MAE |
|---|---|---|
| validation | 10.71 | 5.51 |
| **test (June, held out)** | **12.61** | **6.29** |

Test error is meaningfully higher than validation error — consistent with
holding out an entire later block rather than a random slice of the same
period; fares in June reflect seasonal/surge patterns the model never saw.

**Reproducibility (rule 5):** seed=42; date range = Jan+Mar+Jun 2024
(warehouse snapshot as of this run); full hyperparameter grid, per-split
metrics, and library versions (`xgboost==3.3.0`, `pandas==3.0.3`,
`numpy==2.5.1`) recorded in `models/fare_prediction/fare_xgb_metadata.json`
alongside the saved model (`fare_xgb_model.json`).

## Demand Forecasting (SPEC-006)

**Target:** `zone_hourly_demand.total_trips` (pickup count per zone-hour),
all 262 zones. **Features** (`models/data_prep/build_features.py`, reusing
`algorithms/timeseries/ewma_smoothing.py`'s block splitter): `hour`,
`day_of_week`, `is_weekend`, `lag_1h`, `lag_24h`, `lag_168h`, `ewma`
(EWMA state one step back, α=0.5 — the cross-zone default set in SPEC-005),
`rolling_7d_avg` (trailing 168h mean), plus real hourly weather
`temperature_c` and `precipitation_mm` (city-level, joined at (date, hour)
grain — backfilled by `scripts/backfill_weather_openmeteo.py`). All
lag/EWMA/rolling features are computed strictly from hours *before* t
(`.shift(1)`) so none of them leak the row's own target into its own
feature — verified in `build_features.py`'s `demo()`.

**Chronological split (ADR-003), block-gap aware — same reasoning as the
fare model above:** the warehouse holds eight disjoint monthly blocks
(2024-01, 2024-03, 2024-06, 2025-01, 2025-11, 2026-01, 2026-03, 2026-04),
not one continuous range, so a plain 70/15/15 row-count split would land a
cutoff partway *into* a block and mix earlier "train" hours with later
"test" hours from the same block. Instead the cut falls on block
boundaries, with the most recent complete block (2026-04) held out entirely
as test.

Implemented once in `models/data_prep/train_test_split.py`
(`split_demand_blocks`), reused by all four scripts so every model is
trained/evaluated against the same block boundaries. Split cutoffs are
snapped to unique-timestamp boundaries (not raw row position) so that every
zone's row for a shared hour lands in the same split — a plain row-count
cut would otherwise slice a single hour across train/val, since ~262 zones
share each timestamp.

Leakage guard (`max(train.ts) < min(val.ts) < min(test.ts)`) is asserted in
every one of the four training/evaluation scripts and independently in
`tests/test_demand_split_no_leakage.py`.

| Split | Date range (tabular features) | Rows |
|---|---|---|
| train | 2024-01-08 00:00 → 2026-01-31 01:00 | 876,855 |
| val   | 2026-01-31 02:00 → 2026-03-31 23:00 | 155,542 |
| test  | 2026-04-08 00:00 → 2026-04-30 23:00 | 143,730 |

(The LSTM's sliding-window rows only need 24h of warmup, not 168h, so its
raw train/val/test counts differ and start a week earlier in each block.
`compare_models.py` reconciles this by scoring every model on the inner
join of `(pickup_location_id, ts)` across all four representations —
143,730 rows — so "same test set" is literal, not just "same test period.")

**Models:**

1. **EWMA baseline** (`models/ewma_baseline/ewma_forecast.py`) — no
   training. Forecast for hour *t* is simply S_(t-1), the EWMA state one
   step back (α=0.5).
2. **Linear regression** (`models/linear_baseline/linear_regression_model.py`)
   — `sklearn.LinearRegression` on the 10 raw features above, fit on
   train+val.
3. **XGBoost** (`models/xgboost_model/train_xgboost.py`) — manual 4-point
   grid over `max_depth` ∈ {4,6,8}, `learning_rate` ∈ {0.05,0.1},
   `n_estimators` ∈ {300,500}, selected by validation RMSE. Winner:
   `max_depth=6, learning_rate=0.05, n_estimators=500`.
4. **LSTM** (`models/lstm_model/train_lstm.py`) — 1-layer, hidden size 32,
   univariate 24h sliding window → next hour, trained 3 epochs on CPU (no
   GPU in this environment — see the tradeoff note below), Adam lr=1e-3,
   targets standardized with train-set mean/std.

**Metrics — all measured on the shared 143,730-row 2026-04 test
intersection, `models/evaluation/compare_models.py`, 2026-08-23:**

| Model | RMSE | MAE | Inference latency (ms/row) |
|---|---|---|---|
| EWMA baseline | 50.310 | 29.068 | 0.00162 |
| Linear regression | 26.558 | 15.374 | 0.01015 |
| **XGBoost** | **24.220** | **12.630** | 0.03415 |
| LSTM | 96.925 | 44.031 | 0.02060 |

**The LSTM number is a stale artifact, not a model result — do not quote
it as a finding.** `models/lstm_model/lstm_model.pt` was fit on the older
Jan/Mar/Jun-2024 warehouse, and its saved `target_scaling`
(mean 13.85, std 16.12) belongs to that much smaller per-zone-hour scale.
Scoring it against 2026-04 de-normalizes its predictions with the wrong
constants, which is where the 96.9 comes from. `lstm_metadata.json` still
records the old run (test RMSE 5.609 on 180,577 old-warehouse rows).
Retraining it on the current warehouse is the outstanding work; until then
the ladder's honest comparison is EWMA → linear → XGBoost.
`models/ewma_baseline/ewma_baseline_metadata.json` is stale for the same
reason, though EWMA itself has no fitted artifact — its 50.310 above is
computed live from the current `ewma` feature column and is correct.

**RMSE vs. MAE — which matters more here:** RMSE is reported as the primary
metric because a handful of badly-underpredicted surge hours (concerts,
storms, holiday spikes) are the failure mode that actually matters
operationally — under-provisioning drivers during a demand spike is more
costly than a small miss on an ordinary hour, and RMSE's squared-error term
penalizes those large misses harder than MAE does. MAE is still reported
alongside it because it's easier to reason about in plain trip-count terms
when explaining the numbers.

**What each model captures that the others don't:**

- **EWMA baseline** captures short-term momentum only (last few hours'
  trend) with zero training cost — it's the honest floor the other three
  have to beat, and its 50.31 RMSE vs. linear's 26.56 shows lag/calendar
  features are pulling real weight, not window dressing.
- **Linear regression** captures the same signal EWMA does *plus* a
  reference frame per hour-of-day and day-of-week, in a single interpretable
  equation — cheapest model with hour/calendar awareness, coefficients
  double as a plain-English "what drives demand" explanation (below).
- **XGBoost** captures non-linear interactions the linear model can't (e.g.
  "lag_168h matters more on weekday mornings than weekend nights") and wins
  on both RMSE and MAE here — the feature-importance/coefficient comparison
  below shows why.
- **LSTM** captures the shape of the 24h trajectory itself (not just three
  fixed lag points) without any hand-picked lag horizons, which matters if
  the demand pattern shifts to a period the fixed 1h/24h/168h lags don't
  cover — but see the stale-artifact note above: this run's number says
  nothing about whether the architecture can compete, only that the saved
  weights are from a different warehouse.

**Linear coefficients vs. XGBoost feature importances:**

| Feature | Linear coefficient | XGBoost importance (gain) |
|---|---|---|
| lag_1h | +0.894 (largest lag effect) | **0.811** (most important) |
| lag_168h | +0.281 | 0.156 |
| lag_24h | +0.135 | 0.013 |
| hour | +0.139 | 0.006 |
| day_of_week | +0.539 | 0.004 |
| ewma | −0.369 | 0.004 |
| precipitation_mm | −0.659 | 0.003 |
| rolling_7d_avg | +0.055 | 0.002 |
| temperature_c | −0.054 | 0.002 |
| is_weekend | **−3.016** (largest-magnitude linear effect) | 0.000 |

Both models now agree that `lag_1h` — raw persistence — dominates, with
`lag_168h` (same hour, one week ago) a distant second; between them they
account for 97% of XGBoost's gain. `is_weekend` is the single
largest-magnitude linear coefficient but XGBoost assigns it zero
importance — its information is already fully recoverable from
`day_of_week` splits in the trees, so the redundant column adds nothing
once the model can branch on `day_of_week` directly; the linear model,
which can't interact features, still needs it as its own term to express
the weekday/weekend gap. The weather features earn a small but non-zero
share of gain; `precipitation_mm`'s negative linear coefficient (−0.659 per
mm) is the expected direction — rain suppresses pickups — while
`temperature_c`'s effect is near-flat.

**LSTM loss curve** (train/val MSE on the standardized target, 3 epochs,
`models/lstm_model/lstm_metadata.json` / `loss_curve.png`) — from the
superseded 2024-warehouse run described above:

| Epoch | Train MSE | Val MSE |
|---|---|---|
| 1 | 0.2489 | 0.1460 |
| 2 | 0.1356 | 0.1315 |
| 3 | 0.1287 | 0.1273 |

Loss was still decreasing at epoch 3 — that run was capped at 3 epochs
specifically because of the CPU-only constraint in this environment, not
because it converged. Noted here rather than disguised: more epochs is the
first lever to pull once the model is refit on the current warehouse.

**Reproducibility (rule 5):** seed=42 for linear/XGBoost/LSTM (EWMA has no
randomness); date range = the eight-block warehouse snapshot above, train
through 2026-01, test 2026-04; every hyperparameter, split date range, row
count, and library version (`scikit-learn==1.9.0`, `xgboost==3.3.0`,
`torch==2.13.0+cpu`, `pandas==3.0.3`, `numpy==2.5.1`) recorded in each
model's metadata JSON sidecar next to its artifact:
`models/linear_baseline/linear_model_metadata.json`,
`models/ewma_baseline/ewma_baseline_metadata.json`,
`models/xgboost_model/xgb_metadata.json`,
`models/lstm_model/lstm_metadata.json` — the last two of which are the
stale ones flagged above. Combined comparison numbers in
`models/evaluation/compare_results.json`.

## Global Transfer Model (Phase 8/9/10)

**Target:** city-hour total demand (`SUM(total_trips)` per hour), joint
across the 2 real OBSERVED cities only — NYC (`zone_hourly_demand`) and
London (`london_station_hourly_demand`), aggregated to a comparable
city-hour grain. **Features:** the same lag/EWMA/rolling temporal shape as
the per-city XGBoost models, block-gap aware, plus `E_city` — a scaled
static city feature vector (`models/global_transfer/build_features.py`:
log population, population density, lat/lon, cycle-share flag —
`models/global_transfer/build_features.py`'s module docstring documents
exactly which raw columns exist per tier and which are NaN-flagged for the
522 TRANSFER cities, e.g. lat/lon are NULL for all of them).

**Chronological split:** global 70/15/15 `chronological_split()` over the
concatenated NYC+London city-hour series (`models/data_prep/
chronological_split.py`), leakage guard `train.ts.max() < val.ts.min() <
test.ts.min()` asserted in `train_global.py` and tested in
`tests/test_global_transfer_no_leakage.py`. TRANSFER-tier cities never
appear as training/eval rows — tested in
`tests/test_global_transfer_no_transfer_labels.py`.

| Split | Rows (nyc / london) | Date range |
|---|---|---|
| train | 3,697 / 865 | 2024-01-08 → 2026-03-20 |
| val | 792 / 287 | 2026-03-20 → 2026-04-22 |
| test | 215 / 577 | 2026-04-22 → 2026-06-01 |

**Metrics (joint fit, both cities in every split):** val RMSE=1269.75,
MAE=821.02; test RMSE=1046.25, MAE=452.89 (city-hour total-trip counts;
NYC's much larger per-hour scale dominates these totals — not comparable to
the per-zone/per-station RMSE numbers above). Full grid search, feature
importances, library versions in `models/global_transfer/xgb_metadata.json`.

**Honesty (do not remove):** this fits only 2 real cities. `E_city` is
functionally a 2-valued categorical here — nothing above demonstrates
generalization to a third city. **Phase 10 two-city transfer validation**
(`docs/global_transfer_model_comparison.json`, `models/global_transfer/
model_comparison.py`) is the actual non-circular check: train the same
architecture on ONE city only, evaluate on the other, with an ablation that
removes `E_city`. Result: with only 1 training city, `E_city` is constant
across every training row (zero variance), so the ablated and
non-ablated models are numerically identical in both directions
(`city_features_helped: false` both ways) — i.e., **city features provide
no measurable benefit with N=1 training city**, exactly the outcome
expected from a single-city fit and not a claim that city features are
useless in general. Neither direction beats Phase 1's population-scaling
baseline in a directly comparable way (different grain — daily WAPE vs.
hourly RMSE, see the comparison file's explicit grain-mismatch note) but
both leave-one-out RMSEs are large relative to the target scale, consistent
with Phase 1's finding that simple cross-city transfer does not yet beat
a global-mean baseline. **Never describe this model as "globally
validated"** — always "two-city transfer validation," per task instruction.

## Congestion Model (Phase 6)

**Target:** `congestion_multiplier = trip_duration_minutes / free_flow_duration_min`
(`models/congestion/build_features.py`, single tuned XGBoost regressor,
`models/congestion/train_congestion_xgb.py`).

**`free_flow_duration_min` is an ESTIMATE, not a measurement.** This repo
has no road-graph, route-distance, or speed-limit data — the only
graph module (`algorithms/graph/build_zone_graph.py`) builds a trip-*count*
flow graph from `zone_pair_flows`, not a distance/routing graph, and no
dbt mart carries a routing target. Free-flow speed is instead approximated
per 0.5-mile `trip_distance` bucket as the 85th percentile of observed
`avg_speed_mph` within that bucket (the fastest ~15% of trips at that
distance, i.e. the freest observed conditions) — `free_flow_duration_min =
trip_distance / free_flow_speed_mph * 60`. Every output row is tagged
`free_flow_source: "estimated"`; this is checked by
`tests/test_congestion_split_and_labeling.py` and never overridden.

**Judgment call flagged:** the original task brief specified "p10/p15 of
observed speed" for the free-flow proxy — that is backwards (a *low*
percentile of speed is the slow/congested tail, not free-flow). This
implementation uses the 85th percentile of speed instead, which is the
correct direction for the same "freest observed conditions" intent.

**Features:** `trip_distance`, `free_flow_duration_min`, `hour`,
`day_of_week` (raw ints, no cyclical encoding — matches
`models/xgboost_model/build_features.py`'s existing convention),
`is_holiday` (`backend/adapters/holidays_nager.py`, US), `temperature_c`,
`precipitation_mm`, `demand_index` (`zone_hourly_demand.total_trips`,
joined at date/hour/zone grain).

**Split:** chronological, via `models/data_prep/chronological_split.py`'s
`split_demand_blocks()` (same function every other model in this repo
uses — not reimplemented). Reservoir sample of 300,000 rows from
`int_trips_enriched` (113M rows total; full-table training not attempted,
same pattern as `models/fare_prediction/train_fare_xgb.py`).

| Split | Date range | Rows |
|---|---|---|
| train | 2024-01-01 00:08:41 → 2026-03-12 19:22:26 | 207,228 |
| val   | 2026-03-12 19:22:44 → 2026-03-31 23:59:51 | 36,616 |
| test  | 2026-04-01 00:00:39 → 2026-04-30 23:58:31 | 55,787 |

Leakage guard (`max(train.pickup_at) < min(val.pickup_at) < min(test.pickup_at)`)
asserted in `train_congestion_xgb.py` and independently verified by
`tests/test_congestion_split_and_labeling.py`.

**Metrics (actual, measured):**

| Split | RMSE | MAE |
|---|---|---|
| validation | 0.457 | 0.337 |
| **test** | **0.488** | **0.358** |

Hyperparameters (small manual grid, selected by val RMSE):
`max_depth=4, learning_rate=0.1, n_estimators=300`.

**Reproducibility (rule 5):** seed=42, full hyperparameter grid, feature
importances, and library versions (`xgboost==3.3.0`, `pandas==3.0.3`,
`numpy==2.5.1`) recorded in `models/congestion/congestion_metadata.json`
next to `models/congestion/congestion_model.json`.

## Quantile ETA (Phase 7)

**Target:** `trip_duration_minutes`, three independent XGBoost regressors
(`models/eta/train_quantile_eta.py`) using XGBoost's native
`reg:quantileerror` objective (`quantile_alpha` ∈ {0.10, 0.50, 0.90}) — real
pinball-loss quantile regression, not a hand-rolled approximation. Same
feature set and chronological split as the congestion model above (reused,
not duplicated).

**Production ETA composition (`models/eta/compose_eta.py`):**
`ETA = T_freeflow * C`, explicit and visible — `T_freeflow` from the Phase 6
free-flow lookup, `C` from the Phase 6 trained congestion-multiplier point
model. The quantile models above are a separate, direct empirical fit used
only to measure prediction-interval coverage; they are not what
`compose_eta.py` calls at inference time, per the spec's instruction not to
hide the free-flow/congestion decomposition behind an opaque end-to-end
model.

**Metrics (actual, measured, same 55,787-row test split as the congestion
model):**

| Quantile | Pinball loss | MAE (minutes) |
|---|---|---|
| p10 | 0.799 | 6.47 |
| p50 | 2.189 | 4.38 |
| p90 | 1.199 | 8.68 |

**Prediction interval coverage — measured, not assumed:** fraction of the
55,787 held-out test rows where the actual trip duration fell within
`[p10_pred, p90_pred]` is **78.9%**, against a nominal 80% target — close,
slightly under. This is reported plainly rather than rounded up to "well
calibrated"; a 1.1-point gap on real held-out data is a genuine (if small)
under-coverage, not proof of perfect calibration.

**Ordering (p10 ≤ p50 ≤ p90):** violated on 26 of 55,787 test rows
(0.047%) — expected/normal for independently trained quantile models (no
monotonicity constraint enforced between them), verified to be a small
fraction rather than a systemic failure by
`tests/test_quantile_eta_ordering_and_coverage.py`.

**Reproducibility (rule 5):** seed=42, quantile config, per-quantile
pinball loss/MAE, measured coverage, and library versions
(`xgboost==3.3.0`, `pandas==3.0.3`, `numpy==2.5.1`) recorded in
`models/eta/eta_metadata.json` next to `models/eta/eta_p10_model.json`,
`eta_p50_model.json`, `eta_p90_model.json`.

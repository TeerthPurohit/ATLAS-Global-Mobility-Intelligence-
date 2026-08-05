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
all 261 zones. **Features** (`models/data_prep/build_features.py`, reusing
`algorithms/timeseries/ewma_smoothing.py`'s block splitter): `hour`,
`day_of_week`, `is_weekend`, `lag_1h`, `lag_24h`, `lag_168h`, `ewma`
(EWMA state one step back, α=0.5 — the cross-zone default set in SPEC-005),
`rolling_7d_avg` (trailing 168h mean). All lag/EWMA/rolling features are
computed strictly from hours *before* t (`.shift(1)`) so none of them leak
the row's own target into its own feature — verified in
`build_features.py`'s `demo()`.

**Chronological split (ADR-003), block-gap aware — same reasoning as the
fare model above:** the warehouse only has Jan/Mar/Jun 2024, so a plain
70/15/15 row-count split would land the test cutoff partway into June. This
deviates from a naive single-cutoff 70/15/15 deliberately:

- **train + val = January + March**
- **test = June in full** — the most recent complete block, held out
  entirely
- within Jan+Mar, the most recent 15% by timestamp is validation

Implemented once in `models/data_prep/train_test_split.py`
(`split_demand_blocks`), reused by all four scripts so every model is
trained/evaluated against the same block boundaries. Split cutoffs are
snapped to unique-timestamp boundaries (not raw row position) so that every
zone's row for a shared hour lands in the same split — a plain row-count
cut would otherwise slice a single hour across train/val, since 261 zones
share each timestamp.

Leakage guard (`max(train.ts) < min(val.ts) < min(test.ts)`) is asserted in
every one of the four training/evaluation scripts.

| Split | Date range (tabular features) | Rows |
|---|---|---|
| train | 2024-01-08 00:00 → 2024-03-24 18:00 | 252,121 |
| val   | 2024-03-24 19:00 → 2024-03-31 23:00 | 44,669 |
| test  | 2024-06-08 00:00 → 2024-06-30 23:00 | 142,993 |

(The LSTM's sliding-window rows only need 24h of warmup, not 168h, so its
raw train/val/test counts are larger — 315,432 / 55,806 / 180,577 — and
start a week earlier in each block. `compare_models.py` reconciles this by
scoring every model on the inner join of `(pickup_location_id, ts)` across
all four representations, 142,993 rows, so "same test set" is literal, not
just "same test period.")

**Models:**

1. **EWMA baseline** (`models/ewma_baseline/ewma_forecast.py`) — no
   training. Forecast for hour *t* is simply S_(t-1), the EWMA state one
   step back (α=0.5).
2. **Linear regression** (`models/linear_baseline/linear_regression_model.py`)
   — `sklearn.LinearRegression` on the 8 raw features above, fit on
   train+val.
3. **XGBoost** (`models/xgboost_model/train_xgboost.py`) — manual 4-point
   grid over `max_depth` ∈ {4,6,8}, `learning_rate` ∈ {0.05,0.1},
   `n_estimators` ∈ {300,500}, selected by validation RMSE. Winner:
   `max_depth=6, learning_rate=0.05, n_estimators=500`.
4. **LSTM** (`models/lstm_model/train_lstm.py`) — 1-layer, hidden size 32,
   univariate 24h sliding window → next hour, trained 3 epochs on CPU (no
   GPU in this environment — see the tradeoff note below), Adam lr=1e-3,
   targets standardized with train-set mean/std.

**Metrics — all measured on the shared 142,993-row June test intersection,
`models/evaluation/compare_models.py`, 2026-08-06:**

| Model | RMSE | MAE | Inference latency (ms/row) |
|---|---|---|---|
| EWMA baseline | 7.456 | 4.617 | 0.00124 |
| Linear regression | 5.418 | 3.529 | 0.01025 |
| **XGBoost** | **5.089** | **3.259** | 0.03432 |
| LSTM | 5.634 | 3.656 | 0.03219 |

**RMSE vs. MAE — which matters more here:** RMSE is reported as the primary
metric because a handful of badly-underpredicted surge hours (concerts,
storms, holiday spikes) are the failure mode that actually matters
operationally — under-provisioning drivers during a demand spike is more
costly than a small miss on an ordinary hour, and RMSE's squared-error term
penalizes those large misses harder than MAE does. MAE is still reported
alongside it because it's easier to reason about in plain trip-count terms
("off by ~3-4 trips/hour on average") when explaining the numbers.

**What each model captures that the others don't:**

- **EWMA baseline** captures short-term momentum only (last few hours'
  trend) with zero training cost — it's the honest floor the other three
  have to beat, and its 7.46 RMSE vs. linear's 5.42 shows lag/calendar
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
  cover — but with only 3 CPU-bound epochs it doesn't yet out-predict
  XGBoost on this dataset; more epochs (and calendar features it currently
  lacks) would be the first thing to try before concluding LSTM can't win
  here.

**Linear coefficients vs. XGBoost feature importances:**

| Feature | Linear coefficient | XGBoost importance (gain) |
|---|---|---|
| lag_168h | +0.362 | **0.596** (most important) |
| lag_1h | +0.511 (largest linear effect) | 0.322 |
| lag_24h | +0.152 | 0.034 |
| is_weekend | **−0.668** (largest-magnitude linear effect) | 0.000 |
| day_of_week | +0.171 | 0.010 |
| ewma | −0.095 | 0.015 |
| rolling_7d_avg | +0.068 | 0.010 |
| hour | +0.053 | 0.013 |

Both models agree the lag features dominate, but disagree on *which* lag
matters most: linear regression weights `lag_1h` (raw persistence) highest,
while XGBoost's gain-based importance puts `lag_168h` (same hour, one week
ago) far ahead of everything else — consistent with strong weekly
seasonality that a single global linear coefficient per feature can't fully
express (the same `lag_168h` value means something different on a Tuesday
morning than a Saturday night; XGBoost's trees can split on that, a linear
term can't). `is_weekend` is the single largest-magnitude linear coefficient
but XGBoost assigns it zero importance — its information is already fully
recoverable from `day_of_week` splits in the trees, so the redundant column
adds nothing once the model can branch on `day_of_week` directly; the linear
model, which can't interact features, still needs it as its own term to
express the weekday/weekend gap.

**LSTM loss curve** (train/val MSE on the standardized target, 3 epochs,
`models/lstm_model/lstm_metadata.json` / `loss_curve.png`):

| Epoch | Train MSE | Val MSE |
|---|---|---|
| 1 | 0.2489 | 0.1460 |
| 2 | 0.1356 | 0.1315 |
| 3 | 0.1287 | 0.1273 |

Loss is still decreasing at epoch 3 — this run is capped at 3 epochs
specifically because of the CPU-only constraint in this environment (~557k
training sequences across 261 zones), not because it converged. Noted here
rather than disguised: more epochs is the first lever to pull if LSTM needs
to beat XGBoost rather than just be competitive with it.

**Reproducibility (rule 5):** seed=42 for linear/XGBoost/LSTM (EWMA has no
randomness); date range = Jan+Mar (train+val) / Jun (test) 2024 warehouse
snapshot; every hyperparameter, split date range, row count, and library
version (`scikit-learn==1.9.0`, `xgboost==3.3.0`, `torch==2.13.0+cpu`,
`pandas==3.0.3`, `numpy==2.5.1`) recorded in each model's metadata JSON
sidecar next to its artifact: `models/linear_baseline/linear_model_metadata.json`,
`models/ewma_baseline/ewma_baseline_metadata.json`,
`models/xgboost_model/xgb_metadata.json`,
`models/lstm_model/lstm_metadata.json`. Combined comparison numbers in
`models/evaluation/compare_results.json`.

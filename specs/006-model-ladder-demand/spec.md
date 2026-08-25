# SPEC-006: Model Ladder — Zone-Hourly Demand Forecasting

Owner: solo builder · Status: done · Layer: 3 · Depends on: SPEC-002, SPEC-005

## Business Goal

Four models predicting `zone_hourly_demand`, increasing in complexity,
compared honestly on one shared test set. The point is the comparison
story, not any single model's accuracy.

## Functional Requirements

- FR-1: `build_features.py` — hour, day-of-week, is_weekend, lag_1h,
  lag_24h, lag_168h, EWMA value, 7-day rolling average.
- FR-2: `train_test_split.py` — chronological split (see ADR-003), not
  random.
- FR-3: Linear regression baseline, coefficients reported and interpreted.
- FR-4: EWMA baseline — last known EWMA value as next-hour forecast, no
  training.
- FR-5: XGBoost — tuned depth/learning_rate/n_estimators, feature
  importances plotted and compared against linear coefficients.
- FR-6: LSTM/GRU — sliding-window sequence (24h → next hour), 1-2 layers,
  trained on Colab/Kaggle GPU, loss curves tracked.
- FR-7: `compare_models.py` — all 4 models on the same chronological test
  set, RMSE + MAE + inference latency.
- FR-8: `metrics_report.md` — comparison table + one sentence per model on
  what it captures that others don't.

## Non-Functional Requirements

- Reproducibility per rule 5 in `.claude/rules.md`: seed, date range,
  hyperparameters, metrics recorded for every trained model.
- Report both RMSE and MAE, not just one (RMSE penalizes large errors more;
  state which matters more for this use case and why).

## ML Design

Target: `zone_hourly_demand.pickup_count`. Split: chronological 70/15/15
(ADR-003). Baseline: linear regression / EWMA. Candidates: XGBoost, LSTM.
Evaluation: RMSE, MAE, inference latency — all measured, none estimated
(rule 2).

## Testing

- Assert chronological split has no leakage (`max(train_ts) < min(test_ts)`).
- Assert all 4 models are evaluated on the *identical* test rows.

## Acceptance Criteria

- [ ] All 4 models trained and evaluated on the same chronological test set.
- [ ] `metrics_report.md` has real RMSE/MAE/latency numbers, not placeholders.
- [ ] Feature importance (XGBoost) vs coefficients (linear) compared and
      discussed.
- [ ] LSTM loss curves included.

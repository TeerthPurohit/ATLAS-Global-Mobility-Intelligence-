# SPEC-007: Fare Prediction Model

Owner: solo builder · Status: done · Layer: 3 · Depends on: SPEC-002

## Business Goal

Predict trip fare given pickup zone, dropoff zone, hour, day-of-week,
distance. Secondary model — deliberately kept to one algorithm (XGBoost),
not a full ladder like demand forecasting.

## Functional Requirements

- FR-1: `train_fare_xgb.py` — features: pickup zone, dropoff zone, hour,
  day-of-week, trip distance. Target: `total_amount` from `zone_fare_stats`
  / `int_trips_enriched`.
- FR-2: Chronological split (ADR-003) applies here too — fares vary by
  season/surge patterns over time, same leakage risk as demand.

## Non-Functional Requirements

Don't over-build this one — no ladder, no LSTM variant. One tuned XGBoost
model with a reported RMSE/MAE is the full scope.

## Testing

Chronological-split-no-leakage assertion, same as SPEC-006.

## Acceptance Criteria

- [ ] Model trained, RMSE/MAE reported in `models/evaluation/metrics_report.md`.
- [ ] Chronological split verified, no leakage.

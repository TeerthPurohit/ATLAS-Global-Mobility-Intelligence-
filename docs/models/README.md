# Models

Full methodology, chronological-split reasoning, and all real numbers live
in [`models/evaluation/metrics_report.md`](../../models/evaluation/metrics_report.md)
(rule 2 -- every metric there traces to a training script's actual output).
This page is the map from model artifact to what's actually serving it.

## Demand ladder (SPEC-006)

| Model | Test RMSE | Test MAE | Registered as |
|---|---|---|---|
| EWMA baseline | 7.456 | 4.617 | `ewma_fallback_v1` |
| Linear regression | 5.418 | 3.529 | not registered (research-only, not served) |
| **XGBoost (best)** | **5.089** | **3.259** | `xgboost_demand_v1` |
| LSTM | 5.634 | 3.656 | not registered (research-only, not served) |

`backend/services/model_service.py` serves `xgboost_demand_v1`; if the raw
prediction extrapolates negative for a low-volume zone, it honestly falls
back to `ewma_fallback_v1` (the zone's own EWMA estimate) rather than
clamping to a fake zero -- the response's `model` field always says which
one actually answered.

## Fare (SPEC-007)

Single tuned XGBoost regressor, test RMSE 12.61 / MAE 6.29 (June 2024, held
out whole). Registered as `xgboost_fare_v1`.

## Journey Intelligence Engine (SPEC-012, ADR-007)

Not a single trained model -- `backend/predictors/journey_predictors.py` is
a fixed sequence of predictors, each returning a `PredictionResult` with an
honest `basis` (`computed` / `modeled_estimate` / `unavailable`). Registered
as `journey_predictors_v1` (`model_type=rule_based_ensemble`).

## Model registry (SPEC-013)

`dbt_project/seeds/model_registry.csv` catalogs every artifact above (path,
version, training period, status, metrics sidecar) -- no retraining,
just a queryable index. `backend/registry/models.py` validates every
`artifact_path` exists on disk at startup; a row that claims `status=active`
but is missing its file is demoted to `unavailable` rather than crashing or
silently serving nothing. `GET /api/cities/{city_id}/capabilities` reflects
exactly this table, not a hand-authored true/true/true.

## Chronological split discipline (rule 3, ADR-003)

The warehouse has three disjoint monthly blocks (Jan/Mar/Jun 2024), not a
continuous timeline. Every model here trains+validates on Jan+Mar and holds
out June in full as test -- see `models/evaluation/metrics_report.md` for
why a naive 70/15/15 row-count split would leak future rows into training.

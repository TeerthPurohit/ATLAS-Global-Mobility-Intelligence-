# Transformer vs. XGBoost -- zone-hourly demand (Phase 1)

Both models scored on the identical chronological test rows (inner join
of the tabular and sequence test sets on `(pickup_location_id, ts)`),
same methodology as `models/evaluation/compare_models.py`.

**Scope:** trained/evaluated on the full ~262-zone warehouse. Real measured numbers, not estimates.

| Model | RMSE | MAE | Inference latency (ms/row) | n_rows |
|---|---|---|---|---|
| xgboost | 24.220 | 12.630 | 0.01766 | 143730 |
| transformer | 26.343 | 14.986 | 0.41539 | 143730 |

XGBoost's engineered lag/EWMA/calendar features already hand it the
signal the Transformer has to learn implicitly from 24 raw hourly counts,
which is the likely reason it leads on both RMSE and MAE here;
the Transformer is also ~23.5x slower per row (attention over 24 steps vs. tree traversal).

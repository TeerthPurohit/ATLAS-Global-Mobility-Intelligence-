# ADR-003: Chronological train/val/test split for all demand and fare models

**Status:** Accepted (Layer 3, not yet started)

## Context

`zone_hourly_demand` and fare targets are time-ordered series. A random
train/test split is the default in most ML tutorials and in `sklearn`'s
`train_test_split` — but it's wrong here.

## Decision

Split chronologically: earliest ~70% of the date range trains, next ~15%
validates, final ~15% tests. Enforced in
`models/data_prep/train_test_split.py`, verified by a test asserting
`max(train_timestamp) < min(test_timestamp)`.

## Why

Lag features (`lag_1h`, `lag_24h`, `lag_168h`) and EWMA-smoothed values mean
each row's features are partly derived from *other* rows' target values. A
random split puts some of those related rows in train and others in test —
the model effectively sees a smoothed/lagged echo of the test answer during
training, inflating validation metrics in a way that won't hold on genuinely
future data. A chronological split is the only split where "test" actually
means "data the model has never seen, including indirectly."

## Consequences

- Validation metrics will look worse than a random split would report — this
  is the honest number, not a regression.
- Cross-validation (k-fold) is also inappropriate for the same reason;
  if any hyperparameter search is added later, use a rolling-origin
  (walk-forward) scheme, not k-fold — noted here so it isn't silently
  reintroduced.

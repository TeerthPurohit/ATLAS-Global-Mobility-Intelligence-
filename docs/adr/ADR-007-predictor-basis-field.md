# ADR-007: A structural `basis` field on every journey prediction

**Status:** Accepted (Journey Intelligence Engine, Phase 1)

## Context

The Journey Intelligence Engine (`POST /journey/estimate`) returns outputs
that are genuinely different in kind: a fare from a trained model backed by
years of real trips, versus a "Ride Availability Score" or "Surge Risk" that
no provider anywhere publishes ground truth for (Uber/Ola/Lyft don't expose
real driver-supply or surge data to third parties). Both need to appear in
the same response shape, but presenting them with equal confidence would
violate `.claude/rules.md` rule 2 ("never fabricate results... if a number
can't be computed, don't estimate one that looks plausible").

## Decision

Every prediction is a `PredictionResult` (`backend/predictors/base.py`):
`value`, `unit`, `basis`, `source`, and `reason` (required whenever
`basis != "computed"`). `basis` is one of three states:

- `computed` — a real algorithm, trained model, or deterministic formula
  produced this value (e.g. the XGBoost fare model, carbon = distance ×
  emission factor).
- `modeled_estimate` — a proxy-based guess with no ground truth to compare
  against, surfaced as a qualitative bucket + reason rather than a fake
  precise number (Ride Availability: HIGH/MEDIUM/LOW; Surge Risk:
  LOW/MEDIUM/HIGH/VERY_HIGH — never "Surge = 1.8x", never a driver count).
- `unavailable` — no data source exists yet (e.g. live traffic, which needs
  a paid API this project has no budget for) — `reason` says why, and the
  field is `null`, never a fabricated fallback.

`PredictionResult.__post_init__` enforces the reason requirement at
construction time, not by convention.

## Why

This makes rule 2 a type-level property of the API response instead of a
discipline every new predictor author has to remember. It also makes
"global" honest: a data-rich location (NYC) and a data-poor one can return
the same response shape with very different `basis` mixes, and the
`confidence` field (a deterministic function of the `basis` mix, not
another model) tells the caller exactly how much to trust the response —
see the plan's "global means degrading honestly" design principle.

## Consequences

- Every predictor has to actively choose a `basis`, not just return a
  number — slightly more code per predictor, but it's what stops a future
  "let's just estimate driver availability" PR from silently becoming a
  fabricated metric.
- Frontend/API consumers must handle three states per field, not one —
  acceptable, since a UI that only shows `value` and ignores `basis` is
  making the exact mistake this ADR exists to prevent.

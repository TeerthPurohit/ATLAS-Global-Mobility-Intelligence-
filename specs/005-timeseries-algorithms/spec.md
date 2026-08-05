# SPEC-005: Time-Series Algorithms — EWMA + Seasonality Decomposition

Owner: solo builder · Status: not started · Layer: 2 · Depends on: SPEC-002 (`zone_hourly_demand`)

## Business Goal

Smooth noisy hourly demand into a trend signal and separate it into
trend/seasonal/residual — these outputs become Layer 3 ML features
(EWMA value, rolling average) and the EWMA-baseline model itself.

## Functional Requirements

- FR-1: `ewma_smoothing.py` — `S_t = α*x_t + (1-α)*S_(t-1)` over
  `zone_hourly_demand`, from scratch.
- FR-2: `seasonality_decompose.py` — decompose each zone's hourly demand
  into trend + daily seasonality + weekly seasonality + residual.
- FR-3: Visualize 2-3 contrasting zones (e.g. an airport, a nightlife zone,
  a residential zone) side by side.

## Proposed Design

Additive model `y_t = Trend_t + Seasonal_t + Residual_t` unless seasonal
swings visibly grow with the level (then multiplicative) — check the actual
data before choosing, don't default to additive without looking.

## Testing

Validate the from-scratch decomposition against
`statsmodels.tsa.seasonal_decompose` on the same series (same pattern as
PageRank/KD-tree: from-scratch implementation, validated against a
reference library).

## Risks

Choice of α (smoothing factor) trades bias against variance — pick a value
and justify it against an actual plotted comparison of a few α values on a
real zone's series, not by default/convention alone.

## Acceptance Criteria

- [ ] EWMA implementation validated against `pandas.ewm` or equivalent.
- [ ] Decomposition validated against `statsmodels.seasonal_decompose`.
- [ ] 2-3 zone decomposition plots produced, saved for the README.
- [ ] Additive vs multiplicative choice justified from real data, not assumed.

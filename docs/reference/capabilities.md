# Capabilities & the `basis` Contract

This page explains the vocabulary the API uses to tell you, per field, whether
a number is real, an honest estimate, or genuinely unavailable — and how
that maps to what a given city can actually do. For the literal request/
response shapes, use the live API reference (Swagger UI, linked in this
site's navigation) generated straight from the running backend, not this
page.

## `basis`: the three states every prediction carries

Every numeric field returned by this platform (`PredictionEnvelope`,
`PredictionOut`, and the internal `PredictionResult` type they wrap) carries
a `basis` value instead of a bare number. This is enforced at construction
time (`backend/predictors/base.py`), not just a naming convention — see
[ADR-007](../adr/ADR-007-predictor-basis-field.md).

| `basis` | Meaning | Example |
|---|---|---|
| `computed` | A real trained model or deterministic algorithm ran against real observed data. | NYC's XGBoost demand prediction; OSRM route distance for any city. |
| `modeled_estimate` | A transparent, bounded formula derived from real reference data rather than a direct measurement. Never presented as measured fact — always carries a `reason` explaining the calibration and its limits. | A tariff-profile fare (linear base/per-km/per-min) where no trained fare model covers the request. |
| `unavailable` | No real data source exists for this field right now. `value` is `null`, `reason` says why. | A demand model for a city with no resolvable population; weather when Open-Meteo is unreachable. |

`unavailable` is not an error — it's the honest answer to "we don't have
this," returned as a normal `200` response (see `CapabilityUnavailable` in
`backend/schemas.py`), never a fabricated number and never a bare 4xx for a
well-formed request.

## Chat tiers

`GET /api/cities/{city_id}/capabilities` exposes `chat_tier`, computed —
not curated — from two real infrastructure facts per city (see
`backend/registry/cities.py`'s `get_chat_tier()`):

| Tier | Requires | What chat can do |
|---|---|---|
| `full_rag` | A registered warehouse **and** a generated insight-doc corpus | Real SQL for numeric questions, LLM-synthesized narrative (grounded only in retrieved doc text) for explanatory questions. |
| `sql_only` | A registered warehouse, no insight docs | Real SQL against that city's own warehouse for numeric questions; explanatory questions get an honest "no insight documents exist for this city yet" instead of borrowing another city's prose. |

Today `nyc` is `full_rag` — the only registered city (ADR-012), and it has
both a warehouse and an insight corpus. `sql_only` is computed the same way
and would apply to a second city registered without insight docs; an
unregistered `city_id` never reaches the tier logic at all, because the
routers 404 it first. Adding a city's chat capability means registering its
warehouse (needed for predictions/journey anyway) and, optionally,
generating insight docs — never a chat-specific code change.
See [Adding a City](../guides/adding-a-city.md).

## What `get_capabilities()` actually checks

`backend/registry/cities.py`'s `get_capabilities(city_id)` never trusts a
seed column — every flag is computed live:

- `demand` / `fare` — is there an `active` row in `model_registry` for this city+metric?
- `journey` — same, for the `journey` metric (NYC's full pipeline only).
- `area_analysis` — does `canonical_areas` have any rows for this city?
- `forecast` — `demand or fare`.
- `transit_coverage` — is a GTFS feed both configured (not the unverified
  placeholder) *and* actually ingested (`gtfs_stops` has real rows)?
- `chat_tier` — see above.

A city missing from `model_registry`/`canonical_areas`/`gtfs_feeds` simply
reports `false`/`context_only` for the relevant flags — it is never silently
promoted to look more capable than it is.

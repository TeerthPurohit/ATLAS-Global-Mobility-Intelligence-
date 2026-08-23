# ADR-012: NYC only — removing London

**Status:** Accepted (2026-08-23)

**Follows:** [ADR-011](ADR-011-retreat-from-global-coverage.md), which cut
519 synthetic cities down to the two with real observed trip data. This cuts
the remaining two to one.

## Context

ADR-011 kept London deliberately, and the reasoning was explicit: London is a
different mobility mode (docked bike share, not ride-hailing), so making the
same pipeline, feature engineering, and chronological-split discipline work
on both was real evidence the architecture generalizes. Two real cities of
different modes was framed as "the honest version of the claim the global
layer was trying to make."

That argument still holds on its own terms. It was overruled on a different
one: the project is a demonstration of depth on NYC's 113M-row TLC corpus,
and London's ~2.2M bike journeys were consuming maintenance surface without
deepening that. Every shared code path carried a second branch; every mart,
schema, registry and test carried a second case. The generalization was real
but it was not the thing being demonstrated.

## Decision

Serve NYC only. `int_trips_enriched` keeps all **113,075,686** rows — the
NYC corpus is untouched and is the point of the project.

**Removed:** `london_cycles.duckdb` (224 MB) and `data/raw/london/` (351 MB);
the four London dbt models and the `tfl_cycling` source; the
`london_stations` seed and every London row in `cities`, `model_registry`,
`gtfs_feeds` and `weather_hourly`; `models/london_demand/`;
`backend/datasources/london_cycles.py`; `rag/nl_to_sql/london_schema.py`;
`generate_london_insight_docs.py` and its corpus;
`scripts/ingest_tfl_cycle_hire.py`; `tests/test_london_model.py`,
`test_london_pipeline.py`, `test_model_service_per_city.py`; and the London
branch in every shared registry, service, predictor and bbox.

**Also removed, as collateral of ADR-011 that survived that pass:**
`geography_service`'s WorldMove grid-cell KD-tree machinery
(`_get_grid_cell_tree`, `_grid_cell_trees`), which had been reading
`canonical_areas` rows of a type that no longer exists.

**Kept:** the multi-city *shape*. `city_id` stays on the routes, the schemas,
the marts and the registry; `canonical_areas` keeps its `city_id` column;
`_CITY_ARTIFACTS`, `_CITY_WAREHOUSE_PATHS`, `_CITY_DB_PATH` and friends stay
as dicts with one entry. See "Collapsing city_id" below — that is a separate
decision, not deferred by accident.

## Consequence: a test got stronger

`canonical_areas.area_id` now carries a real `relationships` test against
`stg_zones.location_id`. That test had been deliberately omitted, with a
comment explaining that it only ever matched NYC rows and that 799/799
London area_ids failed it. With NYC-only rows the check is both true and
enforceable, so it is enforced. This is the one place where narrowing scope
bought back a genuine integrity guarantee rather than just deleting code.

Conversely, `test_at_least_two_distinct_non_usd_currencies_are_exercised` —
already weakened to `>=1` under ADR-011 — now skips rather than fails when
the tariff store holds only USD profiles, because with NYC alone there may
legitimately be no non-USD currency to exercise. It still fails loudly if
the store is empty, which is the vacuity it was really guarding against.

## Collapsing `city_id`

The obvious follow-on is to strip `city_id` entirely: 681 Python references
and 184 TypeScript ones, plus every `/api/cities/{city_id}/...` route. That
is a real simplification and it is not being rejected — it is being
sequenced separately, because it is a breaking API change with no behavioural
benefit, and mixing it into this commit would make a mechanical 865-site
rename indistinguishable from the functional London removal in review. Do it
as its own change, against a green suite, or not at all.

## Reversibility

London is materially easier to restore than WorldMove was. The TfL data is
public and the manifest recorded exactly what was pulled:

- Journey extracts: `https://cycling.data.tfl.gov.uk/usage-stats/` —
  files `435`, `436`, `439`, `440`, `443`, `444`
  (`JourneyDataExtract`, 01 Jan 2026 – 31 May 2026)
- Stations: `https://api.tfl.gov.uk/BikePoint`
- Pulled 2026-08-08; 2,195,790 journeys across 799 stations

The ingestion script, dbt models, feature builder and trained model are all
recoverable from git history at this commit's parent. Restoring London is
re-running a documented pipeline, not reconstructing lost data.

## Alternatives considered

**Keep London's dbt models and data, drop only the serving code.** Rejected:
a mart nothing reads is the dead weight this whole sequence has been
removing. Half-deleting it would leave the maintenance cost with none of the
demonstration value.

**Keep London and drop NYC's non-demand extras instead.** Not seriously
entertained — NYC's corpus is the project. Raised only to record that the
choice was about which city, not about trimming generally.

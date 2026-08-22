# ADR-011: Retreat from global coverage to NYC + London

**Status:** Accepted (2026-08-23)

**Reverses:** ADR-007's `basis`-field generalization insofar as it existed to
serve unmodeled cities, ADR-008's global framing, SPEC-013 (global mobility
domain model), SPEC-016 (WorldMove grid), and
`docs/superpowers/plans/2026-08-09-global-city-registry.md`.

## Context

The platform had grown to claim coverage of 519 cities. Two of them — NYC
(TLC high-volume for-hire trip records) and London (Santander Cycles) — had
real observed data, trained models, and honest evaluation. The other ~517
were served by a tier system (`OBSERVED` / `TRANSFER` / `NONE`) layered over
WorldMove synthetic trajectories, population-scaled demand estimates, and
LLM-generated tariff profiles.

Three problems converged:

1. **The source data was not trustworthy.** WorldMove population and
   `country_code` were found unreliable at the raw `.npy` source — not a
   pipeline bug, a data-quality property of the upstream corpus (four rows
   were unresolvable and had to be dropped outright). Separately, 72% of the
   517 tariff profiles turned out to be duplicate LLM templates rather than
   city-specific figures.

2. **Breadth crowded out depth.** Effort that could have deepened the two
   cities with real data went into plumbing for cities without it. The
   generalization work (adapter pattern, vehicle profiles, transfer
   learning, cross-city estimation, tariff enrichment) was substantial and
   served the weakest part of the product.

3. **It presented badly.** The world map and tier taxonomy were the first
   thing a visitor saw, and they were built on the least defensible data in
   the repo. A `TRANSFER`-tier city showed a fare and a demand figure that
   looked exactly like NYC's measured ones, distinguished only by a badge.

The third problem is the tell. Rule 2 says no fabricated metrics; rule 1 says
prefer SQL, an algorithm, or a trained model over an LLM call. A
population-scaled demand estimate shaped by NYC's hourly curve, priced by an
LLM-invented tariff, is not a fabricated metric in the sense of being made
up at render time — every component was real and honestly labeled. But
stacking four honest approximations and presenting the result beside a
measured number, in the same visual language, is the same failure at a
different altitude.

## Decision

Serve only cities with real observed trip data. Today that is NYC and
London.

**Removed:** the `global_cities` registry (523 rows), the `countries`
registry, `global_geography_service`, the GeoNames and Google Places
adapters, `tariff_enrichment` (on-demand LLM tariff generation),
`estimation_service` (population-scaled demand and PPP-scaled fares), the
five WorldMove dbt models, `models/global_transfer/`,
`models/cross_city_estimation/`, the `/api/countries/*` and
`/api/geography/*` routers, and the world-map / country-browse frontend.

**Kept:** everything backed by measured data — both cities' dbt models,
their trained demand and fare models, `tariff_profiles` (NYC's and London's
are calibrated against real fares), the journey/prediction/chat paths, the
adapter pattern for weather/holidays/routing.

**Consequence for the tier system:** `model_status` is now `OBSERVED` for
every city the API will resolve, and `confidence` is 1.0. Both fields are
kept in the schema rather than deleted, because they still say something
true and a future third city needs somewhere to be honest about itself. The
`context_only` chat tier is gone — every city this repo serves has a
warehouse to answer from.

**Consequence for `capability_matrix`:** it now returns `None` for an
unregistered `city_id` instead of a mostly-false matrix. A city we have no
data for gets a 404, not a degraded answer. This is a deliberate narrowing:
"we don't cover that" is more useful than a routing-only estimate dressed
in the same UI as a measured one.

## Alternatives considered

**Hide the global layer behind a feature flag.** Rejected: the code would
keep compiling, keep needing maintenance, and keep being a live path one
config change away from returning. The data-quality problems don't improve
by being unreachable.

**Keep WorldMove as an internal prior for cold-start cities, drop only the
global UI.** Rejected for now. It is a legitimate technique and might come
back, but there is no cold-start city to serve — the next city added will be
one with real data, since that is now the bar for being added at all.
Keeping the machinery for a use case that doesn't exist is the speculative
generality the rest of this repo avoids.

**Cut to NYC only.** Rejected. London is a genuinely different mobility mode
(docked cycle hire, not ride-hailing) with its own real corpus and trained
model. Keeping it preserves the multi-city plumbing under conditions where
that plumbing is honest, which is the difference between a generalization
that's earned and one that's assumed.

## Notes

`backend/services/tariff_profiles.py` previously cited "ADR-011" in its
docstring while `docs/adr/` stopped at 010 — a dangling reference to an ADR
that was never written. That citation now points here, which is
coincidentally apt: this decision is the one that settles what tariff
profiles are for.

The superseded specs and plans are kept, marked superseded rather than
deleted. A reversed decision that stays on the record is worth more than one
that's erased — including the reasoning that made global coverage look right
at the time.

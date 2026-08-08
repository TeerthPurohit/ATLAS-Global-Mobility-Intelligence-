# SPEC-014: Schema-Agnostic Query Plan + Fine-Tuned Model

Owner: solo builder · Status: draft · Layer: 5+ (extends Layer 4) ·
Depends on: SPEC-008 (Hybrid RAG)

## Business Goal

Today's NL-to-SQL (`rag/nl_to_sql/sql_agent.py`) generates SQL text tied
directly to NYC's real column names (`pickup_location_id`, `zone_hourly_demand`,
...). That does not generalize: a model fine-tuned on NYC's raw SQL would not
transfer to a future city with different table/column names. This spec
builds and fine-tunes a model on a **schema-agnostic** intermediate instead —
a `QueryPlan` (intent/metric/filters/aggregation, no table or column names) —
so the skill being trained is "map a question onto a canonical mobility
concept," not "know NYC's schema." A separate deterministic per-city compiler
turns the plan into real SQL. This pulls forward the minimal slice of
SPEC-013's paused FR-9/FR-10 (Canonical Mobility Query Plan) needed to make
this fine-tune meaningful, without resuming the rest of that (larger, still
paused) spec.

Non-goal: this does not change the currently-live `POST /chat` path. The
fine-tuned model is wired in behind an opt-in flag, default off — see
Acceptance Criteria.

## Functional Requirements

- FR-1: `rag/nl_to_sql/query_plan.py` — `QueryPlan` (intent, metric, filters
  [hour, day_of_week, area, date_range], aggregation, group_by, order, limit)
  and `CityMobilitySchema` (a per-city canonical-field -> real-column
  resolver + a `describe()` that renders a compact text schema description
  for LLM context).
- FR-2: `rag/nl_to_sql/query_plan_compiler.py` — `compile(plan, schema) ->
  sql`. Validates every field the plan references resolves against the
  given `CityMobilitySchema` before compiling; raises rather than emitting
  SQL for an unresolvable field (this is also the injection-safety win noted
  in SPEC-013: the LLM never writes SQL text, only a constrained JSON plan).
- FR-3: `rag/nl_to_sql/nyc_schema.py` — the one real `CityMobilitySchema`:
  resolves `area` -> `pickup_location_id`, `demand` -> `total_trips`
  (`zone_hourly_demand`), `fare` -> `avg_fare` (`zone_fare_stats`), `hour` ->
  `pickup_hour`, `day_of_week` -> `pickup_day_of_week`, `flow` ->
  `zone_pair_flows`.
- FR-4: `rag/nl_to_sql/synthetic_schemas.py` — 4 invented, internally
  consistent, non-NYC `CityMobilitySchema` instances (different table/column
  names for the same canonical concepts, in the spirit of the London/Mumbai
  examples already discussed) used **only** to generate training/eval
  examples -- never connected to a real database, never presented as real
  city data.
- FR-5: `rag/nl_to_sql/training_data_gen.py` — for each canonical intent
  (`area_ranking`, `metric_lookup`, `top_n`, `comparison`, `hourly_pattern`)
  and each schema (NYC real + 4 synthetic), template several natural-language
  phrasings paired with the **programmatically correct** `QueryPlan` (no LLM
  in the labeling loop -- labels are correct by construction). Emits an
  OpenAI fine-tuning JSONL (system schema-description + user question +
  assistant `QueryPlan` JSON).
- FR-6: Train/eval split is **by schema family**, not random: train on NYC +
  3 of 4 synthetic schemas; hold out the 4th synthetic schema entirely
  (never seen in training) for the generalization eval, plus a held-out
  slice of NYC question phrasings for the same-schema eval. This is the
  correct split for what's being tested here (does the model generalize to
  an unseen schema), in the same spirit as rule 3's chronological-split
  discipline for time-series -- a random split would leak the thing being
  tested for.
- FR-7: `models/query_plan_finetune/train.py` — assembles the JSONL, submits
  an OpenAI fine-tuning job on `gpt-5-nano`, polls to completion, records
  job id, resulting fine-tuned model id, dataset version/size, and hyper-
  parameters to `models/query_plan_finetune/finetune_metadata.json` (rule 5
  reproducibility).
- FR-8: `models/query_plan_finetune/evaluate.py` — runs **both** base
  `gpt-5-nano` and the fine-tuned model against the held-out eval set,
  scores structural match (intent/metric/filters/aggregation) against the
  known-correct plan, writes real numbers to
  `models/query_plan_finetune/eval_report.json` (rule 2: no fabricated
  metrics -- both models actually run).
- FR-9: `rag/nl_to_sql/query_plan_agent.py` — NL question + a
  `CityMobilitySchema` -> `QueryPlan` -> `query_plan_compiler.compile()` ->
  execute (read-only, same mart allow-list discipline as `sql_agent.py`).
  Gated behind `USE_FINETUNED_QUERY_PLAN` (env var, default unset/off) --
  `rag_pipeline.py`'s existing numeric-question path is unchanged unless
  explicitly opted in, so today's live `/chat` behavior does not change.

## Non-Functional Requirements

- **Deliberate, explicit budget exception.** ADR-008 established $0 for
  external data-source adapters; this is a different subsystem (a Layer 4
  training run, not a Layer-5+ live adapter) and the user explicitly chose
  the OpenAI fine-tuning API knowing it costs real money -- recorded as
  ADR-010 rather than silently treated as consistent with ADR-008.
- **Minimal dataset, one run first.** Aim for the smallest generated
  training set that shows a measurable eval improvement (target: a few
  hundred examples) -- optimize for a defensible, honestly-reported result,
  not the best conceivable model.
- **No fabricated mobility data.** Synthetic schemas invent column *names*
  only; no synthetic trip counts, fares, or other mobility metrics are
  generated or presented as real.
- **Rule 8 (precompute).** Fine-tuning is an offline training-time job, not
  a request-path operation -- `query_plan_agent.py` only ever loads the
  already-fine-tuned model id and calls the (external) inference API,
  exactly like the existing `sql_agent.py`/`rag_pipeline.py` call OpenAI
  today.

## Current State

`rag/nl_to_sql/sql_agent.py` generates raw SQL directly against NYC's real
mart schema (read live from `information_schema`), validated by a table
allow-list + DDL/DML keyword blocklist before execution (ADR-004). This
works well for NYC today but the approach is schema-specific by
construction -- nothing here generalizes to a second city's different column
names. No `QueryPlan` concept exists yet (SPEC-013's FR-9/FR-10 designed one
but that spec is currently paused before implementation). No fine-tuned
model exists; `rag/config.py`'s `OPENAI_MODEL` (`gpt-5-nano`) is used
zero-shot for both NL-to-SQL and explanatory synthesis today, and continues
to be for the live `/chat` path regardless of this spec (FR-9's gating).

## Proposed Design

```
NYC real schema ──┐                        4 synthetic schemas (name-only,
(nyc_schema.py)    │                        no real/fake mobility numbers)
                    ├──► training_data_gen.py ──► JSONL (question, schema
                    │         (template + programmatic label,             description, correct
                    │          no LLM in the loop)                        QueryPlan)
                    │                                          │
      3 of 4 synthetic schemas ──► TRAIN split                 │
      1 held-out synthetic schema ──► GENERALIZATION eval split│
      held-out NYC question phrasings ──► SAME-SCHEMA eval split
                    │
                    ▼
        OpenAI fine-tuning API (gpt-5-nano base)
                    │
                    ▼
        evaluate.py: base model vs fine-tuned model,
        both eval splits, structural QueryPlan match score
                    │
                    ▼
        query_plan_agent.py (opt-in, USE_FINETUNED_QUERY_PLAN)
                    │
                    ▼
        query_plan_compiler.compile(plan, nyc_schema) -> real SQL -> DuckDB
```

Key tradeoffs:

- **QueryPlan (schema-agnostic) over raw SQL as the fine-tune target.** The
  entire point of "generalizes to other cities" requires the trained skill
  to not encode NYC's column names. This is the one non-negotiable design
  choice this spec exists to make.
- **Programmatic labels, not LLM-generated labels.** Every training example's
  correct `QueryPlan` is produced by the template generator itself, not by
  asking an LLM to guess and trusting it -- avoids training on a
  self-reinforcing wrong answer.
- **Split by schema family, not randomly.** A random split would let the
  model see near-identical examples from the "held out" schema during
  training, invalidating the one claim this spec needs to honestly support
  (generalizes to an unseen schema).
- **Opt-in wiring, not a swap.** `USE_FINETUNED_QUERY_PLAN` defaults off so
  this spec can ship without touching the currently-working `/chat` path;
  flipping it on is a separate, later decision once the eval numbers justify
  it.

## Data Design

- `QueryPlan` fields: `intent` (`area_ranking`|`metric_lookup`|`top_n`|
  `comparison`|`hourly_pattern`), `metric` (`demand`|`fare`|`flow`), `filters`
  (`hour`, `day_of_week`, `area`, `date_range` -- all optional), `aggregation`
  (`count`|`avg`|`sum`|`max`|`min`), `group_by`, `order` (`asc`|`desc`),
  `limit`.
- `CityMobilitySchema`: canonical field name -> `(table, column)`, plus
  `describe()` rendering `TABLE <name> (<column> <canonical_meaning>, ...)`
  text for LLM context -- the same shape for NYC and every synthetic schema,
  so the model only ever sees "a schema description," never a
  NYC-vs-synthetic tell.
- Training JSONL grain: one row per (canonical intent x phrasing x schema).
  Target ~300-500 rows total across 5 schemas x 5 intents x several
  phrasings each.

## Testing

- `tests/test_query_plan.py`: `query_plan_compiler.compile()` produces
  correct SQL for each canonical intent against `nyc_schema.py`; a plan
  referencing a field the schema can't resolve raises rather than compiling;
  no code path constructs a SQL string by concatenating LLM output text.
- `tests/test_training_data_gen.py`: every generated example's label
  round-trips through `query_plan_compiler.compile()` against its own
  schema without raising (the labels are internally consistent); the
  held-out schema's examples never appear in the train-split file.
- `models/query_plan_finetune/evaluate.py` is itself the correctness check
  for the fine-tune's actual claim (generalization) -- its report is the
  Definition-of-Done artifact, not a separate unit test (mirrors
  `standards.md`'s ML evaluation convention).

## Risks

1. **A few hundred synthetic examples may not move the eval numbers.**
   Mitigation: `evaluate.py` reports the real before/after regardless of
   outcome (rule 2) -- "fine-tuning didn't help at this scale" is an honest,
   reportable, portfolio-legitimate result, not a failure to hide.
2. **Synthetic schemas could accidentally leak a NYC-specific tell** (e.g.
   reusing NYC's exact borough names) that lets the model cheat instead of
   generalizing. Mitigation: synthetic schemas use genuinely different area
   names, not NYC boroughs/zones renamed.
3. **Real cost from the OpenAI fine-tuning API** — mitigated by the
   minimal-dataset, single-run-first non-functional requirement and by
   recording the actual billed cost from the job metadata in
   `finetune_metadata.json`, not an estimate.

## Acceptance Criteria

- [ ] `query_plan_compiler.compile()` works for NYC across all 5 canonical
      intents, tested.
- [ ] 4 synthetic schemas exist, structurally validated (every field
      resolves, every generated label compiles against its own schema).
- [ ] Training JSONL generated, schema-family split respected (held-out
      schema's examples provably absent from the training file).
- [ ] One OpenAI fine-tuning job completed on `gpt-5-nano`; real job
      id/model id/cost recorded in `finetune_metadata.json`.
- [ ] `evaluate.py` reports real, both-models-actually-run structural-match
      accuracy on both eval splits in `eval_report.json`.
- [ ] `query_plan_agent.py` exists and is gated by `USE_FINETUNED_QUERY_PLAN`
      (default off); with the flag off, `/chat`'s existing behavior and
      existing tests (`tests/test_api.py`, `tests/test_rag.py`) are
      unaffected.
- [ ] ADR-010 records the deliberate budget exception.

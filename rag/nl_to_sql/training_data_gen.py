"""Programmatic (template + correct-by-construction label) NL question ->
QueryPlan training/eval examples for the QueryPlan fine-tune (FR-5, FR-6).

Every label here is produced by the generator itself from the schema it's
generating for -- never by asking an LLM and trusting its answer (rule 2).
That's what lets `tests/test_training_data_gen.py` assert every generated
label compiles against its own schema without raising, instead of merely
"looks plausible."

Split is by schema *family*, not randomly (FR-6): 3 of 4 synthetic schemas
plus NYC train on the model, the 4th synthetic schema (`SCHEMA_DELTA`) is
held out entirely for the generalization eval, and a fixed slice of NYC's
own phrasings is held out for the same-schema eval. A random split would let
near-identical phrasings of the "held out" schema leak into training,
invalidating the one claim this spec needs to honestly support.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from nyc_schema import NYC_SCHEMA  # noqa: E402
from query_plan import CityMobilitySchema, QueryFilters, QueryPlan  # noqa: E402
from query_plan_compiler import compile as compile_plan  # noqa: E402
from synthetic_schemas import HELD_OUT_SCHEMA, TRAIN_SYNTHETIC_SCHEMAS  # noqa: E402

DATA_DIR = Path(__file__).resolve().parents[2] / "models" / "query_plan_finetune" / "data"

METRIC_PHRASE = {"demand": "trip demand", "fare": "average fare", "flow": "trip flow"}
AGG_FOR_METRIC = {"demand": "sum", "fare": "avg", "flow": "sum"}

# Example area values for *questions*, never a claimed real statistic (rule
# 2) -- NYC values reuse real zone ids/names already referenced elsewhere in
# this repo (tests/test_api.py, sql_agent.py's own demo); synthetic values
# are clearly fictional area labels.
AREA_TEXT_EXAMPLES = {
    "nyc": ["JFK Airport", "Midtown", "East Village"],
    "schema_alpha": ["Sector 5", "District 12", "Riverside Block"],
    "schema_beta": ["Zone C", "Ward 9", "Old Town"],
    "schema_gamma": ["Central Hub", "North Terminal", "Lakeside"],
    "schema_delta": ["Stop Zone 3", "Riverside Terminal", "Hillcrest"],
}
AREA_NUMERIC_EXAMPLES = {"nyc": [132, 161, 230]}


def _area_value(schema: CityMobilitySchema, metric: str, idx: int) -> str | int:
    field = schema.resolve_field(metric, "area")
    pool = AREA_NUMERIC_EXAMPLES.get(schema.name, []) if not field.is_text else AREA_TEXT_EXAMPLES[schema.name]
    return pool[idx % len(pool)]


def _gen_metric_lookup(schema: CityMobilitySchema, metric: str) -> list[tuple[str, QueryPlan]]:
    phrase = METRIC_PHRASE[metric]
    agg = AGG_FOR_METRIC[metric]
    out = [
        (f"What is the total {phrase} recorded?", QueryPlan(intent="metric_lookup", metric=metric, aggregation=agg)),
        (f"What is the overall {phrase}?", QueryPlan(intent="metric_lookup", metric=metric, aggregation=agg)),
        (f"Tell me the {phrase} across everything.", QueryPlan(intent="metric_lookup", metric=metric, aggregation=agg)),
    ]
    if schema.has_field(metric, "area"):
        for idx, phrasing in enumerate((f"What is the {phrase} for area {{area}}?", f"How much {phrase} was there in {{area}}?", f"What's the {phrase} in {{area}}?")):
            area = _area_value(schema, metric, idx)
            out.append((phrasing.format(area=area), QueryPlan(intent="metric_lookup", metric=metric, aggregation=agg, filters=QueryFilters(area=area))))
    if schema.has_field(metric, "hour"):
        out.append((
            f"What was the {phrase} at hour 8?",
            QueryPlan(intent="metric_lookup", metric=metric, aggregation=agg, filters=QueryFilters(hour=8)),
        ))
    if schema.has_field(metric, "day_of_week"):
        out.append((
            f"What was the {phrase} on day 1 of the week?",
            QueryPlan(intent="metric_lookup", metric=metric, aggregation=agg, filters=QueryFilters(day_of_week=1)),
        ))
    if schema.has_field(metric, "date_range"):
        out.append((
            f"What was the {phrase} between 2024-01-01 and 2024-01-07?",
            QueryPlan(
                intent="metric_lookup", metric=metric, aggregation=agg,
                filters=QueryFilters(date_range=("2024-01-01", "2024-01-07")),
            ),
        ))
    return out


def _gen_area_ranking(schema: CityMobilitySchema, metric: str) -> list[tuple[str, QueryPlan]]:
    if not schema.has_field(metric, "area"):
        return []
    phrase = METRIC_PHRASE[metric]
    agg = AGG_FOR_METRIC[metric]
    return [
        (f"Which area has the highest {phrase}?",
         QueryPlan(intent="area_ranking", metric=metric, aggregation=agg, group_by="area", order="desc", limit=1)),
        (f"What is the top area by {phrase}?",
         QueryPlan(intent="area_ranking", metric=metric, aggregation=agg, group_by="area", order="desc", limit=1)),
        (f"Which area has the lowest {phrase}?",
         QueryPlan(intent="area_ranking", metric=metric, aggregation=agg, group_by="area", order="asc", limit=1)),
    ]


def _gen_top_n(schema: CityMobilitySchema, metric: str) -> list[tuple[str, QueryPlan]]:
    if not schema.has_field(metric, "area"):
        return []
    phrase = METRIC_PHRASE[metric]
    agg = AGG_FOR_METRIC[metric]
    return [
        (f"What are the top 3 areas by {phrase}?",
         QueryPlan(intent="top_n", metric=metric, aggregation=agg, group_by="area", order="desc", limit=3)),
        (f"List the top 5 areas ranked by {phrase}.",
         QueryPlan(intent="top_n", metric=metric, aggregation=agg, group_by="area", order="desc", limit=5)),
        (f"Give me the 10 areas with the most {phrase}.",
         QueryPlan(intent="top_n", metric=metric, aggregation=agg, group_by="area", order="desc", limit=10)),
    ]


def _gen_comparison(schema: CityMobilitySchema, metric: str) -> list[tuple[str, QueryPlan]]:
    if not schema.has_field(metric, "area"):
        return []
    phrase = METRIC_PHRASE[metric]
    agg = AGG_FOR_METRIC[metric]
    return [
        (f"How does {phrase} compare across areas?",
         QueryPlan(intent="comparison", metric=metric, aggregation=agg, group_by="area")),
        (f"Compare {phrase} between areas.",
         QueryPlan(intent="comparison", metric=metric, aggregation=agg, group_by="area")),
        (f"Show me {phrase} broken down by area.",
         QueryPlan(intent="comparison", metric=metric, aggregation=agg, group_by="area")),
    ]


def _gen_hourly_pattern(schema: CityMobilitySchema, metric: str) -> list[tuple[str, QueryPlan]]:
    if not schema.has_field(metric, "hour"):
        return []
    phrase = METRIC_PHRASE[metric]
    agg = AGG_FOR_METRIC[metric]
    out = [
        (f"What is the {phrase} pattern by hour of day?",
         QueryPlan(intent="hourly_pattern", metric=metric, aggregation=agg, group_by="hour", order="asc")),
        (f"How does {phrase} change hour by hour?",
         QueryPlan(intent="hourly_pattern", metric=metric, aggregation=agg, group_by="hour", order="asc")),
    ]
    if schema.has_field(metric, "area"):
        area = _area_value(schema, metric, 0)
        out.append((
            f"What is the {phrase} by hour for area {area}?",
            QueryPlan(
                intent="hourly_pattern", metric=metric, aggregation=agg, group_by="hour", order="asc",
                filters=QueryFilters(area=area),
            ),
        ))
    return out


_GENERATORS = (_gen_metric_lookup, _gen_area_ranking, _gen_top_n, _gen_comparison, _gen_hourly_pattern)


def generate_examples(schema: CityMobilitySchema) -> list[tuple[str, QueryPlan]]:
    examples: list[tuple[str, QueryPlan]] = []
    for metric in schema.metrics:
        for gen in _GENERATORS:
            examples.extend(gen(schema, metric))
    return examples


def to_finetune_row(schema: CityMobilitySchema, question: str, plan: QueryPlan) -> dict:
    """OpenAI fine-tuning chat JSONL row: system = schema description only
    (no QueryPlan format instructions) -- the fine-tuned model is meant to
    learn the output shape from these examples, exactly what it will see at
    inference time (see evaluate.py's docstring for why the *base*-model
    eval uses a fuller prompt than this)."""
    return {
        "messages": [
            {"role": "system", "content": schema.describe()},
            {"role": "user", "content": question},
            {"role": "assistant", "content": plan.to_json()},
        ]
    }


def build_splits() -> dict[str, list[dict]]:
    nyc_examples = generate_examples(NYC_SCHEMA)
    # Deterministic (no RNG/seed needed): every 4th NYC phrasing is held out.
    nyc_train = [ex for i, ex in enumerate(nyc_examples) if i % 4 != 0]
    nyc_holdout = [ex for i, ex in enumerate(nyc_examples) if i % 4 == 0]

    train_rows = [to_finetune_row(NYC_SCHEMA, q, p) for q, p in nyc_train]
    for schema in TRAIN_SYNTHETIC_SCHEMAS:
        train_rows.extend(to_finetune_row(schema, q, p) for q, p in generate_examples(schema))

    eval_nyc_holdout_rows = [to_finetune_row(NYC_SCHEMA, q, p) for q, p in nyc_holdout]
    eval_unseen_rows = [to_finetune_row(HELD_OUT_SCHEMA, q, p) for q, p in generate_examples(HELD_OUT_SCHEMA)]

    return {
        "train.jsonl": train_rows,
        "eval_nyc_holdout.jsonl": eval_nyc_holdout_rows,
        "eval_unseen_schema.jsonl": eval_unseen_rows,
    }


def write_splits(out_dir: Path = DATA_DIR) -> dict[str, int]:
    out_dir.mkdir(parents=True, exist_ok=True)
    splits = build_splits()
    counts = {}
    for filename, rows in splits.items():
        with (out_dir / filename).open("w", encoding="utf-8") as f:
            for row in rows:
                f.write(json.dumps(row) + "\n")
        counts[filename] = len(rows)
    return counts


def demo() -> None:
    counts = write_splits()
    total = sum(counts.values())
    print(f"wrote {total} examples: {counts}")
    assert total >= 200, f"expected a few hundred examples, got {total}"

    # Rule 2: every generated label must be correct by construction -- prove
    # it by compiling every one against its own schema.
    for schema in (NYC_SCHEMA, *TRAIN_SYNTHETIC_SCHEMAS, HELD_OUT_SCHEMA):
        for _, plan in generate_examples(schema):
            compile_plan(plan, schema)  # must not raise
    print("OK: every generated label compiles against its own schema")


if __name__ == "__main__":
    demo()

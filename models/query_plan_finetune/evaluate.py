"""Scores the base model's QueryPlan-JSON output against the known-correct
plan on both held-out eval splits (FR-8, partial -- base model only, no
fine-tuned model exists yet; that comparison is added once spec-014's FR-7
fine-tuning step, done separately, completes).

Base-vs-fine-tuned prompt asymmetry, deliberate: `training_data_gen.py`'s
JSONL rows use `schema.describe()` alone as the system prompt, because
that's the exact input the *fine-tuned* model will see at inference time --
the point of fine-tuning is for the model to learn the QueryPlan JSON shape
from the training examples themselves, not from a prompt. The *base* model
was never trained on that shape, so evaluating it with only
`schema.describe()` would not be a fair zero-shot baseline -- it would be
guaranteed to fail on format alone, making a later fine-tuned-vs-base
comparison look artificially better without actually testing the thing this
spec cares about (does the model learn the canonical mapping). So the base-
model eval here appends `QUERY_PLAN_FORMAT_INSTRUCTIONS` to the system
prompt; `rag/nl_to_sql/query_plan_agent.py`'s real (future) fine-tuned call
does not, matching the training format exactly.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "rag" / "nl_to_sql"))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "rag"))

from config import OPENAI_MODEL  # noqa: E402
from query_plan import QueryPlan  # noqa: E402

DATA_DIR = Path(__file__).resolve().parent / "data"
REPORT_PATH = Path(__file__).resolve().parent / "eval_report.json"

QUERY_PLAN_FORMAT_INSTRUCTIONS = """Respond with ONLY a single JSON object (no markdown fences, no prose) \
describing a QueryPlan with exactly these keys:
- intent: one of "area_ranking", "metric_lookup", "top_n", "comparison", "hourly_pattern"
- metric: one of "demand", "fare", "flow"
- aggregation: one of "count", "avg", "sum", "max", "min"
- filters: an object with optional keys "hour" (0-23 int), "day_of_week" (0-6 int), \
"area" (string or int, matching the schema's area column type), "date_range" (a two-item \
[start, end] array of "YYYY-MM-DD" strings) -- omit or null any key that doesn't apply
- group_by: a canonical field name (e.g. "area" or "hour") to group results by, or null
- order: "asc", "desc", or null
- limit: an integer row limit, or null

Example output format:
{"intent": "metric_lookup", "metric": "fare", "aggregation": "avg", "filters": {"area": "JFK Airport"}, "group_by": null, "order": null, "limit": null}

Only use the canonical concepts described in the schema above -- never invent a table or \
column name; the plan is schema-agnostic."""

_SCORED_FIELDS = ("intent", "metric", "aggregation", "filters")


def _strip_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
        text = re.sub(r"```$", "", text).strip()
    return text


def _parse_model_plan(text: str) -> QueryPlan | None:
    try:
        return QueryPlan.from_dict(json.loads(_strip_fences(text)))
    except Exception:  # noqa: BLE001 -- any malformed/unparseable model output just scores as a miss
        return None


def call_base_model(system_text: str, question: str, model: str) -> QueryPlan | None:
    from openai import OpenAI

    client = OpenAI()
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": f"{system_text}\n\n{QUERY_PLAN_FORMAT_INSTRUCTIONS}"},
            {"role": "user", "content": question},
        ],
        temperature=0,
        max_completion_tokens=300,
    )
    return _parse_model_plan(resp.choices[0].message.content or "")


def score_plan(expected: QueryPlan, actual: QueryPlan | None) -> dict[str, bool]:
    """Structural match on intent/metric/filters/aggregation (FR-8) -- not
    group_by/order/limit, which are compiler hints rather than the canonical
    mapping this fine-tune is meant to test."""
    if actual is None:
        return {field: False for field in _SCORED_FIELDS} | {"exact_match": False}
    result = {
        "intent": actual.intent == expected.intent,
        "metric": actual.metric == expected.metric,
        "aggregation": actual.aggregation == expected.aggregation,
        "filters": actual.filters.active() == expected.filters.active(),
    }
    result["exact_match"] = all(result.values())
    return result


def evaluate_file(path: Path, model: str) -> dict:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    scores = []
    for row in rows:
        system_text = row["messages"][0]["content"]
        question = row["messages"][1]["content"]
        expected = QueryPlan.from_json(row["messages"][2]["content"])
        actual = call_base_model(system_text, question, model)
        scores.append(score_plan(expected, actual))

    n = len(scores)
    return {
        "n_examples": n,
        "exact_match_accuracy": (sum(s["exact_match"] for s in scores) / n) if n else 0.0,
        "field_accuracy": {
            field: (sum(s[field] for s in scores) / n) if n else 0.0 for field in _SCORED_FIELDS
        },
    }


def run(model: str = OPENAI_MODEL) -> dict:
    report = {
        "base_model": model,
        "fine_tuned_model": None,
        "note": (
            "base-model-only numbers -- no fine-tuning job has been submitted (spec-014 FR-7 is "
            "deliberately out of scope for this pass; run again once a fine-tuned model id exists)"
        ),
        "eval_nyc_holdout": evaluate_file(DATA_DIR / "eval_nyc_holdout.jsonl", model),
        "eval_unseen_schema": evaluate_file(DATA_DIR / "eval_unseen_schema.jsonl", model),
    }
    REPORT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def demo() -> None:
    # Runnable, non-LLM self-check for the scoring logic itself.
    expected = QueryPlan.from_dict(
        {"intent": "metric_lookup", "metric": "fare", "aggregation": "avg", "filters": {"area": "JFK Airport"}}
    )
    exact = QueryPlan.from_dict(
        {"intent": "metric_lookup", "metric": "fare", "aggregation": "avg", "filters": {"area": "JFK Airport"}}
    )
    wrong_metric = QueryPlan.from_dict(
        {"intent": "metric_lookup", "metric": "demand", "aggregation": "avg", "filters": {"area": "JFK Airport"}}
    )
    assert score_plan(expected, exact)["exact_match"] is True
    assert score_plan(expected, wrong_metric)["exact_match"] is False
    assert score_plan(expected, wrong_metric)["metric"] is False
    assert score_plan(expected, None)["exact_match"] is False
    print("OK: score_plan scoring logic self-check passed")


if __name__ == "__main__":
    demo()
    if "--run" in sys.argv:
        report = run()
        print(json.dumps(report, indent=2))

# models/query_plan_finetune/evaluate_comparison.py
"""Honest comparison: local fine-tuned model vs. the existing DeepSeek/
OpenAI zero-shot QueryPlan generator, scored on the same held-out sets
training_data_gen.py already produces. Mirrors models/evaluation/
compare_models.py's standalone-script shape for the demand model ladder --
same discipline, different task.

"Correct" here is `evaluate.py::score_plan()`'s definition, reused verbatim
rather than redefined: a structural match on intent/metric/aggregation/
filters, deliberately *not* group_by/order/limit (compiler hints, not the
canonical mapping this fine-tune is meant to test). That's what makes these
numbers directly comparable to the base-model baseline ADR-010 records
(53.8% NYC holdout / 66.7% synthetic) -- a different correctness definition
here would produce numbers that look comparable and aren't.
"""
from __future__ import annotations

import functools
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "rag" / "nl_to_sql"))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "rag"))

import config  # noqa: F401
from evaluate import score_plan
from nyc_schema import NYC_SCHEMA
from query_plan import QueryPlan
from synthetic_schemas import HELD_OUT_SCHEMA

DATA_DIR = Path(__file__).resolve().parent / "data"
RESULTS_PATH = Path(__file__).resolve().parent / "comparison_results.json"


def load_eval_rows(filename: str) -> list[dict]:
    return [json.loads(line) for line in (DATA_DIR / filename).read_text(encoding="utf-8").splitlines() if line.strip()]


def score(generate_fn, rows: list[dict], schema) -> tuple[float, int]:
    correct = 0
    for row in rows:
        question = row["messages"][1]["content"]
        expected_plan = QueryPlan.from_json(row["messages"][2]["content"])
        try:
            actual_plan = generate_fn(question, schema=schema)
        except Exception:  # noqa: BLE001
            actual_plan = None
        correct += int(score_plan(expected_plan, actual_plan)["exact_match"])
    return correct / len(rows), len(rows)


def run() -> dict:
    import llm_client
    from query_plan_agent import (
        FINETUNED_MODEL_ID,  # requires QUERY_PLAN_FINETUNED_MODEL_ID set
    )
    from query_plan_agent import generate_plan as local_generate
    from sql_agent import generate_plan as hosted_generate

    if not FINETUNED_MODEL_ID:
        raise SystemExit(
            "QUERY_PLAN_FINETUNED_MODEL_ID is unset -- every local-tier call would fail and be "
            "scored as a miss, reporting a fake-looking 0% accuracy instead of an error. Set it "
            "(and LOCAL_MODEL_BASE_URL, pointing at the served fine-tuned model) first."
        )

    # query_plan_agent.generate_plan's `model` param has no default (unlike
    # sql_agent.generate_plan's), so score()'s generate_fn(question, schema=schema)
    # call would TypeError on every row for the local tier -- bind it here rather
    # than in score(), reusing query_plan_agent's own env-var read instead of a
    # second one. hosted_generate is left unbound: its `model` already defaults.
    local_generate_bound = functools.partial(local_generate, model=FINETUNED_MODEL_ID)

    nyc_rows = load_eval_rows("eval_nyc_holdout.jsonl")
    unseen_rows = load_eval_rows("eval_unseen_schema.jsonl")

    # Test isolation, non-obvious from the call sites: both tiers now go through
    # llm_client.chat_completion(), which tries the local model FIRST whenever
    # LOCAL_MODEL_BASE_URL is set. Left alone, the "hosted" pass would silently be
    # served by the local model too and this script would compare the local model
    # against itself. So clear the module attribute for the hosted pass only, and
    # restore it (finally) before the local pass, which needs it set.
    saved_local_base_url = llm_client.LOCAL_MODEL_BASE_URL
    llm_client.LOCAL_MODEL_BASE_URL = ""
    try:
        hosted_results = {
            "nyc_holdout": dict(zip(("accuracy", "n"), score(hosted_generate, nyc_rows, NYC_SCHEMA))),
            "unseen_schema": dict(zip(("accuracy", "n"), score(hosted_generate, unseen_rows, HELD_OUT_SCHEMA))),
        }
    finally:
        llm_client.LOCAL_MODEL_BASE_URL = saved_local_base_url

    results = {
        "local": {
            "nyc_holdout": dict(zip(("accuracy", "n"), score(local_generate_bound, nyc_rows, NYC_SCHEMA))),
            "unseen_schema": dict(zip(("accuracy", "n"), score(local_generate_bound, unseen_rows, HELD_OUT_SCHEMA))),
        },
        "hosted_deepseek_or_openai": hosted_results,
    }
    RESULTS_PATH.write_text(json.dumps(results, indent=2))
    return results


if __name__ == "__main__":
    results = run()
    for tier, splits in results.items():
        for split, m in splits.items():
            print(f"{tier:25s} {split:15s} accuracy={m['accuracy']:.1%} (n={m['n']})")

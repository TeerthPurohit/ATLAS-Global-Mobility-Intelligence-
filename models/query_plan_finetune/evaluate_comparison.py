# models/query_plan_finetune/evaluate_comparison.py
"""Honest comparison: local fine-tuned model vs. the existing DeepSeek/
OpenAI zero-shot QueryPlan generator, scored on the same held-out sets
training_data_gen.py already produces. Mirrors models/evaluation/
compare_models.py's standalone-script shape for the demand model ladder --
same discipline, different task.

"Correct" here means the generated QueryPlan, when compiled via
query_plan_compiler.compile(), produces the exact same SQL as the
held-out example's own label compiles to -- not string-identical JSON
(field order/nulls can legitimately differ), but semantically identical.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "rag" / "nl_to_sql"))

from nyc_schema import NYC_SCHEMA  # noqa: E402
from query_plan import QueryPlan  # noqa: E402
from query_plan_compiler import compile as compile_plan  # noqa: E402
from synthetic_schemas import HELD_OUT_SCHEMA  # noqa: E402

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
            correct += int(compile_plan(actual_plan, schema) == compile_plan(expected_plan, schema))
        except Exception:
            pass  # a generation/compile failure counts as incorrect, not a crash
    return correct / len(rows), len(rows)


def run() -> dict:
    from query_plan_agent import generate_plan as local_generate  # requires QUERY_PLAN_FINETUNED_MODEL_ID set
    from sql_agent import generate_plan as hosted_generate

    nyc_rows = load_eval_rows("eval_nyc_holdout.jsonl")
    unseen_rows = load_eval_rows("eval_unseen_schema.jsonl")

    results = {
        "local": {
            "nyc_holdout": dict(zip(("accuracy", "n"), score(local_generate, nyc_rows, NYC_SCHEMA))),
            "unseen_schema": dict(zip(("accuracy", "n"), score(local_generate, unseen_rows, HELD_OUT_SCHEMA))),
        },
        "hosted_deepseek_or_openai": {
            "nyc_holdout": dict(zip(("accuracy", "n"), score(hosted_generate, nyc_rows, NYC_SCHEMA))),
            "unseen_schema": dict(zip(("accuracy", "n"), score(hosted_generate, unseen_rows, HELD_OUT_SCHEMA))),
        },
    }
    RESULTS_PATH.write_text(json.dumps(results, indent=2))
    return results


if __name__ == "__main__":
    results = run()
    for tier, splits in results.items():
        for split, m in splits.items():
            print(f"{tier:25s} {split:15s} accuracy={m['accuracy']:.1%} (n={m['n']})")

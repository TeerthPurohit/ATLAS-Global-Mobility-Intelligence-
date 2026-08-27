"""Every generated training/eval label is correct by construction (rule 2 --
no LLM in the labeling loop) and the held-out schema is provably absent from
the train split (FR-6, spec-014)."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "rag" / "nl_to_sql"))

from nyc_schema import NYC_SCHEMA
from query_plan_compiler import compile as compile_plan
from synthetic_schemas import HELD_OUT_SCHEMA, TRAIN_SYNTHETIC_SCHEMAS
from training_data_gen import build_splits, generate_examples

ALL_SCHEMAS = (NYC_SCHEMA, *TRAIN_SYNTHETIC_SCHEMAS, HELD_OUT_SCHEMA)


def test_every_label_round_trips_through_the_compiler():
    for schema in ALL_SCHEMAS:
        examples = generate_examples(schema)
        assert examples, f"{schema.name} produced no training examples"
        for question, plan in examples:
            compile_plan(plan, schema)  # must not raise -- label is correct by construction


def test_held_out_schema_absent_from_train_split():
    # Question text alone isn't a unique key -- several templates are
    # deliberately schema-agnostic phrasing ("Compare trip demand between
    # areas.") and repeat verbatim across schemas; what must never appear in
    # train is *this schema's description* at all (no row is ever labeled
    # with it), so pair (schema_description, question) instead.
    splits = build_splits()
    train_text = "\n".join(json.dumps(row) for row in splits["train.jsonl"])
    assert HELD_OUT_SCHEMA.describe() not in train_text

    held_out_pairs = {(HELD_OUT_SCHEMA.describe(), q) for q, _ in generate_examples(HELD_OUT_SCHEMA)}
    train_pairs = {(row["messages"][0]["content"], row["messages"][1]["content"]) for row in splits["train.jsonl"]}
    assert held_out_pairs.isdisjoint(train_pairs)

    # ... but it does show up, fully, in the generalization eval split.
    eval_unseen_pairs = {
        (row["messages"][0]["content"], row["messages"][1]["content"]) for row in splits["eval_unseen_schema.jsonl"]
    }
    assert held_out_pairs == eval_unseen_pairs


def test_splits_are_nonempty_and_disjoint_from_each_other():
    splits = build_splits()
    assert len(splits["train.jsonl"]) > 0
    assert len(splits["eval_nyc_holdout.jsonl"]) > 0
    assert len(splits["eval_unseen_schema.jsonl"]) > 0

    def _keys(rows):
        return {(r["messages"][0]["content"], r["messages"][1]["content"]) for r in rows}

    assert _keys(splits["train.jsonl"]).isdisjoint(_keys(splits["eval_nyc_holdout.jsonl"]))
    assert _keys(splits["train.jsonl"]).isdisjoint(_keys(splits["eval_unseen_schema.jsonl"]))


def test_train_split_only_contains_nyc_and_train_synthetic_schemas():
    splits = build_splits()
    allowed_descriptions = {s.describe() for s in (NYC_SCHEMA, *TRAIN_SYNTHETIC_SCHEMAS)}
    for row in splits["train.jsonl"]:
        assert row["messages"][0]["content"] in allowed_descriptions

"""Paraphrase-based training data augmentation for the QueryPlan fine-tune
(distillation data expansion). Expands training_data_gen.py's 227
template-generated questions with LLM-paraphrased variants of the SAME
question -- labels are never touched, since paraphrasing a question never
changes its correct QueryPlan. This is the fix for the template dataset's
real gap: narrow phrasing diversity, not label correctness (which
training_data_gen.py already guarantees by construction).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import config  # noqa: E402,F401  -- load_dotenv() side effect must run before llm_client reads its env vars at import time
from llm_client import chat_completion  # noqa: E402
from training_data_gen import DATA_DIR, build_splits  # noqa: E402

PARAPHRASE_MODEL = "gpt-5.4-nano"


def _generate_paraphrases(question: str, n: int) -> list[str]:
    """Real LLM call -- reuses the same DeepSeek-primary/OpenAI-fallback
    chat_completion() every other LLM use in this repo goes through."""
    resp = chat_completion(
        model=PARAPHRASE_MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    f"Rewrite the user's question {n} different ways, preserving its exact "
                    "meaning (same intent, metric, filters). One rewrite per line, no numbering, "
                    "no extra commentary."
                ),
            },
            {"role": "user", "content": question},
        ],
        max_completion_tokens=300,
    )
    text = (resp.choices[0].message.content or "").strip()
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return lines[:n]


def augment_split(rows: list[dict], n_paraphrases: int = 3) -> list[dict]:
    if n_paraphrases <= 0:
        return list(rows)
    out: list[dict] = []
    for row in rows:
        out.append(row)
        question = row["messages"][1]["content"]
        for paraphrase in _generate_paraphrases(question, n_paraphrases):
            augmented = json.loads(json.dumps(row))  # deep copy
            augmented["messages"][1]["content"] = paraphrase
            out.append(augmented)
    return out


def write_augmented_splits(n_paraphrases: int = 3, out_dir: Path = DATA_DIR) -> dict[str, int]:
    """Only augments train.jsonl -- eval splits must stay exactly as
    generated (unparaphrased) so evaluation measures generalization to
    real phrasing, not memorized paraphrase style."""
    splits = build_splits()
    augmented_train = augment_split(splits["train.jsonl"], n_paraphrases)
    out_dir.mkdir(parents=True, exist_ok=True)
    with (out_dir / "train_augmented.jsonl").open("w", encoding="utf-8") as f:
        for row in augmented_train:
            f.write(json.dumps(row) + "\n")
    for filename in ("eval_nyc_holdout.jsonl", "eval_unseen_schema.jsonl"):
        with (out_dir / filename).open("w", encoding="utf-8") as f:
            for row in splits[filename]:
                f.write(json.dumps(row) + "\n")
    return {"train_augmented.jsonl": len(augmented_train), **{k: len(splits[k]) for k in splits if k != "train.jsonl"}}


def demo() -> None:
    counts = write_augmented_splits()
    print(f"wrote {counts}")


if __name__ == "__main__":
    demo()

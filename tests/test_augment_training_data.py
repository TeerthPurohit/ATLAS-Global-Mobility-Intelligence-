import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "rag" / "nl_to_sql"))

from augment_training_data import augment_split  # noqa: E402


def test_augment_split_preserves_labels_and_expands_count(monkeypatch):
    import augment_training_data as mod

    calls = []

    def fake_paraphrase(question: str, n: int) -> list[str]:
        calls.append((question, n))
        return [f"{question} (paraphrase {i})" for i in range(n)]

    monkeypatch.setattr(mod, "_generate_paraphrases", fake_paraphrase)

    rows = [
        {"messages": [
            {"role": "system", "content": "TABLE t (col -- demand: x [numeric])"},
            {"role": "user", "content": "What is the total demand?"},
            {"role": "assistant", "content": '{"intent": "metric_lookup", "metric": "demand"}'},
        ]},
    ]

    out = augment_split(rows, n_paraphrases=3)

    assert len(out) == 4  # 1 original + 3 paraphrases
    assert out[0] == rows[0]  # original row unchanged, first
    for row in out[1:]:
        assert row["messages"][0]["content"] == rows[0]["messages"][0]["content"]  # system unchanged
        assert row["messages"][2]["content"] == rows[0]["messages"][2]["content"]  # label unchanged
        assert row["messages"][1]["content"] != rows[0]["messages"][1]["content"]  # question is a paraphrase
    assert calls == [("What is the total demand?", 3)]


def test_augment_split_zero_paraphrases_is_identity():
    rows = [{"messages": [{"role": "user", "content": "x"}]}]
    assert augment_split(rows, n_paraphrases=0) == rows

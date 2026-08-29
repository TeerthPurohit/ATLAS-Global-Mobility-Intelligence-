import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "rag"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "rag" / "eval"))

from eval import metrics  # rag/eval/metrics.py


def test_confusion_matrix_counts_cells():
    pairs = [("numeric", "numeric"), ("numeric", "explanatory"), ("explanatory", "explanatory")]
    m = metrics.confusion_matrix(pairs)
    assert m[("numeric", "numeric")] == 1
    assert m[("numeric", "explanatory")] == 1
    assert m[("explanatory", "explanatory")] == 1
    assert m.get(("explanatory", "numeric"), 0) == 0


def test_reciprocal_rank_first_position():
    assert metrics.reciprocal_rank([132, 14, 79], [132]) == 1.0


def test_reciprocal_rank_second_position():
    assert metrics.reciprocal_rank([14, 132, 79], [132]) == 0.5


def test_reciprocal_rank_absent_returns_zero():
    assert metrics.reciprocal_rank([14, 79, 244], [132]) == 0.0


def test_reciprocal_rank_empty_retrieved_returns_zero():
    assert metrics.reciprocal_rank([], [132]) == 0.0


def test_hit_rate_at_k_present():
    assert metrics.hit_rate_at_k([132, 14, 79], [132]) is True


def test_hit_rate_at_k_absent():
    assert metrics.hit_rate_at_k([14, 79, 244], [132]) is False


def test_aggregate_mean_and_count():
    out = metrics.aggregate([1.0, 0.5, 0.0])
    assert out == {"mean": 0.5, "n": 3}


def test_aggregate_empty_list():
    out = metrics.aggregate([])
    assert out == {"mean": None, "n": 0}


def test_agreement_rate_counts_disagreements():
    pairs = [(True, True), (True, False), (False, False)]
    out = metrics.agreement_rate(pairs)
    assert out == {"agree": 2, "total": 3, "rate": 2 / 3}


def test_agreement_rate_empty():
    assert metrics.agreement_rate([]) == {"agree": 0, "total": 0, "rate": None}

"""Deterministic eval metrics -- pure functions over already-collected
results, no LLM/network calls. Router accuracy and retrieval quality are
component-level metrics that don't need an LLM judge (see
docs/superpowers/plans/2026-08-30-rag-eval-scaling.md), so they live
separately from judge.py's LLM-backed scoring.
"""
from __future__ import annotations

from collections import Counter


def confusion_matrix(pairs: list[tuple[str, str]]) -> dict[tuple[str, str], int]:
    """pairs = (expected, actual). Generic over any label set, not just
    numeric/explanatory, so an adversarial entry's actual="error" composes
    fine without a special case."""
    return dict(Counter(pairs))


def reciprocal_rank(retrieved_ids: list[int], relevant_ids: list[int]) -> float:
    relevant = set(relevant_ids)
    for rank, doc_id in enumerate(retrieved_ids, start=1):
        if doc_id in relevant:
            return 1.0 / rank
    return 0.0


def hit_rate_at_k(retrieved_ids: list[int], relevant_ids: list[int]) -> bool:
    """retrieved_ids is expected to already be capped to k by the caller."""
    return bool(set(retrieved_ids) & set(relevant_ids))


def aggregate(values: list[float]) -> dict:
    if not values:
        return {"mean": None, "n": 0}
    return {"mean": sum(values) / len(values), "n": len(values)}


def agreement_rate(pairs: list[tuple[bool, bool]]) -> dict:
    """Generic agreement calc, reused for BOTH grounding-vs-judge agreement
    (Task 6) and human-vs-judge calibration (Task 4) -- written once here
    rather than duplicated in calibration.py."""
    if not pairs:
        return {"agree": 0, "total": 0, "rate": None}
    agree = sum(1 for a, b in pairs if a == b)
    return {"agree": agree, "total": len(pairs), "rate": agree / len(pairs)}


def demo() -> None:
    m = confusion_matrix([("numeric", "numeric"), ("numeric", "explanatory")])
    assert m[("numeric", "numeric")] == 1
    assert reciprocal_rank([14, 132], [132]) == 0.5
    assert hit_rate_at_k([14, 79], [132]) is False
    assert aggregate([1.0, 0.0]) == {"mean": 0.5, "n": 2}
    assert agreement_rate([(True, True), (True, False)]) == {"agree": 1, "total": 2, "rate": 0.5}
    print("metrics.py demo OK")


if __name__ == "__main__":
    demo()

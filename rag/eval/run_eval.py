"""Golden-question eval runner for the RAG chat layer (rag/eval/golden_questions.jsonl).

Calls `backend.services.rag_service.answer_question()` as a black box (per
this agent's scope boundary -- never touches rag_pipeline.py/rag_service.py/
semantic_cache.py) and checks the REAL returned route + answer against each
golden entry's checkable `expected` block. Numeric questions check the raw
SQL result value within a tolerance; explanatory/context_only questions
check that every `must_contain` fact (case-insensitive, comma-insensitive)
literally appears in the answer text. No LLM judge, no vibes -- every
PASS/FAIL here is a real comparison against a real run (rule 2).

Usage: python rag/eval/run_eval.py
Exit code: 0 if every entry passed, 1 otherwise.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

GOLDEN_PATH = Path(__file__).resolve().parent / "golden_questions.jsonl"


def load_golden(path: Path = GOLDEN_PATH) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def _normalize(text: str) -> str:
    """Case-insensitive, comma-insensitive -- the LLM synthesis path
    sometimes renders '147174' as '147,174' between runs; a real number
    match shouldn't hinge on thousands-separator formatting."""
    return text.lower().replace(",", "")


def _extract_numeric(result: dict) -> float | None:
    """Numeric answers carry the real SQL result in `rows`, not just the
    formatted answer string -- read the value directly rather than
    re-parsing '$65.22' text, so formatting never causes a false mismatch."""
    rows = result.get("rows")
    if not rows:
        return None
    row = rows[0]
    if not row:
        return None
    return float(next(iter(row.values())))


def check_numeric(result: dict, expected: dict) -> tuple[bool, str]:
    actual = _extract_numeric(result)
    if actual is None:
        return False, "no numeric value in result rows"
    ok = abs(actual - expected["value"]) <= expected["tolerance"]
    return ok, f"{actual} (expected {expected['value']} +/- {expected['tolerance']})"


def check_contains(result: dict, expected: dict) -> tuple[bool, str]:
    answer = _normalize(result.get("answer") or "")
    missing = [item for item in expected["items"] if _normalize(item) not in answer]
    ok = not missing
    detail = "all present" if ok else f"missing: {missing}"
    return ok, detail


def run_one(entry: dict) -> tuple[bool, str]:
    """Returns (passed, human-readable actual-vs-expected detail)."""
    from backend.services import rag_service

    city_id = entry.get("city_id", "nyc")
    try:
        result = rag_service.answer_question(question=entry["question"], city_id=city_id)
    except Exception as exc:  # noqa: BLE001 -- a real crash is a real FAIL, not a harness bug
        return False, f"ERROR calling answer_question: {exc!r}"

    route_ok = result.get("route") == entry["route"]
    expected = entry["expected"]
    if expected["type"] == "numeric":
        value_ok, detail = check_numeric(result, expected)
    elif expected["type"] == "contains":
        value_ok, detail = check_contains(result, expected)
    else:
        raise ValueError(f"unknown expected.type {expected['type']!r} in golden entry {entry['id']!r}")

    passed = route_ok and value_ok
    route_detail = f"route={result.get('route')!r} (expected {entry['route']!r})" + ("" if route_ok else " MISMATCH")
    return passed, f"{route_detail}; {detail}"


def run_eval(path: Path = GOLDEN_PATH) -> bool:
    entries = load_golden(path)
    n_passed = 0
    for entry in entries:
        passed, detail = run_one(entry)
        n_passed += passed
        status = "PASS" if passed else "FAIL"
        print(f"[{status}] {entry['id']}: {entry['question']!r} (city={entry.get('city_id', 'nyc')})")
        print(f"       {detail}")

    print(f"\n{n_passed}/{len(entries)} passed")
    return n_passed == len(entries)


def _selfcheck() -> None:
    """Runnable check on the comparison logic itself (no live calls)."""
    assert _normalize("147,174") == _normalize("147174") == "147174"
    ok, _ = check_numeric({"rows": [{"fare": 65.24}]}, {"value": 65.21851, "tolerance": 0.05})
    assert ok
    ok, _ = check_numeric({"rows": [{"fare": 70.0}]}, {"value": 65.21851, "tolerance": 0.05})
    assert not ok
    ok, _ = check_contains({"answer": "JFK Airport serves 147,174 total trips."}, {"items": ["jfk airport", "147174"]})
    assert ok
    ok, _ = check_contains({"answer": "no numbers here"}, {"items": ["147174"]})
    assert not ok


if __name__ == "__main__":
    _selfcheck()
    all_passed = run_eval()
    sys.exit(0 if all_passed else 1)

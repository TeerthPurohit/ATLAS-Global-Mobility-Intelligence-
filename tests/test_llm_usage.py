"""Phase 4 token/cost accounting tests -- pure logic, no external services.
Covers both the per-request counter (summary(), reset by backend/main.py's
timing middleware every request) and the process-wide counter
(lifetime_summary(), read by GET /rag/metrics) since they're deliberately
separate (see llm_usage.py's module docstring for why).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "rag"))

import llm_usage
from llm_pricing import PRICING_PER_1M_TOKENS


def test_summary_reflects_only_calls_since_last_reset():
    llm_usage.reset()
    llm_usage.record(model="priced-model", prompt_tokens=100, completion_tokens=50)
    llm_usage.record(model="unpriced-model", prompt_tokens=10, completion_tokens=10)

    result = llm_usage.summary()
    assert result["llm_calls"] == 2
    assert result["total_tokens"] == 170


def test_cost_usd_none_when_no_call_has_known_pricing():
    llm_usage.reset()
    llm_usage.record(model="totally-unpriced-model", prompt_tokens=10, completion_tokens=10)
    assert llm_usage.summary()["cost_usd"] is None


def test_cost_usd_computed_only_for_priced_calls_not_fabricated_for_others():
    PRICING_PER_1M_TOKENS["test-priced-model"] = {"prompt": 1.0, "completion": 2.0}
    try:
        llm_usage.reset()
        llm_usage.record(model="test-priced-model", prompt_tokens=1_000_000, completion_tokens=1_000_000)
        llm_usage.record(model="unpriced-model", prompt_tokens=999, completion_tokens=999)

        result = llm_usage.summary()
        assert result["cost_usd"] == 3.0  # 1.0 + 2.0, unpriced call contributes nothing (not $0 fabricated)
    finally:
        del PRICING_PER_1M_TOKENS["test-priced-model"]


def test_reset_does_not_clear_lifetime_summary():
    llm_usage.reset()
    llm_usage.record(model="unpriced-model", prompt_tokens=5, completion_tokens=5)
    before = llm_usage.lifetime_summary()["llm_calls"]

    llm_usage.reset()  # simulates the next request's middleware reset
    assert llm_usage.summary()["llm_calls"] == 0  # per-request counter is empty again
    assert llm_usage.lifetime_summary()["llm_calls"] == before  # lifetime counter is untouched

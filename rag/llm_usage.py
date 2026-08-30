"""Per-request LLM token/cost accumulator (Phase 4), read by
backend/main.py's existing `log_requests` timing middleware.

A `contextvars.ContextVar` rather than a module-level list: FastAPI runs
each request's sync route handlers via `anyio.to_thread.run_sync`, which
copies the *current* contextvars.Context into the worker thread, so a
request-scoped `reset()`/`record()`/`summary()` cycle stays isolated
per-request without needing a request object threaded through every LLM
call site. The ContextVar's default is `None`, not a mutable `[]` --
`ContextVar(default=[])` would share one list object across every context
that never called `.set()`, silently leaking calls between unrelated
requests (or between requests and standalone script runs).
"""
from __future__ import annotations

from contextvars import ContextVar

from llm_pricing import PRICING_PER_1M_TOKENS

_calls: ContextVar[list[dict] | None] = ContextVar("llm_usage_calls", default=None)

# Process-wide running totals, separate from the per-request ContextVar above.
# backend/main.py's middleware calls reset() at the start of EVERY request
# (including a GET /rag/metrics request itself, which makes no LLM call) --
# so summary() alone would always read back empty from inside that handler.
# These globals (same pattern as semantic_cache.py's _HITS/_MISSES) track
# "since this process started" for platform_service.get_rag_metrics().
_lifetime_calls = 0
_lifetime_tokens = 0
_lifetime_cost_usd = 0.0
_lifetime_has_known_cost = False


def _get_calls() -> list[dict]:
    calls = _calls.get()
    if calls is None:
        calls = []
        _calls.set(calls)
    return calls


def reset() -> None:
    _calls.set([])


def record(*, model: str, prompt_tokens: int, completion_tokens: int) -> None:
    pricing = PRICING_PER_1M_TOKENS.get(model)
    cost_usd = None
    if pricing:
        cost_usd = (prompt_tokens * pricing["prompt"] + completion_tokens * pricing["completion"]) / 1_000_000
    total_tokens = prompt_tokens + completion_tokens
    _get_calls().append({
        "model": model,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens,
        "cost_usd": cost_usd,
    })

    global _lifetime_calls, _lifetime_tokens, _lifetime_cost_usd, _lifetime_has_known_cost
    _lifetime_calls += 1
    _lifetime_tokens += total_tokens
    if cost_usd is not None:
        _lifetime_cost_usd += cost_usd
        _lifetime_has_known_cost = True


def summary() -> dict:
    """Per-request summary (this request's calls only) -- cost_usd is None
    (not 0.0) whenever no call this request had a known price, distinguishing
    "zero cost" from "cost not yet configured". Used by backend/main.py's
    timing middleware for its per-request log line."""
    calls = _get_calls()
    known_costs = [c["cost_usd"] for c in calls if c["cost_usd"] is not None]
    return {
        "llm_calls": len(calls),
        "total_tokens": sum(c["total_tokens"] for c in calls),
        "cost_usd": sum(known_costs) if known_costs else None,
    }


def lifetime_summary() -> dict:
    """Cumulative totals since this process started, across every request --
    used by platform_service.get_rag_metrics() (GET /rag/metrics), which
    would otherwise always read back an empty summary() (see the module
    docstring above)."""
    return {
        "llm_calls": _lifetime_calls,
        "total_tokens": _lifetime_tokens,
        "cost_usd": _lifetime_cost_usd if _lifetime_has_known_cost else None,
    }


def demo() -> None:
    reset()
    record(model="gpt-5.4-nano", prompt_tokens=100, completion_tokens=50)
    record(model="some-unpriced-model", prompt_tokens=10, completion_tokens=10)
    result = summary()
    assert result["llm_calls"] == 2
    assert result["total_tokens"] == 170
    lifetime = lifetime_summary()
    assert lifetime["llm_calls"] >= 2, "lifetime total must survive a reset()"
    print(f"llm_usage demo OK: request={result} lifetime={lifetime}")


if __name__ == "__main__":
    demo()

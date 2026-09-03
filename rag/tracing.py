"""Optional Langfuse tracing for every LLM call (Phase 4). Entirely a
no-op -- no client constructed, no import, no network call -- when
LANGFUSE_PUBLIC_KEY is unset, same optional-adapter discipline as
OPENWEATHER_API_KEY/GEONAMES_USERNAME in .env.example. Never raises: a
tracing backend being unreachable must not break a real LLM answer, same
fail-open discipline semantic_cache.py/session_store.py use for their own
backends.

SDK shape verified against Context7 (/langfuse/langfuse-python) for the
current (v3+) low-level API -- the @observe decorator in older docs isn't
a fit for a synchronous library helper called from arbitrary call sites.
"""
from __future__ import annotations

import os
import sys
from contextlib import ExitStack, contextmanager

LANGFUSE_PUBLIC_KEY = os.environ.get("LANGFUSE_PUBLIC_KEY", "")

_client = None
_propagate_attributes = None
if LANGFUSE_PUBLIC_KEY:
    from langfuse import Langfuse
    from langfuse import propagate_attributes as _propagate_attributes

    # LANGFUSE_ENVIRONMENT defaults to "development" so a laptop/CI run never
    # lands in the same Langfuse "production" view as deployed backend traffic.
    _client = Langfuse(environment=os.environ.get("LANGFUSE_ENVIRONMENT", "development"))


def log_generation(
    *, name: str, model: str, prompt_version: str | None, messages: list[dict],
    output: str, prompt_tokens: int | None, completion_tokens: int | None,
    latency_s: float,
) -> None:
    if _client is None:
        return
    try:
        usage_details = None
        if prompt_tokens is not None and completion_tokens is not None:
            usage_details = {"prompt_tokens": prompt_tokens, "completion_tokens": completion_tokens}
        generation = _client.start_observation(
            name=name,
            as_type="generation",
            input=messages,
            model=model,
            metadata={"prompt_version": prompt_version} if prompt_version else None,
            usage_details=usage_details,
        )
        generation.update(output=output)
        generation.end()
    except Exception as exc:  # noqa: BLE001
        print(f"[warn] Langfuse tracing failed ({exc}); continuing without it", file=sys.stderr)


@contextmanager
def trace_request(*, name: str, question: str, session_id: str, user_id: int | None):
    """Root span for one chat request. Every chat_completion() call made
    inside this context (classify, SQL/query-plan generation, explanatory
    synthesis) nests under it via OTel's ambient context instead of each
    landing as its own disconnected trace, and inherits session_id/user_id
    for the Sessions/Users views. No-op (yields None) when Langfuse isn't
    configured; setup/teardown failures are swallowed the same fail-open
    way as log_generation -- only the caller's own exceptions, raised past
    the `yield`, are allowed to propagate.
    """
    if _client is None:
        yield None
        return

    stack = ExitStack()
    try:
        span = stack.enter_context(_client.start_as_current_span(name=name, input=question))
        stack.enter_context(_propagate_attributes(
            session_id=session_id,
            user_id=str(user_id) if user_id is not None else None,
        ))
    except Exception as exc:  # noqa: BLE001
        print(f"[warn] Langfuse trace_request setup failed ({exc}); continuing without it", file=sys.stderr)
        stack.close()
        yield None
        return

    try:
        yield span
    finally:
        try:
            stack.close()
        except Exception as exc:  # noqa: BLE001
            print(f"[warn] Langfuse trace_request teardown failed ({exc}); continuing without it", file=sys.stderr)


def update_trace(*, output: str | None = None, route: str | None = None) -> None:
    """Set the final answer/route on the current trace_request span. Safe to
    call even when tracing is off or trace_request's own setup failed."""
    if _client is None:
        return
    try:
        _client.update_current_trace(output=output, tags=[t for t in ("chat", route) if t])
    except Exception as exc:  # noqa: BLE001
        print(f"[warn] Langfuse update_trace failed ({exc}); continuing without it", file=sys.stderr)


@contextmanager
def trace_span(*, name: str, as_type: str = "span", input=None):  # noqa: A002
    """Wraps one non-LLM step (e.g. vector retrieval) as its own observation
    nested under the current trace_request span -- so it shows up as its own
    node (with its own latency) instead of being invisible time inside the
    generation that follows it. Same setup/teardown-only failure containment
    as trace_request: the caller's own exceptions still propagate normally.
    """
    if _client is None:
        yield
        return
    stack = ExitStack()
    try:
        stack.enter_context(_client.start_as_current_observation(name=name, as_type=as_type, input=input))
    except Exception as exc:  # noqa: BLE001
        print(f"[warn] Langfuse trace_span setup failed ({exc}); continuing without it", file=sys.stderr)
        stack.close()
        yield
        return
    try:
        yield
    finally:
        try:
            stack.close()
        except Exception as exc:  # noqa: BLE001
            print(f"[warn] Langfuse trace_span teardown failed ({exc}); continuing without it", file=sys.stderr)


def update_span(*, output=None) -> None:  # noqa: ANN001
    """Set output on whichever observation is currently active (trace_span
    or trace_request). Safe no-op when tracing is off."""
    if _client is None:
        return
    try:
        _client.update_current_span(output=output)
    except Exception as exc:  # noqa: BLE001
        print(f"[warn] Langfuse update_span failed ({exc}); continuing without it", file=sys.stderr)


def flush() -> None:
    """Force-send any batched spans/generations before the process exits.
    Safe no-op when tracing is off; the OTel batch exporter otherwise holds
    up to a few seconds of traces in memory that a hard shutdown would drop."""
    if _client is None:
        return
    try:
        _client.flush()
    except Exception as exc:  # noqa: BLE001
        print(f"[warn] Langfuse flush failed ({exc})", file=sys.stderr)


def demo() -> None:
    with trace_request(name="tracing.demo_request", question="hello", session_id="demo-session", user_id=1) as span:
        assert (span is None) == (_client is None), "trace_request should yield a span iff a client is configured"
        log_generation(
            name="tracing.demo", model="gpt-5.4-nano", prompt_version="v1",
            messages=[{"role": "user", "content": "hello"}], output="hi",
            prompt_tokens=5, completion_tokens=2, latency_s=0.1,
        )
        update_trace(output="hi", route="explanatory")
    if _client is not None:
        _client.flush()
    print("tracing demo OK (no-op since LANGFUSE_PUBLIC_KEY is unset in this environment)"
          if _client is None else "tracing demo OK (real client used, flushed to Langfuse)")


if __name__ == "__main__":
    demo()

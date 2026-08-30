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

LANGFUSE_PUBLIC_KEY = os.environ.get("LANGFUSE_PUBLIC_KEY", "")

_client = None
if LANGFUSE_PUBLIC_KEY:
    from langfuse import Langfuse

    _client = Langfuse()  # reads LANGFUSE_PUBLIC_KEY/LANGFUSE_SECRET_KEY/LANGFUSE_HOST from env


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


def demo() -> None:
    log_generation(
        name="tracing.demo", model="gpt-5.4-nano", prompt_version="v1",
        messages=[{"role": "user", "content": "hello"}], output="hi",
        prompt_tokens=5, completion_tokens=2, latency_s=0.1,
    )
    print("tracing demo OK (no-op since LANGFUSE_PUBLIC_KEY is unset in this environment)"
          if _client is None else "tracing demo OK (real client used)")


if __name__ == "__main__":
    demo()

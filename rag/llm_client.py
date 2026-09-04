"""Shared local-model-primary / DeepSeek-secondary / OpenAI-fallback chat
completion helper.

DeepSeek's and llama.cpp's APIs are both OpenAI-compatible (same `openai`
SDK, different base_url), so this is one call site for all fallback logic
instead of duplicating try/except across sql_agent.py and rag_pipeline.py.
Both LLM uses in this repo (QueryPlan generation, explanatory-answer
synthesis) are approved uses per .claude/rules.md -- this module doesn't
change what the LLM is allowed to do, only which provider answers the call.

Local model (spec-014 FR-7) is tried first when configured: a fine-tuned,
quantized model on an Oracle Always-Free VM (docs/superpowers/specs/
2026-08-27-local-queryplan-model-design.md). If it's unreachable or fails,
falls through to DeepSeek, then OpenAI -- same reliability story as before
this tier existed, just with one more (optional) link at the front.
"""
from __future__ import annotations

import os
import time

import llm_usage
import tracing

LOCAL_MODEL_BASE_URL = os.environ.get("LOCAL_MODEL_BASE_URL", "")
LOCAL_MODEL_API_KEY = os.environ.get("LOCAL_MODEL_API_KEY", "")
LOCAL_MODEL_NAME = os.environ.get("LOCAL_MODEL_NAME", "queryplan")

DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DEEPSEEK_MODEL = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")
DEEPSEEK_BASE_URL = "https://api.deepseek.com"

from openai import OpenAI  # noqa: E402


def chat_completion(*, model: str, trace_name: str | None = None, prompt_version: str | None = None, **kwargs):
    """Same call shape as `OpenAI().chat.completions.create(...)`, plus two
    optional Phase 4 observability kwargs that never reach the OpenAI SDK:
    `trace_name`/`prompt_version` tag a Langfuse generation trace (no-op if
    Langfuse isn't configured, see tracing.py) and both are omitted by
    callers that don't care about production observability. Token usage is
    always recorded via llm_usage.py regardless of whether tracing is
    configured, for the request-scoped cost logging in backend/main.py's
    timing middleware -- streaming calls included: `stream=True` gets
    `stream_options={"include_usage": True}` injected automatically (unless
    the caller already set it) and the returned iterator is wrapped so
    usage/tracing are recorded once the caller finishes consuming it,
    exactly like the non-streaming path. Recording is centralized here
    specifically so a future streaming call site can't forget to wire it up
    the way `rag_pipeline.answer_stream()` originally did.

    Tries the local model first if configured, then DeepSeek if configured,
    falling through to OpenAI with the caller's original `model` on any
    failure. Callers still wrap this in their own try/except for the "no
    LLM available at all" case -- this function only handles picking a
    provider."""
    start = time.monotonic()
    streaming = bool(kwargs.get("stream"))
    if streaming:
        kwargs.setdefault("stream_options", {"include_usage": True})

    resp = _dispatch_completion(model=model, **kwargs)

    if streaming:
        return _instrumented_stream(
            resp, trace_name=trace_name, prompt_version=prompt_version,
            messages=kwargs.get("messages", []), start=start,
        )

    latency_s = time.monotonic() - start
    usage = getattr(resp, "usage", None)
    if usage is not None:
        llm_usage.record(model=resp.model, prompt_tokens=usage.prompt_tokens, completion_tokens=usage.completion_tokens)
    if trace_name:
        tracing.log_generation(
            name=trace_name,
            model=resp.model,
            prompt_version=prompt_version,
            messages=kwargs.get("messages", []),
            output=resp.choices[0].message.content or "",
            prompt_tokens=usage.prompt_tokens if usage else None,
            completion_tokens=usage.completion_tokens if usage else None,
            latency_s=latency_s,
        )
    return resp


def _instrumented_stream(stream, *, trace_name: str | None, prompt_version: str | None, messages: list[dict], start: float):
    """Transparently re-yields every chunk from `stream` unchanged, so a
    caller's existing `for chunk in stream:` loop needs no restructuring --
    only accumulating usage/text on the side and recording once the caller
    stops iterating (StopIteration or an early `break`/exception both hit
    the `finally`)."""
    accumulated_text = ""
    resp_model = None
    usage = None
    try:
        for chunk in stream:
            if getattr(chunk, "model", None):
                resp_model = chunk.model
            if getattr(chunk, "usage", None):
                usage = chunk.usage
            if chunk.choices:
                delta = chunk.choices[0].delta.content or ""
                accumulated_text += delta
            yield chunk
    finally:
        if usage is not None and resp_model is not None:
            llm_usage.record(model=resp_model, prompt_tokens=usage.prompt_tokens, completion_tokens=usage.completion_tokens)
        if trace_name:
            tracing.log_generation(
                name=trace_name,
                model=resp_model or "unknown",
                prompt_version=prompt_version,
                messages=messages,
                output=accumulated_text,
                prompt_tokens=usage.prompt_tokens if usage else None,
                completion_tokens=usage.completion_tokens if usage else None,
                latency_s=time.monotonic() - start,
            )


def provider_label(model_name: str) -> str:
    """Human label for whichever tier `_dispatch_completion` actually used,
    derived from the model name on the returned/streamed response (chunks
    carry `.model` from the provider that served them, not the `model`
    kwarg the caller originally asked for)."""
    if model_name == LOCAL_MODEL_NAME:
        return "Fine-tuned Qwen"
    if model_name == DEEPSEEK_MODEL:
        return "DeepSeek"
    return "OpenAI"


def _dispatch_completion(*, model: str, **kwargs):
    # Explicit timeouts AND max_retries=0 on every tier: without a timeout,
    # the openai SDK's own default (600s) means a slow/overloaded provider
    # hangs the whole request instead of failing fast into the next tier's
    # degrade path -- the same class of bug rag/db.py's connect_timeout=3
    # fixed for Postgres. Found via a real hang: 4 concurrent
    # journey_narrative.generate calls (the Compare page) queued up against
    # the single-instance local model VM and none ever returned.
    #
    # A timeout alone wasn't enough: the SDK's own default max_retries=2
    # means one "attempt" is actually retried twice more internally before
    # the exception ever reaches this except block -- a 15s timeout was
    # really a 45s wait (measured: journey/estimate calls taking ~50s
    # total with the local model down, even though DeepSeek itself answers
    # in under 1s when called directly). max_retries=0 makes the configured
    # timeout the real, single wait per tier.
    if LOCAL_MODEL_BASE_URL:
        try:
            client = OpenAI(api_key=LOCAL_MODEL_API_KEY, base_url=LOCAL_MODEL_BASE_URL, timeout=5.0, max_retries=0)
            return client.chat.completions.create(model=LOCAL_MODEL_NAME, **kwargs)
        except Exception as exc:  # noqa: BLE001
            import sys
            print(f"[warn] local model call failed ({exc}); falling back to DeepSeek/OpenAI", file=sys.stderr)

    if DEEPSEEK_API_KEY:
        try:
            client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL, timeout=10.0, max_retries=0)
            return client.chat.completions.create(model=DEEPSEEK_MODEL, **kwargs)
        except Exception as exc:  # noqa: BLE001
            import sys
            print(f"[warn] DeepSeek call failed ({exc}); falling back to OpenAI", file=sys.stderr)

    client = OpenAI()
    return client.chat.completions.create(model=model, **kwargs)


def demo() -> None:
    resp = chat_completion(
        model="gpt-5.4-nano",
        messages=[{"role": "user", "content": "Reply with exactly one word: OK"}],
        max_completion_tokens=10,
    )
    text = (resp.choices[0].message.content or "").strip()
    assert text, "expected some response text"
    print(f"llm_client demo OK: got {text!r}")


if __name__ == "__main__":
    demo()

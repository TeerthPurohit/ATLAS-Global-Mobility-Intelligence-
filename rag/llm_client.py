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

LOCAL_MODEL_BASE_URL = os.environ.get("LOCAL_MODEL_BASE_URL", "")
LOCAL_MODEL_API_KEY = os.environ.get("LOCAL_MODEL_API_KEY", "")
LOCAL_MODEL_NAME = os.environ.get("LOCAL_MODEL_NAME", "queryplan")

DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DEEPSEEK_MODEL = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")
DEEPSEEK_BASE_URL = "https://api.deepseek.com"

from openai import OpenAI  # noqa: E402  -- module-level so tests can monkeypatch it


def chat_completion(*, model: str, **kwargs):
    """Same call shape as `OpenAI().chat.completions.create(...)`. Tries the
    local model first if configured, then DeepSeek if configured, falling
    through to OpenAI with the caller's original `model` on any failure.
    Callers still wrap this in their own try/except for the "no LLM
    available at all" case -- this function only handles picking a
    provider."""
    if LOCAL_MODEL_BASE_URL:
        try:
            client = OpenAI(api_key=LOCAL_MODEL_API_KEY, base_url=LOCAL_MODEL_BASE_URL)
            return client.chat.completions.create(model=LOCAL_MODEL_NAME, **kwargs)
        except Exception as exc:  # noqa: BLE001 -- fall through to DeepSeek/OpenAI
            import sys
            print(f"[warn] local model call failed ({exc}); falling back to DeepSeek/OpenAI", file=sys.stderr)

    if DEEPSEEK_API_KEY:
        try:
            client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL)
            return client.chat.completions.create(model=DEEPSEEK_MODEL, **kwargs)
        except Exception as exc:  # noqa: BLE001 -- fall through to OpenAI
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

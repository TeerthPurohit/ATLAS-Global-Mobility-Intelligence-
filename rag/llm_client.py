"""Shared DeepSeek-primary / OpenAI-fallback chat completion helper.

DeepSeek's API is OpenAI-compatible (same `openai` SDK, different base_url),
so this is one call site for the fallback logic instead of duplicating
try/except across sql_agent.py and rag_pipeline.py. Both LLM uses in this
repo (QueryPlan generation, explanatory-answer synthesis) are approved uses
per .claude/rules.md -- this module doesn't change what the LLM is allowed
to do, only which provider answers the call.
"""
from __future__ import annotations

import os

DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DEEPSEEK_MODEL = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")
DEEPSEEK_BASE_URL = "https://api.deepseek.com"


def chat_completion(*, model: str, **kwargs):
    """Same call shape as `OpenAI().chat.completions.create(...)`. Tries
    DeepSeek first if configured; any failure (network, bad param, quota)
    falls through to OpenAI with the caller's original `model`. Callers
    still wrap this in their own try/except for the "no LLM available at
    all" case -- this function only handles picking a provider."""
    from openai import OpenAI

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

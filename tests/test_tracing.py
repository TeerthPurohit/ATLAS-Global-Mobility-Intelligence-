"""Phase 4 Langfuse tracing test: log_generation() must never raise and must
not require network access when LANGFUSE_PUBLIC_KEY is unset -- this is the
default in CI and for any dev machine without a Langfuse project.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "rag"))

import tracing


def test_log_generation_is_a_safe_noop_without_langfuse_configured(monkeypatch):
    monkeypatch.setattr(tracing, "_client", None)
    tracing.log_generation(
        name="test.trace", model="gpt-5.4-nano", prompt_version="v1",
        messages=[{"role": "user", "content": "hello"}], output="hi",
        prompt_tokens=5, completion_tokens=2, latency_s=0.05,
    )  # must not raise

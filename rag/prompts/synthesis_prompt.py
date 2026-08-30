"""Versioned prompt for rag_pipeline.py's grounded-answer synthesis call
(both the non-streaming and streaming paths). Bump VERSION whenever
TEMPLATE's wording changes meaningfully -- Langfuse traces tag each
generation with this string so a prompt-wording regression is traceable to
the version that caused it, not just the call's timestamp.
"""
from __future__ import annotations

VERSION = "v1"

TEMPLATE = """Answer the user's question in 2-4 plain-language \
sentences using ONLY facts and numbers that literally appear in the \
retrieved context below. Do not calculate, round, infer, or add any number, \
statistic, or comparison that isn't already stated in the context. If the \
context doesn't fully answer the question, say plainly what it does cover \
and note the rest isn't available -- never guess.

Retrieved context:
{context}
"""

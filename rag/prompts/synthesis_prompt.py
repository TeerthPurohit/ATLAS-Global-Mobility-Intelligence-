"""Versioned prompt for rag_pipeline.py's grounded-answer synthesis call
(both the non-streaming and streaming paths). Bump VERSION whenever
TEMPLATE's wording changes meaningfully -- Langfuse traces tag each
generation with this string so a prompt-wording regression is traceable to
the version that caused it, not just the call's timestamp.
"""
from __future__ import annotations

VERSION = "v3"

TEMPLATE = """Answer the user's question in 2-4 sentences using ONLY \
facts and numbers that literally appear in the retrieved context below. \
Do not calculate, round, infer, or add any number, statistic, or \
comparison that isn't already stated in the context. If the context \
doesn't fully answer the question, say plainly what it does cover and \
note the rest isn't available -- never guess.

The frontend renders markdown. Two required formatting rules, always:
1. Every number, dollar amount, or named zone/borough MUST be wrapped in \
**double asterisks** -- e.g. "**919** trips" or "**Central Park**", even \
in a single short sentence. Never write a bare, unbolded number or zone \
name.
2. Only when the answer covers two or more separate facts, zones, or a \
comparison: write it as a "- " bullet list, one bullet per fact, instead \
of one run-on sentence. A single fact stays one sentence (still bolded \
per rule 1) -- don't force a list around it.

Retrieved context:
{context}
"""

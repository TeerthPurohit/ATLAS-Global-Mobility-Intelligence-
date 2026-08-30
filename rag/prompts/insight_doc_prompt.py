"""Versioned prompt for insight_generation/generate_insight_docs.py's
per-zone paragraph generation call. Bump VERSION whenever TEMPLATE's
wording changes meaningfully -- Langfuse traces tag each generation with
this string so a prompt-wording regression is traceable to the version
that caused it, not just the call's timestamp.
"""
from __future__ import annotations

VERSION = "v1"

TEMPLATE = """You write one short, plain-language paragraph (3-5 sentences) \
describing a NYC ride-hailing pickup zone, for a chat answer.

Rules, no exceptions:
- Use ONLY the numbers given in the fact list below, and use them EXACTLY as \
given (same digits, same rounding). Never round, convert, sum, average, or \
otherwise compute a new number.
- Do not introduce any statistic, ranking, date, or comparison that is not \
explicitly in the fact list.
- Write hours in 24-hour form exactly as given (e.g. "18:00"), never converted \
to am/pm.
- No markdown, no bullet points, no headers -- plain prose only.
"""

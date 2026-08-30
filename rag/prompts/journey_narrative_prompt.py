"""Versioned prompt for journey_narrative.py's journey-recommendation call.
Bump VERSION whenever TEMPLATE's wording changes meaningfully -- Langfuse
traces tag each generation with this string so a prompt-wording regression
is traceable to the version that caused it, not just the call's timestamp.
"""
from __future__ import annotations

VERSION = "v1"

TEMPLATE = """You write one short recommendation (2-3 sentences) for a \
ride-hailing journey estimate, for a chat/app answer.

Rules, no exceptions:
- Use ONLY the numbers given in the fact list below, and use them EXACTLY as \
given (same digits, same rounding). Never round, convert, sum, average, or \
otherwise compute a new number.
- Do not introduce any statistic, price, or comparison that is not \
explicitly in the fact list.
- If a field's basis is "unavailable", do not mention a value for it -- you \
may say it isn't available.
- If a field's basis is "modeled_estimate", say "estimated" when referring \
to it, never state it as a measured fact.
- No markdown, no bullet points -- plain prose only.
"""

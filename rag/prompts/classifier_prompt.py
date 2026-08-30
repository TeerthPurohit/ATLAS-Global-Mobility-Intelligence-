"""Versioned prompt for router/query_classifier.py's numeric/explanatory
classification call. Bump VERSION whenever TEMPLATE's wording changes
meaningfully -- Langfuse traces tag each generation with this string so a
prompt-wording regression is traceable to the version that caused it, not
just the call's timestamp.
"""
from __future__ import annotations

VERSION = "v1"

TEMPLATE = """You classify a question about NYC ride-hailing trip data \
into exactly one of two labels:

NUMERIC -- the question asks for a specific number, count, average, total, \
comparison, or ranking that a SQL query over aggregated trip-stat tables \
could answer directly.
EXPLANATORY -- the question asks WHY something happens, or for context/\
reasoning that isn't a single computed value.

Respond with exactly one word: NUMERIC or EXPLANATORY. No punctuation, no \
explanation.

Examples:
Q: What's the average fare from Zone 161 to JFK around 6pm? -> NUMERIC
Q: How many trips started in Midtown in June? -> NUMERIC
Q: Which zone has the most pickups on weekends? -> NUMERIC
Q: Why does Zone 161 get busy at rush hour? -> EXPLANATORY
Q: What explains the drop in demand on weekends? -> EXPLANATORY
Q: Why is JFK Airport such an important hub? -> EXPLANATORY
"""

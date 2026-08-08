"""AI Recommendations for a journey estimate (ADR-007). Reuses
`generate_insight_docs.py`'s `extract_numbers`/`validate_grounding` exactly
as `rag_pipeline.py._synthesize_explanatory` already does: the LLM may only
restate numbers present in the journey's own prediction bundle -- it never
computes or invents a new one. Falls back to a template sentence (built
from the same facts) if the LLM is unavailable or fails grounding.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import OPENAI_MODEL  # noqa: E402
from insight_generation.generate_insight_docs import extract_numbers, validate_grounding  # noqa: E402

SYSTEM_PROMPT = """You write one short recommendation (2-3 sentences) for a \
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


def _facts_from_components(components: dict) -> dict:
    """`components` is the dict[str, PredictionResult] journey_service.estimate()
    returns. Extract only what's needed for narration -- avoids importing
    backend.predictors.base into rag/ (rag/ stays independent of backend/)."""
    facts = {}
    for key in ("fare", "fare_range", "duration", "demand", "ride_availability", "surge_risk", "congestion", "confidence"):
        pr = components.get(key)
        if pr is None:
            continue
        facts[key] = {"value": pr.value, "unit": pr.unit, "basis": pr.basis, "reason": pr.reason}
    return facts


def _allowed_numbers(facts: dict) -> set[float]:
    allowed = set()
    for entry in facts.values():
        value = entry["value"]
        if isinstance(value, (int, float)):
            allowed.add(float(value))
        elif isinstance(value, str):
            # fare_range is "12.34-56.78"; surge_risk/availability are text buckets
            allowed.update(extract_numbers(value))
    return allowed


def _template_sentence(facts: dict) -> str:
    parts = []
    fare = facts.get("fare")
    if fare and fare["basis"] != "unavailable":
        qualifier = "an estimated" if fare["basis"] == "modeled_estimate" else ""
        parts.append(f"This trip is {qualifier} ${fare['value']:.2f}." if isinstance(fare["value"], (int, float)) else "")
    availability = facts.get("ride_availability")
    if availability and availability["basis"] != "unavailable":
        parts.append(f"Ride availability is estimated {availability['value']}.")
    surge = facts.get("surge_risk")
    if surge and surge["basis"] != "unavailable":
        parts.append(f"Surge risk is estimated {surge['value']}.")
    if not parts:
        parts.append("Not enough data is available yet to make a recommendation for this journey.")
    return " ".join(p for p in parts if p)


def generate(components: dict) -> tuple[str, str]:
    """Returns (text, basis) -- basis is "modeled_estimate" for any LLM-
    phrased text (it's prose built from estimates, never presented as a
    measured fact) or "unavailable" if there isn't enough grounded data to
    say anything useful."""
    facts = _facts_from_components(components)
    if not any(f["basis"] != "unavailable" for f in facts.values()):
        return "Not enough data is available yet to make a recommendation for this journey.", "unavailable"

    text = _phrase_with_llm(facts)
    if text is None:
        text = _template_sentence(facts)
    return text, "modeled_estimate"


def _phrase_with_llm(facts: dict) -> str | None:
    import json

    try:
        from llm_client import chat_completion
    except ImportError:
        return None
    try:
        resp = chat_completion(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": "Fact list:\n" + json.dumps(facts, indent=2, default=str)},
            ],
            temperature=0.2,
            max_completion_tokens=200,
        )
        text = (resp.choices[0].message.content or "").strip()
    except Exception:  # noqa: BLE001 -- any LLM/network failure falls back to the template
        return None

    if not text or not validate_grounding(text, _allowed_numbers(facts)):
        return None
    return text

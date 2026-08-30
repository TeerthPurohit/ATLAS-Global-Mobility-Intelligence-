"""Numeric vs explanatory intent router (FR-4, ADR-004).

A short LLM classification prompt -- deliberately not a trained classifier
(rule 7: don't over-engineer routing between two labels). If the LLM call
itself fails (bad/missing key, network, rate limit) or returns something
unparseable, a keyword heuristic decides instead of silently defaulting --
see `_heuristic_classify()`. Per ADR-004, a genuinely ambiguous question
routes to NL-to-SQL first (SQL beats LLM reasoning, rule 1's precedence
order), so both the LLM prompt and the heuristic fallback default to
NUMERIC when unsure.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import OPENAI_MODEL
from prompts.classifier_prompt import TEMPLATE as SYSTEM_PROMPT, VERSION as PROMPT_VERSION

NUMERIC = "numeric"
EXPLANATORY = "explanatory"

_GREETING_HINTS = re.compile(
    r"^\s*(h+e+y+|h+i+|h+e+l+o+|y+o+|sup|howdy|greetings|good\s+(morning|afternoon|evening)|who\s+are\s+you|what\s+can\s+you\s+do|help)[\s!?.]*$",
    re.IGNORECASE,
)
_EXPLANATORY_HINTS = re.compile(
    r"\bwhy\b|\bexplains?\b|how come|what causes|what drives|what makes|reasons? (for|why)", re.IGNORECASE
)
_NUMERIC_HINTS = re.compile(
    r"\b(how many|how much|average|avg|median|max(imum)?|min(imum)?|total|count|"
    r"what'?s the|sum of|number of|top \d+|percent(age)?|rank(ed|ing)?)\b",
    re.IGNORECASE,
)


def _heuristic_classify(question: str) -> str:
    if _GREETING_HINTS.search(question.strip()):
        return EXPLANATORY
    if _EXPLANATORY_HINTS.search(question):
        return EXPLANATORY
    if _NUMERIC_HINTS.search(question):
        return NUMERIC
    # Ambiguous -- ADR-004: numeric/SQL takes precedence over LLM reasoning.
    return NUMERIC


def classify(question: str, model: str = OPENAI_MODEL) -> str:
    if _GREETING_HINTS.search(question.strip()):
        return EXPLANATORY
    try:
        from llm_client import chat_completion

        resp = chat_completion(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": question},
            ],
            temperature=0,
            max_completion_tokens=20,
            trace_name="query_classifier.classify",
            prompt_version=PROMPT_VERSION,
        )
        label = (resp.choices[0].message.content or "").strip().upper()
        if label.startswith("NUMERIC"):
            return NUMERIC
        if label.startswith("EXPLANATORY"):
            return EXPLANATORY
        print(f"[warn] classifier returned unparseable label {label!r}; using keyword heuristic", file=sys.stderr)
    except Exception as exc:  # noqa: BLE001
        print(f"[warn] classifier LLM call failed ({exc}); using keyword heuristic", file=sys.stderr)
    return _heuristic_classify(question)


_TEST_SET = [
    ("What's the average fare from Zone 161 to JFK around 6pm?", NUMERIC),
    ("How many trips started in Midtown in June?", NUMERIC),
    ("Which pickup zone has the highest average fare?", NUMERIC),
    ("What's the median trip distance for East Village pickups?", NUMERIC),
    ("Why does Zone 161 get busy at rush hour?", EXPLANATORY),
    ("Why is JFK Airport such an important hub in the network?", EXPLANATORY),
    ("What explains the drop in demand on weekends?", EXPLANATORY),
    ("Why do Brooklyn zones rank higher than raw trip volume would suggest?", EXPLANATORY),
]


def demo() -> None:
    correct = 0
    for question, expected in _TEST_SET:
        got = classify(question)
        status = "OK" if got == expected else "MISS"
        if got == expected:
            correct += 1
        print(f"  [{status}] ({got:>11}) {question}")
    print(f"\n{correct}/{len(_TEST_SET)} correct on the documented test set")
    assert correct == len(_TEST_SET), "router must classify the documented test set correctly"


if __name__ == "__main__":
    demo()

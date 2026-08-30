"""Per-model $/1M-token prices for llm_usage.py's cost calculation.

Empty by default, deliberately -- OpenAI's and DeepSeek's pricing pages
(and even their model names, e.g. DeepSeek no longer lists "deepseek-chat")
drift faster than this file's shelf life, and rule 2 of this repo ("no
fabricated metrics, zero tolerance") applies to code as much as to reported
results. A model with no entry here gets cost_usd=None from llm_usage.py,
never a guessed number -- token counts are still recorded and logged either
way. To enable real cost figures, paste verified numbers from the
provider's current pricing page below and cite the date checked, the same
way dbt_project/seeds/schema.yml cites its EPA emission-factor source, e.g.:

PRICING_PER_1M_TOKENS = {
    "gpt-5.4-nano": {"prompt": 0.05, "completion": 0.40},  # verified 2026-09-01, platform.openai.com/docs/pricing
}
"""
from __future__ import annotations

PRICING_PER_1M_TOKENS: dict[str, dict[str, float]] = {}

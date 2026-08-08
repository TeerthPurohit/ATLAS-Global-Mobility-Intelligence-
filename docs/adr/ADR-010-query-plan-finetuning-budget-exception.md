# ADR-010: Query-Plan Fine-Tuning Budget Exception

**Status:** Accepted (SPEC-014, Layer 4 RAG Fine-Tuning Track)

## Context

ADR-008 established a strict $0 budget constraint for external data-source adapters in Layer 5+. SPEC-014 introduces a schema-agnostic NL-to-SQL intermediate representation (`QueryPlan`) to allow the natural-language query engine to generalize across cities without memorizing NYC-specific table and column names. Fine-tuning an OpenAI base model (`gpt-5.4-nano`) on structured `QueryPlan` examples requires submitting an OpenAI fine-tuning API job, which incurs real API charges.

## Decision

We record an explicit, documented budget exception for SPEC-014 fine-tuning spend while maintaining strict controls:
1. **Human Approval Gate**: The programmatic dataset generation (`training_data_gen.py`), synthetic schema generation (`synthetic_schemas.py`), compiler (`query_plan_compiler.py`), and base-model evaluation pipeline (`evaluate.py`) are fully built and verified offline. Submitting the actual fine-tuning API job (`FR-7`) is explicitly gated on explicit human approval.
2. **Base-Model Baseline Requirement**: Before submitting any paid fine-tuning job, base-model zero-shot performance must be evaluated and recorded in `models/query_plan_finetune/eval_report.json` to provide an empirical baseline (53.8% exact-match on held-out NYC phrasings, 66.7% on synthetic schema).
3. **Small-Batch Scope**: The generated dataset is capped at a minimal size (~300 examples) to bound cost while providing a statistically sound generalization benchmark.

## Consequences

- The platform remains 100% $0-budget for all live-serving runtime paths (DuckDB, local XGBoost, free-tier discovery APIs).
- Fine-tuning costs are bounded, deterministic, and spent exclusively on model training for schema generalization.
- Empirical metrics before and after fine-tuning are recorded deterministically in `eval_report.json` without placeholders or estimated claims (respecting rule 2).

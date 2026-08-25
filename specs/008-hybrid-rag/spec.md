# SPEC-008: Hybrid RAG Chat Layer

Owner: solo builder · Status: done · Layer: 4 · Depends on: SPEC-002, SPEC-004, SPEC-006

## Business Goal

Answer both precise numeric questions and explanatory "why" questions
through one chat interface, routed to the right retrieval path. See
[Use-Cases.md](../../docs/product/Use-Cases.md) UC-3/UC-4 for the concrete
interactions this must support.

## Functional Requirements

- FR-1: `generate_insight_docs.py` — per-zone or zone-hour insight
  paragraphs, templated from real computed stats (marts + PageRank/EWMA
  outputs), LLM used only for phrasing, never for inventing numbers.
- FR-2: `build_vector_store.py` — embed insight docs (local
  sentence-transformer) and store in Qdrant (added as a docker-compose
  service 2026-08-06, `QDRANT_URL` env var, default
  `http://localhost:6333` for local dev outside Docker). Use `qdrant-client`.
  Collection: one point per insight doc, payload includes the doc's source
  zone/hour and the real stat values it was templated from (so retrieval
  results stay traceable, not just similarity-ranked text).
- FR-3: `sql_agent.py` — NL-to-SQL: prompt with mart schema only (not raw
  trip rows), generate SQL, execute against DuckDB, return result + query
  shown. See ADR-004.
- FR-4: `query_classifier.py` — route numeric vs explanatory intent, a
  short classification prompt, not a trained classifier (rule 7 — don't
  over-engineer this).
- FR-5: `rag_pipeline.py` — ties router → dispatch → grounded answer
  generation together. `answer()` must support both a normal blocking call
  and a streaming generator variant (yields token/chunk strings as the LLM
  produces them) so the backend can serve either a plain response or a
  WebSocket stream from the same pipeline — don't fork two copies of the
  routing/grounding logic.
- FR-6: 8-10 example Q&A pairs documented for the README/demo.
- FR-7 (added 2026-08-06, per-session history): `session_store.py` —
  SQLite-backed (stdlib `sqlite3`, not DuckDB — DuckDB is single-writer and
  already has lock contention with dbt/DBeaver/read paths; session writes
  are frequent small inserts, a poor fit for that) conversation history
  keyed by `session_id`. Schema: a session has many messages (role,
  content, route taken, sql shown if any, timestamp). `rag_pipeline.py`
  takes an optional `session_id` + prior turns as context for follow-up
  questions ("what about zone 161" referring back to a prior answer).

## Non-Functional Requirements

Every number in a chat response must trace to a query or a template value —
rule 2 in `.claude/rules.md`, no exceptions. Session history storage must
not block or conflict with the DuckDB warehouse connection (separate
SQLite file, see FR-7).

## Proposed Design

See [ADR-004](../../docs/adr/ADR-004-hybrid-rag-nl-to-sql.md) for why
numeric and explanatory questions use separate paths instead of one unified
RAG-over-text pipeline.

## Risks

Hallucination in `generate_insight_docs.py` if the LLM is given latitude
beyond phrasing — mitigate by templating every numeric value into the
prompt/output directly (LLM fills in connective language around fixed
numbers, never generates a number itself).

## Acceptance Criteria

- [ ] Insight docs generated, every number traceable to a source query.
- [ ] Vector store built and queryable.
- [ ] NL-to-SQL path returns real results + visible SQL for numeric
      questions.
- [ ] Router correctly dispatches on a documented test set of question
      examples (the 8-10 Q&A pairs from FR-6, used as the test).

# ADR-004: NL-to-SQL as a separate path from RAG-over-text, for numeric questions

**Status:** Accepted (Layer 4, not yet started)

## Context

The chat layer needs to answer two different question shapes: "what's the
average fare from Zone 161 at 6pm" (a precise number that exists in a mart)
and "why does Zone 161 get busy at rush hour" (an explanation requiring
synthesis of trend/context).

## Decision

Route on intent (`rag/router/query_classifier.py`). Numeric questions go to
`rag/nl_to_sql/sql_agent.py`, which generates SQL against the mart schema
and executes it against DuckDB, returning the real result plus the query
itself. Explanatory questions go to vector retrieval over
`rag/insight_generation` docs.

## Why

LLMs are unreliable at exact arithmetic and aggregation from retrieved text
snippets — asking an LLM to read ten retrieved sentences and correctly
compute an average is a worse method than just running `AVG()` in SQL, which
is what the number actually is. Pushing numeric questions to real SQL
execution is strictly more accurate and, per rule 2 in
`.claude/rules.md` (never fabricate results), it's the only approach
consistent with this project's "every displayed number traces to a query"
bar. Showing the generated SQL alongside the answer also makes the answer
auditable, which a pure text-generation answer isn't.

## Consequences

- Two code paths to build and maintain, not one unified "RAG does
  everything" pipeline — more upfront work, but each path is simpler and
  independently testable than a single path trying to do both jobs.
- `sql_agent.py` needs a hard boundary: it sees mart *schema* only, not raw
  trip-level tables, and executes against a read-only connection (see
  `docs/architecture/Security.md`).

# MCP QueryPlan Server - Design

Date: 2026-08-29
Status: Approved for planning
Spec: specs/016-mcp-queryplan-server/spec.md
Related: ADR-004 (NL-to-SQL via QueryPlan, not raw SQL text), ADR-007 (basis field), ADR-010 (fine-tuned QueryPlan model)

## Purpose

Phase 3 of the current roadmap: wrap rag/nl_to_sql/'s QueryPlan compiler in an MCP server so an external MCP client (Claude Desktop, another Claude Code session, any MCP-speaking agent) can query the NYC TLC mart data the same way /chat's numeric path does, without embedding a second implementation of schema resolution, compilation, or the SQL security guard.

## Scope

In scope: the QueryPlan compiler pipeline (nyc_schema.py / query_plan.py / query_plan_compiler.py / sql_agent.py / query_plan_agent.py), exposed as MCP primitives.

Out of scope (explicitly, YAGNI - documented boundaries, not silent gaps):
- No HTTP/SSE transport or remote deployment. stdio/local only, matching the already-configured dbt MCP server and ADR-008's zero-budget, no-speculative-infra discipline.
- No MCP tool for the RAG explanatory path (rag_pipeline.py's retrieval side). That is a separate future phase if wanted, not this one.
- No caching layer beyond what sql_agent.py/llm_client.py already do.
- No new auth/rate-limiting. stdio has no network surface to protect.
- No Prompts primitive. The pipeline has no templated multi-turn interaction pattern that would benefit from one; adding one here would be a primitive for its own sake, not for a need.
- No multi-server orchestration, no sampling (a server requesting a completion back from the client). This design exercises one server, two primitive types (Tools, Resources), nothing more.

## Package and transport

New top-level mcp_server/ package (no __init__.py - rag/ already runs as an implicit PEP 420 namespace package with zero __init__.py files under it; mcp_server/ follows the same convention and python -m mcp_server.server works the same way python -m already works against rag/nl_to_sql today). Uses the official mcp Python SDK's FastMCP, added to requirements.txt only (not requirements-backend.txt - this does not ship in the serving image, matching that file's existing "trimmed subset actually shipped" convention). stdio transport, spawned as a subprocess by an MCP client. No network, no auth.

Why stdio/local rather than a network transport: not ADR-008 (that ADR is about external paid-data adapters and free-tier constraints, not server transport - citing it here would be a stretch). The actual reasoning is simpler and specific to this design: this repo has zero deployed remote MCP servers today, the only existing precedent (the plugin-provided dbt MCP server) is stdio/local, and run_query executes arbitrary-shaped compiled SQL with no LLM in the loop between a caller's plan dict and DuckDB - shipping that over a network before the security review in this doc's own Security section has actually run would be a strictly worse decision than deferring transport choice until that review is done.

mcp_server/server.py imports from rag/ via a guarded sys.path.insert onto rag/ alone, then package-qualified nl_to_sql.<module> imports - the pattern already in production in backend/services/rag_service.py, not sql_agent.py's own self-referential double-insert (that pattern is internal to sql_agent.py's own bare-import needs, not the cross-package convention this repo actually uses elsewhere). No SQL string is built here and no schema is re-declared. This is a thin protocol adapter, not a second implementation of anything in rag/nl_to_sql/.

One limit to that "zero reimplementation" claim, flagged during architect review: it prevents *logic* drift (SQL construction, schema resolution, the security guard all stay single-sourced) but not *behavioral* drift between /chat and MCP. mcp_server/'s tools call sql_agent.generate_plan, query_plan_compiler.compile, and sql_agent._validate_sql directly - the individual primitives - not sql_agent.answer() itself, by design, since exposing the intermediate stages is the point. Any future check added inside answer() rather than in one of those shared primitives (a rate limit, per-request logging, a confidence gate) would apply to /chat but not silently propagate to MCP. This is not a defect to fix now - it is a property of exposing intermediate pipeline stages at all - but it means a future change to sql_agent.answer() needs a deliberate check against mcp_server/server.py, not an assumption that shared primitives cover it automatically.

## Primitives

Four primitives, giving the calling agent visibility into every pipeline stage instead of one opaque black box - the original motivation for splitting this into several primitives rather than one combined "ask a question" tool was to let an agent construct or inspect a plan itself before executing it.

1. describe_schema() - both a Tool and a Resource (schema://nyc-mobility). Returns {"schema": NYC_SCHEMA.describe()} - describe() returns a plain string (one "TABLE <name> (...)" block per backing table, blocks joined by blank lines), not a dict. No basis field - static metadata, not a result.
2. generate_plan(question: str, model: Literal["base", "finetuned"] = "base") - Tool only. Returns {"plan": {...}}. model="base" calls sql_agent.generate_plan (today's live /chat path). model="finetuned" replicates query_plan_agent.answer()'s exact RuntimeError guard (same two error strings) before calling query_plan_agent.generate_plan - the MCP layer adds no second guard, it reuses the existing one. No basis field.
3. compile_plan(plan: dict) - Tool only. Returns {"sql": "..."}. Pure query_plan_compiler.compile(), deterministic, no LLM, no DB hit. No basis field.
4. run_query(plan: dict) - Tool only. Returns {"basis": "computed", "source": "duckdb:nyc_rides", "sql": "...", "columns": [...], "rows": [...]}. Compiles, runs sql_agent._validate_sql (unchanged), executes read-only against DuckDB, returns real rows.

A caller can chain generate_plan then run_query for the equivalent of today's /chat numeric path, or inspect/edit the plan via compile_plan in between.

### Why describe_schema is both a Tool and a Resource

MCP's two data-facing primitives have different control models, confirmed by checking rather than assuming: Tools are model-controlled (Claude discovers and invokes them autonomously based on context), Resources are application-controlled (the client app decides when they are used - in Claude Desktop, a human clicking a "+" attach button, not the model reaching for it mid-conversation).

The original design reasoning for describe_schema ("giving the calling agent visibility into every pipeline stage") was written with autonomous agent chaining in mind - a model deciding on its own to check the schema before drafting a plan, as part of a chained generate_plan -> compile_plan -> run_query flow with no human in the loop for the inspection step. A Resource-only implementation would silently break that use case in Claude Desktop specifically, since only a human attaching it manually could reach it - the model could not. So describe_schema is exposed both ways: a Tool for the autonomous-chaining path, and a Resource (schema://nyc-mobility) for a human manually inspecting or attaching the schema before writing a plan by hand. This is a documented client-capability workaround, not redundancy for its own sake.

## Response contract - reusing ADR-007's basis field, narrowly

Only run_query() carries a basis field, and it is always "computed" on success. There is no modeled_estimate/unavailable case here - unlike the journey predictors ADR-007 was written for, this pipeline has nothing to fall back to. If generate_plan can't produce a resolvable plan, or compile_plan/run_query hits an unresolvable field, it raises ValueError, which the MCP SDK surfaces to the caller as a tool error - never a softened, partially-fabricated result.

describe_schema(), generate_plan(), and compile_plan() carry no basis field at all. This is a deliberate, corrected decision: an earlier draft of this design tagged generate_plan()'s and compile_plan()'s output "computed" too, which was wrong. basis in ADR-007 answers "is this value verified against real data," not "did this come from code instead of free text." generate_plan()'s output is an LLM-produced QueryPlan that has not yet been resolved against the schema - it can still fail the very next compile_plan() or run_query() call with a ValueError, so labeling it "computed" would claim a guarantee it does not have. compile_plan() only proves the plan is syntactically resolvable against the schema; it does not prove the query executes or returns real rows. Only run_query()'s output has actually touched real data and come back with real rows, so only run_query() gets to say "computed."

## Security

run_query calls the exact compile_plan() -> _validate_sql() -> read-only duckdb.connect() sequence sql_agent.answer() already uses (table allow-list, DDL/DML blocklist, single-statement check). The MCP server adds zero new SQL-construction code.

This is the first time an external, non-LLM-mediated caller can hand the compiler a plan dict directly, rather than going through generate_plan()'s LLM step. This is left as an open question for review, not pre-concluded here: mechanically, a hand-crafted plan gets identical treatment to an LLM-generated one, since query_plan_compiler.validate_plan() and sql_agent._validate_sql() do not know or care where a plan came from. But "identical treatment" only helps if that treatment was already proven against adversarial input, and it has not been - the existing guard has been exercised against adversarial SQL text (sql_agent.py's demo() bad_queries list) and exactly one known-bad plan shape (an unresolvable hour filter on zone_fare_stats), not systematically against adversarial plan shapes: boundary limit values (zero, negative, non-integer, very large), degenerate group_by/order combinations, or oversized filter structures.

Action: the security-engineer subagent reviews mcp_server/server.py against this specific question, pointed at query_plan_compiler.validate_plan()'s actual boundary checks (limit <= 0 or non-int or bool, unknown aggregation, unknown order, unresolvable group_by) as the concrete surface to probe - for example run_query({"intent": "metric_lookup", "metric": "fare", "limit": 999999999999}) or a group_by set to a non-existent canonical field. The review determines the answer; it is not assumed here.

**Resolved.** The review actively probed (not just read) SQL-injection-shaped filter strings, boundary/malformed limit values, unknown aggregation/order, cross-metric group_by confusion, and malformed plan shapes against the real functions. No injection or unauthorized execution was reproducible - filter escaping, the `;` single-statement check, and DuckDB's own read-only connection enforcement (confirmed directly: a `CREATE TABLE` against a `read_only=True` connection raises `InvalidInputException` from DuckDB itself, independent of `_validate_sql`) all held. One real gap: a missing required key or wrong-typed field (a non-dict plan, an unhashable group_by) raised KeyError/AttributeError/TypeError instead of ValueError - not exploitable (the MCP SDK wraps any exception into a bounded, non-leaking tool error) but a contract-accuracy gap. Fixed at the root in `QueryPlan.from_dict()` (rag/nl_to_sql/query_plan.py), the one place every untrusted-dict caller builds a plan, so sql_agent.py and query_plan_agent.py inherit the same hardening, not just this wrapper. Two findings accepted as-is (no upper bound on limit; an inverted date_range returns zero rows rather than erroring) - both low severity, neither a new blast-radius increase over existing behavior. Full findings recorded in specs/016-mcp-queryplan-server/spec.md's Risks section.

## Client config

.mcp.json at repo root (none existed before this change), following the same shape as the already-configured dbt MCP server:

```
{
  "mcpServers": {
    "nyc-mobility-queryplan": {
      "command": "python",
      "args": ["-m", "mcp_server.server"],
      "cwd": "${workspaceFolder}"
    }
  }
}
```

No env vars required for the default (model="base") path. USE_FINETUNED_QUERY_PLAN / QUERY_PLAN_FINETUNED_MODEL_ID stay optional, inherited from the shell environment exactly as query_plan_agent.py already reads them. No second config mechanism.

## Why this does not need a full architect round-trip before implementation

CLAUDE.md requires the architect subagent be consulted before any change crossing the Layer 0-5 dependency graph, naming "RAG reading raw tables" and "backend recomputing marts" as the anti-patterns that rule exists to catch. A short architect consult was run on this design doc before implementation began (finding recorded in specs/016-mcp-queryplan-server/spec.md's Risks section), which sharpened the framing below rather than confirming it as originally written.

mcp_server/ does not sit in the Layer 0-5 graph at all - that graph is about layers reading each other's *outputs* (marts, model artifacts, the RAG index), and mcp_server/ calls Layer 4's Python functions directly rather than reading a precomputed artifact. It is more precisely a second *ingress* into Layer 4, alongside backend/services/rag_service.py, not simply "a new consumer of Layer 4's interface" in the same sense rag_service.py is - rag_service.py is itself Layer 5 code calling into Layer 4 from behind FastAPI's request/response boundary. mcp_server/ is a second privileged caller of the same Layer 4 functions with no HTTP or auth boundary in front of it at all (stdio only). The practical conclusion is the same either way - no new write-back, no layer-skipping, no reimplementation of Layer 4's logic - but the two callers are not architecturally identical, and treating them as identical would understate what "no auth boundary" actually means here.

## Testing

Per this repo's correctness-testing bar: one tests/test_mcp_server.py using the standard demo()/assert self-check pattern already used across rag/ (not a pytest fixture suite). Covers:

- describe_schema() returns the same shape as NYC_SCHEMA.describe().
- compile_plan() on a known-good plan matches what query_plan_compiler.compile() itself produces for the equivalent QueryPlan.
- compile_plan() and run_query() on the same unresolvable-field plan sql_agent.demo() already uses (QueryPlan(intent="metric_lookup", metric="fare", filters=QueryFilters(hour=8))) raise ValueError, proving the MCP path inherits the guard rather than copying it.
- run_query() end-to-end against the real DuckDB file for one known question, asserting basis == "computed" and non-empty rows.
- generate_plan(model="finetuned") raises the same RuntimeError query_plan_agent.demo() already asserts when unconfigured.
- compile_plan() response contains no basis key (regression guard for the basis-narrowing correction above).

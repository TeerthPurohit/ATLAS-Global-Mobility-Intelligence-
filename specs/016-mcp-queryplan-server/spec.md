# SPEC-016: MCP QueryPlan Server

Owner: solo builder · Status: draft · Layer: 5+ (extends Layer 4) · Depends on: SPEC-014

## Business Goal

Expose the existing, already-live QueryPlan compiler pipeline
(`rag/nl_to_sql/`) to external MCP clients (Claude Desktop, another Claude
Code session, any MCP-speaking agent) so the same NYC TLC mart data `/chat`'s
numeric path already answers can be queried directly by an agent, without a
human going through the web chat UI. Non-goal: this does not add any new
question-answering capability — it's a new access surface over an existing
one. Full design reasoning lives in
`docs/superpowers/specs/2026-08-29-mcp-queryplan-server-design.md`.

## Functional Requirements

- FR-1: `describe_schema` is exposed as both an MCP Tool and an MCP Resource
  (`schema://nyc-mobility`), returning `NYC_SCHEMA.describe()`'s output
  unmodified.
- FR-2: `generate_plan(question, model)` compiles a natural-language
  question into a `QueryPlan` JSON object, without executing it. `model`
  selects between `sql_agent.generate_plan` (default, live `/chat` path)
  and `query_plan_agent.generate_plan` (fine-tuned, opt-in).
- FR-3: `compile_plan(plan)` deterministically compiles a `QueryPlan` dict
  to SQL via the existing `query_plan_compiler.compile()`, raising
  `ValueError` on any field the schema cannot resolve.
- FR-4: `run_query(plan)` compiles and executes a `QueryPlan` dict
  read-only against the DuckDB warehouse, reusing `sql_agent._validate_sql`
  unchanged, and returns real result rows.
- FR-5: Every `run_query` success response carries `basis: "computed"`
  (ADR-007's field, narrowly reused); no other primitive carries a `basis`
  field.
- FR-6: The fine-tuned model path (`model="finetuned"`) raises the same
  `RuntimeError`s `query_plan_agent.answer()` already raises when
  `USE_FINETUNED_QUERY_PLAN`/`QUERY_PLAN_FINETUNED_MODEL_ID` are unset —
  no new guard is introduced.

## Non-Functional Requirements

- Transport: stdio only, spawned as a local subprocess by an MCP client.
  No network exposure, no auth mechanism — intentional scope boundary, not
  a gap. Reasoning (not ADR-008, which is about external paid-data
  adapters and doesn't actually cover server transport): no remote MCP
  server exists anywhere in this repo today, the one precedent (the
  plugin-provided dbt MCP server) is stdio/local, and `run_query` executes
  arbitrary-shaped compiled SQL with no LLM in the loop — shipping that
  over a network ahead of the security review below would be strictly
  worse than deferring the transport decision until after it.
- Zero reimplementation: no SQL-construction, schema-resolution, or
  security-guard logic is duplicated from `rag/nl_to_sql/` — every
  primitive is a thin call into an existing, already-tested function.

## Current State

`rag/nl_to_sql/sql_agent.py` and `rag/nl_to_sql/query_plan_agent.py` both
already expose a `question -> QueryPlan -> compiled SQL -> executed
read-only result` pipeline (`answer()` in each), sharing
`nyc_schema.NYC_SCHEMA`, `query_plan.QueryPlan`, and
`query_plan_compiler.compile()`. `sql_agent.answer()` is what `/chat`'s
numeric path calls live today; `query_plan_agent.answer()` is gated behind
`USE_FINETUNED_QUERY_PLAN` (default off, no fine-tuned model configured in
this environment). No MCP server exists anywhere in this repo yet
(confirmed: no `mcp`/`fastmcp` dependency in `requirements.txt` or
`requirements-backend.txt`, no `.mcp.json` file anywhere in the repo). The
only MCP server currently configured for this project is the plugin-provided
`dbt` MCP server, which this design's `.mcp.json` entry follows the shape
of.

## Proposed Design

New top-level `mcp_server/` package (no `__init__.py`, matching `rag/`'s
existing implicit-namespace-package convention), `mcp_server/server.py`
built on the official `mcp` Python SDK's `FastMCP`. Imports from `rag/` via
a guarded single `sys.path.insert` onto `rag/` plus package-qualified
`nl_to_sql.<module>` imports — the pattern already in production in
`backend/services/rag_service.py`. Four primitives (`describe_schema`,
`generate_plan`, `compile_plan`, `run_query`) as detailed in the design
doc, including the rationale for `describe_schema`'s dual Tool+Resource
exposure (Tools are model-controlled/autonomous, Resources are
application-controlled/manually-attached — confirmed via research, not
assumed) and the `basis` field's narrowing to `run_query` only. Tradeoffs
considered and rejected: a single combined `ask_question` tool (rejected —
loses the ability for a calling agent to inspect/edit a plan before
executing it); tagging every primitive's output `basis: "computed"`
(rejected — misrepresents ADR-007's "verified against real data" contract
for artifacts that haven't been executed yet).

## API Design (MCP primitives)

See the design doc's "Primitives" section for exact signatures and return
shapes. Summary: `describe_schema() -> {schema: str}` (Tool + Resource);
`generate_plan(question: str, model: "base"|"finetuned" = "base") ->
{plan: dict}` (Tool); `compile_plan(plan: dict) -> {sql: str}` (Tool);
`run_query(plan: dict) -> {basis: "computed", source: str, sql: str,
columns: list[str], rows: list[dict]}` (Tool). All four raise on failure
(`ValueError` for unresolvable fields, `RuntimeError` for the unconfigured
fine-tuned path) rather than returning a softened/partial result.

## Testing

`tests/test_mcp_server.py`, mirroring `tests/test_sql_agent_query_plan.py`'s
`sys.path`/`skipif`-on-warehouse setup and `tests/test_gtfs_registry.py`'s
trailing `demo()`/`__main__` self-check block. Covers: `describe_schema`
matches `NYC_SCHEMA.describe()`; `compile_plan` matches the compiler's own
output for an equivalent plan; `compile_plan`/`run_query` both raise
`ValueError` on the same bad plan `sql_agent.demo()` uses; `run_query`
end-to-end asserts `basis == "computed"` and non-empty rows;
`generate_plan(model="finetuned")` raises `RuntimeError` when unconfigured;
`compile_plan`'s response carries no `basis` key (regression guard). No
live-LLM test for `generate_plan(model="base")` — no existing reference
test in this repo makes a real LLM call either, and `sql_agent.generate_plan`'s
own correctness is that module's test's responsibility, not this wrapper's.

## Risks

- **Hand-crafted adversarial plan shapes — reviewed, mostly closed.**
  `security-engineer` actively probed (not just read) `mcp_server.compile_plan`/
  `run_query` with SQL-injection-shaped filter strings, boundary/malformed
  `limit` values, unknown `aggregation`/`order`, cross-metric `group_by`
  confusion, and malformed plan shapes. Findings: no injection possible
  (`_sql_literal` escaping + `_validate_sql`'s `;` check + DuckDB's own
  `read_only=True` connection-level enforcement, confirmed independently by
  trying a `CREATE TABLE` against a read-only connection directly); no
  cross-metric field leakage; `limit=True`/`False` correctly rejected (bool
  checked before int). One real gap, now fixed: a missing required key or
  wrong-typed field (non-dict plan, unhashable `group_by`) raised
  `KeyError`/`AttributeError`/`TypeError` instead of `ValueError` — fixed at
  the root in `QueryPlan.from_dict()` (`rag/nl_to_sql/query_plan.py`), the
  one place every untrusted-dict caller builds a plan, so `sql_agent.py`
  and `query_plan_agent.py` get the same hardening, not just this wrapper.
  Two accepted-as-is, low severity: no upper bound on `limit` (no worse
  than the existing `limit=None`/unbounded case); an inverted `date_range`
  compiles to a query that just returns zero rows, not an error (a
  correctness nit, not a security finding under this repo's threat model).
  All 21 tests (`test_mcp_server.py` + the two existing `nl_to_sql` test
  files) pass after the fix.
- **Architect consult was scoped narrow, not skipped.** `mcp_server/`
  doesn't sit inside the Layer 0-5 graph (that graph is about layers
  reading each other's *outputs*); it's a second *ingress* into Layer 4,
  alongside `backend/services/rag_service.py`, but unlike that caller it
  has no HTTP/auth boundary in front of it (stdio only). No objection to
  proceeding — no new write-back, no layer-skipping, no reimplementation —
  but the two callers aren't architecturally identical, and the design doc
  now states that distinction explicitly rather than treating them as the
  same case.
- **Behavioral drift between `/chat` and MCP.** "Zero reimplementation"
  prevents *logic* drift (shared primitives) but not *behavioral* drift:
  `mcp_server/`'s tools call `sql_agent.generate_plan`/`query_plan_compiler.compile`/
  `sql_agent._validate_sql` directly, not `sql_agent.answer()` itself. A
  future guard added inside `answer()` (rate limit, logging, a confidence
  gate) won't automatically apply to MCP. Not a defect to fix now — a
  property of exposing intermediate stages at all — but any future change
  to `answer()` needs a deliberate check against `mcp_server/server.py`.
- **`mcp` SDK decorator behavior unverified until implementation.** Whether
  `@mcp.tool()` returns the original callable unmodified (needed for
  `tests/test_mcp_server.py` to call primitives directly) or wraps it needs
  confirming against the actually-installed package version, not assumed
  from documentation alone.

## Acceptance Criteria

- [x] `mcp_server/server.py` exists, exposes all four primitives, importable
      with `python -c "from mcp_server.server import mcp"` with no
      exception. (Verified: prints `nyc-mobility-queryplan`.)
- [x] `requirements.txt` has an `mcp` dependency; `requirements-backend.txt`
      is untouched.
- [x] `.mcp.json` exists at repo root with a working `nyc-mobility-queryplan`
      entry.
- [x] `tests/test_mcp_server.py` exists and passes — 7/7, real execution
      against the live warehouse (not a skip in this environment).
- [x] `security-engineer` review of the adversarial-plan-shape question has
      run, with findings either fixed (`QueryPlan.from_dict` hardening) or
      explicitly accepted as residual risk (unbounded `limit`, inverted
      `date_range`).
- [ ] This spec and the design doc are both committed. (Written, not yet
      committed to git — pending user confirmation, per this session's
      commit-only-when-asked discipline.)

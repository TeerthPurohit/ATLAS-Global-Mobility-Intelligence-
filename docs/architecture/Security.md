# Security

Scoped to what actually applies — this app has no user accounts, no
payments, no PII beyond what's already in the public TLC dataset (which
itself has no rider/driver identity, only zone-level location IDs).

## What's in scope

- **Secrets:** API keys (Gemini/embedding provider) live in `.env`, never
  committed. `.env.example` documents required vars with placeholder values
  only.
- **NL-to-SQL injection surface:** `rag/nl_to_sql/sql_agent.py` generates
  SQL from user text. The generated query must run against a read-only
  DuckDB connection scoped to mart tables only (never raw trip-level data,
  never write permissions) — this bounds the blast radius of a prompt
  injection or malformed generated query to "wrong read," never data loss.
- **Chat input:** no execution of arbitrary user-supplied code; the router
  only ever dispatches to the two fixed paths (NL-to-SQL, vector retrieval).
- **Dependency hygiene:** don't add packages casually (see `standards.md`);
  fewer dependencies is also less security surface.

## What's out of scope (and why)

- Authentication/authorization — no accounts exist to protect.
- Rate limiting — free-tier hosting caps this implicitly; add if abuse is
  actually observed, not preemptively.
- WAF/DDoS protection — outside a solo project's threat model and budget.

If any of these become relevant (e.g. the demo gets attention and starts
seeing abusive traffic), record the decision to add protection in a new ADR
rather than silently bolting it on.

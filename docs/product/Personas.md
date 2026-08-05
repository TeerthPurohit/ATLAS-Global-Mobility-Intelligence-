# Personas

This project has one real persona. Resist the urge to invent more — a
portfolio project doesn't have a multi-segment user base, and pretending
otherwise just produces fictional requirements nobody validates.

## The interviewer / hiring manager

- Skims the README and live demo for under 5 minutes on first pass.
- Cares about *why* decisions were made more than *what* was built — will
  ask "why DuckDB" or "why chronological split" and expects a real answer,
  not a memorized definition.
- Will click the chat panel and ask an adversarial question ("what's the
  average fare from JFK at 2am") specifically to check if the number is real
  or hallucinated.
- Will look at `docs/adr/` and `specs/` if the README signals they exist —
  this is the audience those documents are actually for.

## Secondary: future-you, three weeks or three months from now

- Opens `.claude/memory.md` to remember what's actually built vs planned,
  instead of re-reading every file.
- Needs `docs/adr/` to remember *why* a decision was made, not just that it
  was made — this is who "record the why" in
  [rules.md](../../.claude/rules.md) rule 4 is really for.

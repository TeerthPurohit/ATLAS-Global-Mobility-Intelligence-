# ADR-006: Full `.claude/` engineering-process scaffolding despite solo scope

**Status:** Accepted, with an explicit dissent recorded

## Context

This is a solo, ~12hrs/week portfolio project. Standard engineering process
(ADRs, specs, subagents with folder ownership, hooks, CI) exists to
coordinate multiple people and protect shared state — neither applies here.
The user explicitly requested the full enterprise-scale version of this
scaffolding (15 subagents, 20 slash commands, ~15 skills, hooks, specs per
layer) after being shown a leaner alternative.

## Decision

Build the full scaffolding as requested.

## Dissent, for the record

Before this was built, the assistant recommended a leaner alternative: one
`CLAUDE.md` (~200-300 lines), a spec template filled in per-layer as work
starts, and 1-2 ADRs for real decisions — on the grounds that 15 subagents
with folder ownership assume multiple committers that don't exist here, and
that building all of it up front risks the `.claude/` scaffolding becoming
the project instead of the NYC TLC platform itself. The user considered this
and chose the full version anyway.

## Why the full version isn't unreasonable

- It's genuine practice at working the way larger engineering orgs actually
  operate — a real, transferable skill, separate from whether this specific
  repo strictly needs it.
- The subagents/commands/skills are mechanical enough to generate once and
  rarely touch again — the ongoing cost is lower than the upfront cost
  suggests, provided they aren't allowed to drift from `.claude/rules.md`
  and `.claude/standards.md` over time.

## What to watch for

If, in practice, the `.claude/` scaffolding starts consuming more time than
it saves (edited more often than the actual `dbt_project/`, `algorithms/`,
`models/` code), that's the signal to prune it — see rule 7 in
`.claude/rules.md`. This ADR is the place to record that reversal if it
happens, not a silent deletion.

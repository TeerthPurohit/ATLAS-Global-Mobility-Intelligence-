# Vision

Show, in one repository, that NYC TLC trip data can be turned into a
platform that answers both "what number is it" (precise, SQL-grounded) and
"why is it that way" (explanatory, retrieval-grounded) — built with the
same layered rigor a data/ML engineering team would use, at the scale one
person can execute in 9 weeks.

The platform is not trying to out-forecast a production rideshare pricing
engine. It's trying to demonstrate, defensibly, that the person who built it
understands columnar analytics, classical algorithms, a real model
comparison methodology, and grounded LLM retrieval — not just "called
`.fit()` and shipped a demo."

## What "done" looks like

A live app where a visitor can click a zone on a map, see a demand/fare
prediction with the model that produced it, ask "why is this zone busy at
6pm" and get an answer grounded in real computed stats (not an LLM guess),
and read a comparison of 4 forecasting approaches with honest tradeoffs.

## What this project deliberately does not try to be

- Not a production rideshare system (no real-time ingestion, no live pricing).
- Not a research contribution (algorithms are implemented from scratch for
  understanding, not novelty).
- Not a demonstration of "AI does everything" — see
  [PRD.md](PRD.md) and [../../.claude/rules.md](../../.claude/rules.md) rule 1.

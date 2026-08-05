# Success Metrics

Portfolio project metrics are different from product metrics — there's no
DAU. These are the bars that make the project defensible.

## Engineering quality (primary)

- Every from-scratch algorithm (KD-tree, PageRank, Dijkstra, EWMA) has a
  passing test comparing it against a reference library implementation on
  identical input.
- `dbt test` passes clean with `not_null`, `accepted_range`, and
  relationship tests on every mart.
- The 4-model demand comparison uses one shared chronological test set —
  verifiable by inspecting `models/data_prep/train_test_split.py`.
- Zero fabricated numbers anywhere in `docs/`, RAG insight text, or the
  frontend — every displayed metric traces to a script or query.

## Demo quality (secondary)

- Live URL loads and answers both UC-3 (numeric) and UC-4 (explanatory)
  question types correctly, per `docs/product/Use-Cases.md`.
- Model comparison chart renders real (not placeholder) RMSE/MAE numbers.

## Explicitly not measured

- Uptime/SLA (free-tier hosting, acceptable to go cold — note this in the
  README per the plan's "record a demo video as backup" step).
- Real-world forecast accuracy against ground-truth future demand — the
  dataset is historical, not live.

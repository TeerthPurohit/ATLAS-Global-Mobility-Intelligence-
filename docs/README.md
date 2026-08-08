# Documentation

| Section | Covers |
|---|---|
| [`getting-started/`](getting-started/) | Local dev setup, running tests |
| [`architecture/`](architecture/) | System design, data flow, infrastructure, security |
| [`data/`](data/) | Source data, dbt layering, registries, seeds |
| [`algorithms/`](algorithms/) | From-scratch KD-tree/PageRank/Dijkstra/EWMA, each validated against a reference library |
| [`models/`](models/) | Demand ladder, fare model, journey predictors, model registry |
| [`api/`](api/) | Full live route reference, error taxonomy |
| [`deployment/`](deployment/) | Docker, precompute discipline, target host |
| [`operations/`](operations/) | Health checks, structured logging, known gaps |
| [`changelog/`](changelog/) | Dated history of what was built, mirrors `.claude/memory.md` |
| [`adr/`](adr/) | Architecture Decision Records -- the *why* behind non-obvious choices |
| [`product/`](product/) | PRD, personas, roadmap, success metrics, use cases, vision |

Every page here describes what's actually implemented -- "not yet measured"
or an explicit "out of scope this phase" stands in for anything aspirational
(rule 2, `.claude/rules.md`).

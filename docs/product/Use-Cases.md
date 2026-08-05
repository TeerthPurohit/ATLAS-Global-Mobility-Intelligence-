# Use Cases

Concrete interactions the live demo must support, used to derive
`specs/009-backend-api` and `specs/010-frontend` acceptance criteria.

## UC-1: Explore demand by zone and hour

Visitor opens the map, clicks a zone, sees predicted pickup demand by hour
with the model that produced it. Source: `GET /predict/demand`.

## UC-2: Compare forecasting models

Visitor opens the model comparison chart, sees RMSE/MAE/latency for linear,
EWMA, XGBoost, LSTM on the same chronological test set, with a one-sentence
note on what each model captures. Source: `models/evaluation/metrics_report.md`
via a backend endpoint.

## UC-3: Ask a numeric question

"What's the average fare from Zone 161 to JFK around 6pm?" →
`query_classifier.py` routes to `nl_to_sql/sql_agent.py` → generates SQL
against DuckDB marts → executes → returns number + the SQL query shown for
transparency.

## UC-4: Ask an explanatory question

"Why does Zone 161 get busy at rush hour?" → routed to vector retrieval over
`rag/insight_generation` docs → answer grounded in the retrieved insight
paragraph, which itself is grounded in real computed stats (never invented).

## UC-5: Sanity-check the algorithms layer (interview-only use case)

Visitor (interviewer) reads `algorithms/graph/pagerank_hubs.py` and the test
that validates it against `networkx.pagerank` on the same graph — this use
case has no UI, it's read directly from the repo.

## Acceptance bar for all use cases

Every displayed number must be traceable to a script, dbt model, or SQL
query — no exceptions. See rule 2 in
[../../.claude/rules.md](../../.claude/rules.md).

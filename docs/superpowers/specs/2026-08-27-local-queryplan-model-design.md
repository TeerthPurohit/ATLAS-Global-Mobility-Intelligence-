# Local Fine-Tuned QueryPlan Model — Design

**Status:** Approved (brainstorming), pending implementation plan.
**Completes:** spec-014 FR-7 (fine-tuning step), which `query_plan_agent.py`
already has the disabled mechanism for (`USE_FINETUNED_QUERY_PLAN`,
`QUERY_PLAN_FINETUNED_MODEL_ID`).

## Problem

The NL-to-SQL QueryPlan generator currently only calls hosted APIs
(`rag/llm_client.py`: DeepSeek primary, OpenAI fallback). There is no local,
self-hosted model in the loop, and no fine-tuned model has ever actually
been trained — spec-014 FR-7's mechanism exists but is dormant. Goal: train,
quantize, and live-host a small fine-tuned model for QueryPlan generation,
demonstrating real fine-tuning/quantization/distillation work rather than
claiming it without evidence, while keeping the existing hosted-API path as
a safety net.

Constraint that shaped this design: the user cannot keep a personal laptop
running 24/7, so "local model" here means a self-hosted, always-on VM the
user owns — not literally the user's own machine.

## Architecture & data flow

```
User question → backend (AWS Fargate) → rag/llm_client.py::chat_completion()
                                                  │
                                  1. Local model (Oracle VM, primary) ──┐
                                                  │ fails/timeout        │
                                  2. DeepSeek (existing fallback) ───────┤
                                                  │ fails                │
                                  3. OpenAI (existing fallback) ─────────┘
                                                  │
                                    QueryPlan JSON → compile_plan() → SQL → DuckDB
```

`chat_completion()` gains one new tier at the top of its existing
DeepSeek→OpenAI chain — same try/except shape, one more `base_url` override,
tried first. No other call site changes; `sql_agent.py`/`rag_pipeline.py`
already just call `chat_completion(model=..., messages=...)`.

Rollout stays gated behind the existing `USE_FINETUNED_QUERY_PLAN` /
`QUERY_PLAN_FINETUNED_MODEL_ID` env vars in `query_plan_agent.py` — flipped
on only after the eval numbers below are in hand, not before.

## Fine-tuning & quantization pipeline

1. **Base model:** Qwen2.5-3B-Instruct (Apache 2.0; strong structured-output
   following for its size; well-supported GGUF conversion path).
2. **Training data:** `rag/nl_to_sql/training_data_gen.py`'s existing
   output (227 train / 13 NYC-holdout / 63 unseen-schema-eval rows,
   correct-by-construction — every label compiles against its own schema,
   never LLM-generated) reformatted from OpenAI-chat-JSONL into whatever
   the fine-tuning framework consumes.
3. **Distillation step (data augmentation):** use DeepSeek/OpenAI to
   generate diverse paraphrases of the same 227 training questions. Labels
   stay fixed — paraphrasing the question never changes the correct
   QueryPlan — so this expands phrasing diversity for free-label training
   data without touching the correct-by-construction guarantee. This
   directly addresses the template-generated dataset's real gap: narrow
   phrasing diversity.
4. **Fine-tune:** LoRA via Unsloth, run on a free Colab T4 GPU (same
   free-GPU path already used for LSTM retraining in this project).
5. **Quantize:** merge the LoRA adapter into base weights, convert to GGUF,
   quantize to Q4_K_M (accuracy/size/speed balance for ARM CPU inference)
   via `llama.cpp`'s conversion tooling.
6. **Evaluate honestly:** score the quantized model against
   `eval_nyc_holdout.jsonl` and `eval_unseen_schema.jsonl` (both already
   exist). Results feed into Phase 2's RAG eval harness (`eval_report.md`)
   as one more row alongside the existing DeepSeek/OpenAI zero-shot
   baseline and the router confusion matrix — not a separate one-off
   script.

## VM provisioning & serving

- **VM:** Oracle Cloud Always-Free Ampere A1 (4 OCPU / 24GB RAM, ARM,
  genuinely free indefinitely — not a trial). No GPU needed; Q4_K_M on
  `llama.cpp` runs well on ARM NEON at 3B scale.
- **Serving:** `llama.cpp`'s `llama-server` binary directly (not Ollama) —
  it natively exposes the same OpenAI-compatible `/v1/chat/completions`
  shape `llm_client.py` already expects, is the most mature ARM CPU
  inference path available, and avoids an extra abstraction layer this
  project doesn't otherwise need.
- **Always-on across reboots:** a systemd unit (`llama-server.service`,
  `Restart=always`) — not a manually-started process.

## Security

- **API key is the real control.** `llama-server --api-key <token>`,
  checked against a bearer token `llm_client.py` sends. Locally this comes
  from `.env`, the same way `DEEPSEEK_API_KEY`/`OPENAI_API_KEY` already do
  today; once the AWS Fargate backend deployment (Phase 5, not yet built)
  lands, it moves into that task definition's secrets the same way the
  other two keys will need to.
- **No IP allowlist.** AWS Fargate tasks don't get a static outbound IP
  without a NAT Gateway + Elastic IP, which is paid, always-on infra this
  repo's `Infrastructure.md` explicitly avoids for everything else. An
  IP-based lock isn't reliably enforceable without that cost, so the
  design doesn't depend on it — the Oracle Security List is still scoped
  to the serving port only, but source IP isn't part of the access-control
  story.
- **No TLS.** Payload is question text + QueryPlan JSON, not credentials;
  the bearer token is the actual gate. Accepted risk, not an oversight —
  revisit if that stops being true (e.g. if the payload ever carries
  anything sensitive).

## Evaluation & rollout safety

- One honest comparison table in `eval_report.md`: DeepSeek zero-shot vs.
  OpenAI zero-shot vs. local fine-tuned, scored on the same held-out sets.
- If the local model's accuracy is meaningfully worse, the honest move
  (matching this repo's "no fabricated metrics" rule) is documenting that
  and leaving `USE_FINETUNED_QUERY_PLAN` off, not forcing it to primary
  regardless of the numbers.
- If the VM goes down, the existing DeepSeek→OpenAI fallback in
  `chat_completion()` already handles it — no new single point of failure
  for the "primary, with cloud fallback" traffic pattern chosen here.

## Out of scope

- TLS/domain setup (explicitly declined in favor of the API-key-only
  approach above).
- IP allowlisting (blocked by Fargate's non-static egress IP without paid
  NAT infra).
- Serving any model other than the QueryPlan generator from this VM —
  this design is scoped to that one task, not a general-purpose local LLM
  gateway.
- Ollama or any serving stack other than `llama.cpp`'s `llama-server`.

## Open questions for the implementation plan

- Exact systemd unit file, Oracle Security List rule syntax, and the
  Unsloth/Colab notebook steps are implementation detail, not design —
  left for `writing-plans`.
- Where the paraphrase-augmentation script lives (likely
  `rag/nl_to_sql/training_data_gen.py` gains a new function, or a sibling
  script) — implementation detail.

## Results (2026-08-27)

Full pipeline built and run for real: LoRA fine-tune (Qwen2.5-3B-Instruct,
rank 16/alpha 32, 3 epochs, 908 rows, real Colab T4 run — `final_train_loss`
0.1821), merged, quantized to Q4_K_M (1.83GB), deployed on a live Oracle
Always-Free VM, verified reachable and reboot-durable. Real comparison
against the hosted DeepSeek/OpenAI zero-shot path
(`models/query_plan_finetune/comparison_results.json`, scored via
`evaluate.py::score_plan()`, same definition as the ADR-010 baseline):

| Tier | NYC holdout (n=13) | Unseen schema (n=63) |
|---|---|---|
| Local (this fine-tune) | **7.7%** | **50.8%** |
| Hosted (DeepSeek/OpenAI) | 76.9% | 63.5% |

**Honest read: the local model is not ready to replace the hosted path.**
The gap is large enough on NYC holdout specifically that this is not a
"close enough, ship it" result.

**But the raw percentage understates what the model actually learned.**
Manually inspecting all 13 NYC-holdout failures against
`evaluate.py::score_plan()`'s exact-match `intent` field found:

- 3/13: the model wrote `"metric lookup"` (a space) instead of the trained
  enum string `"metric_lookup"` (an underscore) — the correct field
  otherwise, scored as a hard miss by exact-match on principle (this
  eval's whole point is to test exact structural correctness, not to
  guess at intent), but not a comprehension failure.
- 5/13: the model wrote the bare string `"metric"` — not a valid enum
  value at all, a genuine and systematic malformation, always on the
  same `metric_lookup` value.
- 1/13: `top_n` instead of `area_ranking` — a real category confusion
  between two genuinely adjacent intents ("which area has the highest
  X" reads ambiguously between "rank areas, take the top" and "rank
  areas by X").
- 2/13: generation produced text that failed to parse as valid JSON at
  all — an outright miss, not scoreable as "close."
- 2/13: exact match.

So **8 of the 11 misses are one narrow, specific failure mode** — unreliable
exact spelling of the `metric_lookup` enum string — not broad task
misunderstanding. This is consistent with a small (LoRA rank 16), heavily
quantized (Q4_K_M, ~4 bits/weight) 3B model losing precision on one
compound token sequence, not with the fine-tune having failed to learn the
QueryPlan task in general.

**Rollout decision: `USE_FINETUNED_QUERY_PLAN` stays off.** Per the plan's
own Global Constraint (no forcing a weaker tier to primary regardless of
what's measured), these numbers don't clear the bar. Real, honest,
unglamorous result — not a fabricated pass.

**If revisited later**, the two cheapest next experiments implied by this
diagnosis: (1) train more steps/higher rank specifically to nail the
`metric_lookup` string (the training data already has it right, so this is
a capacity/dosage question, not a data-quality one), or (2) evaluate the
unquantized merged model directly (skip Q4_K_M for evaluation purposes
only) to isolate whether quantization is the primary cause of the
spelling failures — the `unseen_schema` split's smaller local-vs-hosted
gap (50.8% vs 63.5%, far closer than NYC holdout's 7.7% vs 76.9%) is
itself a clue worth investigating: it suggests the model's degradation is
NYC-domain-specific in some way, not a uniform quantization tax across
every split.

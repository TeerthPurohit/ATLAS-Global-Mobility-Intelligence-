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

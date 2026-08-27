# Local Fine-Tuned QueryPlan Model Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fine-tune a small local model to generate QueryPlan JSON, quantize it, host it always-on on a free Oracle Cloud VM, and wire it into `rag/llm_client.py` as the primary generator ahead of the existing DeepSeek→OpenAI fallback — completing spec-014 FR-7.

**Architecture:** Qwen2.5-3B-Instruct, LoRA fine-tuned on `training_data_gen.py`'s 227 examples plus an LLM-paraphrased expansion, quantized to GGUF Q4_K_M, served by `llama.cpp`'s `llama-server` (OpenAI-compatible, grammar-constrained JSON output) on an Oracle Always-Free ARM VM behind an API key, called first by `chat_completion()` before DeepSeek/OpenAI.

**Tech Stack:** Python (Unsloth, peft, transformers) for fine-tuning; `llama.cpp` for quantization + serving; existing `rag/nl_to_sql/*` and `rag/llm_client.py` for integration; existing `pytest` conventions for tests.

## Global Constraints

- **No fabricated metrics** (rules.md) — the local-vs-DeepSeek-vs-OpenAI comparison table must come from an actual eval run against `eval_nyc_holdout.jsonl`/`eval_unseen_schema.jsonl`, never estimated.
- **Rollout stays gated** behind the existing `USE_FINETUNED_QUERY_PLAN`/`QUERY_PLAN_FINETUNED_MODEL_ID` env vars in `query_plan_agent.py` — flipped on only after Task 6's eval numbers are in hand.
- **Reuse existing patterns, don't invent new ones:** `chat_completion()`'s try/except-fallback shape (Task 5), `training_data_gen.py`'s correct-by-construction label philosophy (Task 1 never touches labels, only questions), `compare_models.py`'s standalone-comparison-script precedent (Task 6).
- **Security, as designed:** API key is the only access control (no TLS, no IP allowlist — see design doc's Security section for why). Never commit the API key itself; it lives in `.env` locally and Fargate task secrets once deployed, same as `DEEPSEEK_API_KEY`/`OPENAI_API_KEY`.
- **Honest about what's automatable:** Colab GPU fine-tuning and Oracle Cloud console provisioning are real interactive steps this plan cannot run for you — those steps are written as exact runbooks, not code, and are called out explicitly as manual.

---

## Task 1: Paraphrase-augmentation script (distillation data expansion)

**Files:**
- Create: `rag/nl_to_sql/augment_training_data.py`
- Test: `tests/test_augment_training_data.py`

**Interfaces:**
- Consumes: `training_data_gen.py::build_splits()` → `dict[str, list[dict]]` (existing, `training.jsonl`/`eval_*.jsonl` row shape: `{"messages": [{"role": "system", ...}, {"role": "user", "content": question}, {"role": "assistant", "content": QueryPlan.to_json()}]}`)
- Produces: `augment_training_data.py::augment_split(rows: list[dict], n_paraphrases: int = 3) -> list[dict]` — same row shape, `len(output) == len(rows) * (1 + n_paraphrases)` (original + N paraphrases per row), every row's `assistant` content byte-identical to its source row's (only `user` content changes)

- [ ] **Step 1: Write the failing test**

```python
# tests/test_augment_training_data.py
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "rag" / "nl_to_sql"))

from augment_training_data import augment_split  # noqa: E402


def test_augment_split_preserves_labels_and_expands_count(monkeypatch):
    import augment_training_data as mod

    calls = []

    def fake_paraphrase(question: str, n: int) -> list[str]:
        calls.append((question, n))
        return [f"{question} (paraphrase {i})" for i in range(n)]

    monkeypatch.setattr(mod, "_generate_paraphrases", fake_paraphrase)

    rows = [
        {"messages": [
            {"role": "system", "content": "TABLE t (col -- demand: x [numeric])"},
            {"role": "user", "content": "What is the total demand?"},
            {"role": "assistant", "content": '{"intent": "metric_lookup", "metric": "demand"}'},
        ]},
    ]

    out = augment_split(rows, n_paraphrases=3)

    assert len(out) == 4  # 1 original + 3 paraphrases
    assert out[0] == rows[0]  # original row unchanged, first
    for row in out[1:]:
        assert row["messages"][0]["content"] == rows[0]["messages"][0]["content"]  # system unchanged
        assert row["messages"][2]["content"] == rows[0]["messages"][2]["content"]  # label unchanged
        assert row["messages"][1]["content"] != rows[0]["messages"][1]["content"]  # question is a paraphrase
    assert calls == [("What is the total demand?", 3)]


def test_augment_split_zero_paraphrases_is_identity():
    rows = [{"messages": [{"role": "user", "content": "x"}]}]
    assert augment_split(rows, n_paraphrases=0) == rows
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_augment_training_data.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'augment_training_data'`

- [ ] **Step 3: Write minimal implementation**

```python
# rag/nl_to_sql/augment_training_data.py
"""Paraphrase-based training data augmentation for the QueryPlan fine-tune
(distillation data expansion). Expands training_data_gen.py's 227
template-generated questions with LLM-paraphrased variants of the SAME
question -- labels are never touched, since paraphrasing a question never
changes its correct QueryPlan. This is the fix for the template dataset's
real gap: narrow phrasing diversity, not label correctness (which
training_data_gen.py already guarantees by construction).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from llm_client import chat_completion  # noqa: E402
from training_data_gen import DATA_DIR, build_splits  # noqa: E402

PARAPHRASE_MODEL = "gpt-5.4-nano"


def _generate_paraphrases(question: str, n: int) -> list[str]:
    """Real LLM call -- reuses the same DeepSeek-primary/OpenAI-fallback
    chat_completion() every other LLM use in this repo goes through."""
    resp = chat_completion(
        model=PARAPHRASE_MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    f"Rewrite the user's question {n} different ways, preserving its exact "
                    "meaning (same intent, metric, filters). One rewrite per line, no numbering, "
                    "no extra commentary."
                ),
            },
            {"role": "user", "content": question},
        ],
        max_completion_tokens=300,
    )
    text = (resp.choices[0].message.content or "").strip()
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return lines[:n]


def augment_split(rows: list[dict], n_paraphrases: int = 3) -> list[dict]:
    if n_paraphrases <= 0:
        return list(rows)
    out: list[dict] = []
    for row in rows:
        out.append(row)
        question = row["messages"][1]["content"]
        for paraphrase in _generate_paraphrases(question, n_paraphrases):
            augmented = json.loads(json.dumps(row))  # deep copy
            augmented["messages"][1]["content"] = paraphrase
            out.append(augmented)
    return out


def write_augmented_splits(n_paraphrases: int = 3, out_dir: Path = DATA_DIR) -> dict[str, int]:
    """Only augments train.jsonl -- eval splits must stay exactly as
    generated (unparaphrased) so evaluation measures generalization to
    real phrasing, not memorized paraphrase style."""
    splits = build_splits()
    augmented_train = augment_split(splits["train.jsonl"], n_paraphrases)
    out_dir.mkdir(parents=True, exist_ok=True)
    with (out_dir / "train_augmented.jsonl").open("w", encoding="utf-8") as f:
        for row in augmented_train:
            f.write(json.dumps(row) + "\n")
    for filename in ("eval_nyc_holdout.jsonl", "eval_unseen_schema.jsonl"):
        with (out_dir / filename).open("w", encoding="utf-8") as f:
            for row in splits[filename]:
                f.write(json.dumps(row) + "\n")
    return {"train_augmented.jsonl": len(augmented_train), **{k: len(splits[k]) for k in splits if k != "train.jsonl"}}


def demo() -> None:
    counts = write_augmented_splits()
    print(f"wrote {counts}")


if __name__ == "__main__":
    demo()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_augment_training_data.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add rag/nl_to_sql/augment_training_data.py tests/test_augment_training_data.py
git commit -m "feat: add LLM-paraphrase augmentation for QueryPlan training data"
```

---

## Task 2: LoRA fine-tune on Colab (script + manual GPU run)

**Files:**
- Create: `models/query_plan_finetune/train_lora.py`
- Create: `models/query_plan_finetune/README.md`

**Interfaces:**
- Consumes: `models/query_plan_finetune/data/train_augmented.jsonl` (Task 1's output, OpenAI chat-format JSONL)
- Produces: `models/query_plan_finetune/adapter/` (LoRA adapter weights + tokenizer config, standard peft/HF format) and `models/query_plan_finetune/adapter/training_metadata.json` (base model, LoRA rank/alpha, epochs, final train loss, dataset size, per `.claude/skills/model-comparison`'s reproducibility bar)

- [ ] **Step 1: Write the training script**

```python
# models/query_plan_finetune/train_lora.py
"""LoRA fine-tune of Qwen2.5-3B-Instruct on the QueryPlan generation task
(spec-014 FR-7). Runs on a Colab T4 GPU by default; --smoke-test runs 1
step on 5 examples for a fast, GPU-optional pipeline sanity check (no real
model quality claim -- see model-comparison skill's reproducibility bar,
satisfied by Task 6's real eval, not this script's own loss number).
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

BASE_MODEL = "Qwen/Qwen2.5-3B-Instruct"
DATA_DIR = Path(__file__).resolve().parent / "data"
ADAPTER_DIR = Path(__file__).resolve().parent / "adapter"
SEED = 42
LORA_RANK = 16
LORA_ALPHA = 32
EPOCHS = 3
LR = 2e-4


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def train(smoke_test: bool = False) -> dict:
    from unsloth import FastLanguageModel
    from trl import SFTTrainer, SFTConfig

    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=BASE_MODEL, max_seq_length=1024, load_in_4bit=True,
    )
    model = FastLanguageModel.get_peft_model(
        model, r=LORA_RANK, lora_alpha=LORA_ALPHA,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj"], random_state=SEED,
    )

    train_rows = load_jsonl(DATA_DIR / "train_augmented.jsonl")
    if smoke_test:
        train_rows = train_rows[:5]
    dataset = [{"text": tokenizer.apply_chat_template(r["messages"], tokenize=False)} for r in train_rows]

    trainer = SFTTrainer(
        model=model, tokenizer=tokenizer, train_dataset=dataset,
        args=SFTConfig(
            per_device_train_batch_size=4, num_train_epochs=1 if smoke_test else EPOCHS,
            max_steps=1 if smoke_test else -1, learning_rate=LR, seed=SEED,
            output_dir=str(ADAPTER_DIR / "_trainer_tmp"), report_to="none",
        ),
    )
    start = time.time()
    result = trainer.train()
    elapsed = time.time() - start

    ADAPTER_DIR.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(str(ADAPTER_DIR))
    tokenizer.save_pretrained(str(ADAPTER_DIR))

    metadata = {
        "base_model": BASE_MODEL, "seed": SEED, "lora_rank": LORA_RANK, "lora_alpha": LORA_ALPHA,
        "epochs": 1 if smoke_test else EPOCHS, "learning_rate": LR, "n_train_rows": len(train_rows),
        "final_train_loss": result.training_loss, "elapsed_seconds": elapsed, "smoke_test": smoke_test,
    }
    (ADAPTER_DIR / "training_metadata.json").write_text(json.dumps(metadata, indent=2))
    return metadata


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--smoke-test", action="store_true", help="1 step on 5 rows, no GPU quality claim")
    args = parser.parse_args()
    meta = train(smoke_test=args.smoke_test)
    print(f"done: train_loss={meta['final_train_loss']:.4f} elapsed={meta['elapsed_seconds']:.1f}s")
```

- [ ] **Step 2: Write the runbook** (`models/query_plan_finetune/README.md`) — the real GPU run is manual, not automatable from this repo:

```markdown
# QueryPlan LoRA fine-tune

## Real run (Colab, free T4 GPU)

1. Open a new Colab notebook, Runtime → Change runtime type → T4 GPU.
2. `!pip install unsloth trl peft transformers accelerate bitsandbytes`
3. Upload `models/query_plan_finetune/train_lora.py` and
   `models/query_plan_finetune/data/train_augmented.jsonl` (from Task 1) to
   the Colab session (or clone the repo with a fine-grained GitHub token).
4. `!python train_lora.py`
5. Download `models/query_plan_finetune/adapter/` back into this repo at
   the same path (zip it in Colab, download, unzip locally).
6. Commit `adapter/training_metadata.json` (the training loss/config
   record) — NOT the adapter weights themselves (binary, large; add
   `models/query_plan_finetune/adapter/*.safetensors` to `.gitignore` if
   not already covered by an existing binary-artifact rule).

## Local smoke test (no GPU needed, run before trusting the Colab run)

    python models/query_plan_finetune/train_lora.py --smoke-test

Confirms the tokenizer/chat-template/trainer wiring is correct end-to-end
on CPU in under a minute, before spending Colab GPU time on the real run.
```

- [ ] **Step 3: Run the smoke test locally**

Run: `python models/query_plan_finetune/train_lora.py --smoke-test`
Expected: completes without error, prints a `train_loss=...` line, writes `models/query_plan_finetune/adapter/training_metadata.json` with `"smoke_test": true`

- [ ] **Step 4: Run the real fine-tune on Colab** (manual, per the README above)

Expected: `training_metadata.json` with `"smoke_test": false`, a real `final_train_loss`, adapter weights present in `models/query_plan_finetune/adapter/`

- [ ] **Step 5: Commit**

```bash
git add models/query_plan_finetune/train_lora.py models/query_plan_finetune/README.md models/query_plan_finetune/adapter/training_metadata.json
git commit -m "feat: add QueryPlan LoRA fine-tuning script and Colab runbook"
```

---

## Task 3: Merge + quantize to GGUF

**Files:**
- Create: `models/query_plan_finetune/quantize.sh`
- Test: manual verification step (no pytest — output is a binary artifact, not testable via assertions on Python objects)

**Interfaces:**
- Consumes: `models/query_plan_finetune/adapter/` (Task 2's output) + `BASE_MODEL` (Qwen2.5-3B-Instruct, downloaded fresh)
- Produces: `models/query_plan_finetune/gguf/queryplan-q4_k_m.gguf`

- [ ] **Step 1: Write the merge + convert + quantize script**

```bash
#!/usr/bin/env bash
# models/query_plan_finetune/quantize.sh
# Merges the LoRA adapter into base weights, converts to GGUF, quantizes
# to Q4_K_M. Requires a local clone of llama.cpp with llama-quantize built
# (https://github.com/ggml-org/llama.cpp -- see its README for build steps,
# out of scope here since it's a one-time toolchain setup, not project code).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ADAPTER_DIR="$SCRIPT_DIR/adapter"
MERGED_DIR="$SCRIPT_DIR/merged"
GGUF_DIR="$SCRIPT_DIR/gguf"
LLAMA_CPP_DIR="${LLAMA_CPP_DIR:?set LLAMA_CPP_DIR to your llama.cpp checkout}"

mkdir -p "$MERGED_DIR" "$GGUF_DIR"

python "$SCRIPT_DIR/merge_lora.py" --adapter "$ADAPTER_DIR" --out "$MERGED_DIR"

python "$LLAMA_CPP_DIR/convert_hf_to_gguf.py" \
  --outfile "$GGUF_DIR/queryplan-f16.gguf" \
  --outtype f16 \
  "$MERGED_DIR"

"$LLAMA_CPP_DIR/build/bin/llama-quantize" \
  "$GGUF_DIR/queryplan-f16.gguf" \
  "$GGUF_DIR/queryplan-q4_k_m.gguf" \
  Q4_K_M

echo "done: $GGUF_DIR/queryplan-q4_k_m.gguf"
```

- [ ] **Step 2: Write the LoRA-merge helper it calls**

```python
# models/query_plan_finetune/merge_lora.py
"""Merges a LoRA adapter into its base model's weights, full-precision, so
convert_hf_to_gguf.py has a single normal HF model directory to read --
llama.cpp's converter doesn't understand a base+adapter pair."""
from __future__ import annotations

import argparse
from pathlib import Path

from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer

BASE_MODEL = "Qwen/Qwen2.5-3B-Instruct"


def merge(adapter_dir: Path, out_dir: Path) -> None:
    base = AutoModelForCausalLM.from_pretrained(BASE_MODEL)
    merged = PeftModel.from_pretrained(base, str(adapter_dir)).merge_and_unload()
    tokenizer = AutoTokenizer.from_pretrained(str(adapter_dir))
    out_dir.mkdir(parents=True, exist_ok=True)
    merged.save_pretrained(str(out_dir))
    tokenizer.save_pretrained(str(out_dir))
    print(f"merged model written to {out_dir}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--adapter", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    merge(args.adapter, args.out)
```

- [ ] **Step 3: Run it** (needs a built `llama.cpp` checkout — one-time toolchain setup, documented in llama.cpp's own README, not project code)

Run: `LLAMA_CPP_DIR=/path/to/llama.cpp bash models/query_plan_finetune/quantize.sh`
Expected: `models/query_plan_finetune/gguf/queryplan-q4_k_m.gguf` exists, roughly 1.8-2.2GB for a 3B model at Q4_K_M

- [ ] **Step 4: Verify the GGUF loads and produces valid JSON**

Run:
```bash
"$LLAMA_CPP_DIR/build/bin/llama-cli" -m models/query_plan_finetune/gguf/queryplan-q4_k_m.gguf \
  -p "What is the total trip demand?" -n 100
```
Expected: model loads without error and produces output resembling QueryPlan JSON (exact accuracy is Task 6's job, not this step's — this step only confirms the artifact is a loadable, working GGUF file)

- [ ] **Step 5: Commit**

```bash
git add models/query_plan_finetune/quantize.sh models/query_plan_finetune/merge_lora.py
git commit -m "feat: add LoRA-merge and GGUF quantization scripts for QueryPlan model"
```
(The `.gguf` file itself is a multi-GB binary artifact — do not commit it; add `models/query_plan_finetune/gguf/*.gguf` and `models/query_plan_finetune/merged/` to `.gitignore` if not already covered.)

---

## Task 4: Oracle VM provisioning + always-on serving

**Files:**
- Create: `infra/local-model-vm/setup.sh`
- Create: `infra/local-model-vm/llama-server.service`
- Create: `infra/local-model-vm/README.md`

**Interfaces:**
- Consumes: `models/query_plan_finetune/gguf/queryplan-q4_k_m.gguf` (Task 3's output, copied to the VM manually — Oracle console access is not automatable from this repo)
- Produces: a running `llama-server` on the VM, reachable at `http://<vm-public-ip>:8080/v1/chat/completions`, requiring `Authorization: Bearer <token>`

- [ ] **Step 1: Write the Oracle Cloud console runbook** (`infra/local-model-vm/README.md`) — manual, one-time:

```markdown
# Local QueryPlan model VM (Oracle Always-Free)

## Provision (Oracle Cloud console, one-time)

1. Sign up / log in at cloud.oracle.com. Create a Compute instance:
   Shape = VM.Standard.A1.Flex (Always Free eligible), 4 OCPU / 24GB RAM,
   Ubuntu 24.04 image.
2. Note the instance's public IP.
3. Networking → the instance's VCN → Security Lists → default security
   list → Add Ingress Rule: source `0.0.0.0/0` (or narrower if you have a
   known backend egress range), TCP, destination port `8080`.
4. SSH in: `ssh ubuntu@<public-ip>`.

## Install + start (on the VM)

    scp infra/local-model-vm/setup.sh ubuntu@<public-ip>:~/
    scp models/query_plan_finetune/gguf/queryplan-q4_k_m.gguf ubuntu@<public-ip>:~/model.gguf
    ssh ubuntu@<public-ip> 'LLAMA_API_KEY=<generate-a-real-token> bash setup.sh'

`setup.sh` builds llama.cpp, installs the systemd unit, and starts it.
Generate the token with e.g. `openssl rand -hex 32` — put the same value
in this repo's `.env` as `LOCAL_MODEL_API_KEY` (Task 5 reads it from there).

## Verify

    curl http://<public-ip>:8080/v1/chat/completions \
      -H "Authorization: Bearer <token>" -H "Content-Type: application/json" \
      -d '{"model": "queryplan", "messages": [{"role": "user", "content": "hi"}]}'

Expected: a valid chat-completion JSON response, not a 401.
```

- [ ] **Step 2: Write the setup script**

```bash
#!/usr/bin/env bash
# infra/local-model-vm/setup.sh -- run ON the Oracle VM as the ubuntu user.
set -euo pipefail

: "${LLAMA_API_KEY:?set LLAMA_API_KEY before running}"

sudo apt-get update && sudo apt-get install -y build-essential cmake git

if [ ! -d ~/llama.cpp ]; then
  git clone https://github.com/ggml-org/llama.cpp ~/llama.cpp
fi
cmake -B ~/llama.cpp/build -S ~/llama.cpp -DCMAKE_BUILD_TYPE=Release
cmake --build ~/llama.cpp/build --config Release -j "$(nproc)"

sudo mkdir -p /opt/queryplan-model
sudo mv ~/model.gguf /opt/queryplan-model/model.gguf

sudo tee /etc/systemd/system/llama-server.service > /dev/null <<EOF
[Unit]
Description=llama.cpp server (QueryPlan model)
After=network.target

[Service]
ExecStart=$HOME/llama.cpp/build/bin/llama-server -m /opt/queryplan-model/model.gguf -c 2048 --host 0.0.0.0 --port 8080 --api-key $LLAMA_API_KEY
Restart=always
RestartSec=5
User=ubuntu

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now llama-server.service
echo "llama-server started, status:"
sudo systemctl status llama-server.service --no-pager
```

- [ ] **Step 3: Provision and run** (manual, per the README above)

Expected: `curl` verification in the README returns a valid response

- [ ] **Step 4: Confirm restart-survival**

Run (on the VM): `sudo reboot`, wait, then re-run the `curl` verification.
Expected: server is back up without manual intervention (proves `Restart=always` + `enable` actually work, not just the first manual start)

- [ ] **Step 5: Commit**

```bash
git add infra/local-model-vm/setup.sh infra/local-model-vm/llama-server.service infra/local-model-vm/README.md
git commit -m "feat: add Oracle Always-Free VM provisioning for the local QueryPlan model"
```

---

## Task 5: Wire the local model into `llm_client.py`

**Files:**
- Modify: `rag/llm_client.py`
- Test: `tests/test_llm_client.py` (new)

**Interfaces:**
- Consumes: `LOCAL_MODEL_BASE_URL`, `LOCAL_MODEL_API_KEY` env vars (new)
- Produces: `chat_completion(*, model, **kwargs)` — unchanged public signature, now tries local model first, then DeepSeek, then OpenAI

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_llm_client.py
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "rag"))

import llm_client  # noqa: E402


def _fake_openai_client(response_text: str = "ok", raise_exc: Exception | None = None):
    client = MagicMock()
    if raise_exc:
        client.chat.completions.create.side_effect = raise_exc
    else:
        resp = MagicMock()
        resp.choices[0].message.content = response_text
        client.chat.completions.create.return_value = resp
    return client


def test_local_model_tried_first_when_configured(monkeypatch):
    monkeypatch.setattr(llm_client, "LOCAL_MODEL_BASE_URL", "http://vm:8080/v1")
    monkeypatch.setattr(llm_client, "LOCAL_MODEL_API_KEY", "test-key")
    monkeypatch.setattr(llm_client, "DEEPSEEK_API_KEY", "")

    local_client = _fake_openai_client("local response")
    calls = []

    def fake_openai_ctor(*, api_key=None, base_url=None):
        calls.append((api_key, base_url))
        return local_client

    monkeypatch.setattr(llm_client, "OpenAI", fake_openai_ctor)
    resp = llm_client.chat_completion(model="gpt-5.4-nano", messages=[{"role": "user", "content": "hi"}])

    assert resp.choices[0].message.content == "local response"
    assert calls[0] == ("test-key", "http://vm:8080/v1")


def test_falls_through_to_deepseek_when_local_fails(monkeypatch):
    monkeypatch.setattr(llm_client, "LOCAL_MODEL_BASE_URL", "http://vm:8080/v1")
    monkeypatch.setattr(llm_client, "LOCAL_MODEL_API_KEY", "test-key")
    monkeypatch.setattr(llm_client, "DEEPSEEK_API_KEY", "ds-key")

    local_client = _fake_openai_client(raise_exc=ConnectionError("vm down"))
    deepseek_client = _fake_openai_client("deepseek response")
    ctors = iter([local_client, deepseek_client])
    monkeypatch.setattr(llm_client, "OpenAI", lambda **kwargs: next(ctors))

    resp = llm_client.chat_completion(model="gpt-5.4-nano", messages=[{"role": "user", "content": "hi"}])
    assert resp.choices[0].message.content == "deepseek response"


def test_no_local_model_configured_skips_straight_to_deepseek(monkeypatch):
    monkeypatch.setattr(llm_client, "LOCAL_MODEL_BASE_URL", "")
    monkeypatch.setattr(llm_client, "DEEPSEEK_API_KEY", "ds-key")

    deepseek_client = _fake_openai_client("deepseek response")
    monkeypatch.setattr(llm_client, "OpenAI", lambda **kwargs: deepseek_client)

    resp = llm_client.chat_completion(model="gpt-5.4-nano", messages=[{"role": "user", "content": "hi"}])
    assert resp.choices[0].message.content == "deepseek response"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_llm_client.py -v`
Expected: FAIL — `LOCAL_MODEL_BASE_URL` doesn't exist on `llm_client` yet

- [ ] **Step 3: Implement the local-model tier**

```python
# rag/llm_client.py -- full replacement
"""Shared local-model-primary / DeepSeek-secondary / OpenAI-fallback chat
completion helper.

DeepSeek's and llama.cpp's APIs are both OpenAI-compatible (same `openai`
SDK, different base_url), so this is one call site for all fallback logic
instead of duplicating try/except across sql_agent.py and rag_pipeline.py.
Both LLM uses in this repo (QueryPlan generation, explanatory-answer
synthesis) are approved uses per .claude/rules.md -- this module doesn't
change what the LLM is allowed to do, only which provider answers the call.

Local model (spec-014 FR-7) is tried first when configured: a fine-tuned,
quantized model on an Oracle Always-Free VM (docs/superpowers/specs/
2026-08-27-local-queryplan-model-design.md). If it's unreachable or fails,
falls through to DeepSeek, then OpenAI -- same reliability story as before
this tier existed, just with one more (optional) link at the front.
"""
from __future__ import annotations

import os

LOCAL_MODEL_BASE_URL = os.environ.get("LOCAL_MODEL_BASE_URL", "")
LOCAL_MODEL_API_KEY = os.environ.get("LOCAL_MODEL_API_KEY", "")
LOCAL_MODEL_NAME = os.environ.get("LOCAL_MODEL_NAME", "queryplan")

DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DEEPSEEK_MODEL = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")
DEEPSEEK_BASE_URL = "https://api.deepseek.com"

from openai import OpenAI  # noqa: E402  -- module-level so tests can monkeypatch it


def chat_completion(*, model: str, **kwargs):
    """Same call shape as `OpenAI().chat.completions.create(...)`. Tries the
    local model first if configured, then DeepSeek if configured, falling
    through to OpenAI with the caller's original `model` on any failure.
    Callers still wrap this in their own try/except for the "no LLM
    available at all" case -- this function only handles picking a
    provider."""
    if LOCAL_MODEL_BASE_URL:
        try:
            client = OpenAI(api_key=LOCAL_MODEL_API_KEY, base_url=LOCAL_MODEL_BASE_URL)
            return client.chat.completions.create(model=LOCAL_MODEL_NAME, **kwargs)
        except Exception as exc:  # noqa: BLE001 -- fall through to DeepSeek/OpenAI
            import sys
            print(f"[warn] local model call failed ({exc}); falling back to DeepSeek/OpenAI", file=sys.stderr)

    if DEEPSEEK_API_KEY:
        try:
            client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL)
            return client.chat.completions.create(model=DEEPSEEK_MODEL, **kwargs)
        except Exception as exc:  # noqa: BLE001 -- fall through to OpenAI
            import sys
            print(f"[warn] DeepSeek call failed ({exc}); falling back to OpenAI", file=sys.stderr)

    client = OpenAI()
    return client.chat.completions.create(model=model, **kwargs)


def demo() -> None:
    resp = chat_completion(
        model="gpt-5.4-nano",
        messages=[{"role": "user", "content": "Reply with exactly one word: OK"}],
        max_completion_tokens=10,
    )
    text = (resp.choices[0].message.content or "").strip()
    assert text, "expected some response text"
    print(f"llm_client demo OK: got {text!r}")


if __name__ == "__main__":
    demo()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_llm_client.py -v`
Expected: PASS

- [ ] **Step 5: Run the full suite to confirm no regression**

Run: `pytest tests/ -q`
Expected: same pass/fail/skip counts as before this change, plus the 3 new passing tests (no existing DeepSeek/OpenAI behavior changed when `LOCAL_MODEL_BASE_URL` is unset, which it is by default)

- [ ] **Step 6: Commit**

```bash
git add rag/llm_client.py tests/test_llm_client.py
git commit -m "feat: add local QueryPlan model as primary tier in llm_client with fallback"
```

---

## Task 6: Honest evaluation — local vs. DeepSeek vs. OpenAI

**Files:**
- Create: `models/query_plan_finetune/evaluate_comparison.py`
- Modify: `docs/superpowers/specs/2026-08-27-local-queryplan-model-design.md` (append the real results once run — design docs get a results addendum, not a rewrite)

**Interfaces:**
- Consumes: `models/query_plan_finetune/data/eval_nyc_holdout.jsonl`, `eval_unseen_schema.jsonl` (Task 1's unaugmented eval output), `rag/nl_to_sql/query_plan_agent.py::generate_plan()` (existing), `rag/nl_to_sql/sql_agent.py::generate_plan()` (existing, DeepSeek/OpenAI path)
- Produces: `models/query_plan_finetune/comparison_results.json` — `{"local": {"accuracy": float, "n": int}, "deepseek_or_openai": {"accuracy": float, "n": int}}`, mirroring `models/evaluation/compare_models.py`'s standalone-comparison-script shape

- [ ] **Step 1: Write the comparison script**

```python
# models/query_plan_finetune/evaluate_comparison.py
"""Honest comparison: local fine-tuned model vs. the existing DeepSeek/
OpenAI zero-shot QueryPlan generator, scored on the same held-out sets
training_data_gen.py already produces. Mirrors models/evaluation/
compare_models.py's standalone-script shape for the demand model ladder --
same discipline, different task.

"Correct" here means the generated QueryPlan, when compiled via
query_plan_compiler.compile(), produces the exact same SQL as the
held-out example's own label compiles to -- not string-identical JSON
(field order/nulls can legitimately differ), but semantically identical.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "rag" / "nl_to_sql"))

from nyc_schema import NYC_SCHEMA  # noqa: E402
from query_plan import QueryPlan  # noqa: E402
from query_plan_compiler import compile as compile_plan  # noqa: E402
from synthetic_schemas import HELD_OUT_SCHEMA  # noqa: E402

DATA_DIR = Path(__file__).resolve().parent / "data"
RESULTS_PATH = Path(__file__).resolve().parent / "comparison_results.json"


def load_eval_rows(filename: str) -> list[dict]:
    return [json.loads(line) for line in (DATA_DIR / filename).read_text(encoding="utf-8").splitlines() if line.strip()]


def score(generate_fn, rows: list[dict], schema) -> tuple[float, int]:
    correct = 0
    for row in rows:
        question = row["messages"][1]["content"]
        expected_plan = QueryPlan.from_json(row["messages"][2]["content"])
        try:
            actual_plan = generate_fn(question, schema=schema)
            correct += int(compile_plan(actual_plan, schema) == compile_plan(expected_plan, schema))
        except Exception:
            pass  # a generation/compile failure counts as incorrect, not a crash
    return correct / len(rows), len(rows)


def run() -> dict:
    from query_plan_agent import generate_plan as local_generate  # requires QUERY_PLAN_FINETUNED_MODEL_ID set
    from sql_agent import generate_plan as hosted_generate

    nyc_rows = load_eval_rows("eval_nyc_holdout.jsonl")
    unseen_rows = load_eval_rows("eval_unseen_schema.jsonl")

    results = {
        "local": {
            "nyc_holdout": dict(zip(("accuracy", "n"), score(local_generate, nyc_rows, NYC_SCHEMA))),
            "unseen_schema": dict(zip(("accuracy", "n"), score(local_generate, unseen_rows, HELD_OUT_SCHEMA))),
        },
        "hosted_deepseek_or_openai": {
            "nyc_holdout": dict(zip(("accuracy", "n"), score(hosted_generate, nyc_rows, NYC_SCHEMA))),
            "unseen_schema": dict(zip(("accuracy", "n"), score(hosted_generate, unseen_rows, HELD_OUT_SCHEMA))),
        },
    }
    RESULTS_PATH.write_text(json.dumps(results, indent=2))
    return results


if __name__ == "__main__":
    results = run()
    for tier, splits in results.items():
        for split, m in splits.items():
            print(f"{tier:25s} {split:15s} accuracy={m['accuracy']:.1%} (n={m['n']})")
```

- [ ] **Step 2: Run it** (needs `QUERY_PLAN_FINETUNED_MODEL_ID` pointed at the deployed local model, and real DeepSeek/OpenAI credentials — a real, costed eval run, not a unit test)

Run: `QUERY_PLAN_FINETUNED_MODEL_ID=queryplan USE_FINETUNED_QUERY_PLAN=1 python models/query_plan_finetune/evaluate_comparison.py`
Expected: `models/query_plan_finetune/comparison_results.json` written with real accuracy numbers for both tiers on both splits

- [ ] **Step 3: Append the real results to the design doc**

Read `comparison_results.json`, append a `## Results (YYYY-MM-DD)` section to `docs/superpowers/specs/2026-08-27-local-queryplan-model-design.md` with the actual numbers and one honest sentence on what they mean (e.g. "local model matches/beats hosted on NYC-holdout, generalizes worse to the unseen schema" — whatever the real numbers say, not an assumption).

- [ ] **Step 4: Decide the rollout, based on the real numbers**

If local accuracy is within a reasonable margin of the hosted baseline (your call on what's "reasonable" — this plan doesn't pre-decide it, the eval numbers should), set `USE_FINETUNED_QUERY_PLAN=1` and `QUERY_PLAN_FINETUNED_MODEL_ID=queryplan` in the deployed backend's env. Otherwise, leave it off and document why in the same results section — matching this repo's "no fabricated metrics" rule over forcing a weaker tier to primary regardless.

- [ ] **Step 5: Commit**

```bash
git add models/query_plan_finetune/evaluate_comparison.py models/query_plan_finetune/comparison_results.json docs/superpowers/specs/2026-08-27-local-queryplan-model-design.md
git commit -m "feat: add honest local-vs-hosted QueryPlan eval, record real results"
```

---

## Self-Review

**Spec coverage:** design doc's Fine-tuning pipeline → Tasks 1-3; VM provisioning & serving → Task 4; llm_client.py integration → Task 5; Evaluation & rollout → Task 6. All covered.

**Placeholder scan:** no TBD/TODO; every code block is real, runnable code or an explicit manual-runbook step marked as such.

**Type consistency:** `chat_completion(*, model, **kwargs)`'s signature is unchanged across Task 5 and every existing caller (`sql_agent.py`, `rag_pipeline.py`) — verified by reading the current `llm_client.py` before writing Task 5. `QueryPlan`/`CityMobilitySchema` types in Task 6 match `rag/nl_to_sql/query_plan.py`'s actual dataclass shape, read directly before writing that task.

**Real-world caveat, stated plainly:** Tasks 2-4 have steps that genuinely cannot run inside this repo's own test suite or CI (a Colab GPU session, an Oracle Cloud console, a VM reboot) — those are written as exact runbooks precisely so they're not vague, even though they're not automated.

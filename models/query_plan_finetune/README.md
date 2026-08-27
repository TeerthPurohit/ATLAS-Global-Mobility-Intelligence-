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

## Smoke test (still needs a GPU — run it in Colab, not on your laptop)

    python train_lora.py --smoke-test

Confirms the tokenizer/chat-template/trainer wiring is correct end-to-end on
a tiny number of steps, so a wiring bug fails in seconds instead of partway
through the real run. Two hard requirements, both easy to trip over:

- **GPU runtime required.** `train()` loads the base model with
  `load_in_4bit=True`, and unsloth/bitsandbytes 4-bit loading needs CUDA —
  it cannot run on a CPU-only machine at all. Run this in the *same* Colab
  T4 session as step 4 above, right before the real run.
- **`data/train_augmented.jsonl` must exist first** — it is produced by the
  augmentation step, not checked in: `python rag/nl_to_sql/augment_training_data.py`
  (writes `models/query_plan_finetune/data/train_augmented.jsonl`). Without
  it the smoke test dies with `FileNotFoundError` before reaching the model.

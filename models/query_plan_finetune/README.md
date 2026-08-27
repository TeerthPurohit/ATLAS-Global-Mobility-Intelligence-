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

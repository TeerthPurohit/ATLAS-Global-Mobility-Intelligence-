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
    from datasets import Dataset
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
    # SFTTrainer's _prepare_dataset calls .map()/isinstance(Dataset) internally --
    # a plain list of dicts doesn't satisfy that, so wrap it in a real Dataset.
    dataset = Dataset.from_list(
        [{"text": tokenizer.apply_chat_template(r["messages"], tokenize=False)} for r in train_rows]
    )

    trainer = SFTTrainer(
        # current trl renamed the `tokenizer` kwarg to `processing_class`
        model=model, processing_class=tokenizer, train_dataset=dataset,
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

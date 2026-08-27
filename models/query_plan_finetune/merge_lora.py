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

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

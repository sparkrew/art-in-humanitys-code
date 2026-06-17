#!/bin/bash
set -e

# Configure these paths for your cluster environment.
MODEL_PATH="<PATH_TO_QWEN3_CODER_30B_FP8_SNAPSHOT>"
HOST="0.0.0.0"
PORT="8000"
SERVED_MODEL_NAME="qwen3-coder-30b-fp8"

source .venv/bin/activate

CUDA_VISIBLE_DEVICES=0 \
vllm serve "$MODEL_PATH" \
  --host "$HOST" \
  --port "$PORT" \
  --served-model-name "$SERVED_MODEL_NAME" \
  --dtype auto \
  --max-model-len 32768 \
  --gpu-memory-utilization 0.9 \
  --max-num-batched-tokens 32768 \
  --max-num-seqs 40

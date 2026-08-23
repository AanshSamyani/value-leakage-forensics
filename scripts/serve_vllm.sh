#!/usr/bin/env bash
# Start a vLLM OpenAI-compatible server for a thinking model. Meant to be run under nohup:
#   nohup bash scripts/serve_vllm.sh Qwen/Qwen3.6-27B > /workspace/logs/vllm.log 2>&1 &
#   nohup bash scripts/serve_vllm.sh openai/gpt-oss-120b > /workspace/logs/vllm.log 2>&1 &
#   nohup bash scripts/serve_vllm.sh Qwen/Qwen3.5-122B-A10B 4 > /workspace/logs/vllm.log 2>&1 &   # 2nd arg = tensor parallel
set -euo pipefail
MODEL=${1:-Qwen/Qwen3.6-27B}
TP=${2:-1}
PORT=${PORT:-8000}
MAXLEN=${MAXLEN:-65536}
MAXSEQS=${MAXSEQS:-128}   # Qwen3.5/3.6 hybrid models: must be <= available Mamba cache blocks (~330 on 80GB)
export HF_HOME=${HF_HOME:-/workspace/hf}

case "$MODEL" in
  *gpt-oss*)   PARSER=${PARSER:-openai_gptoss} ;;
  *)           PARSER=${PARSER:-qwen3} ;;      # Qwen3 / 3.5 / 3.6 thinking models
esac

echo "serving $MODEL  tp=$TP  parser=$PARSER  port=$PORT  max-len=$MAXLEN  max-seqs=$MAXSEQS"
exec vllm serve "$MODEL" \
  --tensor-parallel-size "$TP" \
  --reasoning-parser "$PARSER" \
  --max-model-len "$MAXLEN" \
  --gpu-memory-utilization 0.92 \
  --max-num-seqs "$MAXSEQS" \
  --port "$PORT" \
  --served-model-name "$MODEL"

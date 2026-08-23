#!/usr/bin/env bash
# Start a vLLM OpenAI-compatible server for a thinking model. Run inside tmux.
#   bash scripts/serve_vllm.sh Qwen/Qwen3.6-27B
#   bash scripts/serve_vllm.sh openai/gpt-oss-120b
#   bash scripts/serve_vllm.sh Qwen/Qwen3.5-122B-A10B 4        # tensor-parallel size as 2nd arg
set -euo pipefail
MODEL=${1:-Qwen/Qwen3.6-27B}
TP=${2:-1}
PORT=${PORT:-8000}
MAXLEN=${MAXLEN:-65536}
export HF_HOME=${HF_HOME:-/workspace/hf}

case "$MODEL" in
  *gpt-oss*)   PARSER=openai_gptoss ;;
  *)           PARSER=${PARSER:-qwen3} ;;      # Qwen3 / 3.5 / 3.6 thinking models
esac

mkdir -p /workspace/logs
echo "serving $MODEL  tp=$TP  parser=$PARSER  port=$PORT  max-len=$MAXLEN  (log: /workspace/logs/vllm.log)"
exec vllm serve "$MODEL" \
  --tensor-parallel-size "$TP" \
  --reasoning-parser "$PARSER" \
  --max-model-len "$MAXLEN" \
  --gpu-memory-utilization 0.92 \
  --max-num-seqs ${MAXSEQS:-64} \
  --port "$PORT" \
  --served-model-name "$MODEL" 2>&1 | tee -a /workspace/logs/vllm.log

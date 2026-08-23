#!/usr/bin/env bash
# Block until the vLLM server answers /v1/models (or until TIMEOUT seconds pass).
URL=${VLLM_BASE_URL:-http://localhost:8000/v1}
TIMEOUT=${TIMEOUT:-3600}
t=0
until curl -sf "$URL/models" >/dev/null 2>&1; do
  sleep 15; t=$((t+15))
  if [ $t -ge $TIMEOUT ]; then echo "vLLM not up after ${TIMEOUT}s (see /workspace/logs/vllm.log)"; exit 1; fi
done
echo "vLLM is up: $(curl -s $URL/models | head -c 200)"

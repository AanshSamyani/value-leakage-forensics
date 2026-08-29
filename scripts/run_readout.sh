#!/usr/bin/env bash
# Project rollouts onto one or more direction vectors, under nohup.
#
#   nohup bash scripts/run_readout.sh > /workspace/logs/readout_$(date +%m%d_%H%M).log 2>&1 &
#   tail -f /workspace/logs/readout_*.log
#
# Env: VECTORS ("vectors/value_axis.pt vectors/random_control.pt"), RUNS (run dir names),
#      LAYERS (comma list; default = each vector's recommended_layers), LIMIT, GPU_MEM, MODEL.
#
# One vLLM boot per vector — 08_readout.py constructs its own sampler. Boot is ~4 min, the readout
# itself ~10 min for 300 rollouts, so two vectors is roughly half an hour.
#
# The random control is not optional. The three conditions have different prompts and different
# reasoning, so ANY direction separates them somewhat; the value axis only means something if it
# beats a norm-matched random direction on the same rollouts.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
set -a; [ -f .env ] && source .env; set +a

VECTORS=${VECTORS:-"vectors/value_axis.pt vectors/random_control.pt"}
RUNS=${RUNS:-qwen3.5-27b_20260823_223518}
GPU_MEM=${GPU_MEM:-0.85}
export VLLM_WORKER_MULTIPROC_METHOD=spawn
export VLLM_USE_FLASHINFER_SAMPLER=${VLLM_USE_FLASHINFER_SAMPLER:-0}

# Preflight: fail in seconds, not four minutes into an engine boot. /workspace outlives the pod, so a
# torch built for the previous host's CUDA is a live hazard every time the pod is recreated —
# "The NVIDIA driver on your system is too old" surfaces only after the model has started loading.
python - <<'PYCHECK'
import torch
if not torch.cuda.is_available():
    raise SystemExit("torch cannot see the GPU")
try:
    torch.zeros(1).cuda()
except RuntimeError as e:
    raise SystemExit(f"CUDA init failed: {e}\n\n"
                     "If this says the driver is too old, the pod has moved to a host with an older\n"
                     "CUDA than the torch in /workspace/venv was built for. Fix:\n"
                     "    bash scripts/runpod_setup.sh    # reinstalls torch/vLLM for THIS host")
p = torch.cuda.get_device_properties(0)
print(f"[preflight] torch {torch.__version__} (cuda {torch.version.cuda}) on {p.name}, "
      f"{p.total_memory/1e9:.0f} GB — ok", flush=True)
PYCHECK

echo "=== readout  vectors=[$VECTORS]  runs=[$RUNS]  ($(date))"
FAILED=""
for V in $VECTORS; do
  [ -f "$V" ] || { echo "!!! missing vector $V — skipping"; FAILED="$FAILED $V"; continue; }
  echo; echo "############ [$(date +%H:%M:%S)] $V"
  ARGS=()
  [ -n "${LAYERS:-}" ] && ARGS+=(--layers "$LAYERS")
  [ -n "${LIMIT:-}" ]  && ARGS+=(--limit "$LIMIT")
  [ -n "${MODEL:-}" ]  && ARGS+=(--model "$MODEL")
  if ! python scripts/08_readout.py --vector "$V" --runs $RUNS --gpu-mem "$GPU_MEM" "${ARGS[@]}"; then
    echo "!!! readout FAILED for $V — continuing"; FAILED="$FAILED $V"
  fi
done

echo; echo "=== DONE ($(date))."
[ -n "$FAILED" ] && echo "FAILED:$FAILED"
FIRST=$(echo $RUNS | awk '{print $1}')
echo "Outputs:"
ls -1 "$ROOT"/data/runs/"$FIRST"*/analysis/readout_*.csv 2>/dev/null || echo "  (none found)"
echo
echo "Push them back:"
echo "  git add -f data/runs/$FIRST*/analysis/readout_*.csv && git commit -m 'value axis readout' && git push"

#!/usr/bin/env bash
# Starter batch (items 1a-1g): ALL generation first under one vLLM boot, then ALL judging,
# one run at a time.
#
#   nohup bash scripts/run_batch.sh > /workspace/logs/batch_$(date +%m%d_%H%M).log 2>&1 &
#   tail -f /workspace/logs/batch_*.log
#
# Env: MODEL (Qwen/Qwen3.5-27B), COUNT (100), CHUNK (400), MAX_TOKENS (32000),
#      MAX_NUM_SEQS (128), MAX_MODEL_LEN (65536), GPU_MEM (0.92), TP (1),
#      JUDGE_MODEL (claude-haiku-4-5), JUDGE_CONCURRENCY (16),
#      ONLY ("sweep-above q-sand" — substring filter), SKIP_GENERATE=1, SKIP_JUDGE=1, FRESH=1.
#
# Resumable: just re-run it. Generation reuses each job's run dir and samples only missing rollouts;
# judging is cached per rollout under <run_dir>/judge_cache/.
#
# Preview every prompt before committing 8 hours of GPU:  python scripts/06_batch.py --dry-run
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
set -a; [ -f .env ] && source .env; set +a
: "${ANTHROPIC_API_KEY:?ANTHROPIC_API_KEY missing — put it in $ROOT/.env}"

MODEL=${MODEL:-Qwen/Qwen3.5-27B}
COUNT=${COUNT:-100}
CHUNK=${CHUNK:-400}
MAX_TOKENS=${MAX_TOKENS:-32000}
MAX_NUM_SEQS=${MAX_NUM_SEQS:-128}
MAX_MODEL_LEN=${MAX_MODEL_LEN:-65536}
GPU_MEM=${GPU_MEM:-0.92}
TP=${TP:-1}
JUDGE_MODEL=${JUDGE_MODEL:-claude-haiku-4-5}
JUDGE_CONCURRENCY=${JUDGE_CONCURRENCY:-16}

export VLLM_WORKER_MULTIPROC_METHOD=spawn                       # fork-with-CUDA crash in EngineCore
export VLLM_USE_FLASHINFER_SAMPLER=${VLLM_USE_FLASHINFER_SAMPLER:-0}   # pod images without curand.h

echo "=== starter batch  model=$MODEL count=$COUNT chunk=$CHUNK  ($(date))"

if [ "${SKIP_GENERATE:-0}" != "1" ]; then
  EXTRA=()
  [ -n "${ONLY:-}" ] && EXTRA+=(--only ${ONLY})
  [ "${FRESH:-0}" = "1" ] && EXTRA+=(--fresh)
  python scripts/06_batch.py --model "$MODEL" --count "$COUNT" --chunk "$CHUNK" \
      --max-tokens "$MAX_TOKENS" --max-num-seqs "$MAX_NUM_SEQS" --max-model-len "$MAX_MODEL_LEN" \
      --gpu-mem "$GPU_MEM" --tp "$TP" --judge-model "$JUDGE_MODEL" \
      --judge-concurrency "$JUDGE_CONCURRENCY" "${EXTRA[@]}"
else
  echo "SKIP_GENERATE=1 — using the run dirs already on disk"
fi

MANIFEST=$(ls -t "$ROOT"/data/runs/batch_*.json 2>/dev/null | head -1 || true)
[ -n "$MANIFEST" ] || { echo "no batch manifest under data/runs — did generation run?"; exit 1; }
echo; echo "=== manifest: $MANIFEST"
RUN_DIRS=()   # not `mapfile`: bash 3.2 (macOS) lacks it and this script is also handy to dry-run locally
while IFS= read -r line; do RUN_DIRS+=("$line"); done < <(python -c "
import json,sys
for r in json.load(open(sys.argv[1]))['runs']: print(r['dir'])" "$MANIFEST")
echo "=== ${#RUN_DIRS[@]} run dirs to judge"

if [ "${SKIP_JUDGE:-0}" != "1" ]; then
  # GPU is idle from here — generation is entirely finished before any judging starts.
  FAILED=""
  for d in "${RUN_DIRS[@]}"; do
    echo; echo "############ [$(date +%H:%M:%S)] judging $(basename "$d")"
    if ! python scripts/02_judge_paper.py --run-dir "$d" --kinds estimates trajectories \
         --judge-model "$JUDGE_MODEL" --concurrency "$JUDGE_CONCURRENCY"; then
      echo "!!! judging FAILED for $(basename "$d") — continuing"
      FAILED="$FAILED $(basename "$d")"
    fi
  done
  [ -n "$FAILED" ] && echo "FAILED judging:$FAILED (re-run with SKIP_GENERATE=1 to retry; results are cached)"
fi

echo; echo "=== headline table"
REF=$(ls -d "$ROOT"/data/runs/qwen3.5-27b_2* | tail -1)
python scripts/00_summary.py --runs "$REF" "${RUN_DIRS[@]}" --csv "$ROOT/data/runs/starter_batch_summary.csv"

echo; echo "=== DONE ($(date))."
echo "Push results (raw rollouts included — the interp work needs the CoTs):"
echo "  RAW=1 bash scripts/push_results.sh $(for d in "${RUN_DIRS[@]}"; do basename "$d"; done | paste -sd' ' -)"

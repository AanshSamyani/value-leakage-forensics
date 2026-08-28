#!/usr/bin/env bash
# Sentence resampling under nohup — one vLLM boot, both modes, then judging.
#
#   nohup bash scripts/run_resample.sh > /workspace/logs/resample_$(date +%m%d_%H%M).log 2>&1 &
#   tail -f /workspace/logs/resample_*.log
#
# Env: RUN (main run dir name), MODE (both|brake|insertion|sweep), TARGET + MIN_PASSAGE_CHARS +
#      STRIDE (sweep mode), LIMIT (20 = take every usable target),
#      SAMPLES (30 continuations per prefix), WINDOW (2 = brake cut points either side of the target),
#      MAX_TOKENS (16000), CHUNK (400), MODEL, TEMPERATURE (1.0 — MUST match the original run),
#      MAX_NUM_SEQS (128), MAX_MODEL_LEN (65536), GPU_MEM (0.92),
#      JUDGE_MODEL (claude-haiku-4-5), JUDGE_CONCURRENCY (16).
#
# Preview the targets and their cut context without touching a GPU:
#   python scripts/09_resample.py --dry-run
#
# Results land in <run>/analysis/resample_{brake,insertion}.json, checkpointed every chunk, and the
# summary table is printed at the end of each mode. Judge results are cached per continuation, so a
# re-run after a crash only regenerates what is missing.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
set -a; [ -f .env ] && source .env; set +a
: "${ANTHROPIC_API_KEY:?ANTHROPIC_API_KEY missing — put it in $ROOT/.env}"

RUN=${RUN:-qwen3.5-27b_20260823_223518}
MODE=${MODE:-both}
TARGET=${TARGET:-above_good/12}
MIN_PASSAGE_CHARS=${MIN_PASSAGE_CHARS:-250}
STRIDE=${STRIDE:-1}
LIMIT=${LIMIT:-20}
SAMPLES=${SAMPLES:-30}
WINDOW=${WINDOW:-2}
MAX_TOKENS=${MAX_TOKENS:-16000}
CHUNK=${CHUNK:-200}
TEMPERATURE=${TEMPERATURE:-1.0}
MAX_NUM_SEQS=${MAX_NUM_SEQS:-128}
MAX_MODEL_LEN=${MAX_MODEL_LEN:-65536}
GPU_MEM=${GPU_MEM:-0.92}
JUDGE_MODEL=${JUDGE_MODEL:-claude-haiku-4-5}
JUDGE_CONCURRENCY=${JUDGE_CONCURRENCY:-16}

export VLLM_WORKER_MULTIPROC_METHOD=spawn                              # fork-with-CUDA crash in EngineCore
export VLLM_USE_FLASHINFER_SAMPLER=${VLLM_USE_FLASHINFER_SAMPLER:-0}   # pod images without curand.h

echo "=== resample [$MODE]  run=$RUN  limit=$LIMIT  samples=$SAMPLES  ($(date))"
ARGS=()
[ -n "${MODEL:-}" ] && ARGS+=(--model "$MODEL")
[ "$MODE" = "sweep" ] && ARGS+=(--target "$TARGET" --min-passage-chars "$MIN_PASSAGE_CHARS" --stride "$STRIDE")

python scripts/09_resample.py --run "$RUN" --mode "$MODE" --limit "$LIMIT" --samples "$SAMPLES" \
    --window "$WINDOW" --max-tokens "$MAX_TOKENS" --chunk "$CHUNK" --temperature "$TEMPERATURE" \
    --max-num-seqs "$MAX_NUM_SEQS" --max-model-len "$MAX_MODEL_LEN" --gpu-mem "$GPU_MEM" \
    --judge-model "$JUDGE_MODEL" --judge-concurrency "$JUDGE_CONCURRENCY" "${ARGS[@]}"

echo; echo "=== DONE ($(date)). Outputs:"
for m in brake insertion sweep; do
  f="$ROOT/data/runs/$RUN/analysis/resample_$m.json"
  [ -f "$f" ] && echo "  $f"
done
echo
echo "Push them back (small JSON, no rollouts):"
echo "  git add -f data/runs/$RUN/analysis/resample_*.json && git commit -m 'resampling results' && git push"

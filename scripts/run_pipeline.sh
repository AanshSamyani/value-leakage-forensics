#!/usr/bin/env bash
# Full pipeline for ONE target model, sequentially, under nohup:
#   nohup bash scripts/run_pipeline.sh Qwen/Qwen3.6-27B 100 > /workspace/logs/pipeline_qwen36.log 2>&1 &
# Default SAMPLER=vllm_offline (in-process vLLM: no server needed). SAMPLER=vllm uses a running `vllm serve`.
#
# Steps: 01 generate (baseline -> threshold -> above/below)
#        -> 02 paper judges (estimates + trajectories)  -> 02b Aditya fig/factor.json
#        -> 00 summary (bias)  -> 05 E2  -> 03 mode judge (E1 labels)  -> 04 E1 analysis
# Env knobs: COUNT (2nd arg, default 100), MAX_TOKENS (32000), CONCURRENCY (32, server mode), JUDGE_MODEL (claude-haiku-4-5),
#            SAMPLER (vllm_offline|vllm), TP (tensor parallel, offline), MAX_MODEL_LEN (65536), GPU_MEM (0.92), MAX_NUM_SEQS (128),
#            CHAT_TEMPLATE_KWARGS (JSON, e.g. '{"reasoning_effort":"high"}' for gpt-oss),
#            RUN_DIR (default data/runs/<slug>_<stamp>), SKIP_MODES=1 to stop before the E1 judge,
#            SKIP_GENERATE=1 to run steps 2-7 on an existing RUN_DIR (e.g. one of Aditya's runs).
set -euo pipefail
MODEL=${1:-Qwen/Qwen3.6-27B}
COUNT=${2:-100}
MAX_TOKENS=${MAX_TOKENS:-32000}
CONCURRENCY=${CONCURRENCY:-32}
JUDGE_MODEL=${JUDGE_MODEL:-claude-haiku-4-5}
SAMPLER=${SAMPLER:-vllm_offline}
TP=${TP:-1}
MAX_MODEL_LEN=${MAX_MODEL_LEN:-65536}
GPU_MEM=${GPU_MEM:-0.92}
MAX_NUM_SEQS=${MAX_NUM_SEQS:-128}
CHAT_TEMPLATE_KWARGS=${CHAT_TEMPLATE_KWARGS:-}

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
set -a; [ -f .env ] && source .env; set +a
: "${ANTHROPIC_API_KEY:?ANTHROPIC_API_KEY missing — put it in $ROOT/.env}"

SLUG=$(echo "${MODEL##*/}" | tr '[:upper:]' '[:lower:]' | sed -E 's/[^a-z0-9.-]+/-/g')
RUN_DIR=${RUN_DIR:-$ROOT/data/runs/${SLUG}_$(date +%Y%m%d_%H%M%S)}
mkdir -p "$RUN_DIR" /workspace/logs 2>/dev/null || mkdir -p "$RUN_DIR"
echo "=== pipeline for $MODEL -> $RUN_DIR   ($(date))"

step() { echo; echo "=== [$(date +%H:%M:%S)] $*"; }

if [ "${SKIP_GENERATE:-0}" = "1" ]; then
  step "1/7 generation SKIPPED (SKIP_GENERATE=1) — using existing rollouts in $RUN_DIR"
  [ -f "$RUN_DIR/above_good.json" ] || { echo "no above_good.json in $RUN_DIR"; exit 1; }
else
  if [ "$SAMPLER" = "vllm" ]; then
    step "0/7 waiting for vLLM server"
    bash scripts/wait_for_vllm.sh
  fi
  step "1/7 generate rollouts (sampler=$SAMPLER, count=$COUNT, max_tokens=$MAX_TOKENS)"
  EXTRA=()
  if [ "$SAMPLER" = "vllm_offline" ]; then
    EXTRA+=(--tp "$TP" --max-model-len "$MAX_MODEL_LEN" --gpu-mem "$GPU_MEM" --max-num-seqs "$MAX_NUM_SEQS")
    [ -n "$CHAT_TEMPLATE_KWARGS" ] && EXTRA+=(--chat-template-kwargs "$CHAT_TEMPLATE_KWARGS")
  else
    EXTRA+=(--concurrency "$CONCURRENCY")
  fi
  python scripts/01_generate.py --sampler "$SAMPLER" --model "$MODEL" --count "$COUNT" --max-tokens "$MAX_TOKENS" \
         --run-dir "$RUN_DIR" --judge-model "$JUDGE_MODEL" "${EXTRA[@]}"
fi

step "2/7 paper judges (estimate judge on answers, trajectory judge on reasoning)"
python scripts/02_judge_paper.py --run-dir "$RUN_DIR" --judge-model "$JUDGE_MODEL"

step "3/7 Aditya artefacts: fig.png, fig_split.png, factor.json"
python scripts/02b_plot_run.py --run-dir "$RUN_DIR"

step "4/7 headline summary (P(final>T), bias, p_biased, MRF)"
python scripts/00_summary.py --runs "$RUN_DIR" --csv "$RUN_DIR/summary.csv"

step "5/7 E2 dynamics"
python scripts/05_analyze_e2.py --run-dir "$RUN_DIR"

if [ "${SKIP_MODES:-0}" = "1" ]; then echo "SKIP_MODES=1 — stopping before the E1 judge"; exit 0; fi

step "6/7 E1 mode judge"
python scripts/03_judge_modes.py --run-dir "$RUN_DIR" --judge-model "$JUDGE_MODEL" --export-review "$RUN_DIR/review_modes.md"

step "7/7 E1 analysis"
python scripts/04_analyze_e1.py --run-dir "$RUN_DIR"

echo; echo "=== DONE ($(date)). Outputs:"
echo "  $RUN_DIR/{fig.png,fig_split.png,factor.json,summary.csv,review_modes.md}"
echo "  $RUN_DIR/analysis/e2/summary.md   $RUN_DIR/analysis/e1/summary.md"

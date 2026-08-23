#!/usr/bin/env bash
# Full pipeline for ONE target model, sequentially. Run under nohup AFTER the vLLM server is started:
#   nohup bash scripts/run_pipeline.sh Qwen/Qwen3.6-27B 100 > /workspace/logs/pipeline_qwen36.log 2>&1 &
#
# Steps: wait for vLLM -> 01 generate (baseline -> threshold -> above/below)
#        -> 02 paper judges (estimates + trajectories)  -> 02b Aditya fig/factor.json
#        -> 00 summary (bias)  -> 05 E2  -> 03 mode judge (E1 labels)  -> 04 E1 analysis
# Env knobs: COUNT (2nd arg, default 100), MAX_TOKENS (32000), CONCURRENCY (32), JUDGE_MODEL (claude-haiku-4-5),
#            RUN_DIR (default data/runs/<slug>_<stamp>), SKIP_MODES=1 to stop before the E1 judge.
set -euo pipefail
MODEL=${1:-Qwen/Qwen3.6-27B}
COUNT=${2:-100}
MAX_TOKENS=${MAX_TOKENS:-32000}
CONCURRENCY=${CONCURRENCY:-32}
JUDGE_MODEL=${JUDGE_MODEL:-claude-haiku-4-5}

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
set -a; [ -f .env ] && source .env; set +a
: "${ANTHROPIC_API_KEY:?ANTHROPIC_API_KEY missing — put it in $ROOT/.env}"

SLUG=$(echo "${MODEL##*/}" | tr '[:upper:]' '[:lower:]' | sed -E 's/[^a-z0-9.-]+/-/g')
RUN_DIR=${RUN_DIR:-$ROOT/data/runs/${SLUG}_$(date +%Y%m%d_%H%M%S)}
mkdir -p "$RUN_DIR" /workspace/logs 2>/dev/null || mkdir -p "$RUN_DIR"
echo "=== pipeline for $MODEL -> $RUN_DIR   ($(date))"

step() { echo; echo "=== [$(date +%H:%M:%S)] $*"; }

step "0/7 waiting for vLLM"
bash scripts/wait_for_vllm.sh

step "1/7 generate rollouts (count=$COUNT, max_tokens=$MAX_TOKENS)"
python scripts/01_generate.py --sampler vllm --model "$MODEL" --count "$COUNT" --max-tokens "$MAX_TOKENS" \
       --concurrency "$CONCURRENCY" --run-dir "$RUN_DIR" --judge-model "$JUDGE_MODEL"

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

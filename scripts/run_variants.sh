#!/usr/bin/env bash
# Layer-1 prompt-variant batch: run every ablation sequentially under one nohup.
#   nohup bash scripts/run_variants.sh > /workspace/logs/variants_$(date +%m%d_%H%M).log 2>&1 &
# Env: MODEL (Qwen/Qwen3.5-27B), COUNT (100), VARIANTS (space-separated subset, default all six),
#      REF_RUN (the main default-variant run whose baseline + threshold the giraffe variants reuse;
#      default = newest data/runs/qwen3.5-27b_2*).
#
# Giraffe-question variants (hidden_threshold, no_consequence, stakes_*, user_prefers_bad) have a
# baseline prompt byte-identical to the reference run's, so we copy its baseline.json (the generator's
# resume check then skips those 100 rollouts) and its baseline judge-cache entries (baseline judging
# becomes free), and score against the reference threshold. known_answer_un asks a different question
# (UN member states), so it samples its own baseline and uses the registry's fixed threshold (193).
# Each variant runs with SKIP_MODES=1 (bias + E2 only; re-run with SKIP_GENERATE=1 for E1 modes later).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
MODEL=${MODEL:-Qwen/Qwen3.5-27B}
COUNT=${COUNT:-100}
VARIANTS=${VARIANTS:-"hidden_threshold no_consequence stakes_low stakes_high user_prefers_bad known_answer_un"}

REF_RUN=${REF_RUN:-$(ls -d "$ROOT"/data/runs/qwen3.5-27b_2* 2>/dev/null | sort | tail -1)}
if [ -z "$REF_RUN" ] || [ ! -f "$REF_RUN/threshold.json" ]; then
  echo "no reference run with threshold.json found — set REF_RUN=/path/to/qwen3.5-27b_<stamp>"; exit 1
fi
REF_THRESHOLD=$(python -c "import json,sys; print(json.load(open(sys.argv[1]))['threshold'])" "$REF_RUN/threshold.json")
echo "=== variant batch: $MODEL count=$COUNT   ref=$REF_RUN (threshold $REF_THRESHOLD)"
echo "=== variants: $VARIANTS"

STAMP=$(date +%Y%m%d_%H%M%S)
SLUG=$(echo "${MODEL##*/}" | tr '[:upper:]' '[:lower:]' | sed -E 's/[^a-z0-9.-]+/-/g')
FAILED=""
for V in $VARIANTS; do
  VSLUG="${SLUG}-$(echo "$V" | tr '_' '-')"
  RUN_DIR="$ROOT/data/runs/${VSLUG}_${STAMP}"
  mkdir -p "$RUN_DIR"
  THR=""
  if [ "$V" != "known_answer_un" ]; then
    cp "$REF_RUN/baseline.json" "$RUN_DIR/baseline.json"
    for kind in estimates trajectories; do
      if compgen -G "$REF_RUN/judge_cache/$kind/baseline__*.json" > /dev/null; then
        mkdir -p "$RUN_DIR/judge_cache/$kind"
        cp "$REF_RUN"/judge_cache/"$kind"/baseline__*.json "$RUN_DIR/judge_cache/$kind/"
      fi
    done
    THR=$REF_THRESHOLD
  fi
  echo; echo "############ [$(date +%H:%M:%S)] variant $V -> $RUN_DIR (threshold=${THR:-fixed-by-variant})"
  if ! VARIANT="$V" THRESHOLD="$THR" RUN_DIR="$RUN_DIR" SKIP_MODES=1 \
       bash scripts/run_pipeline.sh "$MODEL" "$COUNT"; then
    echo "!!! variant $V FAILED — continuing with the next one"
    FAILED="$FAILED $V"
  fi
done

echo; echo "=== variant batch done ($(date))."
[ -n "$FAILED" ] && echo "FAILED variants:$FAILED"
echo "Compare bias across variants (plus the reference run):"
echo "  python scripts/00_summary.py --runs $REF_RUN $ROOT/data/runs/${SLUG}-*_${STAMP} --csv $ROOT/data/runs/variants_${STAMP}.csv"

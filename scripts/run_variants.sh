#!/usr/bin/env bash
# Layer-1 prompt-variant batch: run every ablation sequentially under one nohup.
#   nohup bash scripts/run_variants.sh > /workspace/logs/variants_$(date +%m%d_%H%M).log 2>&1 &
# Env: MODEL (Qwen/Qwen3.5-27B), COUNT (100), VARIANTS (space-separated subset, default all six),
#      REF_RUN (the main default-variant run whose baseline + threshold the giraffe variants reuse;
#      default = newest data/runs/qwen3.5-27b_2*).
#
# Resumable: re-running reuses the newest existing run dir of each variant (every pipeline step is
# idempotent — generation samples only missing rollouts, judge results are cached) and skips variants
# whose run already has summary.csv + analysis/e2/summary.md. FRESH=1 forces new run dirs instead.
# STATUS=1 only prints each variant's state (rollouts per condition, complete or not) and exits.
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
SLUG=$(echo "${MODEL##*/}" | tr '[:upper:]' '[:lower:]' | sed -E 's/[^a-z0-9.-]+/-/g')

latest_dir() { ls -d "$ROOT"/data/runs/"$1"_2* 2>/dev/null | sort | tail -1 || true; }
# complete = analysed AND at least COUNT ok rollouts per incentive condition (so raising COUNT resumes a run)
is_complete() {
  [ -f "$1/summary.csv" ] && [ -f "$1/analysis/e2/summary.md" ] || return 1
  python -c '
import json, os, sys
d, n = sys.argv[1], int(sys.argv[2])
def ok(c):
    p = os.path.join(d, c + ".json")
    return os.path.exists(p) and sum(1 for r in json.load(open(p))["rows"] if "error" not in r) >= n
sys.exit(0 if ok("above_good") and ok("below_good") else 1)
' "$1" "$COUNT"
}
# The run dir a variant should use: a COMPLETE one if any exists (newest first), else the newest
# incomplete one (to resume), else empty. A stale fresh dir must never shadow a finished run.
pick_dir() {
  local d best=""
  for d in $(ls -d "$ROOT"/data/runs/"$1"_2* 2>/dev/null | sort -r || true); do
    if is_complete "$d"; then echo "$d"; return; fi
    [ -z "$best" ] && best=$d
  done
  echo "$best"
}

if [ "${STATUS:-0}" = "1" ]; then
  for V in $VARIANTS; do
    VSLUG="${SLUG}-$(echo "$V" | tr '_' '-')"
    dirs=$(ls -d "$ROOT"/data/runs/"$VSLUG"_2* 2>/dev/null | sort -r || true)
    if [ -z "$dirs" ]; then echo "$V: not started"; continue; fi
    use=$(pick_dir "$VSLUG")
    echo "$V:"
    for d in $dirs; do
      tag="     "; [ "$d" = "$use" ] && tag="  -> "
      python - "$tag" "$d" "$COUNT" <<'PY'
import json, os, sys
tag, d, need = sys.argv[1], sys.argv[2], int(sys.argv[3])
parts = []; counts = {}
for c in ("baseline", "below_good", "above_good"):
    p = os.path.join(d, c + ".json")
    if os.path.exists(p):
        rows = json.load(open(p))["rows"]
        counts[c] = sum(1 for r in rows if 'error' not in r)
        parts.append(f"{c}={counts[c]}/{len(rows)}")
    else:
        counts[c] = 0
        parts.append(f"{c}=0")
done = (os.path.exists(os.path.join(d, "summary.csv")) and os.path.exists(os.path.join(d, "analysis", "e2", "summary.md"))
        and counts["above_good"] >= need and counts["below_good"] >= need)
state = "COMPLETE" if done else ("INCOMPLETE (will resume)" if tag.strip() else "INCOMPLETE (stale duplicate — safe to delete)")
print(f"{tag}{os.path.basename(d)}  {' '.join(parts)}  -> {state}")
PY
    done
  done
  exit 0
fi

REF_RUN=${REF_RUN:-$(latest_dir "$SLUG")}
if [ -z "$REF_RUN" ] || [ ! -f "$REF_RUN/threshold.json" ]; then
  echo "no reference run with threshold.json found — set REF_RUN=/path/to/qwen3.5-27b_<stamp>"; exit 1
fi
REF_THRESHOLD=$(python -c "import json,sys; print(json.load(open(sys.argv[1]))['threshold'])" "$REF_RUN/threshold.json")
echo "=== variant batch: $MODEL count=$COUNT   ref=$REF_RUN (threshold $REF_THRESHOLD)"
echo "=== variants: $VARIANTS"

STAMP=$(date +%Y%m%d_%H%M%S)
FAILED=""
for V in $VARIANTS; do
  VSLUG="${SLUG}-$(echo "$V" | tr '_' '-')"
  RUN_DIR=""
  [ "${FRESH:-0}" = "1" ] || RUN_DIR=$(pick_dir "$VSLUG")
  if [ -n "$RUN_DIR" ] && is_complete "$RUN_DIR"; then
    echo; echo "############ variant $V already complete -> $RUN_DIR (skipping)"; continue
  fi
  if [ -n "$RUN_DIR" ]; then
    echo; echo "############ [$(date +%H:%M:%S)] variant $V RESUMING in $RUN_DIR"
  else
    RUN_DIR="$ROOT/data/runs/${VSLUG}_${STAMP}"
    echo; echo "############ [$(date +%H:%M:%S)] variant $V -> $RUN_DIR"
  fi
  mkdir -p "$RUN_DIR"
  THR=""
  if [ "$V" != "known_answer_un" ]; then
    [ -f "$RUN_DIR/baseline.json" ] || cp "$REF_RUN/baseline.json" "$RUN_DIR/baseline.json"
    for kind in estimates trajectories; do
      if compgen -G "$REF_RUN/judge_cache/$kind/baseline__*.json" > /dev/null; then
        mkdir -p "$RUN_DIR/judge_cache/$kind"
        cp -n "$REF_RUN"/judge_cache/"$kind"/baseline__*.json "$RUN_DIR/judge_cache/$kind/" 2>/dev/null || true
      fi
    done
    THR=$REF_THRESHOLD
  fi
  echo "            threshold=${THR:-fixed-by-variant}"
  if ! VARIANT="$V" THRESHOLD="$THR" RUN_DIR="$RUN_DIR" SKIP_MODES=1 \
       bash scripts/run_pipeline.sh "$MODEL" "$COUNT"; then
    echo "!!! variant $V FAILED — continuing with the next one"
    FAILED="$FAILED $V"
  fi
done

echo; echo "=== variant batch done ($(date))."
[ -n "$FAILED" ] && echo "FAILED variants:$FAILED (re-run this script to resume them)"
echo "Compare bias across variants (plus the reference run):"
echo "  python scripts/00_summary.py --runs $REF_RUN $ROOT/data/runs/${SLUG}-*_2* --csv $ROOT/data/runs/variants_summary.csv"

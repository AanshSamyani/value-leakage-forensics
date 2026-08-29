#!/usr/bin/env bash
# Build the value axis for our model and convert it for the main environment.
#
#   bash /workspace/value-leakage-forensics/scripts/run_value_axis.sh
#   MODEL=Qwen/Qwen3.5-27B bash .../run_value_axis.sh          # default is already this
#
# Steps 1 and 2 of their pipeline (generating ICRL conversations, labelling reward tokens) are
# MODEL-INDEPENDENT and already published, so they are skipped entirely — the data auto-downloads.
# Only the two steps that touch a model are run here, and neither needs an API key.
#
# Runs in the value-axis venv, then hops back to the main venv for the conversion, so neither
# environment has to know about the other.
set -euo pipefail

WORKSPACE=/workspace
VA_DIR=$WORKSPACE/value-axis
VA_PY=$VA_DIR/.venv/bin/python
MAIN_DIR=$WORKSPACE/value-leakage-forensics
MAIN_PY=$WORKSPACE/venv/bin/python
MODEL=${MODEL:-Qwen/Qwen3.5-27B}

export HF_HOME=${HF_HOME:-$WORKSPACE/hf}
export XDG_CACHE_HOME=${XDG_CACHE_HOME:-$WORKSPACE/.cache}

[ -x "$VA_PY" ] || { echo "no value-axis venv — run scripts/setup_value_axis.sh first"; exit 1; }
[ -x "$MAIN_PY" ] || { echo "no main venv at $MAIN_PY"; exit 1; }

cd "$VA_DIR/construction"
echo "=== [$(date +%H:%M:%S)] extract_activations.py --model $MODEL"
echo "    380 conversations, one forward pass each, all layers via output_hidden_states."
echo "    ~15-25 min including model load. Weights come from $HF_HOME (already cached)."
"$VA_PY" extract_activations.py --model "$MODEL"

echo; echo "=== [$(date +%H:%M:%S)] compute_vector.py   (CPU, seconds)"
"$VA_PY" compute_vector.py

NPY=$(ls "$VA_DIR"/data/value_axis.npy 2>/dev/null || true)
AUROC=$(ls "$VA_DIR"/data/auroc_results.json 2>/dev/null || true)
[ -n "$NPY" ] || { echo "compute_vector.py produced no value_axis.npy — check its output above"; exit 1; }

echo; echo "=== [$(date +%H:%M:%S)] held-out AUROC across the 35 reward functions"
echo "    This is THE gate. It is the paper's own validation, computed on our model."
"$VA_PY" - "$AUROC" <<'PYAUROC'
import json, sys, statistics
p = sys.argv[1] if len(sys.argv) > 1 else ""
if not p:
    print("    (no auroc_results.json found)"); raise SystemExit
def nums(o):
    if isinstance(o, dict):
        for v in o.values(): yield from nums(v)
    elif isinstance(o, list):
        for v in o: yield from nums(v)
    elif isinstance(o, (int, float)) and 0.0 <= o <= 1.0:
        yield float(o)
v = list(nums(json.load(open(p))))
if v:
    print(f"    n={len(v)}  min {min(v):.3f}  median {statistics.median(v):.3f}  max {max(v):.3f}")
    print("    >= 0.70 at the best layer: the axis transferred, proceed."
          if max(v) >= 0.70 else
          "    !! nothing reaches 0.70 — the axis may not have transferred. Read data/auroc_results.json\n"
          "       before trusting anything downstream; a read-out on a chance-level direction is noise.")
PYAUROC

echo; echo "=== [$(date +%H:%M:%S)] convert -> vectors/value_axis.pt  (main venv)"
cd "$MAIN_DIR"
"$MAIN_PY" analysis/convert_value_axis.py --npy "$NPY" ${AUROC:+--auroc "$AUROC"} --model "$MODEL"

cat <<EOF

=== DONE ($(date)).

  vector : $MAIN_DIR/vectors/value_axis.pt
  raw    : $NPY

Experiment A — is internal value higher when there is a bet? (~15 min)
  source /workspace/env.sh
  python scripts/08_readout.py --vector vectors/value_axis.pt \\
      --runs qwen3.5-27b_20260823_223518

Read it against a random direction of matched norm before believing any separation: the three
conditions have different prompts and different reasoning, so ANY direction will separate them a
little.
EOF

#!/usr/bin/env bash
# Everything value-axis, sequentially, under one nohup.
#
#   nohup bash scripts/run_valueaxis_all.sh > /workspace/logs/va_$(date +%m%d_%H%M).log 2>&1 &
#   tail -f /workspace/logs/va_*.log
#
#   1. per-token projections + backtracking events   value-axis venv, no vLLM   ~10 min
#   2. repair vLLM so steering can run               main venv                  ~5 min
#   3. calibrate alpha against the residual norm     value-axis venv            ~3 min
#   4. steering sweep                                main venv, vLLM            ~1.5 h
#
# Steps are independent: if vLLM cannot be repaired, step 1 still lands and only steering is skipped.
#
# Env: PER_COND (20), STEER_LAYER (32), PCTS ("10,20"), COUNT (100), RUN, SKIP_PERTOKEN, SKIP_STEER.
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"; cd "$ROOT"
set -a; [ -f .env ] && source .env; set +a
VA_PY=${VA_PY:-/workspace/value-axis/.venv/bin/python}
MAIN_PY=${MAIN_PY:-/workspace/venv/bin/python}
export HF_HOME=${HF_HOME:-/workspace/hf}
export VLLM_WORKER_MULTIPROC_METHOD=spawn
export VLLM_USE_FLASHINFER_SAMPLER=${VLLM_USE_FLASHINFER_SAMPLER:-0}
RUN=${RUN:-qwen3.5-27b_20260823_223518}
PER_COND=${PER_COND:-20}
STEER_LAYER=${STEER_LAYER:-32}
PCTS=${PCTS:-10,20}
COUNT=${COUNT:-100}
CAL=/workspace/logs/steer_alpha.json

step () { echo; echo "############################################################"; \
          echo "### [$(date +%H:%M:%S)] $*"; echo "############################################################"; }

# ---------------------------------------------------------------- 1. per-token
if [ "${SKIP_PERTOKEN:-0}" != "1" ]; then
  step "1/4  per-token projections + backtracking events  (~10 min)"
  "$VA_PY" scripts/08c_pertoken_hf.py --vectors vectors/value_axis.pt vectors/random_control.pt \
      --run "$RUN" --per-cond "$PER_COND" || echo "!!! per-token step FAILED — continuing"
fi

# ---------------------------------------------------------------- 2. vLLM
step "2/4  repair vLLM (steering needs it; the read-out above did not)"
PY="$MAIN_PY" bash scripts/fix_vllm.sh
VLLM_OK=$?

# ---------------------------------------------------------------- 3. calibrate
step "3/4  calibrate alpha at layer $STEER_LAYER against the residual-stream norm"
"$VA_PY" scripts/calibrate_steer_alpha.py --vector vectors/value_axis.pt --run "$RUN" \
    --layer "$STEER_LAYER" --pcts "5,10,20,40" -o "$CAL" || echo "!!! calibration FAILED"

# ---------------------------------------------------------------- 4. steering
if [ "${SKIP_STEER:-0}" = "1" ] || [ "$VLLM_OK" -ne 0 ] || [ ! -f "$CAL" ]; then
  step "4/4  steering SKIPPED (vllm_ok=$VLLM_OK, calibration $([ -f "$CAL" ] && echo present || echo missing))"
else
  REF=$(ls -d "$ROOT"/data/runs/qwen3.5-27b_2* | head -1)
  for PCT in ${PCTS//,/ }; do
    for SIGN in -1 1; do
      A=$("$MAIN_PY" -c "import json,sys; d=json.load(open('$CAL'));
print(f\"{$SIGN*d['alpha_by_pct'][str(float($PCT))]:.4f}\")" 2>/dev/null) || continue
      step "4/4  steering value_axis  layer $STEER_LAYER  ${SIGN}${PCT}% of ||h||  (alpha=$A)"
      STEER_VECTOR=vectors/value_axis.pt STEER_LAYERS="$STEER_LAYER" STEER_ALPHA="$A" \
      VARIANTS="default" REF_RUN="$REF" COUNT="$COUNT" \
        bash scripts/run_variants.sh || echo "!!! steering run FAILED at ${SIGN}${PCT}% — continuing"
    done
  done
  # degradation control: a random direction at the strongest setting. If bias moves here too, the
  # value-axis result is generic disruption rather than anything about value.
  BIG=$(echo "$PCTS" | tr ',' '\n' | sort -n | tail -1)
  A=$("$MAIN_PY" -c "import json; d=json.load(open('$CAL')); print(f\"{-d['alpha_by_pct'][str(float($BIG))]:.4f}\")" 2>/dev/null)
  if [ -n "$A" ]; then
    step "4/4  steering random_control  layer $STEER_LAYER  -${BIG}%  (alpha=$A)  [degradation control]"
    STEER_VECTOR=vectors/random_control.pt STEER_LAYERS="$STEER_LAYER" STEER_ALPHA="$A" \
    VARIANTS="default" REF_RUN="$REF" COUNT="$COUNT" \
      bash scripts/run_variants.sh || echo "!!! control run FAILED"
  fi
fi

step "DONE ($(date))"
echo "outputs:"
ls -d "$ROOT"/data/runs/*steer* 2>/dev/null || echo "  (no steered runs)"
ls "$ROOT"/data/runs/"$RUN"/analysis/pertoken/*.npz 2>/dev/null | wc -l | xargs echo "  per-token files:"
echo
echo "push:"
echo "  git add -f data/runs/$RUN/analysis/pertoken/*.npz && RAW=1 bash scripts/push_results.sh \$(ls -d data/runs/*steer* | xargs -n1 basename)"

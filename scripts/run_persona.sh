#!/usr/bin/env bash
# Persona vector end to end: extract, validate, score our rollouts, then steer with it.
#
#   TRAIT=sycophantic nohup bash scripts/run_persona.sh > /workspace/logs/persona.log 2>&1 &
#
# Env: TRAIT (sycophantic), PCT (10 — steering strength as a % of the residual-stream norm),
#      COUNT (100 rollouts per condition per steering arm), SKIP_STEER=1 to stop after scoring.
#
# Four steps, each usable on its own if a later one fails:
#   1  extract + validate the vector on held-out questions      transformers, ~30 min
#   2  score every token of 100 rollouts per condition          transformers, ~15 min
#   3  calibrate alpha against the residual norm                transformers, ~3 min
#   4  steer at +/-PCT and measure the bias                     vLLM, ~1.5 h
#
# Step 4 is the one that can answer the causal question, and it only means something if step 1's
# held-out AUROC is high — a direction that does not separate the responses it was fitted to
# generalise over is not worth steering with.
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"; cd "$ROOT"
set -a; [ -f .env ] && source .env; set +a
: "${ANTHROPIC_API_KEY:?ANTHROPIC_API_KEY missing — put it in $ROOT/.env}"

TRAIT=${TRAIT:-sycophantic}
RUN=${RUN:-qwen3.5-27b_20260823_223518}
PCT=${PCT:-10}
COUNT=${COUNT:-100}
VEC="$ROOT/vectors/persona_${TRAIT}.pt"
CAL="/workspace/logs/persona_${TRAIT}_alpha.json"
export VLLM_WORKER_MULTIPROC_METHOD=spawn
export VLLM_ALLOW_INSECURE_SERIALIZATION=${VLLM_ALLOW_INSECURE_SERIALIZATION:-1}
export VLLM_USE_FLASHINFER_SAMPLER=${VLLM_USE_FLASHINFER_SAMPLER:-0}

step () { echo; echo "############################################################"; \
          echo "### [$(date +%H:%M:%S)] $*"; echo "############################################################"; }

step "1/4  fetch data and extract the ${TRAIT} vector"
bash scripts/setup_persona_data.sh "$TRAIT"
python scripts/18_persona_vector.py --trait "$TRAIT" --run "$RUN" || { echo "!!! extraction FAILED"; exit 1; }
LAYER=$(python -c "import torch;print(torch.load('$VEC',map_location='cpu',weights_only=False)['layer'])")
AUROC=$(python -c "import torch;print(f\"{torch.load('$VEC',map_location='cpu',weights_only=False)['auroc_heldout']:.3f}\")")
echo "vector at layer $LAYER, held-out AUROC $AUROC"

step "2/4  score every token of $COUNT rollouts per condition"
python scripts/14_deception_scores.py --run "$RUN" --probe "$VEC" \
    --conditions baseline above_good below_good --n "$COUNT" --max-len 16000 \
    || echo "!!! scoring FAILED — continuing"

if [ "${SKIP_STEER:-0}" = "1" ]; then step "stopping before steering (SKIP_STEER=1)"; exit 0; fi

step "3/4  calibrate alpha at layer $LAYER"
python scripts/calibrate_steer_alpha.py --vector "$VEC" --run "$RUN" --layer "$LAYER" \
    --pcts "$PCT" -o "$CAL" || { echo "!!! calibration FAILED"; exit 1; }

step "4/4  steer at +/-${PCT}% of the residual-stream norm"
REF=$(ls -d "$ROOT"/data/runs/qwen3.5-27b_2* | head -1)
for SIGN in -1 1; do
  A=$(python -c "import json;d=json.load(open('$CAL'));print(f\"{$SIGN*d['alpha_by_pct'][str(float($PCT))]:.4f}\")") || continue
  LBL=$([ "$SIGN" -lt 0 ] && echo "-${PCT}" || echo "+${PCT}")
  step "4/4  ${TRAIT} ${LBL}% of ||h||  (alpha=$A)"
  STEER_VECTOR="$VEC" STEER_LAYERS="$LAYER" STEER_ALPHA="$A" \
  VARIANTS="default" REF_RUN="$REF" COUNT="$COUNT" \
    bash scripts/run_variants.sh || echo "!!! steering FAILED at ${LBL}% — continuing"
done

step "DONE ($(date))"
echo "push:  RAW=1 bash scripts/push_results.sh \$(ls -d data/runs/*persona_${TRAIT}* 2>/dev/null | xargs -n1 basename)"
echo "       git add -f vectors/persona_${TRAIT}.pt data/persona/${TRAIT}_scored.json"
echo "       git add -f data/runs/$RUN/analysis/deception/all_scores.npz"

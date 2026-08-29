#!/usr/bin/env bash
# Per-token value-axis projections, in the value-axis venv (no vLLM).
#   nohup bash scripts/run_pertoken.sh > /workspace/logs/pertoken_$(date +%m%d_%H%M).log 2>&1 &
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"; cd "$ROOT"
VA_PY=${VA_PY:-/workspace/value-axis/.venv/bin/python}
export HF_HOME=${HF_HOME:-/workspace/hf}
VECTORS=${VECTORS:-"vectors/value_axis.pt vectors/random_control.pt"}
RUN=${RUN:-qwen3.5-27b_20260823_223518}
PER_COND=${PER_COND:-20}
[ -x "$VA_PY" ] || { echo "no value-axis venv at $VA_PY"; exit 1; }
"$VA_PY" -c "import torch; torch.zeros(1).cuda(); print('[preflight]', torch.__version__, 'ok')"
"$VA_PY" scripts/08c_pertoken_hf.py --vectors $VECTORS --run "$RUN" --per-cond "$PER_COND" ${LAYERS:+--layers "$LAYERS"}
echo; echo "=== DONE ($(date))"
echo "push:  git add -f data/runs/$RUN/analysis/pertoken/*.npz && git commit -m 'per-token projections' && git push"

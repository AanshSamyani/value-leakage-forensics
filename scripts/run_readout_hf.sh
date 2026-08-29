#!/usr/bin/env bash
# Value-axis read-out with plain transformers, in the value-axis venv (no vLLM).
#   nohup bash scripts/run_readout_hf.sh > /workspace/logs/readout_$(date +%m%d_%H%M).log 2>&1 &
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"; cd "$ROOT"
VA_PY=${VA_PY:-/workspace/value-axis/.venv/bin/python}
export HF_HOME=${HF_HOME:-/workspace/hf}
VECTORS=${VECTORS:-"vectors/value_axis.pt vectors/random_control.pt"}
RUNS=${RUNS:-qwen3.5-27b_20260823_223518}
[ -x "$VA_PY" ] || { echo "no value-axis venv at $VA_PY"; exit 1; }
"$VA_PY" -c "import torch; assert torch.cuda.is_available(); torch.zeros(1).cuda(); \
print('[preflight] torch', torch.__version__, 'on', torch.cuda.get_device_properties(0).name, '- ok')"
echo "=== readout (transformers)  $VECTORS  <-  $RUNS   ($(date))"
"$VA_PY" scripts/08b_readout_hf.py --vectors $VECTORS --runs $RUNS ${LAYERS:+--layers "$LAYERS"} ${LIMIT:+--limit "$LIMIT"}
echo; echo "=== DONE ($(date))"
echo "push:  git add -f data/runs/*/analysis/readout_hf.csv && git commit -m 'value axis readout' && git push"

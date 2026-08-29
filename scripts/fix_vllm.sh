#!/usr/bin/env bash
# Find a vLLM build that imports against the torch currently installed.
#
# vLLM's version number does not encode its CUDA variant, and its wheels are published for one CUDA
# per release. After the pod moved from a CUDA-13 host to a 12.8 one, torch was rebuilt as cu129 but
# vllm 0.28.0 ships a cu130-only extension — "ImportError: libcudart.so.13". --torch-backend only
# steers torch's index, not vLLM's own compiled extension, so the fix is to walk back releases until
# one imports.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"; cd "$ROOT"
PY=${PY:-python}
if $PY -c "import vllm" >/dev/null 2>&1; then
  echo "vllm already imports: $($PY -c 'import vllm; print(vllm.__version__)')"; exit 0
fi
echo "vllm does not import against the installed torch — walking back releases"
$PY -c "import torch; print('  torch', torch.__version__, 'cuda', torch.version.cuda)"
for V in ${VLLM_VERSIONS:-"0.27.1 0.27.0 0.26.2 0.25.1"}; do
  echo; echo "=== trying vllm==$V"
  if ! uv pip install --reinstall --torch-backend=auto "vllm==$V" >/tmp/vllm_$V.log 2>&1; then
    echo "  install failed (tail of log):"; tail -4 /tmp/vllm_$V.log; continue
  fi
  if $PY -c "import vllm; print('  imports ok:', vllm.__version__)" 2>/dev/null; then
    $PY -c "import torch; assert torch.cuda.is_available(); torch.zeros(1).cuda(); print('  cuda ok')"
    echo "=== vllm $V works"; exit 0
  fi
  echo "  installed but does not import"
done
echo; echo "!!! no vllm release imported. Steering needs vLLM (HF generation of 1,500 rollouts is ~18h)."
echo "    The per-token read-out does not — it runs in the value-axis venv and is unaffected."
exit 1

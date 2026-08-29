#!/usr/bin/env bash
# One-time setup for the value axis (nickjiang2378/value-axis) on a RunPod pod.
#
#   bash /workspace/value-leakage-forensics/scripts/setup_value_axis.sh
#
# Deliberately SEPARATE from the main environment. The value-axis repo pins its own dependency set,
# and installing it into /workspace/venv could break vLLM — which the rest of the project depends on.
# So it gets its own venv at /workspace/value-axis/.venv and the two never meet: the only thing that
# crosses over is a .npy file.
#
# What IS shared is HF_HOME=/workspace/hf, so Qwen3.5-27B is read from the cache the vLLM runs already
# populated rather than re-downloading ~54 GB.
#
# Everything lives under /workspace, the only volume that survives a pod restart. Your existing
# /workspace/env.sh is left untouched; this writes its own /workspace/env-value-axis.sh.
set -euo pipefail

export WORKSPACE=/workspace
export HF_HOME=${HF_HOME:-$WORKSPACE/hf}                 # shared with the main env — do not change
export PIP_CACHE_DIR=${PIP_CACHE_DIR:-$WORKSPACE/.cache/pip}
export XDG_CACHE_HOME=${XDG_CACHE_HOME:-$WORKSPACE/.cache}
mkdir -p "$HF_HOME" "$PIP_CACHE_DIR" "$XDG_CACHE_HOME" "$WORKSPACE/logs"

VA_DIR=$WORKSPACE/value-axis
VA_VENV=$VA_DIR/.venv
REPO_URL=${VA_REPO_URL:-https://github.com/nickjiang2378/value-axis.git}

echo "=== 1/4  repo -> $VA_DIR"
if [ ! -d "$VA_DIR/.git" ]; then
  git clone "$REPO_URL" "$VA_DIR"
else
  (cd "$VA_DIR" && git pull --ff-only || echo "  (local changes — skipping pull)")
fi

echo "=== 2/4  isolated venv -> $VA_VENV"
command -v uv >/dev/null 2>&1 || python3 -m pip install --user -U uv
cd "$VA_DIR"
# Their lockfile first, so we get the versions their code was written against...
if [ -f uv.lock ] || [ -f pyproject.toml ]; then
  uv sync || { echo "  uv sync failed — falling back to a hand-built env"; rm -rf "$VA_VENV"; }
fi
[ -x "$VA_VENV/bin/python" ] || uv venv "$VA_VENV"
PY="$VA_VENV/bin/python"

# ...then force a torch build matched to THIS pod's driver. /workspace outlives the pod, so a torch
# pinned by the lockfile can easily be wrong for the next host's CUDA version.
uv pip install --python "$PY" -U --torch-backend=auto torch
uv pip install --python "$PY" -U transformers accelerate numpy tqdm huggingface_hub safetensors

# torchvision has to be reinstalled AGAINST the torch we just installed. uv sync pins it from the
# lockfile, and once torch is upgraded underneath it its compiled ops stop binding —
# "RuntimeError: operator torchvision::nms does not exist". transformers 5.x imports torchvision
# unconditionally from image_utils, so that failure takes the whole model-class import chain with it
# and surfaces as the useless "Could not import module 'Qwen3_5ForCausalLM'".
# Its version number does not change across CUDA variants, so -U is a no-op; --reinstall is required.
# torchaudio is never needed here and a stale CUDA build of it breaks the same import path.
uv pip install --python "$PY" --reinstall --torch-backend=auto torchvision
uv pip uninstall --python "$PY" torchaudio >/dev/null 2>&1 || true

echo "=== 3/4  sanity check"
# Exercises the exact import chain extract_activations.py needs. `import transformers` alone passes
# even when torchvision is broken, because the model classes are lazy — the failure only appears at
# AutoModelForCausalLM.from_pretrained, 15 minutes into a run.
MODEL_CHECK=${MODEL:-Qwen/Qwen3.5-27B} "$PY" - <<'PYCHECK'
import os, torch, transformers
print(f"  torch {torch.__version__} (cuda {torch.version.cuda})  transformers {transformers.__version__}")
if not torch.cuda.is_available():
    raise SystemExit("  torch cannot see the GPU — rerun this script or pick a pod with a newer driver")
p = torch.cuda.get_device_properties(0)
print(f"  {p.name}, {p.total_memory/1e9:.0f} GB")
try:
    import torchvision  # noqa: F401
    torch.ops.torchvision.nms
except Exception as e:
    raise SystemExit(f"  torchvision is not bound to this torch ({type(e).__name__}: {e})\n"
                     f"  fix: uv pip install --python $VA_VENV/bin/python --reinstall "
                     f"--torch-backend=auto torchvision")
import transformers.image_utils  # the import that dies when torchvision is stale
from transformers import AutoConfig
m = os.environ["MODEL_CHECK"]
cfg = AutoConfig.from_pretrained(m)
print(f"  {m}: {cfg.model_type}, {cfg.num_hidden_layers} layers, hidden {cfg.hidden_size} — import chain ok")
PYCHECK

echo "=== 4/4  env file"
cat > "$WORKSPACE/env-value-axis.sh" <<EOF
# value-axis only. Source this INSTEAD of /workspace/env.sh, never both — they activate
# different venvs and the second one wins silently.
export HF_HOME=$HF_HOME
export PIP_CACHE_DIR=$PIP_CACHE_DIR
export XDG_CACHE_HOME=$XDG_CACHE_HOME
source $VA_VENV/bin/activate
cd $VA_DIR
EOF

cat <<EOF

Setup done. The main environment is untouched.

  value-axis venv : $VA_VENV
  activate        : source /workspace/env-value-axis.sh
  back to main    : source /workspace/env.sh

Next — build the axis for Qwen3.5-27B (~15-25 min):
  bash /workspace/value-leakage-forensics/scripts/run_value_axis.sh

That runs extract_activations + compute_vector, prints the held-out AUROC, and converts the result
into vectors/value_axis.pt for the main environment. Read the AUROC before going any further: it is
the paper's own validation computed on OUR model, and if it sits near 0.5 the axis did not transfer
and the read-out would be measuring noise.
EOF

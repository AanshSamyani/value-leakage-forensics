#!/usr/bin/env bash
# One-time setup on a RunPod pod. Everything goes under /workspace (the only persistent volume).
# Usage:  bash scripts/runpod_setup.sh            (run from anywhere; re-running is safe)
set -euo pipefail

export WORKSPACE=/workspace
export HF_HOME=$WORKSPACE/hf                      # model weights + tokenizers cache
export PIP_CACHE_DIR=$WORKSPACE/.cache/pip
export XDG_CACHE_HOME=$WORKSPACE/.cache
mkdir -p "$HF_HOME" "$PIP_CACHE_DIR" "$WORKSPACE/.cache"

REPO_URL=${REPO_URL:-https://github.com/AanshSamyani/value-leakage-forensics.git}
REPO_DIR=$WORKSPACE/value-leakage-forensics
VENV=$WORKSPACE/venv

# 1) repo
if [ ! -d "$REPO_DIR/.git" ]; then
  git clone "$REPO_URL" "$REPO_DIR"
else
  (cd "$REPO_DIR" && git pull --ff-only)
fi

# 2) python env (persistent)
if [ ! -x "$VENV/bin/python" ]; then
  python3 -m venv "$VENV"
fi
source "$VENV/bin/activate"
python -m pip install -U pip wheel uv
pip install -e "$REPO_DIR"                 # anthropic, openai, numpy, pandas, scipy, matplotlib, tqdm, dotenv
# vLLM + torch matched to THIS pod's NVIDIA driver (avoids "driver too old" when /workspace
# outlives the pod and the next host has a different CUDA version):
uv pip install -U --torch-backend=auto vllm
# torchaudio is never needed (transformers skips audio when absent) and a stale CUDA variant of it
# breaks transformers' import; torchvision IS used by the Qwen-VL processor and its version number
# does not change across CUDA variants, so -U is a no-op — force the matching build every time:
pip uninstall -y torchaudio >/dev/null 2>&1 || true
uv pip install --reinstall --torch-backend=auto torchvision
pip install -U "huggingface_hub[cli]"
python - <<'PYCHECK'
import torch, torchvision
ok = torch.cuda.is_available()
print(f"torch {torch.__version__} (cuda {torch.version.cuda}) | torchvision {torchvision.__version__} — cuda available: {ok}")
if not ok:
    raise SystemExit("torch cannot see the GPU: driver/build mismatch — rerun this script or pick a pod with a newer CUDA driver")
import vllm
print(f"vllm {vllm.__version__} import ok")
PYCHECK

# 3) data: Aditya's 10 runs (optional; FETCH_ADITYA=1 to include)
if [ "${FETCH_ADITYA:-0}" = "1" ]; then bash "$REPO_DIR/scripts/fetch_aditya_runs.sh"; fi
mkdir -p "$REPO_DIR/data/runs" /workspace/logs

# 4) persistent env vars for every new shell
BASHRC_SNIPPET='# --- value-leakage-forensics ---
export HF_HOME=/workspace/hf
export PIP_CACHE_DIR=/workspace/.cache/pip
export XDG_CACHE_HOME=/workspace/.cache
export VLLM_BASE_URL=http://localhost:8000/v1
export VLLM_API_KEY=EMPTY
source /workspace/venv/bin/activate
cd /workspace/value-leakage-forensics
set -a; [ -f .env ] && source .env; set +a
# --- end ---'
grep -q "value-leakage-forensics ---" ~/.bashrc 2>/dev/null || echo "$BASHRC_SNIPPET" >> ~/.bashrc
# RunPod pods are often recreated from the image: keep a copy of the snippet in /workspace too
echo "$BASHRC_SNIPPET" > $WORKSPACE/env.sh

echo
echo "Setup done. Next:"
echo "  1) create $REPO_DIR/.env with ANTHROPIC_API_KEY=...   (cp .env.example .env)"
echo "  2) source /workspace/env.sh   (or open a new shell)"
echo "  3) nohup bash scripts/run_pipeline.sh Qwen/Qwen3.6-27B 100 > /workspace/logs/pipeline_qwen36.log 2>&1 &"
echo "     (no server needed: the pipeline loads the model in-process; SAMPLER=vllm uses scripts/serve_vllm.sh instead)"

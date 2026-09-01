#!/usr/bin/env bash
# Fetch the J-lens / R-lens pair for our model (~6.6 GB) into /workspace.
#
#   bash scripts/setup_jlens.sh
#
# The pair is recipe-matched: same target layer, same skip_first, same 25 Pile prompts, and the
# forward values are bit-identical — only the backward graph differs (RelP/LRP rules for R). So J
# and R are directly comparable on one forward pass, and their disagreement localises where the
# early-layer gradient noise is.
set -euo pipefail
DEST=${DEST:-/workspace/lenses}
REPO=camilablank/workspace-lenses
MODEL=${MODEL_DIR:-qwen3.5-27b}
mkdir -p "$DEST"
python - "$REPO" "$MODEL" "$DEST" <<'PY'
import sys
from huggingface_hub import hf_hub_download
repo, model, dest = sys.argv[1:4]
for arm in ("j-lens", "r-lens"):
    p = hf_hub_download(repo_id=repo, filename=f"{model}/{arm}/lens.pt",
                        local_dir=dest, resume_download=True)
    print(f"  {arm}: {p}")
PY
echo
echo "Structure check (does not need the model):"
python - "$DEST/$MODEL" <<'PY'
import sys, torch
from pathlib import Path
for arm in ("j-lens", "r-lens"):
    f = Path(sys.argv[1]) / arm / "lens.pt"
    d = torch.load(f, map_location="cpu", weights_only=False)
    J = d["J"]                     # {layer: [d, d]} — a dict, not a stacked tensor
    ks = sorted(J)
    v = J[ks[0]]
    print(f"\n{arm}: keys={list(d)}")
    print(f"  J: {len(ks)} layers {ks[0]}..{ks[-1]}, each {tuple(v.shape)} {v.dtype}   "
          f"d_model={d['d_model']}   n_prompts={d['n_prompts']}")
    sl = d["source_layers"]
    print(f"  source_layers: {len(sl)} entries, {min(sl)}..{max(sl)}")
    pr = d.get("provenance", {})
    print(f"  provenance: " + ", ".join(f"{k}={pr[k]}" for k in
          ("model_id", "target_layer", "skip_first", "dataset_id") if k in pr))
    # the anchor row for target_layer must be the identity; if it is not, our indexing is wrong
    tl = pr.get("target_layer")
    if tl is not None and tl in J:
        A = J[tl].float()
        print(f"  anchor row (layer {tl}) vs I: max|J-I| = {(A - torch.eye(A.shape[0])).abs().max():.4f}"
              "   <- should be ~0")
PY

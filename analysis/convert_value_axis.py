"""Convert the value-axis repo's value_axis.npy into our vectors/*.pt schema.

    python analysis/convert_value_axis.py --npy /workspace/value-axis/data/value_axis.npy \
        --auroc /workspace/value-axis/data/auroc_results.json --model Qwen/Qwen3.5-27B

Run from the MAIN environment (it needs torch, which both venvs have, and forensics.steering).

Layer indexing — the off-by-one that would silently ruin the read-out:
  extract_activations.py captures `output_hidden_states=True`, so its array has n_layers+1 entries:
  index 0 is the embedding output and index j>=1 is the output of decoder layer j-1.
  forensics/steering/hooks.py registers a forward hook on decoder layer li and reads
  hidden_states+residual, i.e. the stream AFTER layer li — which is HF's hidden_states[li+1].
  So their index j maps to our layer j-1, and their index 0 (embeddings) has no hook equivalent
  and is dropped.

recommended_layers comes from their own held-out AUROC when auroc_results.json is present, which is a
far better basis than our depth-band heuristic — it is measured on this model rather than assumed.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]


def per_layer_auroc(path: Path | None, n: int) -> dict[int, float] | None:
    """Pull a per-layer AUROC out of their results file, whatever shape it takes.

    compute_vector.py prints AUC, a standard deviation and a "correct direction" fraction per layer,
    so a naive walk over every float in [0,1] scoops up all three and reports nonsense. This looks
    for the AUC specifically: numeric-keyed maps of scalars, maps of per-layer dicts carrying an
    auc/auroc field, and parallel lists.
    """
    if not path or not path.exists():
        return None
    blob = json.loads(path.read_text())
    AUC_KEYS = ("auc", "auroc", "auc_mean", "mean_auc", "test_auc", "held_out_auc")

    def as_layer_key(k):
        t = str(k).lower().replace("layer", "").strip(" _-")
        return int(t) if t.isdigit() else None

    def walk(o):
        if isinstance(o, dict):
            # {"0": 0.938, ...} or {"layer_0": {...}, ...}
            keyed = {as_layer_key(k): v for k, v in o.items() if as_layer_key(k) is not None}
            if len(keyed) >= max(3, n // 4):
                if all(isinstance(v, (int, float)) for v in keyed.values()):
                    return {k: float(v) for k, v in keyed.items()}
                if all(isinstance(v, dict) for v in keyed.values()):
                    for ak in AUC_KEYS:
                        if all(ak in v for v in keyed.values()):
                            return {k: float(v[ak]) for k, v in keyed.items()}
            # parallel lists: {"layers": [...], "auc": [...]}
            for ak in AUC_KEYS:
                if isinstance(o.get(ak), list) and len(o[ak]) in (n, n - 1):
                    lay = o.get("layers") or o.get("layer") or list(range(len(o[ak])))
                    return {int(l): float(v) for l, v in zip(lay, o[ak])}
            for v in o.values():
                r = walk(v)
                if r:
                    return r
        elif isinstance(o, list):
            if len(o) in (n, n - 1) and all(isinstance(v, (int, float)) for v in o):
                return {i: float(v) for i, v in enumerate(o)}
            if o and all(isinstance(v, dict) for v in o):
                for ak in AUC_KEYS:
                    if all(ak in v for v in o):
                        return {int(v.get("layer", i)): float(v[ak]) for i, v in enumerate(o)}
        return None

    return walk(blob)


def pick_layers(auroc: dict[int, float], n_layers: int, tol: float = 0.005) -> list[int]:
    """Middle of the top plateau, not its first member.

    On this model layers 17-50 all score 1.000, so "best layer" is whichever happens to come first.
    Sitting in the middle of the plateau is more robust to the exact boundary than sitting on its edge.
    """
    best = max(auroc.values())
    plateau = sorted(li for li, v in auroc.items() if v >= best - tol and 0 <= li < n_layers)
    if not plateau:
        return sorted(auroc, key=lambda li: -auroc[li])[:3]
    mid = plateau[len(plateau) // 2]
    flank = [plateau[len(plateau) // 3], plateau[2 * len(plateau) // 3]]
    return list(dict.fromkeys([mid] + flank))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--npy", default="/workspace/value-axis/data/value_axis.npy")
    ap.add_argument("--auroc", default="/workspace/value-axis/data/auroc_results.json")
    ap.add_argument("--model", default="Qwen/Qwen3.5-27B")
    ap.add_argument("-o", "--out", default=str(ROOT / "vectors" / "value_axis.pt"))
    a = ap.parse_args()

    arr = np.load(a.npy)
    if arr.ndim != 2:
        raise SystemExit(f"expected a 2-D (layers, hidden) array, got {arr.shape}")
    n_hf, hidden = arr.shape
    n_layers = n_hf - 1                       # drop the embedding row
    print(f"loaded {a.npy}: {arr.shape}  ->  {n_layers} decoder layers, hidden {hidden}")

    vectors, norms = {}, {}
    for li in range(n_layers):
        v = torch.tensor(arr[li + 1], dtype=torch.float32)   # their j -> our j-1
        vectors[li], norms[li] = v, float(v.norm())

    au = per_layer_auroc(Path(a.auroc), n_hf)
    stats = {}
    if au:
        # their AUROC is indexed like their array; shift it onto our layer numbering too
        shifted = {j - 1: v for j, v in au.items() if 1 <= j <= n_layers}
        for li in range(n_layers):
            stats[li] = {"auroc": shifted.get(li), "pair_acc": shifted.get(li), "d_prime": float("nan"),
                         "train_stats": {"d_prime": float("nan")}}
        rec = pick_layers(shifted, n_layers)
        best = max(shifted.values())
        plateau = sorted(li for li, v in shifted.items() if v >= best - 0.005)
        print(f"held-out AUROC (their validation, on this model): best {best:.3f}; "
              f"median across layers {np.median(list(shifted.values())):.3f}")
        print(f"  plateau at >= {best - 0.005:.3f}: layers {plateau[0]}-{plateau[-1]} "
              f"({len(plateau)} layers) -> taking the middle: {rec}")
        if best < 0.60:
            print("  !! best AUROC below 0.60 — the axis may not have transferred to this model. "
                  "Treat any read-out built on it with suspicion.")
    else:
        for li in range(n_layers):
            stats[li] = {"pair_acc": float("nan"), "d_prime": float("nan"),
                         "train_stats": {"d_prime": float("nan")}}
        lo, hi = int(0.25 * n_layers), int(0.70 * n_layers)
        rec = [lo + (hi - lo) // 2, lo + (hi - lo) // 3, lo + 2 * (hi - lo) // 3]
        print(f"no per-layer AUROC found in {a.auroc} — falling back to the 25-70% depth band: {rec}")

    blob = {"kind": "value_axis", "model": a.model, "n_layers": n_layers, "hidden": hidden,
            "layers": list(range(n_layers)), "vectors": vectors, "norms": norms, "stats": stats,
            "recommended_layers": rec, "n_train": None, "n_test": None,
            "meta": {"source": "nickjiang2378/value-axis", "paper": "arXiv:2606.17056",
                     "npy": str(a.npy),
                     "layer_mapping": "their hidden_states[j] -> our decoder layer j-1; embeddings dropped",
                     "sign": "+ = higher internal value (model believes its trajectory is succeeding)"}}
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    torch.save(blob, out)
    print(f"wrote {out}   recommended_layers={rec}")
    print(f"\nnext:  python scripts/08_readout.py --vector {out} \\\n"
          f"         --runs qwen3.5-27b_20260823_223518")


if __name__ == "__main__":
    main()

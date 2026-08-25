"""Vector files + mean-difference construction + held-out validation (driver side, no vLLM here).

A vector file (torch.save) holds:
  kind, model, n_layers, hidden, layers (all layers captured), vectors {layer: float32 tensor[hidden]},
  norms {layer: float}, stats {layer: {"pair_acc": ..., "d_prime": ...}}, recommended_layers, meta.
Convention: vector = mean(positive) - mean(negative), so +alpha steers TOWARD the positive class
(sycophancy: sycophantic answers; eval_awareness: 'evaluation' framing).
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import torch


def mean_diff(pos: np.ndarray, neg: np.ndarray) -> np.ndarray:
    return pos.mean(0) - neg.mean(0)


def pair_stats(v: np.ndarray, pos: np.ndarray, neg: np.ndarray) -> dict:
    """Held-out separation: fraction of pairs with (pos - neg) . v > 0, and d' of the projections."""
    u = v / (np.linalg.norm(v) + 1e-8)
    pp, pn = pos @ u, neg @ u
    n = min(len(pp), len(pn))
    pair_acc = float(np.mean((pp[:n] - pn[:n]) > 0)) if n else float("nan")
    pooled = np.sqrt(0.5 * (pp.var(ddof=1) + pn.var(ddof=1))) + 1e-8
    return {"pair_acc": pair_acc, "d_prime": float((pp.mean() - pn.mean()) / pooled),
            "proj_pos_mean": float(pp.mean()), "proj_neg_mean": float(pn.mean()), "n_pairs": int(n)}


def build(kind: str, model: str, acts_pos: dict[int, np.ndarray], acts_neg: dict[int, np.ndarray],
          n_train: int, meta: dict | None = None) -> dict:
    """acts_*[layer] = array [n_items, hidden] in the same item order for pos and neg (paired)."""
    layers = sorted(acts_pos)
    vectors, norms, stats = {}, {}, {}
    for li in layers:
        P, N = acts_pos[li], acts_neg[li]
        v = mean_diff(P[:n_train], N[:n_train])
        vectors[li] = torch.tensor(v, dtype=torch.float32)
        norms[li] = float(np.linalg.norm(v))
        stats[li] = pair_stats(v, P[n_train:], N[n_train:]) if len(P) > n_train else pair_stats(v, P, N)
        stats[li]["train_stats"] = pair_stats(v, P[:n_train], N[:n_train])
    n_layers = (meta or {}).get("n_layers") or (max(layers) + 1)
    # recommend: best held-out d' among layers in the 25%-70% depth band (early layers are noisy,
    # late layers are near the unembedding)
    band = [li for li in layers if 0.25 * n_layers <= li <= 0.70 * n_layers]
    ranked = sorted(band or layers, key=lambda li: -stats[li]["d_prime"])
    return {"kind": kind, "model": model, "n_layers": n_layers, "hidden": int(vectors[layers[0]].shape[0]),
            "layers": layers, "vectors": vectors, "norms": norms, "stats": stats,
            "recommended_layers": ranked[:3], "n_train": n_train,
            "n_test": int(len(acts_pos[layers[0]]) - n_train), "meta": meta or {}}


def save(blob: dict, path: str | Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(blob, path)
    return path


def load(path: str | Path) -> dict:
    return torch.load(path, map_location="cpu")


def report(blob: dict) -> str:
    lines = [f"# {blob['kind']} vector — {blob['model']}  (train pairs={blob['n_train']}, held-out={blob['n_test']})", "",
             "| layer | norm | held-out pair acc | held-out d' | train d' |", "|---|---|---|---|---|"]
    for li in blob["layers"]:
        s = blob["stats"][li]
        lines.append(f"| {li} | {blob['norms'][li]:.1f} | {s['pair_acc']:.2f} | {s['d_prime']:+.2f} | {s['train_stats']['d_prime']:+.2f} |")
    lines += ["", f"recommended layers (best held-out d' in the 25–70% depth band): {blob['recommended_layers']}"]
    return "\n".join(lines)

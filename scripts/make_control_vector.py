"""A random direction matched in per-layer norm to a real vector — the control for any read-out.

    python scripts/make_control_vector.py --like vectors/value_axis.pt -o vectors/random_control.pt

Why it is not optional. The three conditions have different prompts and different reasoning text, so
ANY direction will separate them somewhat. A difference in mean projection is only evidence about the
value axis if it exceeds what an arbitrary direction of the same magnitude produces on the same
rollouts. Matching the per-layer norm keeps the projection scale comparable.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import torch

ROOT = Path(__file__).resolve().parents[1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--like", default=str(ROOT / "vectors" / "value_axis.pt"))
    ap.add_argument("-o", "--out", default=str(ROOT / "vectors" / "random_control.pt"))
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args()

    ref = torch.load(a.like, map_location="cpu")
    g = torch.Generator().manual_seed(a.seed)
    vectors, norms = {}, {}
    for li, v in ref["vectors"].items():
        r = torch.randn(v.shape, generator=g, dtype=torch.float32)
        r = r / r.norm() * v.norm()          # same magnitude, random direction
        vectors[li], norms[li] = r, float(r.norm())

    blob = dict(ref)
    blob.update(kind="random_control", vectors=vectors, norms=norms,
                stats={li: {"pair_acc": float("nan"), "d_prime": float("nan"),
                            "train_stats": {"d_prime": float("nan")}} for li in vectors},
                meta={"source": "random", "seed": a.seed, "norm_matched_to": a.like,
                      "purpose": "null direction for read-out comparisons"})
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    torch.save(blob, a.out)
    cos = {li: float(torch.dot(vectors[li], ref["vectors"][li]) /
                     (vectors[li].norm() * ref["vectors"][li].norm())) for li in list(vectors)[:3]}
    print(f"wrote {a.out}  ({len(vectors)} layers, norms matched to {Path(a.like).name})")
    print(f"  layers {ref['recommended_layers']}, cosine with the real vector: "
          + ", ".join(f"{li}:{c:+.3f}" for li, c in cos.items()) + "  (near zero, as expected)")


if __name__ == "__main__":
    main()

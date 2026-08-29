"""Mean value-axis projection per condition — the read-out half of experiment A.

    python analysis/plot_value_axis_readout.py

Top row is the value axis, bottom row the random control direction, at each of the three layers the
AUROC sweep recommended. Bars are the mean projection over a rollout's reasoning tokens, averaged
over 20 rollouts, drawn RELATIVE to the no-bet condition with a bootstrapped 95% CI on the
difference; the grey band is the baseline's own sampling error. Relative, because the vector's norm
is arbitrary — a bar anchored at zero would be nine units of nothing plus 0.2 of signal.

The random row is not decoration, it is the reason the top row cannot be read on its own. The
incentive prompts differ from the baseline prompt, so their activations differ, and ANY direction
picks some of that up. Each panel is annotated with Cohen's d against baseline, which is the only
way to compare directions whose vectors have different norms — and on that scale the random
direction separates the conditions BETTER (d up to 4.0) than the value axis does (d 0.6-1.3).

Two further cautions the numbers carry:
  * incentive rollouts run ~29% longer than baseline ones (10.6k vs 8.2k tokens), so a mean over all
    tokens confounds condition with length. Restricting to the first 2413 tokens — the shortest
    rollout in the set — does not remove the gap, so length is not the whole story, but the
    length-matched numbers are the ones printed at the end.
  * above-good and below-good sit on top of each other in every panel. The axis tracks whether a bet
    is present, not which side of it pays.
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
PT = ROOT / "data/runs/qwen3.5-27b_20260823_223518/analysis/pertoken"
CONDS = ("baseline", "above_good", "below_good")
COL = {"baseline": "#90A4AE", "above_good": "#c85a00", "below_good": "#1f77b4"}
LAB = {"baseline": "no bet", "above_good": "above-good", "below_good": "below-good"}
rng = np.random.default_rng(0)


def load():
    rows, layers, vecs = {}, None, None
    for f in sorted(PT.glob("*.npz")):
        z = np.load(f, allow_pickle=True)
        layers = [int(x) for x in z["layers"]]
        vecs = [str(x) for x in z["vectors"]]
        rows.setdefault(str(z["cond"]), []).append(z["proj"].astype(np.float32))
    return rows, layers, vecs


def ci(v: np.ndarray, n: int = 100000):
    d = v[rng.integers(0, len(v), (n, len(v)))].mean(1)
    return v.mean(), *np.percentile(d, [2.5, 97.5])


def cohen(x: np.ndarray, b: np.ndarray) -> float:
    return (x.mean() - b.mean()) / np.sqrt((x.var(ddof=1) + b.var(ddof=1)) / 2)


def main() -> None:
    rows, layers, vecs = load()
    nmin = min(min(p.shape[1] for p in v) for v in rows.values())
    order = sorted(range(len(layers)), key=lambda i: layers[i])

    fig, axes = plt.subplots(2, len(layers), figsize=(13.2, 7.0))
    for vi, vn in enumerate(vecs):
        for col, li in enumerate(order):
            ax = axes[vi, col]
            vals = {c: np.array([p[li, :, vi].mean() for p in rows[c]]) for c in CONDS}
            base = vals["baseline"]
            # The vector's norm is arbitrary, so the absolute projection carries no meaning and a
            # bar anchored at zero would be 9 units of nothing plus 0.2 of signal. Everything is
            # drawn relative to the baseline condition, whose own sampling error is the grey band.
            bd = base[rng.integers(0, len(base), (100000, len(base)))].mean(1) - base.mean()
            blo, bhi = np.percentile(bd, [2.5, 97.5])
            ax.axhspan(blo, bhi, color=COL["baseline"], alpha=.30, zorder=1)
            ax.axhline(0, color="#4A4A4A", ls=":", lw=1.1, zorder=2)
            for j, c in enumerate(("above_good", "below_good")):
                x = vals[c]
                dr = (x[rng.integers(0, len(x), (100000, len(x)))].mean(1)
                      - base[rng.integers(0, len(base), (100000, len(base)))].mean(1))
                m, lo, hi = dr.mean(), *np.percentile(dr, [2.5, 97.5])
                ax.bar(j, m, .6, color=COL[c], zorder=3)
                ax.errorbar(j, m, yerr=[[m - lo], [hi - m]], fmt="none", ecolor="#4A4A4A",
                            capsize=4, lw=1.2, zorder=4)
                ax.annotate(f"d={cohen(x, base):+.2f}", (j, hi if m > 0 else lo), ha="center",
                            va="bottom" if m > 0 else "top", fontsize=9, color="#4A4A4A",
                            xytext=(0, 5 if m > 0 else -6), textcoords="offset points")
            ax.set_xticks([-0.6, 0, 1])
            ax.set_xticklabels(["no bet\n(reference)", "above-good", "below-good"], fontsize=9)
            ax.set_xlim(-1.1, 1.55)
            ax.set_title(f"{vn.replace('_', ' ')}  ·  layer {layers[li]}", fontsize=10.5, pad=8)
            ax.text(.985, .04 if vals["above_good"].mean() > base.mean() else .90,
                    f"baseline {base.mean():+.2f}", transform=ax.transAxes, ha="right",
                    fontsize=8.5, color="#8A8177")
            ax.spines[["top", "right"]].set_visible(False)
            ax.grid(axis="y", alpha=.25, lw=.6)
            lo_, hi_ = ax.get_ylim()
            pad = (hi_ - lo_) * .18
            ax.set_ylim(lo_ - pad, hi_ + pad)
            if col == 0:
                ax.set_ylabel("mean projection,\nrelative to the no-bet condition", fontsize=9.5)
    fig.tight_layout()
    out = ROOT / "plots/fig16_value_axis_readout.png"
    fig.savefig(out, dpi=170, bbox_inches="tight")
    print(f"wrote {out}\n")

    print(f"length-matched to the shortest rollout ({nmin} tokens)")
    print(f"{'layer':>6} {'vector':<16} {'above - base':>20} {'below - base':>20}")
    print("-" * 66)
    for li in order:
        for vi, vn in enumerate(vecs):
            v = {c: np.array([p[li, :nmin, vi].mean() for p in rows[c]]) for c in CONDS}
            cells = [f"{v[c].mean() - v['baseline'].mean():+7.3f}  d={cohen(v[c], v['baseline']):+5.2f}"
                     for c in ("above_good", "below_good")]
            print(f"{layers[li]:>6} {vn:<16} {cells[0]:>20} {cells[1]:>20}")
    print(f"\ntokens per rollout (median): "
          + ", ".join(f"{c} {int(np.median([p.shape[1] for p in rows[c]])):,}" for c in CONDS))


if __name__ == "__main__":
    main()

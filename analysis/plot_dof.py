"""1d-v2: bias against degrees of freedom.

    python analysis/plot_dof.py   ->  plots/items/d_dof_line.png

DoF = the number of multiplicative factors the question requires, i.e. how many places the model can
shade. Each rung's threshold is its own baseline median, so the null is 50/50 on every rung and the
bias values are directly comparable.

DoF 5 (pigment cells) is excluded by request. For the record it measured +0.78 [+0.69, +0.86] with a
baseline spread of 116x — by far the widest of the ladder and yet lower bias than DoF 4, which is the
observation that rules out uncertainty as the driver.
"""

from __future__ import annotations

import glob
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "plots" / "items"
LINE = "#6795AE"

RUNGS = [(1, "population", "dof1-population"), (2, "spots", None),
         (3, "spot area", "dof3-area"), (4, "skin mass", "dof4-mass")]


def run(slug):
    if slug is None:
        return ROOT / "data/runs/qwen3.5-27b_20260823_223518"
    return Path(sorted(glob.glob(str(ROOT / f"data/runs/qwen3.5-27b-{slug}_2*")))[-1])


def bias_ci(d, n_boot=8000, seed=0):
    T = float(json.loads((d / "threshold.json").read_text())["threshold"])
    est = json.loads((d / "estimates.json").read_text())
    a = np.array([float(x) > T for x in est["above_good"] if x])
    b = np.array([float(x) <= T for x in est["below_good"] if x])
    r = np.random.default_rng(seed)
    dr = np.array([a[r.integers(0, len(a), len(a))].mean() + b[r.integers(0, len(b), len(b))].mean() - 1
                   for _ in range(n_boot)])
    return float(a.mean() + b.mean() - 1), np.percentile(dr, [2.5, 97.5])


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    x, y, lo, hi, names = [], [], [], [], []
    for k, name, slug in RUNGS:
        v, (l, h) = bias_ci(run(slug), seed=k * 37)
        x.append(k); y.append(v); lo.append(v - l); hi.append(h - v); names.append(name)
        print(f"  DoF {k}  {name:<12} bias {v:+.3f}  [{l:+.3f}, {h:+.3f}]")

    fig, ax = plt.subplots(figsize=(7.4, 5.0))
    ax.errorbar(x, y, yerr=[lo, hi], color=LINE, marker="o", ms=9, lw=2.4, capsize=5,
                elinewidth=1.4, mfc="white", mew=2.4, zorder=3)
    ax.set_xticks(x)
    # the quantity under each tick — axis labelling, so the reader knows what a rung is
    ax.set_xticklabels([f"{k}\n{n}" for k, n in zip(x, names)], fontsize=10.5)
    ax.set_xlabel("degrees of freedom  (multiplicative factors the estimate requires)", fontsize=11.5)
    ax.set_ylabel("bias   = 2 × (mean P(favoured) − 0.5)", fontsize=11.5)
    ax.set_xlim(0.6, 4.4)
    ax.set_ylim(0, 1.0)
    ax.grid(axis="y", alpha=0.25, lw=0.6)
    ax.set_axisbelow(True)
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    fig.tight_layout()
    p = OUT / "d_dof_line.png"
    fig.savefig(p, dpi=150, bbox_inches="tight", pad_inches=0.2)
    plt.close(fig)
    print("  ", p.name)


if __name__ == "__main__":
    main()

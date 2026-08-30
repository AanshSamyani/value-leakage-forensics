"""The two read-out figures: value axis alone, and value axis against the random control.

    python analysis/plot_value_axis_final.py

Units are the paper's eq. (2): cos(h, v) averaged over a rollout's reasoning tokens, one point per
rollout, layer 40. Error bars are bootstrapped 95% CIs on the condition mean.

Points rather than bars, on a zoomed axis. The conditions differ by ~0.006 on a base of 0.148, so
bars anchored at zero would render the entire result as three identical rectangles; bars on a
truncated axis would exaggerate it. Points carry no area to misread.

The comparison figure keeps each vector on its own scale because their raw cosines differ by an
order of magnitude (0.148 against -0.015) — the vectors are norm-matched, so that gap is alignment,
not magnitude, and forcing one axis would flatten the control to a line.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
PT = ROOT / "data/runs/qwen3.5-27b_20260823_223518/analysis/pertoken"
LAYER = 40
CONDS = ("baseline", "above_good", "below_good")
COL = {"baseline": "#90A4AE", "above_good": "#c85a00", "below_good": "#1f77b4"}
LAB = {"baseline": "no bet", "above_good": "above-good", "below_good": "below-good"}
rng = np.random.default_rng(0)


def load() -> dict:
    out: dict = {}
    for f in sorted(PT.glob("*.npz")):
        z = np.load(f, allow_pickle=True)
        li = [int(x) for x in z["layers"]].index(LAYER)
        vecs = [str(x) for x in z["vectors"]]
        rec = {v: float((z["proj"][li, :, i].astype(np.float32)
                         / z["hnorm"][li].astype(np.float32)).mean())
               for i, v in enumerate(vecs)}
        out.setdefault(str(z["cond"]), []).append(rec)
    return out


def panel(ax, data, vec, ylabel):
    for j, c in enumerate(CONDS):
        v = np.array([r[vec] for r in data[c]])
        d = v[rng.integers(0, len(v), (200000, len(v)))].mean(1)
        lo, hi = np.percentile(d, [2.5, 97.5])
        ax.scatter(j + rng.uniform(-.11, .11, len(v)), v, s=24, color=COL[c], alpha=.35, lw=0,
                   zorder=2)
        ax.plot([j - .26, j + .26], [v.mean()] * 2, color=COL[c], lw=3, zorder=4)
        ax.errorbar(j, v.mean(), yerr=[[v.mean() - lo], [hi - v.mean()]], fmt="none",
                    ecolor=COL[c], capsize=6, lw=2, zorder=3)
    ax.set_xticks(range(len(CONDS)))
    ax.set_xticklabels([LAB[c] for c in CONDS], fontsize=10.5)
    ax.set_xlim(-.6, len(CONDS) - .4)
    ax.set_ylabel(ylabel, fontsize=10.5)
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="y", alpha=.22, lw=.6)


def main() -> None:
    data = load()

    # ---- figure 1: value axis only
    fig, ax = plt.subplots(figsize=(6.4, 4.8))
    panel(ax, data, "value_axis", "Mean value-axis projection\n(cosine similarity)")
    fig.tight_layout()
    fig.savefig(ROOT / "plots/fig20_value_axis_only.png", dpi=170, bbox_inches="tight")

    # ---- figure 2: value axis against the random control
    fig, axes = plt.subplots(1, 2, figsize=(11.2, 4.8))
    panel(axes[0], data, "value_axis", "Mean value-axis projection\n(cosine similarity)")
    panel(axes[1], data, "random_control",
          "Mean random-direction projection\n(cosine similarity)")
    fig.tight_layout()
    fig.savefig(ROOT / "plots/fig21_value_vs_random.png", dpi=170, bbox_inches="tight")

    print("wrote plots/fig20_value_axis_only.png and plots/fig21_value_vs_random.png\n")
    for vec in ("value_axis", "random_control"):
        b = np.array([r[vec] for r in data["baseline"]])
        print(f"{vec}:  no bet {b.mean():+.4f}")
        for c in ("above_good", "below_good"):
            v = np.array([r[vec] for r in data[c]])
            dr = (v[rng.integers(0, len(v), (200000, len(v)))].mean(1)
                  - b[rng.integers(0, len(b), (200000, len(b)))].mean(1))
            lo, hi = np.percentile(dr, [2.5, 97.5])
            d = (v.mean() - b.mean()) / np.sqrt((v.var(ddof=1) + b.var(ddof=1)) / 2)
            print(f"   {LAB[c]:<11} {v.mean():+.4f}   diff {dr.mean():+.4f} "
                  f"[{lo:+.4f},{hi:+.4f}]  d={d:+.2f}")


if __name__ == "__main__":
    main()

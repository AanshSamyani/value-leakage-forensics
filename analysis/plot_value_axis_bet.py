"""Is the model's internal "value" higher when there is a bet? One panel, layer 40.

    python analysis/plot_value_axis_bet.py

Each dot is one rollout's mean value-axis projection over its reasoning tokens. Layer 40 of the
three the AUROC sweep recommended, because it separates the conditions most strongly.

Everything is z-scored against the no-bet condition of the SAME vector, so the y-axis reads in
standard deviations of the baseline spread. That is the only scale on which the value axis and the
random control can be compared — their vectors have different norms, and the raw projections differ
by an order of magnitude.

The random control is in the panel because without it the left half proves nothing: the incentive
prompts differ from the baseline prompt, so their activations differ, and some of that lands on any
direction you care to measure. What the control cannot do, being a single vector, is establish a
null. Its sign is arbitrary; that it happens to move down here is not evidence that moving up is
special. A proper test needs a distribution over many random directions, with the value axis in its
tail. That run does not exist yet, and this figure should be read as the best available evidence
rather than as a settled result.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
PT = ROOT / "data/runs/qwen3.5-27b_20260823_223518/analysis/pertoken"
CONDS = ("baseline", "above_good", "below_good")
COL = {"baseline": "#90A4AE", "above_good": "#c85a00", "below_good": "#1f77b4"}
LAB = {"baseline": "no bet", "above_good": "above-good", "below_good": "below-good"}
LAYER = 40
rng = np.random.default_rng(0)


def main() -> None:
    rows, layers, vecs = {}, None, None
    for f in sorted(PT.glob("*.npz")):
        z = np.load(f, allow_pickle=True)
        layers = [int(x) for x in z["layers"]]
        vecs = [str(x) for x in z["vectors"]]
        rows.setdefault(str(z["cond"]), []).append(z["proj"].astype(np.float32))
    li = layers.index(LAYER)

    fig, ax = plt.subplots(figsize=(8.2, 5.2))
    for gi, vn in enumerate(vecs):
        raw = {c: np.array([p[li, :, gi].mean() for p in rows[c]]) for c in CONDS}
        mu, sd = raw["baseline"].mean(), raw["baseline"].std(ddof=1)
        for j, c in enumerate(CONDS):
            x0 = gi * 4 + j
            v = (raw[c] - mu) / sd
            ax.scatter(x0 + rng.uniform(-.13, .13, len(v)), v, s=26, color=COL[c],
                       alpha=.42, lw=0, zorder=2)
            d = v[rng.integers(0, len(v), (100000, len(v)))].mean(1)
            lo, hi = np.percentile(d, [2.5, 97.5])
            ax.plot([x0 - .28, x0 + .28], [v.mean()] * 2, color=COL[c], lw=3, zorder=4)
            ax.errorbar(x0, v.mean(), yerr=[[v.mean() - lo], [hi - v.mean()]], fmt="none",
                        ecolor=COL[c], capsize=5, lw=1.8, zorder=3)
            if c != "baseline":
                b = (raw["baseline"] - mu) / sd
                dd = (v.mean() - b.mean()) / np.sqrt((v.var(ddof=1) + b.var(ddof=1)) / 2)
                ax.annotate(f"d={dd:+.2f}", (x0, hi), ha="center", va="bottom", fontsize=10,
                            color="#4A4A4A", xytext=(0, 7), textcoords="offset points")
        ax.text(gi * 4 + 1, ax.get_ylim()[1], "", ha="center")
    ax.axhline(0, color="#4A4A4A", ls=":", lw=1.1, zorder=1)
    ax.axvline(3, color="#E6E1DA", lw=1.4, zorder=0)
    ax.set_xticks(range(7))
    ax.set_xticklabels([LAB[c] for c in CONDS] + [""] + [LAB[c] for c in CONDS], fontsize=9.5)
    ax.set_ylim(-4.6, 3.9)
    for gi, t in enumerate(("value axis", "random direction (control)")):
        ax.text(gi * 4 + 1, 3.6, t, ha="center", fontsize=11.5, color="#26221E")
    ax.set_ylabel(f"mean projection over reasoning tokens\n"
                  f"(SDs from the no-bet condition, layer {LAYER})", fontsize=10)
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="y", alpha=.25, lw=.6)
    fig.tight_layout()
    out = ROOT / "plots/fig17_value_axis_bet.png"
    fig.savefig(out, dpi=170, bbox_inches="tight")
    print(f"wrote {out}\n")
    for gi, vn in enumerate(vecs):
        raw = {c: np.array([p[li, :, gi].mean() for p in rows[c]]) for c in CONDS}
        b = raw["baseline"]
        print(f"{vn} @ layer {LAYER}:  no bet {b.mean():+.3f}")
        for c in ("above_good", "below_good"):
            v = raw[c]
            dr = (v[rng.integers(0, len(v), (200000, len(v)))].mean(1)
                  - b[rng.integers(0, len(b), (200000, len(b)))].mean(1))
            lo, hi = np.percentile(dr, [2.5, 97.5])
            d = (v.mean() - b.mean()) / np.sqrt((v.var(ddof=1) + b.var(ddof=1)) / 2)
            print(f"   {c:<11} {v.mean():+.3f}   diff {dr.mean():+.3f} [{lo:+.3f},{hi:+.3f}]  d={d:+.2f}")


if __name__ == "__main__":
    main()

"""Value-axis projection across the reasoning trace, in the style of the paper's Figure 3b.

    python analysis/plot_value_axis_bands.py

Follows their construction: each point is the mean value-axis projection within a 500-token band,
averaged over the rollouts long enough to reach that band, so the contributing count falls with
position. Bands are dropped once fewer than MIN_ROLLOUTS remain, since the CI there is carried by a
handful of unusually long traces rather than by the condition.

Units are the paper's eq. (2) — cos(h, v) averaged over the tokens in the band, not the raw dot
product. Bands are absolute token positions rather than normalised depth: normalising stretches
short and long rollouts onto the same axis and washes the signal out (r = -0.01 between the
bet/no-bet gap and normalised depth).

The random-direction control is deliberately not on this figure; it is on fig17 and fig18.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
PT = ROOT / "data/runs/qwen3.5-27b_20260823_223518/analysis/pertoken"
LAYER, VEC, BAND, MIN_ROLLOUTS = 40, "value_axis", 500, 8
CONDS = ("baseline", "above_good", "below_good")
COL = {"baseline": "#90A4AE", "above_good": "#c85a00", "below_good": "#1f77b4"}
LAB = {"baseline": "no bet", "above_good": "above-good", "below_good": "below-good"}
rng = np.random.default_rng(0)


def main() -> None:
    series: dict[str, list[np.ndarray]] = {}
    for f in sorted(PT.glob("*.npz")):
        z = np.load(f, allow_pickle=True)
        li = [int(x) for x in z["layers"]].index(LAYER)
        vi = [str(x) for x in z["vectors"]].index(VEC)
        series.setdefault(str(z["cond"]), []).append(
            z["proj"][li, :, vi].astype(np.float32) / z["hnorm"][li].astype(np.float32))

    nb = max(len(c) for v in series.values() for c in v) // BAND + 1
    # Stop every line at the last band ALL THREE conditions still populate. The no-bet rollouts are
    # ~2400 tokens shorter on average, so they run out first, and letting the incentive lines
    # continue past them would leave the right of the plot comparing two conditions against nothing.
    last = min(next((b for b in range(nb)
                     if sum(len(c) > b * BAND for c in series[cond]) < MIN_ROLLOUTS), nb)
               for cond in CONDS)
    fig, ax = plt.subplots(figsize=(7.6, 4.8))
    counts = {}
    for cond in CONDS:
        xs, ys, los, his, ns = [], [], [], [], []
        for b in range(last):
            vals = np.array([c[b * BAND:(b + 1) * BAND].mean()
                             for c in series[cond] if len(c) > b * BAND])
            draws = vals[rng.integers(0, len(vals), (20000, len(vals)))].mean(1)
            xs.append((b + 0.5) * BAND)
            ys.append(vals.mean())
            los.append(np.percentile(draws, 2.5))
            his.append(np.percentile(draws, 97.5))
            ns.append(len(vals))
        counts[cond] = ns
        ax.fill_between(xs, los, his, color=COL[cond], alpha=.16, lw=0)
        ax.plot(xs, ys, color=COL[cond], lw=2.2, zorder=3, label=LAB[cond])

    ax.set_xlabel("Token position in the reasoning trace", fontsize=11)
    ax.set_ylabel("Mean value-axis projection\n(cosine similarity)", fontsize=11)
    ax.legend(frameon=False, fontsize=10.5, loc="lower right")
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(alpha=.22, lw=.6)
    fig.tight_layout()
    out = ROOT / "plots/fig19_value_axis_bands.png"
    fig.savefig(out, dpi=170, bbox_inches="tight")
    print(f"wrote {out}\n")
    print(f"{'band':>14} " + " ".join(f"{LAB[c]:>12}" for c in CONDS))
    print("-" * 56)
    n = max(len(v) for v in counts.values())
    for b in range(n):
        row = " ".join(f"{counts[c][b] if b < len(counts[c]) else '-':>12}" for c in CONDS)
        print(f"{b * BAND:>6}-{(b + 1) * BAND:<7} {row}")


if __name__ == "__main__":
    main()

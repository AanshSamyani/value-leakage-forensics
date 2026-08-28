"""1c bet-amount ladder: bias vs the stated donation, with bootstrap error bars.

    python analysis/plot_stakes_bias.py   ->  plots/items/c_bias_line.png

Two-sided bias IS defined here (both arms share one threshold), so it is the y-axis:
    bias = 2 * (mean P(favoured) - 0.5) = P(fav|above_good) + P(fav|below_good) - 1
Intervals are a 8,000-draw bootstrap resampling both arms.

The main run states no amount at all, so it has no place on a dollar axis; it is drawn as the
horizontal reference band every rung should be compared against.
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from results_data import collect  # noqa: E402

OUT = Path(__file__).resolve().parents[1] / "plots" / "items"
LINE, BAND = "#6795AE", "#9aa3a7"

TICK = {5: "$5", 10: "$10", 1e3: "$1k", 1e5: "$100k", 1e6: "$1M", 1e7: "$10M", 1e8: "$100M"}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    d = collect()
    rung = [r for r in d["items"]["1c"] if r["amount"] is not None]
    rung.sort(key=lambda r: r["amount"])
    x = [r["amount"] for r in rung]
    y = [r["res"]["bias"] for r in rung]
    err = [[r["res"]["bias"] - r["res"]["bias_ci"][0] for r in rung],
           [r["res"]["bias_ci"][1] - r["res"]["bias"] for r in rung]]
    m, mlo, mhi = d["main"]["bias"], *d["main"]["bias_ci"]

    fig, ax = plt.subplots(figsize=(9.2, 5.0))
    ax.axhspan(mlo, mhi, color=BAND, alpha=0.22, zorder=1,
               label="no amount stated (95% CI)")
    ax.axhline(m, color=BAND, lw=1.6, ls="--", zorder=2)
    ax.errorbar(x, y, yerr=err, color=LINE, marker="o", ms=8, lw=2.2, capsize=4,
                elinewidth=1.3, mfc="white", mew=2.2, zorder=4,
                label="stated donation (95% CI)")
    ax.set_xscale("log")
    ax.set_xticks(list(TICK))
    ax.set_xticklabels(list(TICK.values()), fontsize=10)
    ax.minorticks_off()
    ax.set_xlabel("donation at stake", fontsize=11)
    ax.set_ylabel("bias   = 2 × (mean P(favoured) − 0.5)", fontsize=11)
    ax.set_ylim(0, 0.85)
    ax.legend(fontsize=10, frameon=False, loc="lower left")
    ax.grid(axis="y", alpha=0.25, lw=0.6)
    ax.set_axisbelow(True)
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    fig.tight_layout()
    p = OUT / "c_bias_line.png"
    fig.savefig(p, dpi=150, bbox_inches="tight", pad_inches=0.2)
    plt.close(fig)
    print("  ", p.name)
    for r in rung:
        lo, hi = r["res"]["bias_ci"]
        dd = r.get("delta") or {}
        print(f"   {r['label']:<14} bias {r['res']['bias']:+.3f} [{lo:+.3f}, {hi:+.3f}]"
              f"   Δ vs main {dd.get('delta', float('nan')):+.3f} sig={dd.get('sig')}")


if __name__ == "__main__":
    main()

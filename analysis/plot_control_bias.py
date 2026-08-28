"""1e: does the model still bias when its answer changes nothing?

    python analysis/plot_control_bias.py   ->  plots/items/e_bias_bars.png

Three bars, all two-sided bias (both arms share one threshold in every case):
    base case             the estimate settles the bet
    bet already settled   outcome fixed and known — removes control AND stake
    settles on the truth  bet is live and directional, but resolved from an independent source,
                          so the estimate has no causal effect — removes control, keeps the motive

Colour encodes the variable under test (whether the estimate can move the outcome), which is why
there is a legend at all; the x labels alone would make it redundant.
Intervals are an 8,000-draw bootstrap resampling both arms.
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
C_LIVE, C_NULL = "#CC8A5E", "#6795AE"


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    d = collect()
    bars = [("base case", d["main"], C_LIVE),
            ("bet already settled", d["items"]["1e.2"]["res"], C_NULL),
            ("settles on the true value", d["items"]["1e.1"]["res"], C_NULL)]
    x = np.arange(len(bars))
    y = [b[1]["bias"] for b in bars]
    err = [[b[1]["bias"] - b[1]["bias_ci"][0] for b in bars],
           [b[1]["bias_ci"][1] - b[1]["bias"] for b in bars]]

    fig, ax = plt.subplots(figsize=(7.6, 5.0))
    ax.bar(x, y, color=[b[2] for b in bars], width=0.6, zorder=3)
    ax.errorbar(x, y, yerr=err, fmt="none", ecolor="#4a4a4a", elinewidth=1.2, capsize=4, zorder=4)
    ax.axhline(0, color="#333", lw=1.0, zorder=5)
    ax.set_xticks(x)
    ax.set_xticklabels([b[0] for b in bars], fontsize=10.5)
    ax.set_xlabel("what the estimate controls", fontsize=11)
    ax.set_ylabel("bias   = 2 × (mean P(favoured) − 0.5)", fontsize=11)
    ax.set_ylim(-0.18, 0.82)
    ax.legend(handles=[plt.Rectangle((0, 0), 1, 1, color=C_LIVE),
                       plt.Rectangle((0, 0), 1, 1, color=C_NULL)],
              labels=["the estimate settles the bet", "the estimate cannot change the outcome"],
              fontsize=10, frameon=False, loc="upper right")
    ax.grid(axis="y", alpha=0.25, lw=0.6)
    ax.set_axisbelow(True)
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    fig.tight_layout()
    p = OUT / "e_bias_bars.png"
    fig.savefig(p, dpi=150, bbox_inches="tight", pad_inches=0.2)
    plt.close(fig)
    print("  ", p.name)
    for lab, res, _ in bars:
        lo, hi = res["bias_ci"]
        print(f"   {lab:<26} bias {res['bias']:+.3f} [{lo:+.3f}, {hi:+.3f}]")


if __name__ == "__main__":
    main()

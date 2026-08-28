"""1f: is "most accurate point estimate" protective?

    python analysis/plot_phrase.py  ->  plots/items/f_bias_bars.png
                                        plots/items/f_estimates.png

The phrase occurs twice in the prompt (header + footer), so the arms are a dose: 0, 1, 2 removed.

f_bias_bars.png  the requested three-bar view of two-sided bias. Colour is a sequential ramp
                 because the arms are ordered, not categorical.

f_estimates.png  the same experiment as raw final estimates. A bias bar hides the fact that removing
                 the phrase ALSO moves the no-bet baseline: its median falls 104.5M -> 93.6M -> 75.0M,
                 with no incentive anywhere in the prompt. So 1f is two effects, and only one of them
                 is about values; the bar chart can only show the other. Condition colours follow the
                 adsingh-64 convention used by the other trajectory figures.
"""

from __future__ import annotations

import glob
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from results_data import collect  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "plots" / "items"
# same clay / slate pair as the 1b and 1e bar charts: clay = the unmodified prompt,
# slate = the prompt with the phrase taken out. The dose (0 / 1 / 2) is carried by the x-axis.
C_BASE, C_CUT = "#CC8A5E", "#6795AE"
RAMP = [C_BASE, C_CUT, C_CUT]
COND = {"baseline": "#90A4AE", "below_good": "#1f77b4", "above_good": "#c85a00"}
CLAB = {"baseline": "baseline (no bet)", "below_good": "below favoured", "above_good": "above favoured"}
ARMS = ["phrase present (base)", "footer sentence removed", "footer + header removed"]


def runs():
    ref = ROOT / "data/runs/qwen3.5-27b_20260823_223518"
    a = sorted(glob.glob(str(ROOT / "data/runs/qwen3.5-27b-no-phrase-footer_2*")))[-1]
    b = sorted(glob.glob(str(ROOT / "data/runs/qwen3.5-27b-no-phrase-both_2*")))[-1]
    return [ref, Path(a), Path(b)]


def bars(d):
    res = [d["main"], d["items"]["1f"][1]["res"], d["items"]["1f"][2]["res"]]
    x = np.arange(3)
    y = [r["bias"] for r in res]
    err = [[r["bias"] - r["bias_ci"][0] for r in res], [r["bias_ci"][1] - r["bias"] for r in res]]
    fig, ax = plt.subplots(figsize=(7.6, 5.0))
    ax.bar(x, y, color=RAMP, width=0.6, zorder=3)
    ax.errorbar(x, y, yerr=err, fmt="none", ecolor="#4a4a4a", elinewidth=1.2, capsize=4, zorder=4)
    ax.axhline(0, color="#333", lw=1.0, zorder=5)
    ax.set_xticks(x)
    ax.set_xticklabels(["0", "1", "2"], fontsize=11)
    ax.set_xlabel("occurrences of “most accurate point estimate” removed from the prompt", fontsize=11)
    ax.set_ylabel("bias   = 2 × (mean P(favoured) − 0.5)", fontsize=11)
    ax.set_ylim(0, 1.0)
    ax.legend(handles=[plt.Rectangle((0, 0), 1, 1, color=C_BASE),
                       plt.Rectangle((0, 0), 1, 1, color=C_CUT)],
              labels=["phrase present (base)", "phrase removed"],
              fontsize=10, frameon=False, loc="upper left")
    ax.grid(axis="y", alpha=0.25, lw=0.6)
    ax.set_axisbelow(True)
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    fig.tight_layout()
    p = OUT / "f_bias_bars.png"
    fig.savefig(p, dpi=150, bbox_inches="tight", pad_inches=0.2)
    plt.close(fig)
    print("  ", p.name)


def estimates():
    T = 104475000.0
    fig, ax = plt.subplots(figsize=(9.6, 5.4))
    order = ["baseline", "above_good", "below_good"]
    off = {"baseline": -0.26, "above_good": 0.0, "below_good": 0.26}
    for gi, d in enumerate(runs()):
        est = json.loads((d / "estimates.json").read_text())
        for c in order:
            v = np.array([float(x) for x in est.get(c, []) if x])
            if not len(v):
                continue
            pos = gi + off[c]
            pr = ax.violinplot([np.log10(v)], positions=[pos], widths=0.23, showextrema=False)
            for bdy in pr["bodies"]:
                bdy.set_facecolor(COND[c]); bdy.set_alpha(0.35)
                bdy.set_edgecolor(COND[c]); bdy.set_linewidth(0.9)
            m = np.median(v)
            ax.plot([pos - 0.10, pos + 0.10], [np.log10(m)] * 2, color=COND[c], lw=2.4, zorder=5)
            if c == "baseline":
                ax.annotate(f"{m/1e6:.0f}M", (pos - 0.14, np.log10(m)), textcoords="offset points",
                            xytext=(-6, 0), ha="right", va="center", fontsize=9.5,
                            color="#5c6a70", fontweight="bold",
                            bbox=dict(boxstyle="round,pad=0.18", fc="white", ec="none", alpha=0.85))
    ax.axhline(np.log10(T), color="#c0392b", lw=1.5, ls="--", zorder=1)
    ax.annotate("threshold", (2.62, np.log10(T)), fontsize=9, color="#c0392b",
                va="bottom", fontweight="bold")
    ax.set_xticks(range(3))
    ax.set_xticklabels(["0", "1", "2"], fontsize=11)
    ax.set_xlim(-0.6, 2.7)
    ticks = [7, 7.5, 8, 8.5, 9]
    ax.set_yticks(ticks)
    ax.set_yticklabels(["10M", "32M", "100M", "320M", "1B"], fontsize=10)
    ax.set_ylim(6.8, 9.3)
    ax.set_xlabel("occurrences of “most accurate point estimate” removed from the prompt", fontsize=11)
    ax.set_ylabel("final estimate (log scale)", fontsize=11)
    ax.legend(handles=[plt.Rectangle((0, 0), 1, 1, color=COND[c], alpha=0.55) for c in order],
              labels=[CLAB[c] for c in order], fontsize=10, frameon=False, loc="upper left", ncol=3)
    ax.grid(axis="y", alpha=0.25, lw=0.6)
    ax.set_axisbelow(True)
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    fig.tight_layout()
    p = OUT / "f_estimates.png"
    fig.savefig(p, dpi=150, bbox_inches="tight", pad_inches=0.2)
    plt.close(fig)
    print("  ", p.name)


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    d = collect()
    bars(d)
    estimates()
    for lab, r in zip(ARMS, [d["main"], d["items"]["1f"][1]["res"], d["items"]["1f"][2]["res"]]):
        lo, hi = r["bias_ci"]
        print(f"   {lab:<26} bias {r['bias']:+.3f} [{lo:+.3f}, {hi:+.3f}]   "
              f"baseline P(>T) {r['p_base_above']:.2f}   p_biased {r['p_biased_mean']:.3f}")

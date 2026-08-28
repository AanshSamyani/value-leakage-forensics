"""Bias across the 1b threshold sweep: side-by-side (b.1 | b.2) and both on one axis.

    python analysis/plot_sweep_bias.py   ->  plots/items/b_bias_side_by_side.png
                                             plots/items/b_bias_combined.png

Two-sided `bias` is undefined here — each sweep run generates a single incentive arm — so the metrics are:

  P(fav)     raw win rate: the fraction of rollouts landing on the favoured side of that rung's T.
  P(fav|base) the null. Because each threshold IS a baseline percentile, this comes free: at T = the
             baseline p90, an unbiased model already clears it 10% of the time.
  p_biased   (P(fav) - P(fav|base)) / (1 - P(fav|base)) — a latent-mixture lower bound on the fraction
             of rollouts that were actually biased. This is the y-axis to compare rungs on, since the
             raw rate is dragged down by the null getting harder as T moves out.

x is the STRETCH FACTOR: how far the target sits from the model's default, in the direction the
incentive wants. Above rungs use T/median, below rungs use median/T, so both directions land on one
positive axis and the combined plot can ask whether the limit is the same in each.
"""

from __future__ import annotations

import glob
import json
import math
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / "data" / "runs"
OUT = ROOT / "plots" / "items"
REF = RUNS / "qwen3.5-27b_20260823_223518"
C_AB, C_BE = "#c85a00", "#1f77b4"      # adsingh-64 colours: above favoured / below favoured
# softer pair for the standalone bar chart (desaturated clay / slate, readable on white and in print)
B_AB, B_BE = "#CC8A5E", "#6795AE"


def wilson(k, n, z=1.96):
    if n <= 0:
        return (float("nan"),) * 2
    p, den = k / n, 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return (max(0.0, min(c - h, p)), min(1.0, max(c + h, p)))


def est(d, cond):
    p = Path(d) / "estimates.json"
    return [float(x) for x in json.loads(p.read_text()).get(cond, []) if x] if p.exists() else []


def collect():
    base = est(REF, "baseline")
    MED = float(np.median(base))
    rows = {"above": [], "below": []}
    for side, tags, cond in (("above", ("p75", "p90", "p95", "max", "2max"), "above_good"),
                             ("below", ("p25", "p10", "min", "halfmin"), "below_good")):
        T0 = float(json.loads((REF / "threshold.json").read_text())["threshold"])
        pack = [("median", REF, T0)]
        for t in tags:
            c = sorted(glob.glob(str(RUNS / f"qwen3.5-27b-sweep-{side}-{t}_2*")))
            if c:
                pack.append((t, Path(c[-1]), float(json.loads((Path(c[-1]) / "threshold.json").read_text())["threshold"])))
        for tag, d, T in pack:
            up = side == "above"
            e = est(d, cond)
            k = sum(1 for v in e if (v > T) == up)
            n = len(e)
            pb_base = sum(1 for v in base if (v > T) == up) / len(base)
            p = k / n
            rows[side].append(dict(
                tag=tag, T=T, stretch=(T / MED if up else MED / T), p=p, ci=wilson(k, n), n=n,
                base=pb_base, pbi=(p - pb_base) / (1 - pb_base) if pb_base < 1 else float("nan"),
                med_est=float(np.median(e))))
    return MED, rows


def series(ax, rows, col, lbl, marker="o", null_label=True):
    x = [r["stretch"] for r in rows]
    p = [r["p"] for r in rows]
    err = [[r["p"] - r["ci"][0] for r in rows], [r["ci"][1] - r["p"] for r in rows]]
    ax.errorbar(x, p, yerr=err, color=col, marker=marker, ms=7, lw=2, capsize=3, mfc="white", mew=2,
                label=f"{lbl} — P(fav)", zorder=4)
    ax.plot(x, [r["pbi"] for r in rows], color=col, marker="s", ms=5, lw=1.5, ls="--", alpha=0.75,
            mfc=col, label=f"{lbl} — p_biased", zorder=3)
    ax.plot(x, [r["base"] for r in rows], color="#90A4AE", marker=".", ms=6, lw=1.2, ls=":",
            label="baseline P(fav) — the null" if null_label else "_nolegend_", zorder=2)


def cross50(rows):
    """Where P(fav) crosses 0.5, by linear interpolation in log-stretch."""
    for a, b in zip(rows, rows[1:]):
        if (a["p"] - 0.5) * (b["p"] - 0.5) <= 0 and a["p"] != b["p"]:
            f = (a["p"] - 0.5) / (a["p"] - b["p"])
            return 10 ** (math.log10(a["stretch"]) + f * (math.log10(b["stretch"]) - math.log10(a["stretch"])))
    return None


def limit_line(ax, rows, col, xytext, prefix="stretch limit\n"):
    x50 = cross50(rows)
    if not x50:
        return None
    ax.axvline(x50, color=col, lw=1.2, ls="-", alpha=0.45, zorder=1)
    ax.annotate(f"{prefix}{x50:.1f}×", xy=(x50, 0.5), xytext=xytext, textcoords="offset points",
                fontsize=8.5, color=col, fontweight="bold", ha="center",
                bbox=dict(boxstyle="round,pad=0.28", fc="white", ec=col, lw=0.8, alpha=0.9))
    return x50


def decorate(ax, rows, col, dy=13):
    ax.axhline(0.5, color="#6b6b6b", lw=0.9, ls="--", zorder=1)
    for r in rows:
        ax.annotate(r["tag"], (r["stretch"], r["p"]), textcoords="offset points", xytext=(0, dy),
                    ha="center", fontsize=7.5, color=col,
                    bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="none", alpha=0.75))
    ax.set_xscale("log")
    ax.set_ylim(-0.05, 1.02)
    ax.grid(alpha=0.25, lw=0.6)
    ax.set_axisbelow(True)
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)


def bars(MED, rows):
    """Bare bar chart: p_biased per rung, laid out as a continuum in the threshold itself —
    low thresholds (below favoured) on the left, high ones (above favoured) on the right, and the
    two median bars, which are the same main run read from each arm, meeting in the middle."""
    items = [dict(r, side=side) for side in ("above", "below") for r in rows[side]]
    items.sort(key=lambda r: (r["T"] / MED, r["side"] == "above"))
    y = [r["pbi"] for r in items]
    # transform the Wilson interval on P(fav) through p_biased = (p - p0) / (1 - p0)
    err = [[max(0.0, r["pbi"] - (r["ci"][0] - r["base"]) / (1 - r["base"])) for r in items],
           [max(0.0, (r["ci"][1] - r["base"]) / (1 - r["base"]) - r["pbi"]) for r in items]]
    col = [B_AB if r["side"] == "above" else B_BE for r in items]
    x = np.arange(len(items))

    fig, ax = plt.subplots(figsize=(9.8, 4.9))
    ax.bar(x, y, color=col, width=0.76, zorder=3)
    ax.errorbar(x, y, yerr=err, fmt="none", ecolor="#4a4a4a", elinewidth=1.1, capsize=3, zorder=4)
    ax.axhline(0, color="#333", lw=0.9)
    ax.set_xticks(x)
    ax.set_xticklabels([f"{r['T'] / MED:.2f}×" if r["T"] / MED < 10 else f"{r['T'] / MED:.1f}×"
                        for r in items], fontsize=9)
    ax.set_xlabel("threshold ÷ the model's default estimate", fontsize=10.5)
    ax.set_ylabel("p_biased  (fraction of rollouts biased)", fontsize=10.5)
    ax.legend(handles=[plt.Rectangle((0, 0), 1, 1, color=B_BE),
                       plt.Rectangle((0, 0), 1, 1, color=B_AB)],
              labels=["below favoured", "above favoured"], fontsize=10, frameon=False,
              loc="upper center", ncol=2)
    ax.set_ylim(0, max(y) * 1.32)
    ax.grid(axis="y", alpha=0.25, lw=0.6)
    ax.set_axisbelow(True)
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    fig.tight_layout()
    pth = OUT / "b_bias_bars.png"
    fig.savefig(pth, dpi=150, bbox_inches="tight", pad_inches=0.2)
    plt.close(fig)
    print("  ", pth.name)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    MED, rows = collect()

    # ---------------- side by side ----------------
    fig, axes = plt.subplots(1, 2, figsize=(13, 5.2), sharey=True)
    for ax, side, col, ttl, xl in (
            (axes[0], "above", C_AB, "1b.1  threshold walked UP",
             "T ÷ baseline median   (further right = higher target)"),
            (axes[1], "below", C_BE, "1b.2  threshold walked DOWN",
             "baseline median ÷ T   (further right = lower target)")):
        series(ax, rows[side], col, "above favoured" if side == "above" else "below favoured")
        decorate(ax, rows[side], col)
        limit_line(ax, rows[side], col, (0, 46))
        ax.set_title(ttl, fontsize=11.5)
        ax.set_xlabel(xl, fontsize=9.5)
        ax.legend(fontsize=8, loc="upper right", framealpha=0.93)
    axes[0].set_ylabel("fraction of rollouts", fontsize=10)
    fig.tight_layout(rect=[0, 0, 1, 0.90])
    fig.suptitle("1b  How far will it stretch? Bias against threshold distance",
                 fontsize=13.5, fontweight="bold", y=0.995, va="top")
    fig.text(0.5, 0.945, "Solid = raw win rate (Wilson 95%).  Dashed = p_biased, corrected for the null.  "
             "Dotted grey = what an unbiased model already achieves at that threshold.",
             ha="center", va="top", fontsize=8.5, color="#555")
    p = OUT / "b_bias_side_by_side.png"
    fig.savefig(p, dpi=150, bbox_inches="tight", pad_inches=0.25)
    plt.close(fig)
    print("  ", p.name)

    # ---------------- combined ----------------
    fig, ax = plt.subplots(figsize=(9.6, 5.6))
    series(ax, rows["above"], C_AB, "above favoured (T above median)")
    h = ax.get_legend_handles_labels()
    series(ax, rows["below"], C_BE, "below favoured (T below median)", marker="D", null_label=False)
    decorate(ax, rows["above"], C_AB, dy=15)
    decorate(ax, rows["below"], C_BE, dy=-22)
    xa = limit_line(ax, rows["above"], C_AB, (34, 78), "above stops at\n")
    xb = limit_line(ax, rows["below"], C_BE, (-40, 122), "below stops at\n")
    if xa and xb:
        ax.text(0.5, 0.035, f"the two limits agree to within {abs(xa - xb) / max(xa, xb):.0%} — "
                "the elastic limit is the same in both directions",
                transform=ax.transAxes, ha="center", fontsize=9, style="italic", color="#444")
    ax.set_xlabel("STRETCH FACTOR — how far the target sits from the model's default, "
                  "in the direction the incentive wants  (log)", fontsize=9.5)
    ax.set_ylabel("fraction of rollouts", fontsize=10)
    ax.set_title("1b  Both directions on one axis — is the stretch limit symmetric?",
                 fontsize=13, fontweight="bold")
    hs, ls = ax.get_legend_handles_labels()
    order = sorted(range(len(ls)), key=lambda i: ("P(fav)" not in ls[i], "below" in ls[i]))
    ax.legend([hs[i] for i in order], [ls[i] for i in order], fontsize=8.5, loc="upper right",
              framealpha=0.95, ncol=1)
    ax.set_ylim(-0.08, 1.06)
    p = OUT / "b_bias_combined.png"
    fig.tight_layout()
    fig.savefig(p, dpi=150, bbox_inches="tight", pad_inches=0.25)
    plt.close(fig)
    print("  ", p.name)

    bars(MED, rows)

    print(f"\n{'side':<7} {'rung':<9} {'T':>16} {'stretch':>8} {'P(fav)':>7} {'null':>6} {'p_biased':>9} {'n':>4}")
    print("-" * 74)
    for side in ("above", "below"):
        for r in rows[side]:
            print(f"{side:<7} {r['tag']:<9} {r['T']:>16,.0f} {r['stretch']:>7.2f}× {r['p']:>7.2f} "
                  f"{r['base']:>6.2f} {r['pbi']:>9.3f} {r['n']:>4}")
        print()


if __name__ == "__main__":
    main()

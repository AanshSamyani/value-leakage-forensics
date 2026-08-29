"""Three panels that tell the whole steering story: the result, the confound, and the test.

    python analysis/plot_steering.py

A  bias vs alpha, measured the obvious way. Monotone, and in the direction the hypothesis predicts.
B  what steering does to the model's answer when there is NO bet at all. A 7x swing. This is why
   panel A looks the way it does: move the model's numbers and a fixed threshold re-reads that as
   bias, because "above T" and "below T" get easier and harder for free.
C  the test that separates them. Steering displaces the baseline away from the threshold; the
   incentive conditions stay pinned near it, so the gap between them grows with displacement alone.
   Plotting the gap against |displacement| shows a tight relationship (r=0.86) in which the SIGN of
   steering — the thing that means "value" — carries no extra information. The two circled arms are
   displaced almost equally in opposite directions and land on top of each other.
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
R = ROOT / "data/runs"
REF = R / "qwen3.5-27b_20260823_223518"
CLAY, SLATE, GREY = "#CC8A5E", "#6795AE", "#90A4AE"
rng = np.random.default_rng(0)
B = 100000


def load(d: Path):
    e = json.loads((d / "estimates.json").read_text())
    return {c: np.array([float(x) for x in e[c] if x is not None and float(x) > 0])
            for c in ("baseline", "above_good", "below_good") if e.get(c)}


def main() -> None:
    T = float(json.loads((REF / "threshold.json").read_text())["threshold"])
    arms = {0.0: load(REF)}
    for p in R.glob("*steer-value_axis*"):
        arms[round(float(p.name.split("-a")[1].split("_")[0]), 4)] = load(p)
    al = sorted(arms)
    pct = [a / 1.0091 * 10 for a in al]          # alpha 1.0091 == 10% of the residual-stream norm

    bias, blo, bhi, med, sep, disp = [], [], [], [], [], []
    for a in al:
        v = arms[a]
        # Strict ties: answering EXACTLY the threshold is not landing below it. This matters in
        # exactly one arm — at -20% the attractor pins 27% of below_good answers to the threshold
        # verbatim — where the project's usual `(e > T) == up` would score every one of them a win
        # and read bias as 0.535 instead of 0.267.
        pa = np.mean(v["above_good"] > T)
        pb = np.mean(v["below_good"] < T)
        d = (rng.binomial(len(v["above_good"]), pa, B) / len(v["above_good"])
             + rng.binomial(len(v["below_good"]), pb, B) / len(v["below_good"]) - 1)
        bias.append(pa + pb - 1)
        blo.append(np.percentile(d, 2.5)); bhi.append(np.percentile(d, 97.5))
        med.append(np.median(v["baseline"]) / T)
        disp.append(abs(np.log(np.median(v["baseline"]) / T)))
        sep.append(np.log(np.median(v["above_good"]) / np.median(v["below_good"])))

    fig, ax = plt.subplots(1, 3, figsize=(14.0, 4.2))
    for x in ax:
        x.spines[["top", "right"]].set_visible(False)
        x.grid(alpha=.25, lw=.6)

    # ---- A: the result as it first appears
    ax[0].errorbar(pct, bias, yerr=[np.array(bias) - blo, np.array(bhi) - np.array(bias)],
                   fmt="o-", color=CLAY, lw=2, ms=7, capsize=4, zorder=3)
    ax[0].axhline(bias[al.index(0.0)], color=GREY, ls="--", lw=1, zorder=1)
    ax[0].set_xlabel("steering strength (% of residual-stream norm)\n$\\leftarrow$ away from value"
                     "        toward value $\\rightarrow$")
    ax[0].set_ylabel("bias")
    ax[0].set_xticks(pct)

    # ---- B: the confound
    ax[1].plot(pct, med, "o-", color=SLATE, lw=2, ms=7, zorder=3)
    ax[1].axhline(1.0, color=GREY, ls="--", lw=1, zorder=1)
    ax[1].set_yscale("log")
    ax[1].set_yticks([0.25, 0.5, 1, 2]); ax[1].set_yticklabels(["0.25", "0.5", "1", "2"])
    ax[1].set_xlabel("steering strength (% of residual-stream norm)")
    ax[1].set_ylabel("median estimate with NO bet\n(multiples of the threshold)")
    ax[1].set_xticks(pct)

    # ---- C: the test
    col = [CLAY if a > 0 else (SLATE if a < 0 else "#4A4A4A") for a in al]
    ax[2].scatter(disp, sep, c=col, s=90, zorder=3, edgecolor="white", lw=1.2)
    for d_, s_, p_ in zip(disp, sep, pct):
        ax[2].annotate(f"{p_:+.0f}%".replace("+0%", "0"), (d_, s_), textcoords="offset points",
                       xytext=(9, -4), fontsize=9, color="#4A4A4A")
    k = [i for i, a in enumerate(al) if a in (-2.0181, 1.0091)]
    ax[2].scatter([disp[i] for i in k], [sep[i] for i in k], s=290, facecolor="none",
                  edgecolor="#4A4A4A", lw=1.4, zorder=2)
    x = np.array(disp); y = np.array(sep)
    m, b = np.polyfit(x, y, 1)
    xs = np.linspace(0, max(x) * 1.05, 50)
    ax[2].plot(xs, m * xs + b, color=GREY, ls="--", lw=1.2, zorder=1)
    ax[2].set_xlabel("|displacement| of the no-bet answer\nfrom the threshold (log units)")
    ax[2].set_ylabel("above-good vs below-good\nseparation (log units)")
    ax[2].set_xlim(-0.08, max(x) * 1.22)
    ax[2].set_ylim(min(y) - .06, max(y) * 1.14)

    fig.tight_layout()
    out = ROOT / "plots" / "fig10_steering.png"
    out.parent.mkdir(exist_ok=True)
    fig.savefig(out, dpi=170, bbox_inches="tight")
    print(f"wrote {out}")
    print(f"\n{'% of ||h||':>10} {'alpha':>9} {'bias':>7} {'no-bet median':>14} "
          f"{'|disp|':>7} {'separation':>11}")
    for p_, a, bi, m_, d_, s_ in zip(pct, al, bias, med, disp, sep):
        print(f"{p_:>+10.0f} {a:>+9.4f} {bi:>7.3f} {m_:>13.2f}x {d_:>7.3f} {s_:>11.3f}")
    print(f"\nseparation vs |displacement|: r = {np.corrcoef(x, y)[0, 1]:.3f}")


if __name__ == "__main__":
    main()

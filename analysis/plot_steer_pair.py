"""Two standalone steering figures: the result, and the test that undercuts it.

    python analysis/plot_steer_pair.py

fig12  bias against steering strength. The value-axis arms trace a clean monotone ladder in the
       direction the hypothesis predicts. The random-direction control sits at the same alpha as the
       -20% arm and is drawn in plum, because it is a different vector, not another point on that
       curve.

fig13  the same data against what actually explains it: how far steering displaced the model's
       no-bet answer from the threshold. Sign of steering carries no extra information, and the
       random control falls on the line with everything else.

Both score ties strictly — answering EXACTLY the threshold is not landing below it. That matters
only in the -20% value-axis arm, where the attractor pins 27% of below_good answers to the
threshold verbatim.
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D

ROOT = Path(__file__).resolve().parents[1]
R = ROOT / "data/runs"
REF = R / "qwen3.5-27b_20260823_223518"
# Coloured by what the arm IS, not by an arbitrary series index: steering away from value, the
# unsteered reference, steering toward value, and the random direction are four different things.
AWAY, TOWARD, REFC, PLUM, GREY = "#6795AE", "#CC8A5E", "#5F8D6E", "#8A6FA3", "#90A4AE"


def arm_colour(alpha: float) -> str:
    return REFC if alpha == 0 else (AWAY if alpha < 0 else TOWARD)
rng = np.random.default_rng(0)
B = 200000


def load(d: Path) -> dict:
    e = json.loads((d / "estimates.json").read_text())
    return {c: np.array([float(x) for x in e[c] if x is not None and float(x) > 0])
            for c in ("baseline", "above_good", "below_good") if e.get(c)}


def stats(v: dict, T: float):
    pa, pb = np.mean(v["above_good"] > T), np.mean(v["below_good"] < T)
    d = (rng.binomial(len(v["above_good"]), pa, B) / len(v["above_good"])
         + rng.binomial(len(v["below_good"]), pb, B) / len(v["below_good"]) - 1)
    return dict(bias=pa + pb - 1, lo=np.percentile(d, 2.5), hi=np.percentile(d, 97.5),
                disp=abs(np.log(np.median(v["baseline"]) / T)),
                sep=np.log(np.median(v["above_good"]) / np.median(v["below_good"])))


def main() -> None:
    T = float(json.loads((REF / "threshold.json").read_text())["threshold"])
    axis = {0.0: stats(load(REF), T)}
    for p in R.glob("*steer-value_axis*"):
        axis[round(float(p.name.split("-a")[1].split("_")[0]), 4)] = stats(load(p), T)
    cp = next(R.glob("*steer-random_control*"))
    ctrl_a = round(float(cp.name.split("-a")[1].split("_")[0]), 4)
    ctrl = stats(load(cp), T)

    al = sorted(axis)
    pct = [a / 1.0091 * 10 for a in al]
    bias = [axis[a]["bias"] for a in al]
    err = [[axis[a]["bias"] - axis[a]["lo"] for a in al], [axis[a]["hi"] - axis[a]["bias"] for a in al]]

    # ---------------------------------------------------------------- fig 12: bias vs strength
    fig, ax = plt.subplots(figsize=(6.9, 4.8))
    ax.plot(pct, bias, "-", color=GREY, lw=1.6, zorder=2)          # link, not a series colour
    ax.axhline(axis[0.0]["bias"], color=GREY, ls=":", lw=1, zorder=1)
    for i, a in enumerate(al):
        ax.errorbar([pct[i]], [bias[i]], yerr=[[err[0][i]], [err[1][i]]], fmt="o",
                    color=arm_colour(a), ms=9, capsize=4, zorder=3)
    cx = ctrl_a / 1.0091 * 10
    # nudged off -20% so the two error bars do not overlap; it IS at that strength
    ax.errorbar([cx + 0.9], [ctrl["bias"]],
                yerr=[[ctrl["bias"] - ctrl["lo"]], [ctrl["hi"] - ctrl["bias"]]],
                fmt="s", color=PLUM, ms=9, capsize=4, zorder=4, label="random direction")
    ax.set_xlabel("steering strength (% of residual-stream norm)\n"
                  "$\\leftarrow$ away from value            toward value $\\rightarrow$")
    ax.set_ylabel("bias")
    ax.set_xticks(pct)
    ax.set_ylim(0.10, 0.99)
    h = [Line2D([], [], ls="", marker=m, ms=8.5, color=c, label=t) for m, c, t in
         (("o", AWAY, "value axis, away from value"), ("o", REFC, "unsteered"),
          ("o", TOWARD, "value axis, toward value"), ("s", PLUM, "random direction"))]
    ax.legend(handles=h, frameon=False, fontsize=9.5, loc="upper left", handletextpad=.5,
              labelspacing=.45)
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(alpha=.25, lw=.6)
    fig.tight_layout()
    fig.savefig(ROOT / "plots/fig12_steer_bias.png", dpi=170, bbox_inches="tight")

    # ---------------------------------------------------------------- fig 13: vs displacement
    fig, ax = plt.subplots(figsize=(6.9, 4.8))
    x = np.array([axis[a]["disp"] for a in al])
    y = np.array([axis[a]["sep"] for a in al])
    m, b = np.polyfit(np.append(x, ctrl["disp"]), np.append(y, ctrl["sep"]), 1)
    xs = np.linspace(0, max(x.max(), ctrl["disp"]) * 1.12, 50)
    ax.plot(xs, m * xs + b, color=GREY, ls="--", lw=1.2, zorder=1)
    ax.scatter([ctrl["disp"]], [ctrl["sep"]], marker="s", s=360, facecolor="none",
               edgecolor=PLUM, lw=2.4, zorder=2)
    for a_, xi, yi in zip(al, x, y):
        ax.scatter([xi], [yi], s=100, color=arm_colour(a_), zorder=3, edgecolor="white", lw=1.2)
    # placed by hand: -20% and +10% sit 0.13 apart in x with the control ringing +10%, so the
    # default offset collides three ways
    off = {-2.0181: (0, 13, "center"), -1.0091: (0, -20, "center"), 0.0: (13, -4, "left"),
           1.0091: (0, -25, "center"), 2.0181: (13, -4, "left")}
    for a_, xi, yi, p_ in zip(al, x, y, pct):
        dx, dy, ha = off[a_]
        ax.annotate(f"{p_:+.0f}%".replace("+0%", "unsteered"), (xi, yi), ha=ha,
                    textcoords="offset points", xytext=(dx, dy), fontsize=9.5,
                    color=arm_colour(a_), fontweight="medium")
    ax.annotate(f"random {cx:+.0f}%", (ctrl["disp"], ctrl["sep"]), textcoords="offset points",
                xytext=(19, 10), fontsize=9.5, color=PLUM, fontweight="medium")
    ax.set_xlabel("|displacement| of the no-bet answer\nfrom the threshold (log units)")
    ax.set_ylabel("above-good vs below-good separation (log units)")
    ax.set_xlim(-0.10, max(x.max(), ctrl["disp"]) * 1.24)
    ax.set_ylim(-0.02, max(y.max(), ctrl["sep"]) * 1.20)
    h = [Line2D([], [], ls="", marker=m, ms=8.5, color=c, mfc=f, label=t) for m, c, f, t in
         (("o", AWAY, AWAY, "away from value"), ("o", REFC, REFC, "unsteered"),
          ("o", TOWARD, TOWARD, "toward value"), ("s", PLUM, "none", "random direction"))]
    ax.legend(handles=h, frameon=False, fontsize=9.5, loc="upper left", handletextpad=.5,
              labelspacing=.45)
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(alpha=.25, lw=.6)
    fig.tight_layout()
    fig.savefig(ROOT / "plots/fig13_steer_displacement.png", dpi=170, bbox_inches="tight")

    r = np.corrcoef(np.append(x, ctrl["disp"]), np.append(y, ctrl["sep"]))[0, 1]
    print("wrote plots/fig12_steer_bias.png and plots/fig13_steer_displacement.png")
    print(f"\n{'arm':<22} {'bias':>7} {'95% CI':>16} {'|disp|':>7} {'sep':>7}")
    print("-" * 64)
    for a in al:
        s = axis[a]
        nm = "unsteered" if a == 0 else f"value axis {a / 1.0091 * 10:+.0f}%"
        print(f"{nm:<22} {s['bias']:>7.3f} [{s['lo']:+.3f},{s['hi']:+.3f}] {s['disp']:>7.3f} "
              f"{s['sep']:>7.3f}")
    print(f"{'random ' + f'{cx:+.0f}%':<22} {ctrl['bias']:>7.3f} "
          f"[{ctrl['lo']:+.3f},{ctrl['hi']:+.3f}] {ctrl['disp']:>7.3f} {ctrl['sep']:>7.3f}")
    print(f"\nseparation vs |displacement|, all six points: r = {r:.3f}")


if __name__ == "__main__":
    main()

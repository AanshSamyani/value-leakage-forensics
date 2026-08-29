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

ROOT = Path(__file__).resolve().parents[1]
R = ROOT / "data/runs"
REF = R / "qwen3.5-27b_20260823_223518"
CLAY, GREY, PLUM = "#CC8A5E", "#90A4AE", "#8A6FA3"
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
    fig, ax = plt.subplots(figsize=(6.4, 4.6))
    ax.errorbar(pct, bias, yerr=err, fmt="o-", color=CLAY, lw=2.2, ms=8, capsize=4,
                zorder=3, label="value axis")
    ax.axhline(axis[0.0]["bias"], color=GREY, ls="--", lw=1, zorder=1)
    cx = ctrl_a / 1.0091 * 10
    # nudged off -20% so the two error bars do not overlap; it IS at that strength
    ax.errorbar([cx + 0.9], [ctrl["bias"]],
                yerr=[[ctrl["bias"] - ctrl["lo"]], [ctrl["hi"] - ctrl["bias"]]],
                fmt="s", color=PLUM, ms=9, capsize=4, zorder=4, label="random direction")
    ax.set_xlabel("steering strength (% of residual-stream norm)\n"
                  "$\\leftarrow$ away from value            toward value $\\rightarrow$")
    ax.set_ylabel("bias")
    ax.set_xticks(pct)
    ax.legend(frameon=False, fontsize=10, loc="upper left")
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(alpha=.25, lw=.6)
    fig.tight_layout()
    fig.savefig(ROOT / "plots/fig12_steer_bias.png", dpi=170, bbox_inches="tight")

    # ---------------------------------------------------------------- fig 13: vs displacement
    fig, ax = plt.subplots(figsize=(6.4, 4.6))
    x = np.array([axis[a]["disp"] for a in al])
    y = np.array([axis[a]["sep"] for a in al])
    m, b = np.polyfit(np.append(x, ctrl["disp"]), np.append(y, ctrl["sep"]), 1)
    xs = np.linspace(0, max(x.max(), ctrl["disp"]) * 1.12, 50)
    ax.plot(xs, m * xs + b, color=GREY, ls="--", lw=1.2, zorder=1)
    ax.scatter([ctrl["disp"]], [ctrl["sep"]], marker="s", s=340, facecolor="none",
               edgecolor=PLUM, lw=2.4, zorder=2, label="random direction")
    ax.scatter(x, y, s=95, color=CLAY, zorder=3, edgecolor="white", lw=1.2, label="value axis")
    off = {1.0091: (-13, -18), 2.0181: (11, -4), -2.0181: (-2, 12), -1.0091: (11, -4), 0.0: (11, -4)}
    for a_, xi, yi, p_ in zip(al, x, y, pct):
        ha = "right" if off[a_][0] < 0 else "left"
        ax.annotate(f"{p_:+.0f}%".replace("+0%", "unsteered"), (xi, yi), ha=ha,
                    textcoords="offset points", xytext=off[a_], fontsize=9, color="#4A4A4A")
    ax.annotate(f"random {cx:+.0f}%", (ctrl["disp"], ctrl["sep"]), textcoords="offset points",
                xytext=(15, 9), fontsize=9, color=PLUM)
    ax.set_xlabel("|displacement| of the no-bet answer\nfrom the threshold (log units)")
    ax.set_ylabel("above-good vs below-good separation (log units)")
    ax.set_xlim(-0.08, max(x.max(), ctrl["disp"]) * 1.22)
    ax.legend(frameon=False, fontsize=10, loc="upper left")
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

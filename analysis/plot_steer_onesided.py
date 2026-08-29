"""One-sided bias under steering: the two incentive conditions move in OPPOSITE directions.

    python analysis/plot_steer_onesided.py

The two-sided bias, p(above wins) + p(below wins) - 1, rises monotonically with steering strength.
Splitting it reveals why, and it is not the hypothesis: as alpha goes from -20% to +20%,

    below-good  0.310 -> 0.980   (r = +0.97 with alpha)
    above-good  0.957 -> 0.860   (r = -0.87 with alpha)

If steering the value axis made the model care more about the donation, BOTH conditions would win
more often — the model would favour whichever side pays, and which side that is differs between
them. Instead one rises exactly as the other falls, which is the signature of the estimate simply
sliding across a fixed threshold. The two-sided metric partially cancels that slide; a one-sided
metric does not cancel it at all, so one-sided bias is MORE confounded, not less.

Above-good also saturates at 0.860 for every alpha >= 0 — the attractor ceiling. It cannot rise
further no matter how far steering pushes the free estimate down.
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
R = ROOT / "data/runs"
REF = R / "qwen3.5-27b_20260823_223518"
ABOVE, BELOW, PLUM, GREY = "#c85a00", "#1f77b4", "#8A6FA3", "#90A4AE"


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return 0.0, 1.0
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return c - h, c + h


def wins(d: Path, T: float):
    e = json.loads((d / "estimates.json").read_text())
    g = lambda k: np.array([float(x) for x in e[k] if x is not None and float(x) > 0])
    out = {}
    for c, test in (("above_good", lambda v: v > T), ("below_good", lambda v: v < T)):
        v = g(c)
        k = int(test(v).sum())
        out[c] = (k / len(v),) + wilson(k, len(v))
    return out


def main() -> None:
    T = float(json.loads((REF / "threshold.json").read_text())["threshold"])
    arms = {0.0: wins(REF, T)}
    for p in R.glob("*steer-value_axis*"):
        arms[round(float(p.name.split("-a")[1].split("_")[0]), 4)] = wins(p, T)
    cp = next(R.glob("*steer-random_control*"))
    ctrl_pct = round(float(cp.name.split("-a")[1].split("_")[0]), 4) / 1.0091 * 10
    ctrl = wins(cp, T)

    al = sorted(arms)
    pct = [a / 1.0091 * 10 for a in al]
    fig, ax = plt.subplots(figsize=(6.8, 4.7))
    for cond, col, lab, mk in (("above_good", ABOVE, "above-good  (wins by exceeding T)", "o"),
                               ("below_good", BELOW, "below-good  (wins by staying under T)", "o")):
        y = [arms[a][cond][0] for a in al]
        e = [[y[i] - arms[a][cond][1] for i, a in enumerate(al)],
             [arms[a][cond][2] - y[i] for i, a in enumerate(al)]]
        ax.errorbar(pct, y, yerr=e, fmt=mk + "-", color=col, lw=2.2, ms=7.5, capsize=3.5,
                    zorder=3, label=lab)
    for cond, mk in (("above_good", "o"), ("below_good", "s")):
        v = ctrl[cond]
        ax.errorbar([ctrl_pct + 0.9], [v[0]], yerr=[[v[0] - v[1]], [v[2] - v[0]]], fmt=mk,
                    color=PLUM, ms=8.5, capsize=3.5, zorder=4,
                    label="random direction" if cond == "above_good" else None)
    ax.axvline(0, color=GREY, ls="--", lw=1, zorder=1)
    ax.set_xlabel("steering strength (% of residual-stream norm)\n"
                  "$\\leftarrow$ away from value            toward value $\\rightarrow$")
    ax.set_ylabel("P(lands on the side that wins the bet)")
    ax.set_xticks(pct)
    ax.set_ylim(0.15, 1.03)
    ax.legend(frameon=False, fontsize=9.5, loc="lower left")
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(alpha=.25, lw=.6)
    fig.tight_layout()
    out = ROOT / "plots/fig14_steer_onesided.png"
    fig.savefig(out, dpi=170, bbox_inches="tight")
    print(f"wrote {out}\n")
    print(f"{'arm':<20} {'above-good':>12} {'below-good':>12} {'two-sided':>11}")
    print("-" * 58)
    for a in al:
        u, d_ = arms[a]["above_good"][0], arms[a]["below_good"][0]
        nm = "unsteered" if a == 0 else f"value axis {a / 1.0091 * 10:+.0f}%"
        print(f"{nm:<20} {u:>12.3f} {d_:>12.3f} {u + d_ - 1:>11.3f}")
    u, d_ = ctrl["above_good"][0], ctrl["below_good"][0]
    print(f"{'random ' + f'{ctrl_pct:+.0f}%':<20} {u:>12.3f} {d_:>12.3f} {u + d_ - 1:>11.3f}")
    ab = [arms[a]["above_good"][0] for a in al]
    be = [arms[a]["below_good"][0] for a in al]
    print(f"\ncorrelation with alpha:  above-good r = {np.corrcoef(al, ab)[0, 1]:+.3f}   "
          f"below-good r = {np.corrcoef(al, be)[0, 1]:+.3f}")


if __name__ == "__main__":
    main()

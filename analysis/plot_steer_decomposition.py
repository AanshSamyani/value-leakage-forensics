"""The steering ladder, decomposed into the two halves that make it.

    python analysis/plot_steer_decomposition.py

Bias here is p(above-good wins) + p(below-good wins) - 1, so the left panel is exactly the middle
panel plus the right panel minus one. Splitting it that way is the point:

  above-good  is flat. 0.860 at every alpha >= 0 and never better than 0.957 — the attractor
              ceiling. Steering drags the model's free answer from 1.00x the threshold down to
              0.27x, and this condition does not move.
  below-good  carries the whole ladder. 0.310 -> 0.980, r = +0.97 with alpha.

A representation that made the model care more about the donation would lift BOTH, since the two
conditions win on opposite sides of the threshold. One flat and one steep is what an estimate
sliding underneath a fixed threshold looks like.

The random direction is the exception worth noticing: it is the only point that breaks the
above-good floor, at 0.720. It does not shift where the model aims — its above-good median is
1.01x the threshold, same as the value axis — it makes the model miss more often.
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
AWAY, TOWARD, REFC, PLUM, GREY = "#6795AE", "#CC8A5E", "#5F8D6E", "#8A6FA3", "#90A4AE"


def colour(a: float) -> str:
    return REFC if a == 0 else (AWAY if a < 0 else TOWARD)


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    p, d = k / n, 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return c - h, c + h


def measure(d: Path, T: float) -> dict:
    e = json.loads((d / "estimates.json").read_text())
    g = lambda k: np.array([float(x) for x in e[k] if x is not None and float(x) > 0])
    out = {}
    for c, hit in (("above_good", lambda v: v > T), ("below_good", lambda v: v < T)):
        v = g(c)
        k = int(hit(v).sum())
        out[c] = (k / len(v), *wilson(k, len(v)))
    pa, pb = out["above_good"][0], out["below_good"][0]
    # bias CI by bootstrap: it is a sum of two independent proportions, not a proportion itself
    rng = np.random.default_rng(0)
    na = len(g("above_good")); nb = len(g("below_good"))
    dr = rng.binomial(na, pa, 200000) / na + rng.binomial(nb, pb, 200000) / nb - 1
    out["bias"] = (pa + pb - 1, np.percentile(dr, 2.5), np.percentile(dr, 97.5))
    return out


def main() -> None:
    T = float(json.loads((REF / "threshold.json").read_text())["threshold"])
    arms = {0.0: measure(REF, T)}
    for p in R.glob("*steer-value_axis*"):
        arms[round(float(p.name.split("-a")[1].split("_")[0]), 4)] = measure(p, T)
    cp = next(R.glob("*steer-random_control*"))
    cx = round(float(cp.name.split("-a")[1].split("_")[0]), 4) / 1.0091 * 10
    ctrl = measure(cp, T)

    al = sorted(arms)
    pct = [a / 1.0091 * 10 for a in al]
    panels = [("bias", "bias", None),
              ("above_good", "P(above-good wins)\nlands above the threshold", (0.22, 1.02)),
              ("below_good", "P(below-good wins)\nlands below the threshold", (0.22, 1.02))]

    fig, axes = plt.subplots(1, 3, figsize=(14.2, 4.5))
    for ax, (key, ylab, ylim) in zip(axes, panels):
        y = [arms[a][key][0] for a in al]
        ax.plot(pct, y, "-", color=GREY, lw=1.6, zorder=2)
        for i, a in enumerate(al):
            v = arms[a][key]
            ax.errorbar([pct[i]], [v[0]], yerr=[[v[0] - v[1]], [v[2] - v[0]]], fmt="o",
                        color=colour(a), ms=9, capsize=4, zorder=3)
        v = ctrl[key]
        ax.errorbar([cx + 0.9], [v[0]], yerr=[[v[0] - v[1]], [v[2] - v[0]]], fmt="s",
                    color=PLUM, ms=8.5, capsize=4, zorder=4)
        ax.axhline(arms[0.0][key][0], color=GREY, ls=":", lw=1, zorder=1)
        ax.set_xticks(pct)
        ax.set_ylabel(ylab, fontsize=10)
        ax.set_xlabel("steering strength (% of residual-stream norm)", fontsize=9.5)
        if ylim:
            ax.set_ylim(*ylim)
        ax.spines[["top", "right"]].set_visible(False)
        ax.grid(alpha=.25, lw=.6)

    h = [Line2D([], [], ls="", marker=m, ms=8.5, color=c, label=t) for m, c, t in
         (("o", AWAY, "away from value"), ("o", REFC, "unsteered"),
          ("o", TOWARD, "toward value"), ("s", PLUM, "random direction"))]
    axes[0].legend(handles=h, frameon=False, fontsize=9, loc="upper left",
                   handletextpad=.5, labelspacing=.4)
    fig.tight_layout()
    out = ROOT / "plots/fig15_steer_decomposition.png"
    fig.savefig(out, dpi=170, bbox_inches="tight")
    print(f"wrote {out}\n")
    print(f"{'arm':<22} {'bias':>7} {'above-good':>12} {'below-good':>12}")
    print("-" * 56)
    for a in al:
        nm = "unsteered" if a == 0 else f"value axis {a / 1.0091 * 10:+.0f}%"
        print(f"{nm:<22} {arms[a]['bias'][0]:>7.3f} {arms[a]['above_good'][0]:>12.3f} "
              f"{arms[a]['below_good'][0]:>12.3f}")
    print(f"{'random ' + f'{cx:+.0f}%':<22} {ctrl['bias'][0]:>7.3f} "
          f"{ctrl['above_good'][0]:>12.3f} {ctrl['below_good'][0]:>12.3f}")
    ab = [arms[a]["above_good"][0] for a in al]
    be = [arms[a]["below_good"][0] for a in al]
    bi = [arms[a]["bias"][0] for a in al]
    print(f"\nr with alpha:  bias {np.corrcoef(al, bi)[0, 1]:+.3f}   "
          f"above-good {np.corrcoef(al, ab)[0, 1]:+.3f}   below-good {np.corrcoef(al, be)[0, 1]:+.3f}")
    print(f"above-good range across the value-axis arms: "
          f"{min(ab):.3f} to {max(ab):.3f}  (span {max(ab) - min(ab):.3f})")
    print(f"below-good range across the value-axis arms: "
          f"{min(be):.3f} to {max(be):.3f}  (span {max(be) - min(be):.3f})")


if __name__ == "__main__":
    main()

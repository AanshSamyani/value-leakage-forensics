"""Estimate trajectories under steering: where the answer sits, moment by moment, in each arm.

    python analysis/plot_steer_trajectories.py

One panel per steering strength. x is position through the rollout's candidate estimates
(0 = first number the model writes down, 1 = last). y is (estimate - threshold) / threshold, so
0 is exactly the threshold and the sign says which side of the bet the model is on.

Bands are the interquartile range across rollouts, not mean +/- sd: the candidate distribution has a
1135x outlier and a 99th percentile of +10.7, so a mean would be reporting the tail rather than the
trajectory. The median line is what the typical rollout does.

Read the panels left to right and the confound in the steering sweep is visible directly: the grey
baseline band slides from far above the threshold to far below it as alpha goes negative to positive,
while the two incentive bands stay pinned near zero. That gap is what the bias metric was reading.
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
R = ROOT / "data/runs"
REF = R / "qwen3.5-27b_20260823_223518"
COL = {"baseline": "#90A4AE", "above_good": "#c85a00", "below_good": "#1f77b4"}
LBL = {"baseline": "no bet", "above_good": "above-good", "below_good": "below-good"}
GRID = np.linspace(0, 1, 40)
MIN_CANDIDATES = 3          # below this there is no trajectory to speak of, only an endpoint


def curves(rolls: list, T: float) -> np.ndarray | None:
    """Resample every rollout's candidate sequence onto a common 0..1 grid."""
    out = []
    for r in rolls or []:
        v = [x for x in (r or []) if x]
        if len(v) < MIN_CANDIDATES:
            continue
        y = np.array(v, float) / T - 1.0
        out.append(np.interp(GRID, np.linspace(0, 1, len(y)), y))
    return np.array(out) if out else None


def main() -> None:
    T = float(json.loads((REF / "threshold.json").read_text())["threshold"])
    arms = [("unsteered", 0.0, REF)]
    for p in R.glob("*steer-value_axis*"):
        arms.append(("value_axis", float(p.name.split("-a")[1].split("_")[0]), p))
    ctrl = next(R.glob("*steer-random_control*"), None)
    arms.sort(key=lambda t: t[1])
    if ctrl is not None:
        arms.append(("random", float(ctrl.name.split("-a")[1].split("_")[0]), ctrl))

    fig, axes = plt.subplots(2, 3, figsize=(14.5, 7.4), sharex=True, sharey=True)
    for ax, (vec, alpha, d) in zip(axes.ravel(), arms):
        tr = json.loads((d / "trajectories.json").read_text())
        n_shown = 0
        for c in ("baseline", "above_good", "below_good"):
            C = curves(tr.get(c), T)
            if C is None:
                continue
            n_shown = max(n_shown, len(C))
            lo, md, hi = np.percentile(C, [25, 50, 75], axis=0)
            ax.fill_between(GRID, lo, hi, color=COL[c], alpha=.17, lw=0)
            ax.plot(GRID, md, color=COL[c], lw=2.1, label=LBL[c], zorder=3)
        ax.axhline(0, color="#4A4A4A", ls="--", lw=1, zorder=2)
        pct = alpha / 1.0091 * 10
        name = "unsteered" if alpha == 0 else (
            f"{'random direction' if vec == 'random' else 'value axis'}  {pct:+.0f}%")
        ax.set_title(name, fontsize=11, pad=7)
        ax.text(.985, .04, f"n={n_shown}", transform=ax.transAxes, ha="right",
                fontsize=8.5, color="#8A8177")
        ax.spines[["top", "right"]].set_visible(False)
        ax.grid(alpha=.22, lw=.6)

    axes[0, 0].set_ylim(-1.05, 1.55)
    axes[0, 0].legend(frameon=False, fontsize=9.5, loc="upper left")
    for ax in axes[1]:
        ax.set_xlabel("position in reasoning\n(0 = first candidate, 1 = last)", fontsize=9.5)
    for ax in axes[:, 0]:
        ax.set_ylabel("(estimate $-$ threshold) / threshold", fontsize=9.5)
    fig.tight_layout()
    out = ROOT / "plots" / "fig11_steer_trajectories.png"
    fig.savefig(out, dpi=170, bbox_inches="tight")
    print(f"wrote {out}")

    print(f"\n{'arm':<22} {'cond':<11} {'start':>8} {'end':>8} {'IQR at end':>18}")
    print("-" * 72)
    for vec, alpha, d in arms:
        tr = json.loads((d / "trajectories.json").read_text())
        for c in ("baseline", "above_good", "below_good"):
            C = curves(tr.get(c), T)
            if C is None:
                continue
            lo, md, hi = np.percentile(C, [25, 50, 75], axis=0)
            nm = "unsteered" if alpha == 0 else f"{vec} {alpha / 1.0091 * 10:+.0f}%"
            print(f"{nm:<22} {c:<11} {md[0]:>+8.2f} {md[-1]:>+8.2f} "
                  f"[{lo[-1]:+.2f},{hi[-1]:+.2f}]".rjust(18))


if __name__ == "__main__":
    main()

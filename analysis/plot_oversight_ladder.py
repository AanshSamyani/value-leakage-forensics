"""The oversight decomposition on its own: one panel, no annotation.

    python analysis/plot_oversight_ladder.py

Same data and same normalisation as the left panel of fig19 (see plot_oversight.py for the
footer wording and the reasoning). Written out twice:

  fig20  the four-colour palette used elsewhere in the sprint
  fig21  a single hue, light to dark along the ladder

The x tick labels already name every arm, so neither version carries a legend. In fig21 the ramp
is ordered -- light at "no observer", dark at "the bet named" -- so the shade encodes position on
the ladder rather than category identity, which is what this axis actually is.
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from plot_oversight import MAIN, R, ROOT, find, measure  # noqa: E402

GREY = "#90A4AE"
ARMS = [("obs_none", "no observer\n(dated note)"),
        ("obs_logged", "logged,\nno purpose given"),
        ("obs_accuracy", "reviewed for\naccuracy"),
        ("obs_bias", "reviewed for the\nbet's influence")]

# fig20: the sprint palette -- sage / slate / plum / clay
CATEGORICAL = ["#5F8D6E", "#6795AE", "#8A6FA3", "#CC8A5E"]
# fig21: one hue (H=201, the slate), lightness 0.74 -> 0.32
SEQUENTIAL = ["#A6C3D3", "#76A3BB", "#4C7F9B", "#35586B"]


def draw(A: dict, ref: float, colours: list[str], out: Path) -> None:
    fig, ax = plt.subplots(figsize=(6.4, 4.9))
    xs = np.arange(len(ARMS))
    keys = [v for v, _ in ARMS]
    ax.fill_between(xs, [A[k]["lo"] for k in keys], [A[k]["hi"] for k in keys],
                    color=GREY, alpha=.16, lw=0, zorder=1)
    ax.plot(xs, [A[k]["m"] for k in keys], "-", color=GREY, lw=1.7, zorder=2)
    for x, k, c in zip(xs, keys, colours):
        d = A[k]
        ax.errorbar([x], [d["m"]], yerr=[[d["m"] - d["lo"]], [d["hi"] - d["m"]]], fmt="o",
                    color=c, ms=11.5, capsize=4, lw=1.7, zorder=3)
    ax.axhline(ref, color=GREY, ls=":", lw=1.2, zorder=1)
    ax.text(len(ARMS) - .6, ref + .022, f"no footer note  ({ref:.2f})",
            fontsize=8.6, color="#5c6b73", ha="right")
    ax.axhline(0, color="#b0bec5", lw=.9, zorder=1)
    ax.set_xticks(xs)
    ax.set_xticklabels([lab for _, lab in ARMS], fontsize=9.2)
    ax.set_xlim(-.42, len(ARMS) - .58)
    ax.set_ylim(-.28, 1.0)
    ax.set_ylabel("bias (own-baseline normalised)", fontsize=10.5)
    ax.set_xlabel("what the notice says is being looked at", fontsize=10)
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(alpha=.25, lw=.6, axis="y")
    ax.tick_params(labelsize=9.2)
    fig.tight_layout()
    fig.savefig(out, dpi=170, bbox_inches="tight")
    plt.close(fig)
    print(f"wrote {out}")


def main() -> None:
    rng = np.random.default_rng(0)
    A = {v: measure(find(v), rng) for v, _ in ARMS}
    ref = measure(R / MAIN, rng)["m"]
    draw(A, ref, CATEGORICAL, ROOT / "plots/fig20_oversight_ladder.png")
    draw(A, ref, SEQUENTIAL, ROOT / "plots/fig21_oversight_ladder_mono.png")
    print()
    for v, lab in ARMS:
        d = A[v]
        print(f"  {v:<14} {d['m']:+.3f} [{d['lo']:+.3f},{d['hi']:+.3f}]  n={d['n']}")


if __name__ == "__main__":
    main()

"""Evaluation awareness, in the shape the paper plots it (Figures 29 and 30).

    python analysis/plot_eval_awareness.py

fig24 follows Figure 29: a wide light bar for any weak or indirect signal (score >= 2) with a
narrower dark bar inset on it for clear eval awareness (score >= 4), Wilson 95% intervals, counts
printed above each. The paper puts models on the x-axis; we have one model, so conditions go
there instead -- which adds the control the paper has no room for. baseline carries no donation
note, and it is the note the paper names as the likely trigger for suspicion.

fig25 follows Figure 30, the split of outcome by the rubric's decision boundary. Left panel is the
paper's own quantity, the bias metric over both arms pooled. Right panel is the same split
computed within each arm: awareness rates differ by condition and the conditions differ in bias,
so the pooled bar lets one masquerade as the other. Both are shown because the pooled number is
what compares to the paper and the per-condition one is what survives the confound.

Scores are Haiku medians over three independent judgements. Calibration against 20 hand-read
traces (analysis/calibrate_eval_awareness.py) put the mean shift at -0.16 -- the >= 4 boundary
sits where the paper put it -- but exact agreement at 21%, which is why the median is taken.
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "data/runs/qwen3.5-27b_20260823_223518"
PALE, DARK, SLATE, CLAY, GREY = "#A6C3D3", "#35586B", "#6795AE", "#CC8A5E", "#90A4AE"
CONDS = [("baseline", "baseline\n(no bet)"), ("above_good", "above-good"),
         ("below_good", "below-good")]


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (0.0, 0.0)
    p, d = k / n, 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return max(0.0, c - h), min(1.0, c + h)


def load() -> dict[str, list[tuple[int, int]]]:
    lab = json.loads((RUN / "analysis/eval_awareness.json").read_text())
    by = defaultdict(list)
    for k, v in lab.items():
        c, i = k.split("/")
        by[c].append((int(i), v["score"]))
    return by


def fig_rates(by: dict) -> None:
    """Figure 29: the >=4 bar inset on the >=2 bar."""
    fig, ax = plt.subplots(figsize=(6.6, 4.8))
    x = np.arange(len(CONDS))
    for xi, (key, _) in zip(x, CONDS):
        v = np.array([s for _, s in by[key]])
        n = len(v)
        for w, thr, colour, z in ((0.62, 2, PALE, 2), (0.30, 4, DARK, 3)):
            k = int((v >= thr).sum())
            p = k / n
            lo, hi = wilson(k, n)
            ax.bar([xi], [100 * p], w, color=colour, zorder=z)
            ax.errorbar([xi], [100 * p], yerr=[[100 * (p - lo)], [100 * (hi - p)]],
                        fmt="none", ecolor="#455A64", capsize=4, lw=1.3, zorder=z + 2)
            ax.text(xi + (0.0 if thr == 4 else 0.40), 100 * hi + 2.2, f"{100*p:.0f}",
                    ha="center", va="bottom", fontsize=9.6, color="#37474F")
    ax.set_xticks(x)
    ax.set_xticklabels([lab for _, lab in CONDS], fontsize=10.4)
    ax.set_ylim(0, 104)
    ax.set_yticks(range(0, 101, 20))
    ax.set_yticklabels([f"{v}%" for v in range(0, 101, 20)])
    ax.set_ylabel("% of scored rollouts", fontsize=10.5)
    ax.set_xlabel("condition", fontsize=10.5)
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(alpha=.25, lw=.6, axis="y")
    ax.set_axisbelow(True)
    ax.tick_params(labelsize=9.6)
    h = [plt.Rectangle((0, 0), 1, 1, color=c) for c in (PALE, DARK)]
    ax.legend(h, ["weak/indirect signal (score ≥ 2)", "eval-aware (score ≥ 4)"],
              frameon=False, fontsize=9.6, loc="upper left", handlelength=1.3,
              handletextpad=.6, labelspacing=.4)
    fig.tight_layout()
    out = ROOT / "plots/fig24_eval_awareness.png"
    fig.savefig(out, dpi=170, bbox_inches="tight")
    plt.close(fig)
    print(f"wrote {out}")


def fig_split(by: dict) -> None:
    """Figure 30: outcome split by the >=4 boundary, pooled and within condition."""
    T = float(json.loads((RUN / "threshold.json").read_text())["threshold"])
    est = json.loads((RUN / "estimates.json").read_text())
    base = np.array([float(v) for v in est["baseline"] if v is not None and float(v) > 0])
    win, ref = {}, {}
    for c in ("above_good", "below_good"):
        e = est[c]
        hit = (lambda v: v > T) if c == "above_good" else (lambda v: v <= T)
        win[c] = {i: bool(hit(float(e[i]))) for i, _ in by[c]
                  if i < len(e) and e[i] is not None and float(e[i]) > 0}
        ref[c] = float(np.mean(base > T) if c == "above_good" else np.mean(base <= T))

    groups = [("eval-aware (score ≥ 4)", lambda s: s >= 4, SLATE),
              ("not eval-aware (score < 4)", lambda s: s < 4, CLAY)]
    rng = np.random.default_rng(0)
    fig, axes = plt.subplots(1, 2, figsize=(11.6, 4.8),
                             gridspec_kw={"width_ratios": [0.78, 1.0]})

    # --- left: the paper's own quantity, both arms pooled ---------------------------------
    ax = axes[0]
    for j, (name, keep, colour) in enumerate(groups):
        ka = [win["above_good"][i] for i, s in by["above_good"] if keep(s) and i in win["above_good"]]
        kb = [win["below_good"][i] for i, s in by["below_good"] if keep(s) and i in win["below_good"]]
        bias = np.mean(ka) + np.mean(kb) - 1
        a = rng.beta(np.sum(ka) + .5, len(ka) - np.sum(ka) + .5, 200000)
        b = rng.beta(np.sum(kb) + .5, len(kb) - np.sum(kb) + .5, 200000)
        lo, hi = np.percentile(a + b - 1, [2.5, 97.5])
        ax.bar([j], [bias], 0.56, color=colour, zorder=2)
        ax.errorbar([j], [bias], yerr=[[bias - lo], [hi - bias]], fmt="none",
                    ecolor="#455A64", capsize=4, lw=1.3, zorder=3)
        ax.text(j, hi + .022, f"{bias:.3f}", ha="center", va="bottom", fontsize=10,
                color="#37474F")
        ax.text(j, .022, f"n={len(ka)}, {len(kb)}", ha="center", va="bottom", fontsize=8.8,
                color="white")
    ax.set_xticks([0, 1])
    ax.set_xticklabels(["eval-aware\n(≥ 4)", "not aware\n(< 4)"], fontsize=10)
    ax.set_ylim(0, 1.0)
    ax.set_ylabel("bias metric", fontsize=10.5)
    ax.set_xlabel("both arms pooled", fontsize=10.5)

    # --- right: the same split inside each arm --------------------------------------------
    ax = axes[1]
    x = np.arange(2)
    for j, (name, keep, colour) in enumerate(groups):
        off = (j - 0.5) * 0.34
        for xi, c in zip(x, ("above_good", "below_good")):
            v = [win[c][i] for i, s in by[c] if keep(s) and i in win[c]]
            k, n = int(np.sum(v)), len(v)
            lo, hi = wilson(k, n)
            ax.bar([xi + off], [k / n], 0.34, color=colour, label=name if xi == 0 else None,
                   zorder=2)
            ax.errorbar([xi + off], [k / n], yerr=[[k / n - lo], [hi - k / n]], fmt="none",
                        ecolor="#455A64", capsize=4, lw=1.3, zorder=3)
            ax.text(xi + off, hi + .018, f"{k/n:.3f}", ha="center", va="bottom", fontsize=9.4,
                    color="#37474F")
            ax.text(xi + off, .02, f"n={n}", ha="center", va="bottom", fontsize=8.8, color="white")
    for xi, c in zip(x, ("above_good", "below_good")):
        ax.plot([xi - .36, xi + .36], [ref[c]] * 2, ":", color=GREY, lw=1.5, zorder=4)
    ax.text(x[-1] + .40, ref["below_good"], "no-bet rate", fontsize=8.6, color="#5c6b73",
            va="center")
    ax.set_xticks(x)
    ax.set_xticklabels(["above-good", "below-good"], fontsize=10.4)
    ax.set_xlim(-.55, 1.62)
    ax.set_ylim(0, 1.06)
    ax.set_ylabel("P(the bet is won)", fontsize=10.5)
    ax.set_xlabel("within each arm, so the condition effect cannot masquerade", fontsize=10.5)
    ax.legend(frameon=False, fontsize=9.6, loc="lower left", handlelength=1.3,
              handletextpad=.6, labelspacing=.4)

    for ax in axes:
        ax.spines[["top", "right"]].set_visible(False)
        ax.grid(alpha=.25, lw=.6, axis="y")
        ax.set_axisbelow(True)
        ax.tick_params(labelsize=9.6)
    fig.tight_layout()
    out = ROOT / "plots/fig25_eval_awareness_split.png"
    fig.savefig(out, dpi=170, bbox_inches="tight")
    plt.close(fig)
    print(f"wrote {out}")


def main() -> None:
    by = load()
    fig_rates(by)
    fig_split(by)
    print()
    for key, _ in CONDS:
        v = np.array([s for _, s in by[key]])
        print(f"  {key:<11} n={len(v):>3}  mean {v.mean():.2f}  "
              f">=2 {100*(v >= 2).mean():>5.1f}%  >=4 {100*(v >= 4).mean():>5.1f}%")


if __name__ == "__main__":
    main()

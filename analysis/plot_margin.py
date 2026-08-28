"""Among rollouts that actually WON, how far past the threshold did they land?

    python analysis/plot_margin.py  ->  plots/items/b_margin_bars.png
                                        plots/items/b_margin_dists.png

Conditioned on landing on the favoured side, the margin is
    above favoured:  (estimate - T) / T
    below favoured:  (T - estimate) / T
i.e. "percent past the line", so small = hugging.

Caveat the figures cannot state: the below margin is capped at 100% (an estimate cannot go below
zero) while the above margin is unbounded. Medians are unaffected at these values, but do not read
the two directions' upper tails against each other.
"""

from __future__ import annotations

import glob
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "plots" / "items"
C_AB, C_BE = "#CC8A5E", "#6795AE"


def run(slug):
    if slug == "main":
        return ROOT / "data/runs/qwen3.5-27b_20260823_223518"
    return Path(sorted(glob.glob(str(ROOT / f"data/runs/qwen3.5-27b-{slug}_2*")))[-1])


def est(d, c):
    return [float(x) for x in json.loads((d / "estimates.json").read_text())[c] if x]


def boot(x, n=8000, seed=0):
    r = np.random.default_rng(seed)
    x = np.asarray(x, float)
    return np.percentile([np.median(x[r.integers(0, len(x), len(x))]) for _ in range(n)], [2.5, 97.5])


CASES = [("below", "p10", "sweep-below-p10"), ("below", "p25", "sweep-below-p25"),
         ("below", "base", "main"), ("above", "base", "main"),
         ("above", "p75", "sweep-above-p75"), ("above", "p90", "sweep-above-p90")]


def gather(MED):
    out = []
    for side, tag, slug in CASES:
        d = run(slug)
        T = float(json.loads((d / "threshold.json").read_text())["threshold"])
        up = side == "above"
        win = [v for v in est(d, f"{side}_good") if (v > T) == up]
        m = np.array([(v - T) / T if up else (T - v) / T for v in win]) * 100
        m = m[m > 0]
        out.append(dict(side=side, tag=tag, T=T, ratio=T / MED, m=m, n=len(m),
                        med=float(np.median(m)), ci=boot(m, seed=abs(hash(side + tag)) % 997),
                        hug1=float(np.mean(m <= 1)), hug5=float(np.mean(m <= 5))))
    return out


def bars(rows):
    rows = sorted(rows, key=lambda r: (r["ratio"], r["side"] == "above"))
    x = np.arange(len(rows))
    y = [r["med"] for r in rows]
    err = [[max(0, r["med"] - r["ci"][0]) for r in rows], [max(0, r["ci"][1] - r["med"]) for r in rows]]
    col = [C_AB if r["side"] == "above" else C_BE for r in rows]
    fig, ax = plt.subplots(figsize=(8.6, 4.9))
    ax.bar(x, y, color=col, width=0.7, zorder=3)
    ax.errorbar(x, y, yerr=err, fmt="none", ecolor="#4a4a4a", elinewidth=1.2, capsize=4, zorder=4)
    ax.axhline(0, color="#333", lw=0.9)
    ax.set_xticks(x)
    ax.set_xticklabels([f"{r['ratio']:.2f}×" for r in rows], fontsize=10)
    ax.set_xlabel("threshold ÷ the model's default estimate", fontsize=11)
    ax.set_ylabel("distance past the threshold, among rollouts that won  (%)", fontsize=11)
    ax.set_ylim(0, max(r["ci"][1] for r in rows) * 1.25)
    ax.legend(handles=[plt.Rectangle((0, 0), 1, 1, color=C_BE), plt.Rectangle((0, 0), 1, 1, color=C_AB)],
              labels=["below favoured", "above favoured"], fontsize=10, frameon=False,
              loc="upper center", ncol=2)
    ax.grid(axis="y", alpha=0.25, lw=0.6)
    ax.set_axisbelow(True)
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    fig.tight_layout()
    p = OUT / "b_margin_bars.png"
    fig.savefig(p, dpi=150, bbox_inches="tight", pad_inches=0.2)
    plt.close(fig)
    print("  ", p.name)


def kde(x, grid, h=0.18):
    """Gaussian KDE of log10(x), evaluated on `grid` (also in log10). Fixed bandwidth rather than
    Scott's rule so all six panels are directly comparable — and tight enough (0.18 decades) to keep
    the two modes at T = default, which are the point of the figure."""
    lx = np.log10(np.asarray(x, float))
    z = (grid[:, None] - lx[None, :]) / h
    return np.exp(-0.5 * z ** 2).sum(axis=1) / (len(lx) * h * np.sqrt(2 * np.pi))


def _panels(rows, draw, path, ylabel):
    by = {(r["side"], r["tag"]): r for r in rows}
    layout = [[("below", "base"), ("below", "p25"), ("below", "p10")],
              [("above", "base"), ("above", "p75"), ("above", "p90")]]
    fig, axes = plt.subplots(2, 3, figsize=(12.6, 6.4), sharex=True, sharey=True)
    for ri, row in enumerate(layout):
        for ci_, key in enumerate(row):
            r = by[key]
            ax = axes[ri][ci_]
            col = C_AB if r["side"] == "above" else C_BE
            draw(ax, r, col)
            ax.axvspan(0.01, 1, color="#4a4a4a", alpha=0.10, zorder=1)
            ax.axvline(r["med"], color="#333", lw=1.8, ls="--", zorder=5)
            ax.annotate(f"median {r['med']:.1f}%", (0.97, 0.95), xycoords="axes fraction",
                        ha="right", va="top", fontsize=10, family="monospace")
            ax.set_xscale("log")
            ax.set_title(f"{'above' if r['side'] == 'above' else 'below'} favoured   "
                         f"T = {r['ratio']:.2f}× default", fontsize=10)
            ax.grid(alpha=0.22, lw=0.5)
            ax.set_axisbelow(True)
            for sp in ("top", "right"):
                ax.spines[sp].set_visible(False)
    for ax in axes[1]:
        ax.set_xlabel("distance past the threshold (%)", fontsize=10)
        ax.set_xticks([0.1, 1, 10, 100, 1000])
        ax.set_xticklabels(["0.1%", "1%", "10%", "100%", "1000%"], fontsize=9)
    for row in axes:
        row[0].set_ylabel(ylabel, fontsize=10)
    fig.tight_layout()
    fig.savefig(path, dpi=150, bbox_inches="tight", pad_inches=0.2)
    plt.close(fig)
    print("  ", path.name)


def dists_smooth(rows):
    g = np.linspace(-2, 3, 400)
    x = 10 ** g
    dens = {(r["side"], r["tag"]): kde(r["m"], g) for r in rows}
    top = max(d.max() for d in dens.values()) * 1.10   # panels share y, so leave headroom for the tallest

    def draw(ax, r, col):
        d = dens[(r["side"], r["tag"])]
        ax.fill_between(x, d, color=col, alpha=0.42, lw=0, zorder=3)
        ax.plot(x, d, color=col, lw=2, zorder=4)
        ax.set_ylim(0, top)

    _panels(rows, draw, OUT / "b_margin_dists_smooth.png", "density")


def dists(rows):
    bins = np.logspace(-2, 3, 34)

    def draw(ax, r, col):
        ax.hist(r["m"], bins=bins, color=col, alpha=0.8, zorder=3)

    _panels(rows, draw, OUT / "b_margin_dists.png", "rollouts that won")


def overlay(rows, palette, path):
    """Two panels, three KDE curves each: the same rung ordering in both, so colour encodes distance
    from the model's default and the panel encodes direction."""
    by = {(r["side"], r["tag"]): r for r in rows}
    groups = {"above favoured": [("above", "base"), ("above", "p75"), ("above", "p90")],
              "below favoured": [("below", "base"), ("below", "p25"), ("below", "p10")]}
    g = np.linspace(-2, 3, 400)
    x = 10 ** g
    dens = {k: kde(r["m"], g) for k, r in by.items()}
    top = max(d.max() for d in dens.values()) * 1.10

    fig, axes = plt.subplots(1, 2, figsize=(12.4, 5.0), sharey=True, sharex=True)
    for ax, (ttl, keys) in zip(axes, groups.items()):
        for key, col in zip(keys, palette):
            r, d = by[key], dens[key]
            lab = f"T = {r['ratio']:.2f}× default   ·   median {r['med']:.1f}%"
            ax.fill_between(x, d, color=col, alpha=0.30, lw=0, zorder=3)
            ax.plot(x, d, color=col, lw=2.2, zorder=4, label=lab)
            ax.axvline(r["med"], color=col, lw=1.4, ls="--", alpha=0.85, zorder=5)
        ax.set_xscale("log")
        ax.set_ylim(0, top)
        ax.set_xticks([0.1, 1, 10, 100, 1000])
        ax.set_xticklabels(["0.1%", "1%", "10%", "100%", "1000%"], fontsize=9.5)
        ax.set_xlabel("distance past the threshold (%)", fontsize=10.5)
        ax.set_title(ttl, fontsize=11.5)
        ax.legend(fontsize=9.5, frameon=False, loc="upper right")
        ax.grid(alpha=0.22, lw=0.5)
        ax.set_axisbelow(True)
        for sp in ("top", "right"):
            ax.spines[sp].set_visible(False)
    axes[0].set_ylabel("density", fontsize=10.5)
    fig.tight_layout()
    fig.savefig(path, dpi=150, bbox_inches="tight", pad_inches=0.2)
    plt.close(fig)
    print("  ", path.name)


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    MED = float(np.median(est(run("main"), "baseline")))
    rows = gather(MED)
    bars(rows)
    dists(rows)
    dists_smooth(rows)
    # palette 1: the clay / slate already in use, plus a muted plum for the third rung
    overlay(rows, ["#6795AE", "#CC8A5E", "#9C8AA6"], OUT / "b_margin_overlay.png")
    # palette 2: a fresh SEQUENTIAL ramp — the rungs are ordered (distance from the default), so a
    # ramp encodes that ordering, which three unrelated hues cannot
    overlay(rows, ["#C7B8D6", "#9878B0", "#5E3D7A"], OUT / "b_margin_overlay_alt.png")
    for r in sorted(rows, key=lambda r: (r["ratio"], r["side"] == "above")):
        print(f"   {r['side']+' '+r['tag']:<12} T={r['ratio']:.2f}×  n={r['n']:>3}  "
              f"median {r['med']:>5.1f}% [{r['ci'][0]:.1f}, {r['ci'][1]:.1f}]  "
              f"≤1% {r['hug1']:.0%}  ≤5% {r['hug5']:.0%}")

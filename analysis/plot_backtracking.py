"""Value axis around backtracking events — Figure 3c of Jiang et al. (arXiv:2606.17056), for our task.

    python analysis/plot_backtracking.py   ->  plots/items/value_backtracking.png
                                               plots/items/value_trace.png

value_trace.png   one rollout: the projection at every reasoning token, with each backtracking
                  marker drawn as a tick. The "see it in a single trace" view.
value_backtracking.png
                  the event-aligned average: every marker across every rollout, lined up at zero.
                  Their claim is that the projection DROPS at the event.

Two departures from the paper, both forced by our data:

  * They contrast rollouts with backtracking against rollouts without. We cannot — "Wait" appears in
    299 of 300 rollouts, 6,994 times. Every trace self-corrects, so their Figure 3b has no contrast
    here and only the event-aligned panel carries over.
  * Each rollout is centred on its own mean before averaging. Between-rollout offsets are large
    compared with the local dip, so without centring the average measures which rollouts happen to
    contribute events at each lag rather than what happens at an event.

The random control is plotted alongside. Any direction wanders, so a dip only means something if the
value axis dips and the control does not.
"""

from __future__ import annotations

import argparse
import glob
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "plots" / "items"
COL = {"value_axis": "#CC8A5E", "random_control": "#6795AE"}


def load(run_dir: Path):
    fs = sorted(glob.glob(str(run_dir / "analysis" / "pertoken" / "*.npz")))
    if not fs:
        raise SystemExit(f"no per-token files under {run_dir}/analysis/pertoken — "
                         f"run scripts/08c_pertoken_hf.py first")
    return [np.load(f, allow_pickle=True) for f in fs]


def aligned(files, li_idx, v_idx, half=400, min_gap=120, edge=200):
    """Event-aligned matrix, each rollout centred on its own mean.

    Events closer together than min_gap are dropped: overlapping windows would smear one dip into its
    neighbour and manufacture a trend.
    """
    rows = []
    for f in files:
        p = f["proj"][li_idx, :, v_idx].astype(np.float32)
        if len(p) < 2 * half:
            continue
        p = p - p.mean()
        ev = np.sort(f["events"])
        keep = [e for k, e in enumerate(ev)
                if edge <= e < len(p) - edge
                and (k == 0 or e - ev[k - 1] >= min_gap)
                and (k == len(ev) - 1 or ev[k + 1] - e >= min_gap)]
        for e in keep:
            lo, hi = e - half, e + half
            seg = np.full(2 * half, np.nan, np.float32)
            a, b = max(0, lo), min(len(p), hi)
            seg[a - lo: b - lo] = p[a:b]
            rows.append(seg)
    return np.array(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", default="qwen3.5-27b_20260823_223518")
    ap.add_argument("--layer", type=int, default=None, help="default: the deepest available")
    ap.add_argument("--half", type=int, default=400)
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    d = Path(a.run) if Path(a.run).is_dir() else ROOT / "data/runs" / a.run
    files = load(d)
    layers = list(files[0]["layers"]); names = [str(x) for x in files[0]["vectors"]]
    li = a.layer if a.layer is not None else max(layers)
    li_idx = layers.index(li)
    print(f"{len(files)} rollouts, layers {layers}, vectors {names}; plotting layer {li}")

    # ---- event-aligned
    x = np.arange(-a.half, a.half)
    fig, ax = plt.subplots(figsize=(9.2, 5.2))
    for nm in names:
        A = aligned(files, li_idx, names.index(nm), half=a.half)
        if not len(A):
            continue
        m = np.nanmean(A, axis=0)
        se = np.nanstd(A, axis=0) / np.sqrt(np.sum(~np.isnan(A), axis=0))
        ax.fill_between(x, m - 1.96 * se, m + 1.96 * se, color=COL.get(nm, "#888"), alpha=0.22, lw=0)
        ax.plot(x, m, color=COL.get(nm, "#888"), lw=2.2,
                label=f"{nm.replace('_', ' ')}  (n={len(A):,} events)")
        print(f"  {nm}: {len(A):,} events, dip at 0 = {m[a.half]:+.3f}, "
              f"pre-event mean {np.nanmean(m[:a.half//2]):+.3f}")
    ax.axvline(0, color="#333", lw=1.4, ls="--")
    ax.axhline(0, color="#999", lw=0.8)
    ax.set_xlabel("tokens relative to the backtracking marker", fontsize=11.5)
    ax.set_ylabel("value-axis projection, each rollout centred on its own mean", fontsize=11.5)
    ax.legend(fontsize=10, frameon=False, loc="lower right")
    ax.grid(alpha=0.22, lw=0.5); ax.set_axisbelow(True)
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    fig.tight_layout()
    fig.savefig(OUT / "value_backtracking.png", dpi=150, bbox_inches="tight", pad_inches=0.2)
    plt.close(fig); print("  ", "value_backtracking.png")

    # ---- one trace, the rollout with the most events
    f = max(files, key=lambda f: len(f["events"]))
    p = f["proj"][li_idx, :, names.index("value_axis")].astype(np.float32)
    k = 51
    sm = np.convolve(p, np.ones(k) / k, mode="same")
    fig, ax = plt.subplots(figsize=(11, 4.6))
    ax.plot(np.arange(len(p)), p, color=COL["value_axis"], lw=0.5, alpha=0.30)
    ax.plot(np.arange(len(sm))[k:-k], sm[k:-k], color=COL["value_axis"], lw=2.0)
    for e in f["events"]:
        ax.axvline(int(e), color="#333", lw=0.7, alpha=0.45)
    ax.set_xlabel(f"reasoning token   ({f['cond']}/#{int(f['i'])}, "
                  f"{len(f['events'])} backtracking markers marked)", fontsize=11)
    ax.set_ylabel("value-axis projection", fontsize=11.5)
    ax.grid(alpha=0.22, lw=0.5); ax.set_axisbelow(True)
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    fig.tight_layout()
    fig.savefig(OUT / "value_trace.png", dpi=150, bbox_inches="tight", pad_inches=0.2)
    plt.close(fig); print("  ", "value_trace.png")


if __name__ == "__main__":
    main()

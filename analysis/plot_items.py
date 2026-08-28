"""One figure per experiment item (a-g), in adsingh-64/value-leakage's plotting style.

    python analysis/plot_items.py            -> plots/items/{a,b1,b2,c,d,e,f,g}_*.png

Style, ported in forensics/analysis/trajectory_plot.py:
    y  = (estimate - threshold) / threshold        0 == the threshold, shared across conditions
    x  = normalised position in the reasoning      0 = first candidate, 1 = last
    per-condition median line + IQR band, condition labelled at the right end of its own curve.

Two deviations, both because the threshold sweep breaks the original assumptions:

  ARTIFACT CUT is absolute (5e6), not T/20. The judge sometimes captures a giraffe *population*
  count (~1e5) as a spot total; candidate values have a clean empty gap between 1e6 and 1e7 so a
  fixed cut separates them. A T-relative rule cuts at 1.2e8 on the 2x-max rung and eats real data.

  OUTLIER BAND is [T/10, T*10] only where T sits inside the data (every run at the reference
  threshold). On the sweep, T is deliberately far from the data — the paper's filter keeps 6% of the
  2x-max rung — so there the band is taken around the BASELINE MEDIAN instead. n is printed on every
  curve so the cost is visible.
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
RUNS = ROOT / "data" / "runs"
OUT = ROOT / "plots" / "items"
REF = "qwen3.5-27b_20260823_223518"
GIRAFFE_CUT = 5e6
N_GRID = 1000
COLORS = {"baseline": "#90A4AE", "below_good": "#1f77b4", "above_good": "#c85a00"}
LABELS = {"baseline": "baseline", "below_good": "below favoured", "above_good": "above favoured"}
ORDER = ("baseline", "below_good", "above_good")


def newest(slug):
    if slug == "main":
        return RUNS / REF
    c = sorted(glob.glob(str(RUNS / f"qwen3.5-27b-{slug}_2*")))
    return Path(c[-1]) if c else None


def load(slug):
    d = newest(slug)
    if d is None or not d.is_dir():
        return None
    T = float(json.loads((d / "threshold.json").read_text())["threshold"])
    tr = json.loads((d / "trajectories.json").read_text())
    est = json.loads((d / "estimates.json").read_text()) if (d / "estimates.json").exists() else {}
    cfg = json.loads((d / "config.json").read_text()) if (d / "config.json").exists() else {}
    giraffe = "giraffe" in (cfg.get("task") or "giraffe").lower()
    be = [float(x) for x in est.get("baseline", []) if x]
    med = float(np.median(be)) if be else T
    cut = GIRAFFE_CUT if giraffe else med / 20
    # band centre: T when it sits inside the data, else the baseline median (sweep rungs)
    centre = T if abs(np.log10(max(T, 1) / max(med, 1))) < 0.35 else med
    traj = {}
    for c in ORDER:
        keep = []
        for t in tr.get(c, []) or []:
            if not t:
                continue
            xs = [float(v) for v in t if float(v) >= cut and centre / 10 <= float(v) <= centre * 10]
            if len(xs) >= 2:
                keep.append(xs)
        traj[c] = keep
    return {"dir": d, "T": T, "median": med, "traj": traj, "slug": slug}


def curve(trajs, T):
    if not trajs:
        return None
    g = np.linspace(0, 1, N_GRID)
    S = (np.vstack([np.interp(g, np.linspace(0, 1, len(t)), t) for t in trajs]) - T) / T
    lo, hi = np.percentile(S, [25, 75], axis=0)
    return np.median(S, axis=0), lo, hi, len(trajs)


def draw(ax, run, conds, title, annot=True):
    g = np.linspace(0, 1, N_GRID)
    ends = []
    for c in conds:
        p = curve(run["traj"].get(c) or [], run["T"])
        if p is None:
            continue
        centre, lo, hi, n = p
        ax.fill_between(g, lo, hi, color=COLORS[c], alpha=0.15, linewidth=0)
        ax.plot(g, centre, color=COLORS[c], linewidth=2)
        ends.append((centre[-1], f"{LABELS[c]}  n={n}", COLORS[c]))
    # nudge labels apart when curves converge (they do exactly where the finding is "no separation")
    ends.sort()
    span = (max(e[0] for e in ends) - min(e[0] for e in ends)) if len(ends) > 1 else 0
    lim = ax.get_ylim()
    minsep = max((lim[1] - lim[0]) * 0.055, span * 0.001)
    placed = []
    for y, txt, col in ends:
        yy = y if not placed else max(y, placed[-1] + minsep)
        placed.append(yy)
        ax.annotate(txt, xy=(1.0, y), xytext=(4, 0), textcoords="offset points",
                    va="center", fontsize=7.5, color=col) if yy == y else \
            ax.annotate(txt, xy=(1.0, yy), xytext=(4, 0), textcoords="offset points",
                        va="center", fontsize=7.5, color=col)
    ax.axhline(0, color="#6b6b6b", linewidth=0.9, linestyle="--", zorder=0)
    a = curve(run["traj"].get("above_good") or [], run["T"])
    b = curve(run["traj"].get("below_good") or [], run["T"])
    if annot and a and b:
        s, e = float(a[0][0] - b[0][0]), float(a[0][-1] - b[0][-1])
        ax.text(0.025, 0.965, f"gap @ first candidate  {s:+.3f}\ngap @ last            {e:+.3f}",
                transform=ax.transAxes, va="top", fontsize=7, family="monospace",
                bbox=dict(boxstyle="round,pad=0.35", fc="white", ec="#d9d9d9", lw=0.7, alpha=0.92))
    ax.set_xlim(0, 1)
    ax.grid(True, alpha=0.25, linewidth=0.6)
    ax.set_axisbelow(True)
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    ax.set_title(title, fontsize=9.5)


def figure(specs, cols, path, suptitle, sub, sharey=False, w=4.3, h=3.3):
    n = len(specs)
    rows = int(np.ceil(n / cols))
    fig, axes = plt.subplots(rows, cols, figsize=(w * cols, h * rows), squeeze=False, sharey=sharey)
    for ax in axes.flat[n:]:
        ax.axis("off")
    for ax, (run, conds, title) in zip(axes.flat, specs):
        draw(ax, run, conds, title)
    for ax in axes.flat[max(0, n - cols):n]:
        ax.set_xlabel("Normalised position in reasoning", fontsize=8.5)
    for r in axes:
        r[0].set_ylabel("(estimate − threshold) / threshold", fontsize=8.5)
    top = 0.90 if rows == 1 else (0.93 if rows == 2 else 0.95)
    fig.tight_layout(rect=[0, 0, 1, top])
    fig.suptitle(suptitle, fontsize=13, fontweight="bold", y=0.995, va="top")
    fig.text(0.5, top + (0.995 - top) * 0.30, sub, ha="center", va="top", fontsize=8.5, color="#555")
    fig.savefig(path, dpi=150, bbox_inches="tight", pad_inches=0.25)
    plt.close(fig)
    print("  ", path.name)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    L = load
    main_run = L("main")
    ALL3, BOTH = list(ORDER), ["below_good", "above_good"]
    print("items:")

    figure([(main_run, ALL3, "main — threshold shown (104,475,000)"),
            (L("hidden-threshold"), ALL3, "1a — threshold hidden")],
           2, OUT / "a_hidden_threshold.png", "1a  Does the effect need a visible threshold?",
           "With the number withheld the two arms sit on top of each other and neither separates from baseline.",
           sharey=True, w=5.2, h=4.0)

    ab = [(main_run, "T = baseline median  (1.00× med)")] + [
        (L(f"sweep-above-{t}"), f"T = {t}  ({L(f'sweep-above-{t}')['T']/main_run['median']:.2f}× med)")
        for t in ("p75", "p90", "p95", "max", "2max")]
    figure([(r, ["baseline", "above_good"], t) for r, t in ab if r], 3,
           OUT / "b1_threshold_up.png", "1b.1  Threshold walked UP the baseline distribution",
           "y = 0 is that panel's own threshold. Reaching 0 means the reasoning arrived at the number it was given.",
           sharey=True)

    bl = [(main_run, "T = baseline median  (1.00× med)")] + [
        (L(f"sweep-below-{t}"), f"T = {t}  ({main_run['median']/L(f'sweep-below-{t}')['T']:.2f}× below med)")
        for t in ("p25", "p10", "min", "halfmin")]
    figure([(r, ["baseline", "below_good"], t) for r, t in bl if r], 3,
           OUT / "b2_threshold_down.png", "1b.2  Threshold walked DOWN the baseline distribution",
           "y = 0 is that panel's own threshold — note each panel has its OWN y-scale, since T moves 14× "
           "across the ladder.",
           sharey=False)

    stk = [(main_run, "no amount stated (main)")] + [
        (L(s), f"stake = {t}") for t, s in (("$5", "stakes-low"), ("$10", "stakes-10"), ("$1k", "stakes-1k"),
                                            ("$100k", "stakes-100k"), ("$1M", "stakes-high"),
                                            ("$10M", "stakes-10m"), ("$100M", "stakes-100m"))]
    figure([(r, ALL3, t) for r, t in stk if r], 4, OUT / "c_bet_amount.png",
           "1c  Bet-amount ladder", "Eight rungs, $5 to $100M. Nothing separates — the curves are the same shape throughout.",
           sharey=True, w=3.9, h=3.1)

    lad = [(L("known-answer-un"), "UN member states"), (L("q-everest"), "Mt Everest (m)"),
           (L("q-lagos"), "Lagos population"), (main_run, "giraffe spots"),
           (L("q-trees"), "trees on Earth"), (L("q-sand"), "grains of sand")]
    figure([(r, ALL3, t) for r, t in lad if r], 3, OUT / "d_determinism.png",
           "1d  Determinism ladder",
           "An empty panel means every rollout gave a single candidate — there is no reasoning path to draw.",
           w=4.3, h=3.3)

    figure([(main_run, ALL3, "main — the estimate settles the bet"),
            (L("settles-on-truth"), ALL3, "1e.1 — settles on an independent true value"),
            (L("no-consequence"), ALL3, "1e.2 — bet already settled")],
           3, OUT / "e_no_control.png", "1e  Does it still bias when its answer changes nothing?",
           "Remove the model's causal lever and the two arms collapse onto each other from the first candidate.",
           sharey=True, w=4.6, h=3.8)

    figure([(main_run, ALL3, "main — phrase present"),
            (L("no-phrase-footer"), ALL3, "1f-A — footer sentence removed"),
            (L("no-phrase-both"), ALL3, "1f-B — footer + header removed")],
           3, OUT / "f_accuracy_phrase.png", "1f  Is “most accurate point estimate” protective?",
           "The gap is widest at the FIRST candidate and narrows from there — the phrase acts on the opening move.",
           sharey=True, w=4.6, h=3.8)

    figure([(main_run, ALL3, "main — flat payoff"),
            (L("proportional"), ALL3, "1g — payoff proportional to |estimate − T|")],
           2, OUT / "g_proportional.png", "1g  Does a payoff that rewards distance move it further?",
           "A payoff that explicitly pays for leaving the line produces the same curves as one that does not.",
           sharey=True, w=5.2, h=4.0)


if __name__ == "__main__":
    main()

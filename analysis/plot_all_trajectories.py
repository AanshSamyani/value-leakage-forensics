"""Trajectory plots for every starter-batch run.

    python analysis/plot_all_trajectories.py            # sheets + cross-run syntheses
    python analysis/plot_all_trajectories.py --per-run  # also one PNG per run

A trajectory is the ordered list of candidate estimates the judge pulled out of one rollout's
reasoning. x is position within the rollout (0 = first candidate, 1 = last), y is the value.

Two filtering notes that matter:

* ARTIFACT CUT is ABSOLUTE, not T-relative. The judge sometimes captures a giraffe *population*
  count (~1e5) as if it were a spot total. The candidate distribution has a clean empty gap between
  1e6 and 1e7, so a fixed 5e6 cut separates them. The old T/20 rule was calibrated at T=104M and
  would cut at 1.2e8 on the 2x-max rung — eating real data and making the sweep look like it drifts.
* DISPLAY BAND is relative to the BASELINE MEDIAN, not T. The paper's +/-10x-of-T filter throws away
  94% of the 2x-max rung, because there T is nowhere near the data. That is the finding, not noise.
"""

from __future__ import annotations

import argparse
import glob
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / "data" / "runs"
OUT = ROOT / "plots" / "traj"
REF = "qwen3.5-27b_20260823_223518"
GIRAFFE_CUT = 5e6          # absolute; sits inside the empty 1e6-1e7 gap
COL = {"baseline": "#5b6467", "above_good": "#3f6497", "below_good": "#8a6a00"}
LBL = {"baseline": "baseline", "above_good": "above_good", "below_good": "below_good"}
SHORT = {"baseline": "base", "above_good": "above", "below_good": "below"}
GRID = 50


def newest(slug):
    c = sorted(glob.glob(str(RUNS / f"qwen3.5-27b-{slug}_2*")))
    return c[-1] if c else None


def load(run_dir):
    d = Path(run_dir)
    if not d.is_dir():
        return None
    tr = json.loads((d / "trajectories.json").read_text()) if (d / "trajectories.json").exists() else {}
    est = json.loads((d / "estimates.json").read_text()) if (d / "estimates.json").exists() else {}
    T = float(json.loads((d / "threshold.json").read_text())["threshold"])
    cfg = json.loads((d / "config.json").read_text()) if (d / "config.json").exists() else {}
    q = (cfg.get("task") or "")
    giraffe = "giraffe" in q.lower() or not q
    base_est = [float(x) for x in est.get("baseline", []) if x]
    med = float(np.median(base_est)) if base_est else T
    cut = GIRAFFE_CUT if giraffe else med / 20
    out = {"dir": d, "T": T, "median": med, "cut": cut, "giraffe": giraffe, "traj": {}}
    for c in COL:
        keep = []
        for t in tr.get(c, []):
            if not t:
                continue
            xs = [float(v) for v in t if float(v) >= cut]
            if xs:
                keep.append(xs)
        out["traj"][c] = keep
    return out


def med_path(trajs):
    """Median candidate value at each normalised position, over rollouts with >=2 candidates."""
    L = [t for t in trajs if len(t) >= 2]
    if len(L) < 5:
        return None, None
    g = np.linspace(0, 1, GRID)
    M = np.array([np.interp(g, np.linspace(0, 1, len(t)), np.log10(t)) for t in L])
    return g, 10 ** np.median(M, axis=0)


def panel(ax, run, conds, title, show_med_ref=True, nmax=60):
    T, med = run["T"], run["median"]
    for c in conds:
        L = run["traj"].get(c) or []
        if not L:
            continue
        for t in L[:nmax]:
            x = np.linspace(0, 1, len(t)) if len(t) > 1 else [0.5]
            ax.plot(x, t, color=COL[c], alpha=0.10, lw=0.8, solid_capstyle="round",
                    marker="." if len(t) == 1 else None, ms=3)
        g, m = med_path(L)
        if m is not None:
            ax.plot(g, m, color=COL[c], lw=2.4, label=f"{LBL[c]} (n={len(L)})", zorder=5)
        else:
            ax.axhline(float(np.median([t[-1] for t in L])), color=COL[c], lw=2.4, ls=(0, (4, 2)),
                       label=f"{LBL[c]} (n={len(L)}, single-value)", zorder=5)
    ax.axhline(T, color="#c0392b", lw=1.6, ls="--", zorder=6)
    ax.text(1.004, T, " T", color="#c0392b", va="center", ha="left", fontsize=8,
            transform=ax.get_yaxis_transform(), fontweight="bold")
    if show_med_ref and abs(np.log10(med / T)) > 0.02:
        ax.axhline(med, color="#2f6b4f", lw=1.2, ls=":", zorder=6)
        ax.text(1.004, med, " base\n med", color="#2f6b4f", va="center", ha="left", fontsize=7,
                transform=ax.get_yaxis_transform())
    ax.set_yscale("log")
    ax.set_xlim(-0.02, 1.02)
    ax.set_title(title, fontsize=9.5, pad=5)
    ax.grid(alpha=0.18, lw=0.5)
    ax.tick_params(labelsize=8)


def sheet(specs, cols, path, suptitle, sub=""):
    n = len(specs)
    rows = int(np.ceil(n / cols))
    fig, axes = plt.subplots(rows, cols, figsize=(3.5 * cols, 2.9 * rows), squeeze=False)
    for ax in axes.flat[n:]:
        ax.axis("off")
    for ax, (run, conds, title) in zip(axes.flat, specs):
        panel(ax, run, conds, title)
        ax.legend(fontsize=6.5, loc="upper left", framealpha=0.9)
    for ax in axes[-1]:
        ax.set_xlabel("position in reasoning (0 = first candidate, 1 = last)", fontsize=7.5)
    for r in axes:
        r[0].set_ylabel("candidate estimate", fontsize=8)
    top = 0.90 if rows <= 2 else 0.94
    fig.tight_layout(rect=[0, 0, 1, top])
    fig.suptitle(suptitle, fontsize=12.5, fontweight="bold", y=0.995, va="top")
    if sub:
        fig.text(0.5, top + (0.995 - top) * 0.28, sub, ha="center", va="top", fontsize=8.5, color="#555")
    fig.savefig(path, dpi=150)
    plt.close(fig)
    print("  ", path.name)


# --------------------------------------------------------------------------- cross-run figures

def fig_convergence(above, below, ref, path):
    """Every rung's median path, divided by that rung's OWN T. Landing on 1.0 == the model
    answered the number in the prompt."""
    fig, axes = plt.subplots(1, 2, figsize=(12.5, 4.6), sharey=True)
    for ax, rungs, cond, ttl in ((axes[0], above, "above_good", "above_good — threshold walked UP"),
                                 (axes[1], below, "below_good", "below_good — threshold walked DOWN")):
        cm = plt.cm.viridis(np.linspace(0.08, 0.9, len(rungs)))
        for (tag, run), col in zip(rungs, cm):
            g, m = med_path(run["traj"].get(cond) or [])
            r = run["T"] / ref["median"]
            lab = f"{tag}  (T={r:.2f}×med)"
            if m is None:
                L = run["traj"].get(cond) or []
                if not L:
                    continue
                ax.axhline(float(np.median([t[-1] for t in L])) / run["T"], color=col, lw=2, ls=":", label=lab)
            else:
                ax.plot(g, m / run["T"], color=col, lw=2.4, label=lab)
        ax.axhline(1.0, color="#c0392b", lw=1.6, ls="--", zorder=1)
        ax.text(0.012, 1.0, " estimate == threshold", color="#c0392b", fontsize=8, va="bottom", fontweight="bold")
        ax.set_yscale("log")
        ax.set_title(ttl, fontsize=11)
        ax.set_xlabel("position in reasoning", fontsize=9)
        ax.grid(alpha=0.2, lw=0.5)
        ax.legend(fontsize=7.5, loc="best", framealpha=0.92)
    axes[0].set_ylabel("median candidate ÷ that rung's threshold", fontsize=9.5)
    fig.suptitle("Does the reasoning converge on the threshold it was given?",
                 fontsize=13, fontweight="bold")
    fig.text(0.5, 0.925, "Inside the reachable envelope every rung lands on 1.0. Outside it they flatten out "
             "far from the line and stop trying.", ha="center", fontsize=9, color="#555")
    fig.tight_layout(rect=[0, 0, 1, 0.90])
    fig.savefig(path, dpi=150)
    plt.close(fig)
    print("  ", path.name)


def fig_halting(entries, path):
    """First / middle / last candidate: fraction on the favoured side of T."""
    rows = []
    for label, run, conds in entries:
        for c in conds:
            L = [t for t in (run["traj"].get(c) or []) if len(t) >= 3]
            if len(L) < 15:
                continue
            up = c != "below_good"
            f = lambda v: (v > run["T"]) == up
            first = np.mean([f(t[0]) for t in L])
            mid = np.mean([f(v) for t in L for v in t[1:-1]])
            last = np.mean([f(t[-1]) for t in L])
            rows.append((f"{label} · {SHORT[c]}", c, first, mid, last, len(L)))
    fig, ax = plt.subplots(figsize=(max(10, 0.42 * len(rows)), 5.4))
    x = np.arange(len(rows))
    for i, (lab, c, a, b, d, n) in enumerate(rows):
        ax.plot([i - 0.26, i, i + 0.26], [a, b, d], color=COL[c], lw=1.6, marker="o", ms=5.5,
                mfc="white", mew=1.6, zorder=3)
        ax.annotate(f"{d:.2f}", (i + 0.26, d), textcoords="offset points", xytext=(0, 8 if d > b else -13),
                    ha="center", fontsize=7, color=COL[c], fontweight="bold")
    ax.axhline(0.5, color="#888", lw=1, ls="--")
    ax.set_xticks(x)
    ax.set_xticklabels([r[0] for r in rows], fontsize=7.5, rotation=42, ha="right",
                       rotation_mode="anchor")
    ax.set_ylabel("fraction on the favoured side of T", fontsize=9.5)
    ax.set_ylim(0, 1)
    ax.grid(axis="y", alpha=0.2, lw=0.5)
    ax.set_title("Where the bias enters: first → middle → last candidate  (each triple, left to right)",
                 fontsize=12, fontweight="bold")
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)
    print("  ", path.name)


def fig_deliberation(entries, path):
    """How many candidates the model tries before it stops."""
    labs, data, cols = [], [], []
    for label, run, conds in entries:
        for c in conds:
            L = run["traj"].get(c) or []
            if len(L) < 15:
                continue
            labs.append(f"{label} · {SHORT[c]}")
            data.append([len(t) for t in L])
            cols.append(COL[c])
    fig, ax = plt.subplots(figsize=(max(10, 0.42 * len(labs)), 5.4))
    parts = ax.violinplot(data, showextrema=False, widths=0.85)
    for b, c in zip(parts["bodies"], cols):
        b.set_facecolor(c); b.set_alpha(0.42); b.set_edgecolor(c); b.set_lw(1)
    for i, (d, c) in enumerate(zip(data, cols), 1):
        ax.plot(i, np.median(d), "o", color=c, ms=7, mfc="white", mew=1.8, zorder=4)
        ax.annotate(f"{int(np.median(d))}", (i, np.median(d)), textcoords="offset points",
                    xytext=(0, 10), ha="center", fontsize=7.5, fontweight="bold", color=c)
    ax.set_xticks(range(1, len(labs) + 1))
    ax.set_xticklabels(labs, fontsize=7.5, rotation=42, ha="right", rotation_mode="anchor")
    ax.set_ylabel("candidates per rollout", fontsize=9.5)
    ax.set_yscale("log")
    ax.grid(axis="y", alpha=0.2, lw=0.5)
    ax.set_title("How much it deliberates  (median annotated)", fontsize=12, fontweight="bold")
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)
    print("  ", path.name)


# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--per-run", action="store_true", help="also write one PNG per run")
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    ref = load(RUNS / REF)
    G = lambda s: load(newest(s))
    BOTH, ALL3 = ["above_good", "below_good"], ["baseline", "above_good", "below_good"]

    ABOVE = [("median (main)", ref)] + [(t, G(f"sweep-above-{t}")) for t in ("p75", "p90", "p95", "max", "2max")]
    BELOW = [("median (main)", ref)] + [(t, G(f"sweep-below-{t}")) for t in ("p25", "p10", "min", "halfmin")]
    ABOVE = [(t, r) for t, r in ABOVE if r]
    BELOW = [(t, r) for t, r in BELOW if r]

    print("sheets:")
    sheet([(r, ["baseline", "above_good"], f"T = {t}  ({r['T']/ref['median']:.2f}× median)") for t, r in ABOVE],
          3, OUT / "1b_above_sweep.png", "1b.1  threshold walked UP",
          "red dashed = that run's threshold · green dotted = baseline median · thick line = median path")
    sheet([(r, ["baseline", "below_good"], f"T = {t}  ({ref['median']/r['T']:.2f}× below median)") for t, r in BELOW],
          3, OUT / "1b_below_sweep.png", "1b.2  threshold walked DOWN",
          "red dashed = that run's threshold · green dotted = baseline median · thick line = median path")

    STK = [("none (main)", ref), ("$5", G("stakes-low")), ("$10", G("stakes-10")), ("$1k", G("stakes-1k")),
           ("$100k", G("stakes-100k")), ("$1M", G("stakes-high")), ("$10M", G("stakes-10m")),
           ("$100M", G("stakes-100m"))]
    sheet([(r, ALL3, f"stake = {t}") for t, r in STK if r], 4, OUT / "1c_stakes.png",
          "1c  bet-amount ladder", "bias is flat across the whole ladder — so are the paths")

    LAD = [("UN member states", G("known-answer-un")), ("Mt Everest", G("q-everest")),
           ("Lagos population", G("q-lagos")), ("giraffe spots", ref),
           ("trees on Earth", G("q-trees")), ("grains of sand", G("q-sand"))]
    sheet([(r, ALL3, t) for t, r in LAD if r], 3, OUT / "1d_determinism.png",
          "1d  determinism ladder",
          "flat dashed = every rollout gave a single candidate, so there is no path to draw")

    OTH = [("main", ref), ("1a hidden threshold", G("hidden-threshold")),
           ("1e.1 settles on truth", G("settles-on-truth")), ("1e.2 already settled", G("no-consequence")),
           ("1f-A footer removed", G("no-phrase-footer")), ("1f-B footer+header", G("no-phrase-both")),
           ("1g proportional", G("proportional")), ("user prefers bad", G("user-prefers-bad"))]
    sheet([(r, ALL3, t) for t, r in OTH if r], 4, OUT / "1aefg_variants.png",
          "1a · 1e · 1f · 1g  (and the sycophancy control)", "all share T = 104,475,000")

    print("cross-run:")
    fig_convergence(ABOVE, BELOW, ref, OUT / "sweep_convergence.png")
    SHORT_OTH = {"1a hidden threshold": "1a hidden-T", "1e.1 settles on truth": "1e.1 on-truth",
                 "1e.2 already settled": "1e.2 settled", "1f-A footer removed": "1f-A",
                 "1f-B footer+header": "1f-B", "1g proportional": "1g prop",
                 "user prefers bad": "syco"}
    ENT = ([("main", ref, ALL3)]
           + [(f"T={t}", r, ["above_good"]) for t, r in ABOVE[1:]]
           + [(f"T={t}", r, ["below_good"]) for t, r in BELOW[1:]]
           + [(SHORT_OTH.get(t, t), r, BOTH) for t, r in OTH[1:] if r])
    fig_halting(ENT, OUT / "halting_all.png")
    fig_deliberation(ENT, OUT / "deliberation_all.png")

    if a.per_run:
        print("per-run:")
        seen = set()
        for t, r in ABOVE + BELOW + STK + LAD + OTH:
            if not r or r["dir"] in seen:
                continue
            seen.add(r["dir"])
            conds = [c for c in ALL3 if r["traj"].get(c)]
            fig, ax = plt.subplots(figsize=(6.2, 4.2))
            panel(ax, r, conds, r["dir"].name)
            ax.legend(fontsize=7.5)
            ax.set_xlabel("position in reasoning", fontsize=9)
            ax.set_ylabel("candidate estimate", fontsize=9)
            fig.tight_layout()
            p = OUT / f"run_{r['dir'].name.replace('qwen3.5-27b','q35')}.png"
            fig.savefig(p, dpi=140)
            plt.close(fig)
            print("  ", p.name)


if __name__ == "__main__":
    main()

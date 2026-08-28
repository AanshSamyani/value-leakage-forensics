"""
Plots from trajectories.json — no new model runs, pure analysis of data already on disk.

A "trajectory" is the ordered list of candidate estimates the judge extracted from one
rollout's chain of thought. Element 0 is the first number the model floated; the last
element is (in ~90% of rollouts) the number it actually answered with.

Outputs land in plots/.  Run:  python3 analysis/plot_trajectories.py
"""
import json, os, math
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAIN = os.path.join(ROOT, "data/runs/qwen3.5-27b_20260823_223518")
OUT = os.path.join(ROOT, "plots"); os.makedirs(OUT, exist_ok=True)

CONDS = ["baseline", "above_good", "below_good"]
LABEL = {"baseline": "baseline (no bet)",
         "above_good": "above_good  (high = good cause)",
         "below_good": "below_good  (low = good cause)"}
# achromatic-friendly, colourblind-safe
COL = {"baseline": "#5b6467", "above_good": "#3f6497", "below_good": "#8a6a00"}

plt.rcParams.update({
    "figure.dpi": 130, "savefig.dpi": 130, "savefig.bbox": "tight",
    "font.size": 9, "axes.titlesize": 10, "axes.labelsize": 9,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.alpha": .25, "grid.linewidth": .6,
    "legend.frameon": False, "figure.facecolor": "white",
})


# ---------------------------------------------------------------- load & clean
def load(run=MAIN):
    T = json.load(open(f"{run}/threshold.json"))["threshold"]
    traj = json.load(open(f"{run}/trajectories.json"))
    est = json.load(open(f"{run}/estimates.json"))
    out = {}
    for c in CONDS:
        rows = []
        for i, x in enumerate(traj[c]):
            if not isinstance(x, list):
                continue
            xs = [v for v in x if isinstance(v, (int, float)) and v > 0]
            if not xs:
                continue
            e = est[c][i] if i < len(est[c]) else None
            rows.append(dict(i=i, cand=xs, final=(e if e is not None else xs[-1])))
        out[c] = rows
    return T, out


def drop_population_artifact(rows, T, cut=None):
    """The judge sometimes captured a giraffe *population* count (~1e5) as if it were a
    spot-total candidate. Those sit ~3 orders of magnitude below the threshold. We strip
    any candidate below T/20 and drop rollouts left with nothing."""
    cut = cut or T / 20
    kept = []
    for r in rows:
        xs = [v for v in r["cand"] if v >= cut]
        if xs:
            kept.append(dict(r, cand=xs))
    return kept


def wilson(k, n, z=1.96):
    if n == 0:
        return (0, 0, 0)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return p, max(0, c - h), min(1, c + h)


T, DATA = load()
CLEAN = {c: drop_population_artifact(DATA[c], T) for c in CONDS}


# ---------------------------------------------------------------- 1. spaghetti
def fig1():
    fig, axes = plt.subplots(1, 3, figsize=(12.4, 4.0), sharey=True)
    for ax, c in zip(axes, CONDS):
        rows = CLEAN[c]
        for r in rows:
            y = np.array(r["cand"], float)
            above = r["final"] > T
            ax.plot(range(1, len(y) + 1), y / T, lw=.7, alpha=.45,
                    color=("#b0453c" if above else "#2f6f5e"))
        ax.axhline(1.0, color="black", lw=1.2, ls="--", zorder=5)
        ax.set_yscale("log"); ax.set_xscale("symlog", linthresh=10)
        ax.set_title(f"{LABEL[c]}\nn={len(rows)}")
        ax.set_xlabel("candidate # within the chain of thought")
        ax.set_ylim(1e-2, 1e2)
    axes[0].set_ylabel("candidate value ÷ threshold\n(1.0 = exactly at threshold)")
    fig.legend(handles=[Line2D([], [], color="#b0453c", lw=2, label="rollout ended ABOVE threshold"),
                        Line2D([], [], color="#2f6f5e", lw=2, label="rollout ended BELOW threshold"),
                        Line2D([], [], color="black", lw=1.2, ls="--", label="threshold")],
               loc="lower center", ncol=3, bbox_to_anchor=(.5, -.06))
    fig.suptitle("Fig 1 — Every candidate estimate, in threshold units", y=1.02, fontsize=11)
    fig.savefig(f"{OUT}/fig1_trajectories.png"); plt.close(fig)


# ------------------------------------------------- 2. the halting test (H1)
def fig2():
    """Is a candidate more likely to be above T at the END than in the MIDDLE?"""
    fig, ax = plt.subplots(figsize=(7.4, 4.0))
    buckets = ["first", "middle", "last"]
    W, stats = .26, {}
    for k, c in enumerate(CONDS):
        rows = [r for r in CLEAN[c] if len(r["cand"]) >= 3]
        vals = {b: [] for b in buckets}
        for r in rows:
            xs = r["cand"]
            vals["first"].append(xs[0] > T)
            vals["last"].append(xs[-1] > T)
            vals["middle"] += [v > T for v in xs[1:-1]]
        stats[c] = {b: wilson(sum(vals[b]), len(vals[b])) for b in buckets}
        xs_ = np.arange(len(buckets)) + (k - 1) * W
        p = [stats[c][b][0] for b in buckets]
        err = [[p[j] - stats[c][b][1] for j, b in enumerate(buckets)],
               [stats[c][b][2] - p[j] for j, b in enumerate(buckets)]]
        ax.bar(xs_, p, W * .9, color=COL[c], label=f"{LABEL[c]}  (n={len(rows)})")
        ax.errorbar(xs_, p, yerr=err, fmt="none", ecolor="#333", elinewidth=.9, capsize=2.5)
    ax.axhline(.5, color="black", lw=.9, ls=":")
    ax.set_xticks(range(len(buckets)))
    ax.set_xticklabels(["FIRST candidate", "MIDDLE candidates\n(all of them)", "LAST candidate\n(= the answer)"])
    ax.set_ylabel("fraction of candidates above the threshold")
    ax.set_ylim(0, 1); ax.legend(loc="upper left")
    ax.set_title("Fig 2 — Where in the reasoning does the bias appear?\n"
                 "If middle ≈ baseline but last is skewed, the incentive acts on when the model STOPS.")
    fig.savefig(f"{OUT}/fig2_halting.png"); plt.close(fig)
    json.dump({c: {b: stats[c][b] for b in buckets} for c in CONDS},
              open(f"{OUT}/fig2_halting.json", "w"), indent=1)
    return stats


# ---------------------------------------------- 3. margin / hole near threshold
def fig3():
    fig, axes = plt.subplots(1, 2, figsize=(11.4, 3.9))
    rel = {c: np.array([(r["final"] - T) / T for r in CLEAN[c]]) for c in CONDS}
    b = np.linspace(-1, 2, 46)
    for c in CONDS:
        axes[0].hist(np.clip(rel[c], -1, 2), bins=b, histtype="step", lw=1.6,
                     color=COL[c], label=LABEL[c])
    axes[0].axvline(0, color="black", lw=1.2, ls="--")
    axes[0].set_xlabel("(final estimate − threshold) ÷ threshold")
    axes[0].set_ylabel("rollouts"); axes[0].legend(fontsize=7.5)
    axes[0].set_title("full range")

    bz = np.linspace(-.30, .30, 25)
    for c in ["above_good", "below_good"]:
        axes[1].hist(rel[c][np.abs(rel[c]) <= .30], bins=bz, histtype="step", lw=1.8,
                     color=COL[c], label=LABEL[c])
    axes[1].axvline(0, color="black", lw=1.2, ls="--")
    axes[1].axvspan(-.01, .01, color="#b0453c", alpha=.13)
    axes[1].set_xlabel("(final estimate − threshold) ÷ threshold")
    axes[1].set_title("zoom: ±30% around the threshold\n(shaded = within ±1%)")
    axes[1].legend(fontsize=7.5)
    fig.suptitle("Fig 3 — How far past the line do the answers land?", y=1.04, fontsize=11)
    fig.savefig(f"{OUT}/fig3_margin.png"); plt.close(fig)

    rep = {}
    for c in CONDS:
        r = rel[c]
        rep[c] = {"n": len(r),
                  "within_1pct": int((np.abs(r) <= .01).sum()),
                  "within_5pct": int((np.abs(r) <= .05).sum()),
                  "in_3_to_15pct_favoured": int((((r > .03) & (r < .15)).sum()) if c == "above_good"
                                                else ((r < -.03) & (r > -.15)).sum())}
    json.dump(rep, open(f"{OUT}/fig3_margin.json", "w"), indent=1)
    return rep


# ------------------------------------------- 4. prior gating + inverted-U (H2/H4)
def fig4():
    fig, axes = plt.subplots(1, 2, figsize=(11.4, 4.0))
    for c in ["above_good", "below_good"]:
        rows = CLEAN[c]
        x = np.array([r["cand"][0] / T for r in rows])
        y = np.array([1 if r["final"] > T else 0 for r in rows])
        j = (np.random.RandomState(0).rand(len(y)) - .5) * .10
        axes[0].scatter(x, y + j, s=16, alpha=.65, color=COL[c], label=LABEL[c], lw=0)
    axes[0].set_xscale("log"); axes[0].axvline(1, color="black", lw=1.1, ls="--")
    axes[0].set_xlabel("FIRST candidate ÷ threshold  (log)")
    axes[0].set_yticks([0, 1]); axes[0].set_yticklabels(["ended below T", "ended above T"])
    axes[0].set_title("Does the opening guess decide the outcome?")
    axes[0].legend(fontsize=7.5, loc="center left")

    for c in CONDS:
        rows = [r for r in CLEAN[c] if len(r["cand"]) >= 1]
        d = np.array([abs(math.log10(r["cand"][0] / T)) for r in rows])
        n = np.array([len(r["cand"]) for r in rows], float)
        axes[1].scatter(d, n, s=15, alpha=.55, color=COL[c], label=LABEL[c], lw=0)
        if len(d) > 12:  # binned median trend
            bins = np.quantile(d, np.linspace(0, 1, 6))
            cx, cy = [], []
            for a, b_ in zip(bins[:-1], bins[1:]):
                m = (d >= a) & (d <= b_)
                if m.sum() >= 3:
                    cx.append(np.median(d[m])); cy.append(np.median(n[m]))
            axes[1].plot(cx, cy, color=COL[c], lw=1.8)
    axes[1].set_xlabel("|log10(first candidate ÷ threshold)|   0 = opens exactly at the line")
    axes[1].set_ylabel("number of candidates in the trace")
    axes[1].set_title("Is the most reasoning done near the line?")
    axes[1].legend(fontsize=7.5)
    fig.suptitle("Fig 4 — The opening guess", y=1.03, fontsize=11)
    fig.savefig(f"{OUT}/fig4_prior_gating.png"); plt.close(fig)


# ---------------------------------------------------- 5. how much deliberation
def fig5():
    fig, ax = plt.subplots(figsize=(7.0, 3.9))
    data = [[len(r["cand"]) for r in CLEAN[c]] for c in CONDS]
    parts = ax.violinplot(data, showmedians=True, widths=.75)
    for pc, c in zip(parts["bodies"], CONDS):
        pc.set_facecolor(COL[c]); pc.set_alpha(.55); pc.set_edgecolor("none")
    for key in ("cbars", "cmins", "cmaxes", "cmedians"):
        parts[key].set_color("#333"); parts[key].set_linewidth(1.0)
    for k, d in enumerate(data, 1):
        ax.text(k, max(d) + 1.5, f"median {int(np.median(d))}", ha="center", fontsize=8.5)
    ax.set_xticks([1, 2, 3]); ax.set_xticklabels([LABEL[c] for c in CONDS], fontsize=8)
    ax.set_ylabel("candidates considered per rollout")
    ax.set_title("Fig 5 — Does the bet make the model think more, or less?")
    fig.savefig(f"{OUT}/fig5_deliberation.png"); plt.close(fig)


# ---------------------------------------------------------- 6. within-trace drift
def fig6():
    fig, ax = plt.subplots(figsize=(7.4, 4.0))
    grid = np.linspace(0, 1, 21)
    for c in CONDS:
        rows = [r for r in CLEAN[c] if len(r["cand"]) >= 4]
        M = []
        for r in rows:
            y = np.array(r["cand"], float) / T
            pos = np.linspace(0, 1, len(y))
            M.append(np.interp(grid, pos, y))
        M = np.array(M)
        med = np.median(M, 0)
        lo, hi = np.percentile(M, 25, 0), np.percentile(M, 75, 0)
        ax.plot(grid, med, color=COL[c], lw=2, label=f"{LABEL[c]} (n={len(rows)})")
        ax.fill_between(grid, lo, hi, color=COL[c], alpha=.13, lw=0)
    ax.axhline(1.0, color="black", lw=1.2, ls="--")
    ax.set_yscale("log")
    ax.set_xlabel("position through the chain of thought  (0 = start, 1 = final answer)")
    ax.set_ylabel("candidate value ÷ threshold")
    ax.legend(fontsize=7.5)
    ax.set_title("Fig 6 — Median path through the reasoning\n"
                 "(band = interquartile range; only traces with ≥4 candidates)")
    fig.savefig(f"{OUT}/fig6_drift.png"); plt.close(fig)


# -------------------------------------------------- 7. first → last movement
def fig7():
    fig, axes = plt.subplots(1, 2, figsize=(10.6, 4.4), sharex=True, sharey=True)
    for ax, c in zip(axes, ["above_good", "below_good"]):
        rows = CLEAN[c]
        x = np.array([r["cand"][0] / T for r in rows])
        y = np.array([r["final"] / T for r in rows])
        moved_up = y > x
        ax.scatter(x[moved_up], y[moved_up], s=20, color="#b0453c", alpha=.7, lw=0, label="moved up")
        ax.scatter(x[~moved_up], y[~moved_up], s=20, color="#2f6f5e", alpha=.7, lw=0, label="moved down")
        lims = [1e-2, 1e2]
        ax.plot(lims, lims, color="#999", lw=.9, ls=":")
        ax.axhline(1, color="black", lw=1.1, ls="--"); ax.axvline(1, color="black", lw=1.1, ls="--")
        ax.set_xscale("log"); ax.set_yscale("log"); ax.set_xlim(*lims); ax.set_ylim(*lims)
        ax.set_title(f"{LABEL[c]}\nmoved up {moved_up.sum()}/{len(rows)}")
        ax.set_xlabel("first candidate ÷ threshold")
        ax.legend(fontsize=7.5, loc="lower right")
    axes[0].set_ylabel("final answer ÷ threshold")
    fig.suptitle("Fig 7 — Where it started vs where it ended", y=1.02, fontsize=11)
    fig.savefig(f"{OUT}/fig7_first_vs_last.png"); plt.close(fig)


# ------------------------------------------------------------- 8. artifact check
def fig8():
    fig, ax = plt.subplots(figsize=(7.0, 3.8))
    cut = T / 20
    fr, lab = [], []
    for c in CONDS:
        rows = DATA[c]
        n = len(rows)
        k = sum(1 for r in rows if r["cand"][0] < cut)
        p, lo, hi = wilson(k, n)
        fr.append((p, p - lo, hi - p)); lab.append(f"{LABEL[c]}\n{k}/{n}")
    xs = np.arange(3)
    ax.bar(xs, [f[0] for f in fr], .55, color=[COL[c] for c in CONDS])
    ax.errorbar(xs, [f[0] for f in fr], yerr=np.array([[f[1] for f in fr], [f[2] for f in fr]]),
                fmt="none", ecolor="#333", elinewidth=1, capsize=3)
    ax.set_xticks(xs); ax.set_xticklabels(lab, fontsize=8)
    ax.set_ylabel(f"fraction whose FIRST candidate < T/20\n(i.e. looks like a population count)")
    ax.set_title("Fig 8 — The parse artifact, quantified\n"
                 "Baseline is contaminated ~4–7× more than the incentive arms.")
    fig.savefig(f"{OUT}/fig8_parse_artifact.png"); plt.close(fig)


# ------------------------------------------------------------ 9. ablation bias
def fig9():
    import csv, glob
    rows = []
    for d in sorted(glob.glob(os.path.join(ROOT, "data/runs/qwen3.5-27b*"))):
        try:
            r = list(csv.DictReader(open(f"{d}/summary.csv")))[0]
            cfg = json.load(open(f"{d}/config.json"))
            rows.append((cfg.get("variant") or "MAIN", float(r["bias"]), cfg.get("task")))
        except Exception:
            pass
    rows.sort(key=lambda x: x[1])
    fig, ax = plt.subplots(figsize=(7.6, 4.0))
    ys = np.arange(len(rows))
    cols = ["#8a6a00" if b < 0.05 else "#3f6497" for _, b, _ in rows]
    ax.barh(ys, [b for _, b, _ in rows], .6, color=cols)
    ax.set_yticks(ys); ax.set_yticklabels([f"{v}" + ("" if t == "giraffes" else f"  [{t}]")
                                           for v, _, t in rows], fontsize=8.5)
    ax.axvline(0, color="black", lw=1)
    for y, (_, b, _) in zip(ys, rows):
        ax.text(b + (.015 if b >= 0 else -.015), y, f"{b:+.2f}",
                va="center", ha="left" if b >= 0 else "right", fontsize=8.5)
    ax.set_xlabel("bias   =   2 × (fraction landing on the favoured side − 0.5)")
    ax.set_xlim(-.25, .75)
    ax.set_title("Fig 9 — What removes the effect?  (runs already on disk)")
    fig.savefig(f"{OUT}/fig9_ablations.png"); plt.close(fig)
    return rows


if __name__ == "__main__":
    fig1(); s2 = fig2(); m3 = fig3(); fig4(); fig5(); fig6(); fig7(); fig8(); abl = fig9()
    print("wrote 9 figures to plots/\n")
    print("Fig 2 — fraction of candidates above threshold")
    for c in CONDS:
        f, m, l = s2[c]["first"][0], s2[c]["middle"][0], s2[c]["last"][0]
        print(f"  {c:11} first={f:.2f}  middle={m:.2f}  last={l:.2f}")
    print("\nFig 3 — final estimates near the threshold")
    for c, v in m3.items():
        print(f"  {c:11} within±1%={v['within_1pct']:>2}  within±5%={v['within_5pct']:>2}  "
              f"favoured 3–15% band={v['in_3_to_15pct_favoured']:>2}   (n={v['n']})")
    print("\nFig 9 — bias by variant")
    for v, b, t in abl:
        print(f"  {v:22} {b:+.2f}")

"""E2 — where does the bias enter the reasoning? (start shift vs biased revision/stopping)

Three pre-specified tests, each with the BASELINE condition as control under the same labelling
('good' = above for comparison with above_good; 'good' = below for comparison with below_good):

  T1 start shift        P(first candidate > T) by condition vs baseline.
  T2 biased stopping    reasoning length (completion tokens; fallback #candidates) by
                        first-estimate side x condition; interaction vs baseline.
  T3 dynamics           transition probabilities P(move toward good | on bad side) vs
                        P(move toward bad | on good side), and the stopping hazard
                        P(trajectory ends here | side of current candidate), vs baseline.
                        (The trajectory judge never repeats consecutive numbers, so every step is a move;
                        regression toward the median pushes both 'toward' rates above 0.5 — hence the
                        baseline control under the same labelling.)

Inputs: trajectories.json (trajectory judge), threshold.json, rows[*].usage.completion_tokens.
Outputs: run_dir/analysis/e2/{t1_start.csv,t2_length.csv,t3_transitions.csv,t3_hazard.csv,summary.md,*.png}
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from forensics.runs import OUTLIER_FACTOR, Run, rollout_frame
from forensics.stats import bootstrap_diff_ci, wilson_ci

LABELLINGS = {"above_good": True, "below_good": False}  # good_above


def _rate(mask) -> tuple[float, int, float, float]:
    s = pd.Series(mask).dropna().astype(bool)
    n = len(s)
    k = int(s.sum())
    lo, hi = wilson_ci(k, n)
    return (k / n if n else float("nan"), n, lo, hi)


# ---------------------------------------------------------------------------
# T1 — start shift
# ---------------------------------------------------------------------------

def t1_start_shift(df: pd.DataFrame, n_boot: int = 2000) -> pd.DataFrame:
    recs = []
    d = df[df.first_above.notna() & df.traj_ok]
    for cond in ["baseline", "above_good", "below_good"]:
        s = d[d.cond == cond]
        p, n, lo, hi = _rate(s.first_above)
        recs.append(dict(metric="P(first > T)", cond=cond, value=p, n=n, ci_lo=lo, ci_hi=hi))
    a = d[d.cond == "above_good"].first_above.astype(float).to_numpy()
    b = d[d.cond == "below_good"].first_above.astype(float).to_numpy()
    base = d[d.cond == "baseline"].first_above.astype(float).to_numpy()
    if len(a) and len(b):
        lo, hi = bootstrap_diff_ci(a, b, n_boot=n_boot)
        recs.append(dict(metric="P(first>T|above_good) - P(first>T|below_good)", cond="diff", value=a.mean() - b.mean(),
                         n=len(a) + len(b), ci_lo=lo, ci_hi=hi))
    if len(a) and len(base):
        lo, hi = bootstrap_diff_ci(a, base, n_boot=n_boot)
        recs.append(dict(metric="P(first>T|above_good) - P(first>T|baseline)", cond="diff_vs_base", value=a.mean() - base.mean(),
                         n=len(a) + len(base), ci_lo=lo, ci_hi=hi))
    if len(b) and len(base):
        lo, hi = bootstrap_diff_ci(base, b, n_boot=n_boot)
        recs.append(dict(metric="P(first>T|baseline) - P(first>T|below_good)", cond="diff_vs_base", value=base.mean() - b.mean(),
                         n=len(b) + len(base), ci_lo=lo, ci_hi=hi))
    # pooled first-on-favoured-side
    fav = d[d.cond.isin(["above_good", "below_good"])]
    pf = (fav.first_side == "good")
    p, n, lo, hi = _rate(pf)
    recs.append(dict(metric="P(first on favoured side)", cond="pooled", value=p, n=n, ci_lo=lo, ci_hi=hi))
    return pd.DataFrame(recs)


# ---------------------------------------------------------------------------
# T2 — length by first side x condition, interaction vs baseline
# ---------------------------------------------------------------------------

def _length_col(df: pd.DataFrame) -> str:
    return "tokens" if df.tokens.notna().mean() > 0.8 else "K"


def t2_length(df: pd.DataFrame, n_boot: int = 2000) -> tuple[pd.DataFrame, str]:
    col = _length_col(df)
    d = df[df.first_above.notna() & df.traj_ok & df[col].notna()].copy()
    d["logL"] = np.log(d[col].astype(float).clip(lower=1))
    recs = []
    inter = []
    for cond, good_above in LABELLINGS.items():
        inc = d[d.cond == cond]
        base = d[d.cond == "baseline"]
        # side under this labelling
        inc_bad = inc[inc.first_side == "bad"]
        inc_good = inc[inc.first_side == "good"]
        base_bad = base[base.first_above != good_above]
        base_good = base[base.first_above == good_above]
        for name, grp in [("incentive", (inc_bad, inc_good)), ("baseline", (base_bad, base_good))]:
            bad, good = grp
            for side, g in [("bad", bad), ("good", good)]:
                recs.append(dict(comparison=cond, condition=name, first_side=side, n=len(g),
                                 mean_len=g[col].mean() if len(g) else float("nan"),
                                 median_len=g[col].median() if len(g) else float("nan"),
                                 mean_logL=g.logL.mean() if len(g) else float("nan")))
        # deltas and interaction (on log length — robust to skew — and on raw)
        for scale in ["logL", col]:
            d_inc = inc_bad[scale].mean() - inc_good[scale].mean() if len(inc_bad) and len(inc_good) else float("nan")
            d_base = base_bad[scale].mean() - base_good[scale].mean() if len(base_bad) and len(base_good) else float("nan")
            # bootstrap interaction
            rng = np.random.default_rng(0)
            vals = []
            if len(inc_bad) and len(inc_good) and len(base_bad) and len(base_good):
                ib, ig = inc_bad[scale].to_numpy(float), inc_good[scale].to_numpy(float)
                bb, bg = base_bad[scale].to_numpy(float), base_good[scale].to_numpy(float)
                for _ in range(n_boot):
                    vals.append((ib[rng.integers(0, len(ib), len(ib))].mean() - ig[rng.integers(0, len(ig), len(ig))].mean())
                                - (bb[rng.integers(0, len(bb), len(bb))].mean() - bg[rng.integers(0, len(bg), len(bg))].mean()))
                lo, hi = np.percentile(vals, [2.5, 97.5])
            else:
                lo = hi = float("nan")
            inter.append(dict(comparison=cond, scale=scale, delta_incentive=d_inc, delta_baseline=d_base,
                              interaction=d_inc - d_base, ci_lo=lo, ci_hi=hi,
                              n_inc_bad=len(inc_bad), n_inc_good=len(inc_good), n_base_bad=len(base_bad), n_base_good=len(base_good)))
    cells = pd.DataFrame(recs)
    inter_df = pd.DataFrame(inter)
    inter_df["metric"] = "length_interaction"
    out = pd.concat([cells.assign(metric="cell"), inter_df], ignore_index=True, sort=False)
    return out, col


# ---------------------------------------------------------------------------
# T3 — transitions and stopping hazard
# ---------------------------------------------------------------------------

def _steps(traj: list, T: float, good_above: bool) -> list[dict]:
    """Per-position records: side of current candidate, move direction to next, whether it is the last."""
    out = []
    K = len(traj)
    for t in range(K):
        cur = traj[t]
        side = "good" if ((cur > T) == good_above) else "bad"
        if t < K - 1:
            nxt = traj[t + 1]
            if nxt == cur:
                move = "same"
            else:
                up = nxt > cur
                move = "toward_good" if (up == good_above) else "toward_bad"
        else:
            move = None
        out.append(dict(t=t, K=K, side=side, move=move, is_last=(t == K - 1)))
    return out


def _step_frame(run: Run, df: pd.DataFrame) -> pd.DataFrame:
    """All steps for incentive rollouts (own labelling) and baseline rollouts (both labellings)."""
    T = run.threshold
    recs = []
    ok = df[df.traj_ok & (df.K >= 1)]
    for _, r in ok.iterrows():
        traj = run.trajectory(r.cond, int(r.i))
        if not traj:
            continue
        if r.cond in LABELLINGS:
            for s in _steps(traj, T, LABELLINGS[r.cond]):
                recs.append(dict(group=r.cond, rollout=f"{r.cond}/{int(r.i)}", **s))
        elif r.cond == "baseline":
            for name, ga in LABELLINGS.items():
                for s in _steps(traj, T, ga):
                    recs.append(dict(group=f"baseline[good={'above' if ga else 'below'}]", rollout=f"baseline/{int(r.i)}", **s))
    return pd.DataFrame(recs)


def _cluster_boot_rate(sub: pd.DataFrame, num_mask, den_mask, n_boot: int = 1000, seed: int = 0) -> tuple[float, float]:
    """Bootstrap a ratio sum(num)/sum(den) resampling ROLLOUTS (clusters)."""
    if len(sub) == 0:
        return (float("nan"), float("nan"))
    g = sub.assign(_num=num_mask.astype(float), _den=den_mask.astype(float)).groupby("rollout")[["_num", "_den"]].sum()
    arr = g.to_numpy()
    rng = np.random.default_rng(seed)
    vals = []
    for _ in range(n_boot):
        idx = rng.integers(0, len(arr), len(arr))
        s = arr[idx].sum(axis=0)
        vals.append(s[0] / s[1] if s[1] > 0 else np.nan)
    vals = np.asarray(vals)
    vals = vals[~np.isnan(vals)]
    if len(vals) == 0:
        return (float("nan"), float("nan"))
    return (float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5)))


def t3_transitions(steps: pd.DataFrame) -> pd.DataFrame:
    recs = []
    moves = steps[steps.move.notna()]
    for group, s in moves.groupby("group"):
        bad = s[s.side == "bad"]
        good = s[s.side == "good"]
        # P(toward good | bad), P(toward bad | good), P(same | side)
        for side, sub, target in [("bad", bad, "toward_good"), ("good", good, "toward_bad")]:
            n = len(sub)
            k = int((sub.move == target).sum())
            lo, hi = _cluster_boot_rate(sub, sub.move == target, pd.Series(True, index=sub.index))
            recs.append(dict(group=group, side=side, metric=f"P({target} | on {side} side)", p=(k / n if n else float("nan")),
                             k=k, n_steps=n, n_rollouts=sub.rollout.nunique(), ci_lo=lo, ci_hi=hi))
    out = pd.DataFrame(recs)
    # asymmetry per group: P(toward good|bad) - P(toward bad|good)
    asym = []
    for group, s in out.groupby("group"):
        pg = s[(s.side == "bad") & s.metric.str.startswith("P(toward_good")].p.values
        pb = s[(s.side == "good") & s.metric.str.startswith("P(toward_bad")].p.values
        if len(pg) and len(pb):
            asym.append(dict(group=group, side="both", metric="asymmetry: P(toward good|bad) - P(toward bad|good)",
                             p=float(pg[0] - pb[0]), k=np.nan, n_steps=np.nan, n_rollouts=np.nan, ci_lo=np.nan, ci_hi=np.nan))
    return pd.concat([out, pd.DataFrame(asym)], ignore_index=True)


def t3_hazard(steps: pd.DataFrame) -> pd.DataFrame:
    """Stopping hazard: P(this candidate is the last | side). Also excluding t=0 (single-candidate rollouts)."""
    recs = []
    for group, s in steps.groupby("group"):
        for side in ["good", "bad"]:
            sub = s[s.side == side]
            n = len(sub)
            k = int(sub.is_last.sum())
            lo, hi = _cluster_boot_rate(sub, sub.is_last, pd.Series(True, index=sub.index))
            recs.append(dict(group=group, side=side, metric="hazard P(stop | side)", p=(k / n if n else float("nan")),
                             k=k, n_steps=n, ci_lo=lo, ci_hi=hi))
            sub2 = sub[sub.K >= 2]
            n2 = len(sub2)
            k2 = int(sub2.is_last.sum())
            recs.append(dict(group=group, side=side, metric="hazard P(stop | side), K>=2", p=(k2 / n2 if n2 else float("nan")),
                             k=k2, n_steps=n2, ci_lo=np.nan, ci_hi=np.nan))
    out = pd.DataFrame(recs)
    diffs = []
    for group, s in out[out.metric == "hazard P(stop | side)"].groupby("group"):
        hg = s[s.side == "good"].p.values
        hb = s[s.side == "bad"].p.values
        if len(hg) and len(hb):
            diffs.append(dict(group=group, side="both", metric="hazard(good) - hazard(bad)", p=float(hg[0] - hb[0]),
                              k=np.nan, n_steps=np.nan, ci_lo=np.nan, ci_hi=np.nan))
            diffs.append(dict(group=group, side="both", metric="hazard ratio good/bad", p=float(hg[0] / hb[0]) if hb[0] else float("nan"),
                              k=np.nan, n_steps=np.nan, ci_lo=np.nan, ci_hi=np.nan))
    return pd.concat([out, pd.DataFrame(diffs)], ignore_index=True)


# ---------------------------------------------------------------------------
# Figures + driver
# ---------------------------------------------------------------------------

def _yerr(p, lo, hi):
    p = np.asarray(p, dtype=float); lo = np.asarray(lo, dtype=float); hi = np.asarray(hi, dtype=float)
    return [np.nan_to_num(np.clip(p - lo, 0, None), nan=0.0), np.nan_to_num(np.clip(hi - p, 0, None), nan=0.0)]


def _fig_t2(t2: pd.DataFrame, col: str, out: Path, title: str):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    cells = t2[t2.metric == "cell"]
    fig, axes = plt.subplots(1, 2, figsize=(10, 4), sharey=True)
    for ax, comp in zip(axes, ["above_good", "below_good"]):
        c = cells[cells.comparison == comp]
        x = np.arange(2)
        w = 0.38
        for j, condition in enumerate(["incentive", "baseline"]):
            s = c[c.condition == condition].set_index("first_side").reindex(["bad", "good"])
            ax.bar(x + (j - 0.5) * w, s.mean_len, w, label=f"{condition} (n={int(s.n.sum())})")
        ax.set_xticks(x)
        ax.set_xticklabels(["first on BAD side", "first on GOOD side"])
        ax.set_title(f"{comp} vs baseline[same labelling]")
        ax.legend(fontsize=8)
    axes[0].set_ylabel(f"mean reasoning length ({col})")
    fig.suptitle(title)
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)


def _fig_t3(trans: pd.DataFrame, haz: pd.DataFrame, out: Path, title: str):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    groups = ["above_good", "baseline[good=above]", "below_good", "baseline[good=below]"]
    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    ax = axes[0]
    x = np.arange(len(groups))
    w = 0.38
    tg = trans[trans.metric.str.startswith("P(toward_good")].set_index("group").reindex(groups)
    tb = trans[trans.metric.str.startswith("P(toward_bad")].set_index("group").reindex(groups)
    ax.bar(x - w / 2, tg.p, w, yerr=_yerr(tg.p, tg.ci_lo, tg.ci_hi), capsize=3, label="P(move toward good | on bad side)")
    ax.bar(x + w / 2, tb.p, w, yerr=_yerr(tb.p, tb.ci_lo, tb.ci_hi), capsize=3, label="P(move toward bad | on good side)")
    ax.set_xticks(x)
    ax.set_xticklabels(groups, rotation=20, ha="right", fontsize=8)
    ax.set_ylim(0, 1)
    ax.set_title("Revision direction")
    ax.legend(fontsize=8)
    ax = axes[1]
    hz = haz[haz.metric == "hazard P(stop | side)"]
    hg = hz[hz.side == "good"].set_index("group").reindex(groups)
    hb = hz[hz.side == "bad"].set_index("group").reindex(groups)
    ax.bar(x - w / 2, hg.p, w, yerr=_yerr(hg.p, hg.ci_lo, hg.ci_hi), capsize=3, label="hazard | on good side")
    ax.bar(x + w / 2, hb.p, w, yerr=_yerr(hb.p, hb.ci_lo, hb.ci_hi), capsize=3, label="hazard | on bad side")
    ax.set_xticks(x)
    ax.set_xticklabels(groups, rotation=20, ha="right", fontsize=8)
    top = np.nanmax(np.concatenate([hg.ci_hi.to_numpy(float), hb.ci_hi.to_numpy(float)]))
    ax.set_ylim(0, (top * 1.6) if np.isfinite(top) and top > 0 else 1)
    ax.set_title("Stopping hazard P(this candidate is the last)")
    ax.legend(fontsize=8)
    fig.suptitle(title)
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)


def run_e2(run: Run, out_dir: Path | None = None, outlier_factor: float | None = OUTLIER_FACTOR) -> dict:
    out_dir = Path(out_dir) if out_dir else run.run_dir / "analysis" / "e2"
    out_dir.mkdir(parents=True, exist_ok=True)
    df = rollout_frame(run, outlier_factor=outlier_factor)
    df.to_csv(out_dir / "rollout_frame.csv", index=False)
    t1 = t1_start_shift(df)
    t2, col = t2_length(df)
    steps = _step_frame(run, df)
    trans = t3_transitions(steps) if len(steps) else pd.DataFrame()
    haz = t3_hazard(steps) if len(steps) else pd.DataFrame()
    t1.to_csv(out_dir / "t1_start.csv", index=False)
    t2.to_csv(out_dir / "t2_length.csv", index=False)
    steps.to_csv(out_dir / "t3_steps.csv", index=False)
    trans.to_csv(out_dir / "t3_transitions.csv", index=False)
    haz.to_csv(out_dir / "t3_hazard.csv", index=False)
    _fig_t2(t2, col, out_dir / "t2_length.png", f"{run.model}: T2 biased stopping")
    if len(trans) and len(haz):
        _fig_t3(trans, haz, out_dir / "t3_dynamics.png", f"{run.model}: T3 dynamics")

    lines = [f"# E2 — {run.model} ({run.name})", "", f"threshold = {run.threshold:,.0f}; length column = {col}", "",
             "## T1 start shift", ""]
    for _, r in t1.iterrows():
        lines.append(f"- {r.metric} [{r.cond}]: {r.value:.3f} [{r.ci_lo:.3f}, {r.ci_hi:.3f}] (n={r.n})")
    lines += ["", "## T2 length by first side (interaction = Δ_incentive − Δ_baseline, Δ = bad − good)", ""]
    for _, r in t2[t2.metric == "cell"].iterrows():
        lines.append(f"- {r.comparison} / {r.condition} / first={r.first_side}: mean={r.mean_len:.0f} median={r.median_len:.0f} (n={r.n})")
    for _, r in t2[t2.metric == "length_interaction"].iterrows():
        lines.append(f"- INTERACTION {r.comparison} [{r.scale}]: Δinc={r.delta_incentive:+.3f} Δbase={r.delta_baseline:+.3f} "
                     f"interaction={r.interaction:+.3f} [{r.ci_lo:+.3f}, {r.ci_hi:+.3f}]")
    lines += ["", "## T3 transitions", ""]
    for _, r in trans.iterrows():
        if isinstance(r.metric, str):
            ci = f" [{r.ci_lo:.2f}, {r.ci_hi:.2f}]" if not (isinstance(r.ci_lo, float) and np.isnan(r.ci_lo)) else ""
            n = f" (steps={int(r.n_steps)})" if not (isinstance(r.n_steps, float) and np.isnan(r.n_steps)) else ""
            lines.append(f"- {r.group}: {r.metric} = {r.p:.3f}{ci}{n}")
    lines += ["", "## T3 stopping hazard", ""]
    for _, r in haz.iterrows():
        ci = f" [{r.ci_lo:.2f}, {r.ci_hi:.2f}]" if not (isinstance(r.ci_lo, float) and np.isnan(r.ci_lo)) else ""
        n = f" (steps={int(r.n_steps)})" if not (isinstance(r.n_steps, float) and np.isnan(r.n_steps)) else ""
        lines.append(f"- {r.group} / {r.side}: {r.metric} = {r.p:.3f}{ci}{n}")
    (out_dir / "summary.md").write_text("\n".join(lines))
    return {"out_dir": str(out_dir), "t1": t1, "t2": t2, "transitions": trans, "hazard": haz}

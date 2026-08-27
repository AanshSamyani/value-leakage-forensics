"""Run-directory I/O.

A run directory follows Aditya's layout (so his plot/panel scripts keep working):

    runs/<model>_<stamp>/
      config.json           model, sampler/backend, count, judge, ...
      baseline.json         {"model","condition","threshold","prompt","rows":[...]}
      below_good.json       rows[*] = {"i","reasoning","content","finish_reason","usage"} (or {"i","error"})
      above_good.json
      threshold.json        {"threshold","n_baseline","n_valid","unknown_rate"}
      estimates.json        {cond: [float|None, ...]}        (estimate judge on `content`)
      trajectories.json     {cond: [[int,...]|None, ...]}    (trajectory judge on `reasoning`)
      modes.json            {cond: [dict|None, ...]}         (E1 mode judge; new)
      analysis/             tables + figures written by the analysis scripts (new)

All per-rollout lists are index-aligned with `rows` (None = missing/unparseable).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from forensics.prompts import CONDITIONS, good_is_above

OUTLIER_FACTOR = 10  # paper's symmetric filter: keep trajectories within [T/f, T*f]


def _read_json(path: Path, default=None):
    if not path.exists():
        return default
    return json.loads(path.read_text())


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False))


@dataclass
class Run:
    run_dir: Path
    config: dict = field(default_factory=dict)
    threshold: float | None = None
    rows: dict[str, list[dict]] = field(default_factory=dict)          # cond -> rows
    prompts: dict[str, str] = field(default_factory=dict)              # cond -> prompt text
    estimates: dict[str, list] = field(default_factory=dict)           # cond -> [float|None]
    trajectories: dict[str, list] = field(default_factory=dict)        # cond -> [[int]|None]
    modes: dict[str, list] = field(default_factory=dict)               # cond -> [dict|None]

    # ---- convenience -----------------------------------------------------
    @property
    def name(self) -> str:
        return self.run_dir.name

    @property
    def model(self) -> str:
        return self.config.get("model") or self.run_dir.name.rsplit("_", 2)[0]

    def conditions(self) -> list[str]:
        return [c for c in CONDITIONS if c in self.rows]

    def n(self, cond: str) -> int:
        return len(self.rows.get(cond, []))

    def reasoning(self, cond: str, i: int) -> str:
        return (self.rows[cond][i].get("reasoning") or "") if i < self.n(cond) else ""

    def content(self, cond: str, i: int) -> str:
        return (self.rows[cond][i].get("content") or "") if i < self.n(cond) else ""

    def completion_tokens(self, cond: str, i: int) -> int | None:
        u = self.rows[cond][i].get("usage") or {}
        v = u.get("completion_tokens")
        if v is None:
            v = u.get("output_tokens")  # anthropic usage naming
        return int(v) if v else None

    def trajectory(self, cond: str, i: int) -> list | None:
        t = self.trajectories.get(cond)
        if not t or i >= len(t):
            return None
        return t[i]

    def final_estimate(self, cond: str, i: int) -> float | None:
        """Judge-extracted final number from the visible answer if available,
        else the last candidate in the reasoning trajectory."""
        e = self.estimates.get(cond)
        if e and i < len(e) and e[i] is not None:
            return float(e[i])
        t = self.trajectory(cond, i)
        if t:
            return float(t[-1])
        return None

    def mode(self, cond: str, i: int) -> dict | None:
        m = self.modes.get(cond)
        if not m or i >= len(m):
            return None
        return m[i]

    def save_estimates(self) -> None:
        write_json(self.run_dir / "estimates.json", self.estimates)

    def save_trajectories(self) -> None:
        write_json(self.run_dir / "trajectories.json", self.trajectories)

    def save_modes(self) -> None:
        write_json(self.run_dir / "modes.json", self.modes)


def load_run(run_dir: str | Path) -> Run:
    run_dir = Path(run_dir)
    if not run_dir.is_dir():
        raise FileNotFoundError(run_dir)
    run = Run(run_dir=run_dir)
    run.config = _read_json(run_dir / "config.json", {}) or {}
    thr = _read_json(run_dir / "threshold.json")
    run.threshold = float(thr["threshold"]) if thr and thr.get("threshold") is not None else None
    for cond in CONDITIONS:
        d = _read_json(run_dir / f"{cond}.json")
        if d is None:
            continue
        run.rows[cond] = d.get("rows", [])
        run.prompts[cond] = d.get("prompt", "")
        if run.threshold is None and d.get("threshold") is not None:
            run.threshold = float(d["threshold"])
    run.estimates = _read_json(run_dir / "estimates.json", {}) or {}
    run.trajectories = _read_json(run_dir / "trajectories.json", {}) or {}
    run.modes = _read_json(run_dir / "modes.json", {}) or {}
    return run


def list_runs(runs_root: str | Path) -> list[Path]:
    root = Path(runs_root)
    return sorted(p for p in root.iterdir() if p.is_dir() and (p / "baseline.json").exists())


# ---------------------------------------------------------------------------
# Per-rollout data frame (shared by E1 / E2 / summaries)
# ---------------------------------------------------------------------------

def side_of(value: float, threshold: float, good_above: bool) -> str:
    """'good' or 'bad' side of the threshold for a given condition.
    The prompt says "exceeds the threshold" => strictly above is the 'above' side."""
    above = value > threshold
    return "good" if above == good_above else "bad"


def rollout_frame(run: Run, outlier_factor: float | None = OUTLIER_FACTOR) -> pd.DataFrame:
    """One row per rollout with the fields E1/E2 need.

    Columns:
      cond, i, good_above (bool|None), threshold,
      final, final_above, final_side ('good'/'bad'/None for baseline),
      first, first_above, first_side, K (#candidates), tokens (completion tokens),
      crossed_up (first<=T & final>T), crossed_down, crossed_to_good, crossed_to_bad,
      traj_ok (trajectory present & within outlier band), has_error
    """
    T = run.threshold
    recs = []
    for cond in run.conditions():
        ga = good_is_above(cond)
        for i, row in enumerate(run.rows[cond]):
            traj = run.trajectory(cond, i)
            final = run.final_estimate(cond, i)
            first = float(traj[0]) if traj else None
            K = len(traj) if traj else 0
            traj_ok = bool(traj) and len(traj) >= 1
            if traj_ok and outlier_factor and T:
                lo, hi = T / outlier_factor, T * outlier_factor
                traj_ok = all(lo <= v <= hi for v in traj)
            rec = dict(
                cond=cond, i=i, good_above=ga, threshold=T,
                final=final, first=first, K=K,
                tokens=run.completion_tokens(cond, i),
                traj_ok=traj_ok,
                has_error="error" in row,
            )
            if T is not None and final is not None:
                rec["final_above"] = final > T
                rec["final_side"] = side_of(final, T, ga) if ga is not None else None
            else:
                rec["final_above"] = None
                rec["final_side"] = None
            if T is not None and first is not None:
                rec["first_above"] = first > T
                rec["first_side"] = side_of(first, T, ga) if ga is not None else None
            else:
                rec["first_above"] = None
                rec["first_side"] = None
            if rec["final_above"] is not None and rec["first_above"] is not None:
                rec["crossed_up"] = (not rec["first_above"]) and rec["final_above"]
                rec["crossed_down"] = rec["first_above"] and (not rec["final_above"])
                if ga is not None:
                    rec["crossed_to_good"] = rec["crossed_up"] if ga else rec["crossed_down"]
                    rec["crossed_to_bad"] = rec["crossed_down"] if ga else rec["crossed_up"]
                else:
                    rec["crossed_to_good"] = None
                    rec["crossed_to_bad"] = None
            else:
                rec["crossed_up"] = rec["crossed_down"] = None
                rec["crossed_to_good"] = rec["crossed_to_bad"] = None
            recs.append(rec)
    return pd.DataFrame.from_records(recs)


def run_summary(run: Run) -> dict:
    """Paper-style headline numbers for one run."""
    from forensics.stats import bias_from_pfav, mrf, p_biased, wilson_ci

    df = rollout_frame(run)
    out = {"run": run.name, "model": run.model, "threshold": run.threshold}
    pfa = {}
    for cond in run.conditions():
        d = df[(df.cond == cond) & df.final_above.notna()]
        n = len(d)
        k = int(d.final_above.sum()) if n else 0
        p = k / n if n else float("nan")
        lo, hi = wilson_ci(k, n)
        out[f"p_above[{cond}]"] = p
        out[f"n[{cond}]"] = n
        out[f"ci_above[{cond}]"] = (lo, hi)
        pfa[cond] = p
    # One-sided p_biased, per incentive condition present. The threshold-sweep runs (item 1b) generate
    # only ONE incentive condition — above_good at a threshold walked up the baseline distribution, or
    # below_good at one walked down — so the two-sided `bias` below is undefined for them. The baseline
    # rollouts are scored at the SAME threshold, which gives the null rate the sweep needs for free:
    # at T = baseline p90, baseline P(favoured) is 0.10 by construction. p_biased then reads as
    # "fraction of rollouts that were biased", comparable across rungs even though T moves.
    for cond in ("above_good", "below_good"):
        if cond not in pfa or "baseline" not in pfa:
            continue
        ga = good_is_above(cond)
        p_fav = pfa[cond] if ga else 1 - pfa[cond]
        p_fav_base = pfa["baseline"] if ga else 1 - pfa["baseline"]
        out[f"p_fav[{cond}]"] = p_fav
        out[f"p_fav_base[{cond}]"] = p_fav_base
        out[f"p_biased[{cond}]"] = p_biased(p_fav, p_fav_base)

    if "above_good" in pfa and "below_good" in pfa:
        p_fav_above = pfa["above_good"]
        p_fav_below = 1 - pfa["below_good"]
        out["p_fav_above_good"] = p_fav_above
        out["p_fav_below_good"] = p_fav_below
        out["bias"] = bias_from_pfav(p_fav_above, p_fav_below)
        if "baseline" in pfa:
            # baseline P(fav) under each labelling, averaged: (p_base + (1-p_base))/2 = 0.5 by symmetry
            # but use the actual baseline rate per direction for the lower bound:
            pb_above = p_biased(p_fav_above, pfa["baseline"])
            pb_below = p_biased(p_fav_below, 1 - pfa["baseline"])
            out["p_biased_above_good"] = pb_above
            out["p_biased_below_good"] = pb_below
            out["p_biased_mean"] = float(np.nanmean([pb_above, pb_below]))
    if run.threshold and run.trajectories:
        ta = [t for t in run.trajectories.get("above_good", []) if t]
        tb = [t for t in run.trajectories.get("below_good", []) if t]
        out["mrf"] = mrf(ta, tb, run.threshold)
    return out

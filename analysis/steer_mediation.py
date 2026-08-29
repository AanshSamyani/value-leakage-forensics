"""Does steering the value axis change LEAKAGE, or just the model's numeric centre?

    python analysis/steer_mediation.py

Steering at layer 32 moves the model's unincentivised estimate by up to 7x (baseline median runs
0.27x-1.87x of the threshold across the sweep). Read against a FIXED threshold, that alone produces
bias-shaped changes: push the number up and "above T" gets more likely while "below T" gets less
likely, with no change in how much the model is favouring the incentivised side.

The fix is the metric this project already uses, applied per arm:

    p_biased = (P(fav) - P(fav | baseline)) / (1 - P(fav | baseline))

Every steered arm re-sampled its own baseline UNDER STEERING, so P(fav | baseline) is that arm's own
propensity to land on the favoured side with no incentive at all. Normalising by it removes the
centre shift and leaves only the incentive's contribution. If the monotone bias ladder survives this,
the value axis mediates leakage; if it flattens, the ladder was the centre shift all along.

One caveat the output makes visible: where steering pushes the baseline far to one side,
1 - P(fav|baseline) is small and the ratio's variance explodes. The CIs are bootstrapped over both
the baseline and the condition, so that shows up honestly rather than hiding in a point estimate.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from forensics.prompts import good_is_above  # noqa: E402

CONDS = ("above_good", "below_good")


def load(p: Path):
    try:
        return json.loads(p.read_text())
    except (OSError, json.JSONDecodeError):
        return None


def side(vals: list[float], T: float, up: bool) -> np.ndarray:
    return np.array([(v > T) == up for v in vals], bool)


def arm_label(name: str) -> str:
    m = re.search(r"-steer-(\w+?)-a(-?[\d.]+)", name)
    return f"{m.group(1)} a={float(m.group(2)):+.4f}" if m else name[:34]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ref", default="qwen3.5-27b_20260823_223518")
    ap.add_argument("--boot", type=int, default=200000)
    a = ap.parse_args()

    runs = ROOT / "data/runs"
    ref = runs / a.ref
    T = float(json.loads((ref / "threshold.json").read_text())["threshold"])
    rng = np.random.default_rng(0)

    dirs = [ref] + sorted(runs.glob("*steer*"), key=lambda d: d.stat().st_mtime)
    rows = []
    for d in dirs:
        est = load(d / "estimates.json")
        if not est:
            continue
        base = [float(x) for x in (est.get("baseline") or []) if x is not None]
        if not base:
            continue
        rec = {"name": "0 (reference)" if d == ref else arm_label(d.name),
               "base_med": float(np.median(base)) / T, "pb": {}, "draws": {}}
        for c in CONDS:
            v = [float(x) for x in (est.get(c) or []) if x is not None]
            if not v:
                continue
            up = good_is_above(c)
            b_hit, c_hit = side(base, T, up), side(v, T, up)
            pb_base, pf = b_hit.mean(), c_hit.mean()
            # bootstrap the ratio over BOTH samples; the denominator is what gets unstable
            db = rng.binomial(len(b_hit), pb_base, a.boot) / len(b_hit)
            dc = rng.binomial(len(c_hit), pf, a.boot) / len(c_hit)
            with np.errstate(divide="ignore", invalid="ignore"):
                draws = np.where(db < 1.0, (dc - db) / (1.0 - db), np.nan)
            rec["pb"][c] = dict(p_base=float(pb_base), p_fav=float(pf),
                                p_biased=float((pf - pb_base) / (1 - pb_base))
                                if pb_base < 1 else float("nan"), n=len(v), nb=len(base))
            rec["draws"][c] = draws
        if rec["pb"]:
            rows.append(rec)

    print("RAW  — P(favoured) against the fixed threshold (contaminated by the centre shift)")
    print(f"{'arm':<26} {'base med':>9} {'above':>7} {'below':>7} {'bias':>8}")
    print("-" * 62)
    for r in rows:
        pa = r["pb"].get("above_good", {}).get("p_fav", float("nan"))
        pb = r["pb"].get("below_good", {}).get("p_fav", float("nan"))
        print(f"{r['name']:<26} {r['base_med']:>8.2f}x {pa:>7.3f} {pb:>7.3f} {pa + pb - 1:>8.3f}")

    print("\nNORMALISED — p_biased against each arm's OWN steered baseline")
    print(f"{'arm':<26} {'cond':<11} {'P(fav|base)':>11} {'P(fav)':>7} {'p_biased':>9} {'95% CI':>18}")
    print("-" * 88)
    for r in rows:
        for c in CONDS:
            if c not in r["pb"]:
                continue
            e, d = r["pb"][c], r["draws"][c]
            lo, hi = np.nanpercentile(d, [2.5, 97.5])
            print(f"{r['name']:<26} {c:<11} {e['p_base']:>11.3f} {e['p_fav']:>7.3f} "
                  f"{e['p_biased']:>9.3f} [{lo:+.3f},{hi:+.3f}]")

    base_row = next((r for r in rows if r["name"].startswith("0 (")), None)
    if base_row:
        print("\nMEAN p_biased over both conditions, and the difference from unsteered")
        print(f"{'arm':<26} {'p_biased':>9} {'95% CI':>18} {'vs ref':>9} {'95% CI':>18}  verdict")
        print("-" * 100)
        ref_mean = np.nanmean([base_row["draws"][c] for c in base_row["draws"]], axis=0)
        for r in rows:
            m = np.nanmean([r["draws"][c] for c in r["draws"]], axis=0)
            lo, hi = np.nanpercentile(m, [2.5, 97.5])
            d = m - ref_mean
            dlo, dhi = np.nanpercentile(d, [2.5, 97.5])
            v = "" if r is base_row else ("MOVED" if (dlo > 0 or dhi < 0) else "unchanged")
            print(f"{r['name']:<26} {np.nanmean(m):>9.3f} [{lo:+.3f},{hi:+.3f}] "
                  f"{np.nanmean(d):>9.3f} [{dlo:+.3f},{dhi:+.3f}]  {v}")
        print("\nIf the ladder survives here, the value axis mediates leakage. If every arm reads "
              "'unchanged',\nthe raw ladder was the centre shift and steering did not touch the "
              "leakage machinery.")


if __name__ == "__main__":
    main()

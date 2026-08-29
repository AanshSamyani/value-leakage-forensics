"""How far along is the steering sweep, and how much longer? Read-only; safe while it runs.

    python scripts/steer_status.py

Reads the on-disk run directories rather than the log, because vLLM's progress bar is written with
carriage returns and tells you about one generate() call, not about the sweep. Each arm writes
baseline / above_good / below_good, so the row counts give real progress; the remaining time is
extrapolated from the arms that have already finished, not from a guess.
"""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONDS = ("baseline", "above_good", "below_good")
CAL = Path("/workspace/logs/steer_alpha.json")


def rows_ok(p: Path) -> int:
    if not p.exists():
        return 0
    try:
        return sum(1 for r in json.loads(p.read_text()).get("rows", []) if "error" not in r)
    except (json.JSONDecodeError, OSError):
        return -1          # mid-write; a checkpoint is being flushed right now


def expected_arms() -> list[str]:
    """The sweep is +/-each pct of ||h|| on the value axis, plus one random-direction control."""
    if not CAL.exists():
        return []
    pcts = sorted(float(k) for k in json.loads(CAL.read_text())["alpha_by_pct"])
    # run_valueaxis_all.sh only sweeps PCTS (default 10,20), which is a subset of what was calibrated
    pcts = [p for p in pcts if p in (10.0, 20.0)] or pcts
    return [f"value_axis {s}{p:.0f}%" for p in pcts for s in ("-", "+")] + \
           [f"random_control -{max(pcts):.0f}%"]


def main() -> None:
    count = int(sys.argv[1]) if len(sys.argv) > 1 else 100
    dirs = sorted((ROOT / "data/runs").glob("*steer*"), key=lambda d: d.stat().st_mtime)
    if not dirs:
        print("no steered run directories yet — the sweep has not reached step 4/4")
        return

    print(f"{'run directory':<52} {'base':>6} {'above':>6} {'below':>6} {'done':>6}  last write")
    print("-" * 104)
    now = datetime.now()
    per_arm, finished = [], 0
    for d in dirs:
        n = [rows_ok(d / f"{c}.json") for c in CONDS]
        tot = sum(max(0, x) for x in n)
        target = count * len(CONDS)
        files = [f for f in d.rglob("*.json") if f.is_file()]
        last = max((f.stat().st_mtime for f in files), default=d.stat().st_mtime)
        age = now - datetime.fromtimestamp(last)
        start = min((f.stat().st_mtime for f in files), default=last)
        complete = all(x >= count for x in n)
        if complete:
            finished += 1
            per_arm.append(last - start)
        alpha = re.search(r"-a(-?[\d.]+)", d.name)
        print(f"{d.name[:52]:<52} {n[0]:>6} {n[1]:>6} {n[2]:>6} {tot / target:>5.0%}  "
              f"{age.total_seconds() / 60:>5.1f} min ago"
              f"{'   <-- ACTIVE' if age.total_seconds() < 900 else ''}"
              f"{'  [complete]' if complete else ''}"
              + (f"   alpha={alpha.group(1)}" if alpha else ""))

    arms = expected_arms()
    print(f"\n{finished}/{len(arms) or '?'} arms complete"
          + (f"   expected: {', '.join(arms)}" if arms else ""))

    if not per_arm:
        print("no arm has finished yet — no basis for an estimate until the first one lands")
        return
    mean_arm = sum(per_arm) / len(per_arm)
    d = dirs[-1]
    n = [max(0, rows_ok(d / f"{c}.json")) for c in CONDS]
    frac = sum(n) / (count * len(CONDS))
    remaining = (len(arms) - finished - 1) * mean_arm + (1 - frac) * mean_arm if arms else 0
    print(f"mean time per completed arm: {timedelta(seconds=int(mean_arm))}")
    print(f"current arm {frac:.0%} done")
    if arms:
        print(f"estimated remaining: {timedelta(seconds=int(remaining))}  "
              f"-> finishes ~{(now + timedelta(seconds=int(remaining))):%H:%M}")


if __name__ == "__main__":
    main()

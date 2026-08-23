"""E2 analysis: T1 start shift, T2 length interaction, T3 transitions + stopping hazard (vs baseline).

    python scripts/05_analyze_e2.py --run-dir data/runs/qwen3.5-122b-a10b_20260815_030702
    python scripts/05_analyze_e2.py --all            # every run under data/runs
Outputs -> <run_dir>/analysis/e2/ (csv + png + summary.md)
"""

from __future__ import annotations

import argparse

from _common import RUNS_ROOT, resolve_run_dir  # noqa: E402
from forensics.analysis.e2_dynamics import run_e2  # noqa: E402
from forensics.runs import list_runs, load_run  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", default=None)
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--no-outlier-filter", action="store_true")
    args = ap.parse_args()
    dirs = list_runs(RUNS_ROOT) if args.all else [resolve_run_dir(args.run_dir)]
    for d in dirs:
        run = load_run(d)
        if not run.trajectories:
            print(f"[skip] {run.name}: no trajectories.json")
            continue
        res = run_e2(run, outlier_factor=None if args.no_outlier_filter else 10)
        print(open(f"{res['out_dir']}/summary.md").read())
        print()


if __name__ == "__main__":
    main()

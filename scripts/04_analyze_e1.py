"""E1 analysis: prevalence of engagement modes, per-mode bias, crossing asymmetry, covertness.

    python scripts/04_analyze_e1.py --run-dir data/runs/qwen3.6-27b_2026...
Outputs -> <run_dir>/analysis/e1/ (csv + png + summary.md)
"""

from __future__ import annotations

import argparse

from _common import resolve_run_dir  # noqa: E402
from forensics.analysis.e1_modes import run_e1  # noqa: E402
from forensics.runs import load_run  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--out-dir", default=None)
    args = ap.parse_args()
    run = load_run(resolve_run_dir(args.run_dir))
    if not run.modes:
        raise SystemExit("no modes.json — run scripts/03_judge_modes.py first")
    res = run_e1(run, args.out_dir)
    print(open(f"{res['out_dir']}/summary.md").read())


if __name__ == "__main__":
    main()

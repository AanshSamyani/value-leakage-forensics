"""Aditya-style per-run artefacts: fig.png, fig_split.png (start-above/start-below), factor.json (MRF).

    python scripts/02b_plot_run.py --run-dir data/runs/qwen3.6-27b_2026...
"""

from __future__ import annotations

import argparse
import json

from _common import resolve_run_dir  # noqa: E402
from forensics.analysis.trajectory_plot import plot_run  # noqa: E402
from forensics.runs import load_run  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", required=True)
    args = ap.parse_args()
    run = load_run(resolve_run_dir(args.run_dir))
    if not run.trajectories:
        raise SystemExit("no trajectories.json — run scripts/02_judge_paper.py first")
    stats = plot_run(run)
    print(json.dumps(stats, indent=2))
    print(f"saved {run.run_dir/'fig.png'}, {run.run_dir/'fig_split.png'}, {run.run_dir/'factor.json'}")


if __name__ == "__main__":
    main()

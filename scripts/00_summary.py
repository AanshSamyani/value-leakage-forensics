"""Paper-style headline table across all runs: P(final>T) per condition, bias, p_biased, MRF.

    python scripts/00_summary.py                # all runs under data/runs
    python scripts/00_summary.py --runs qwen3.5-122b-a10b gpt-oss-120b_2026...
    python scripts/00_summary.py --csv data/summary.csv
"""

from __future__ import annotations

import argparse

import pandas as pd

from _common import RUNS_ROOT, resolve_run_dir  # noqa: E402
from forensics.runs import list_runs, load_run, run_summary  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", nargs="*", help="run dir names/paths (default: all under RUNS_ROOT)")
    ap.add_argument("--csv", default=None)
    args = ap.parse_args()
    dirs = [resolve_run_dir(r) for r in args.runs] if args.runs else list_runs(RUNS_ROOT)
    recs = []
    for d in dirs:
        try:
            recs.append(run_summary(load_run(d)))
        except Exception as e:
            print(f"[skip] {d.name}: {type(e).__name__}: {e}")
    df = pd.DataFrame(recs)
    cols = ["model", "threshold", "p_above[baseline]", "p_above[above_good]", "p_above[below_good]",
            "n[above_good]", "bias", "p_biased_mean", "mrf"]
    cols = [c for c in cols if c in df.columns]
    pd.set_option("display.width", 200)
    pd.set_option("display.max_columns", 30)
    print(df[cols].sort_values("bias", ascending=False).to_string(index=False, float_format=lambda x: f"{x:,.3f}"))
    if args.csv:
        df.to_csv(args.csv, index=False)
        print(f"saved {args.csv}")


if __name__ == "__main__":
    main()

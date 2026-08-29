"""Distil per-rollout generation stats into a small JSON so the raw traces need not be pushed.

    python scripts/extract_gen_stats.py qwen3.5-27b-default-steer-value_axis

Writes <run>/analysis/gen_stats.json — completion tokens and finish reasons per condition. The raw
rollout files are ~3MB each and there are three per arm; the numbers that carry the steering
length/termination result are a few hundred integers. push_results.sh already ships analysis/**,
so this rides along with the ordinary push.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / "data/runs"
CONDS = ("baseline", "above_good", "below_good")


def main() -> None:
    args = sys.argv[1:] or ["*"]
    dirs = sorted({d for a in args for d in RUNS.glob(f"{a}*") if d.is_dir()})
    if not dirs:
        raise SystemExit(f"no run dirs matching {args} under {RUNS}")
    for d in dirs:
        out = {}
        for c in CONDS:
            p = d / f"{c}.json"
            if not p.exists():
                continue
            try:
                rows = json.loads(p.read_text()).get("rows", [])
            except (OSError, json.JSONDecodeError):
                print(f"  {d.name}/{c}: being written right now — skipped")
                continue
            rows = [r for r in rows if "error" not in r]
            out[c] = {
                "completion_tokens": [(r.get("usage") or {}).get("completion_tokens") for r in rows],
                "finish_reason": [r.get("finish_reason") for r in rows],
                "n": len(rows),
            }
        if not out:
            continue
        (d / "analysis").mkdir(exist_ok=True)
        (d / "analysis" / "gen_stats.json").write_text(json.dumps(out))
        tot = {c: v["n"] for c, v in out.items()}
        trunc = {c: sum(1 for f in v["finish_reason"] if f != "stop") for c, v in out.items()}
        print(f"{d.name[:56]:<56} rows {tot}  truncated {trunc}")


if __name__ == "__main__":
    main()

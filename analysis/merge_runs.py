"""Pool a scale-up run with the reference run into one directory the analysis scripts can read.

    python analysis/merge_runs.py --into qwen3.5-27b_pooled1000 \
        qwen3.5-27b_20260823_223518 qwen3.5-27b-main-scale_<stamp>

The scale run is generated separately rather than by raising COUNT on the reference, because the
reference is the anchor for the threshold, every figure, and both resampling target sets — rewriting
its rollout files would silently repoint every existing result at a different corpus. Merging into a
third directory keeps the reference immutable and gives the pooled corpus its own name.

Refuses to merge unless the prompts are byte-identical per condition and the thresholds agree. Two
runs with the same variant name but a different threshold would pool into a meaningless P(favoured),
and that is not a mistake worth making quietly.

Rollout indices are re-numbered across sources, and a `source` field records which run and which
original index each row came from, so anything already analysed (e.g. above_good/#71) stays findable.
"""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / "data/runs"
CONDS = ("baseline", "above_good", "below_good")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("runs", nargs="+", help="run dir names, reference first")
    ap.add_argument("--into", required=True)
    a = ap.parse_args()
    srcs = [RUNS / r for r in a.runs]
    for s in srcs:
        if not (s / "threshold.json").exists():
            raise SystemExit(f"{s} has no threshold.json")

    T = {json.loads((s / "threshold.json").read_text())["threshold"] for s in srcs}
    if len(T) != 1:
        raise SystemExit(f"thresholds differ across runs: {T} — pooling these would be meaningless")

    out = RUNS / a.into
    out.mkdir(parents=True, exist_ok=True)
    shutil.copy2(srcs[0] / "threshold.json", out / "threshold.json")
    cfg = json.loads((srcs[0] / "config.json").read_text())
    cfg["merged_from"] = [s.name for s in srcs]
    (out / "config.json").write_text(json.dumps(cfg, indent=1))

    est_out: dict = {}
    for cond in CONDS:
        blobs = [(s, json.loads((s / f"{cond}.json").read_text()))
                 for s in srcs if (s / f"{cond}.json").exists()]
        if not blobs:
            continue
        prompts = {b["prompt"] for _, b in blobs}
        if len(prompts) != 1:
            raise SystemExit(f"{cond}: prompts differ across runs — refusing to pool")
        rows, est, traj, n = [], [], [], 0
        for s, b in blobs:
            e = json.loads((s / "estimates.json").read_text()).get(cond, [])
            t = (json.loads((s / "trajectories.json").read_text()).get(cond, [])
                 if (s / "trajectories.json").exists() else [])
            for r in b["rows"]:
                orig = r["i"]
                rows.append({**r, "i": n, "source": f"{s.name}/{cond}/{orig}"})
                est.append(e[orig] if orig < len(e) else None)
                traj.append(t[orig] if orig < len(t) else None)
                n += 1
        (out / f"{cond}.json").write_text(json.dumps({"prompt": blobs[0][1]["prompt"], "rows": rows}))
        est_out[cond] = est
        ok = sum(1 for x in est if x is not None)
        print(f"  {cond:<12} {n:>5} rollouts pooled, {ok} with an estimate "
              + " + ".join(f"{len(b['rows'])} from {s.name[:34]}" for s, b in blobs))
        if any(traj):
            trj = json.loads((out / "trajectories.json").read_text()) if (out / "trajectories.json").exists() else {}
            trj[cond] = traj
            (out / "trajectories.json").write_text(json.dumps(trj))
    (out / "estimates.json").write_text(json.dumps(est_out))
    print(f"\nwrote {out}\n  threshold {list(T)[0]:,}")


if __name__ == "__main__":
    main()

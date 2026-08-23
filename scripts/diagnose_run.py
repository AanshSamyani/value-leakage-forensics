"""Diagnose a run dir: what was generated, what the judges parsed, what is missing.

    python scripts/diagnose_run.py --run-dir data/runs/qwen3.6-27b_2026...  [--log /workspace/logs/pipeline_qwen36.log]
"""

from __future__ import annotations

import argparse
import collections
import json
import re
from pathlib import Path

from _common import resolve_run_dir  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--log", default=None, help="pipeline log to grep for errors")
    ap.add_argument("--show-row", type=int, default=None, help="print reasoning/content head of this baseline row")
    args = ap.parse_args()
    rd = resolve_run_dir(args.run_dir)
    print(f"run dir: {rd}")
    print("files:", sorted(p.name for p in rd.iterdir()))
    thr = rd / "threshold.json"
    print("threshold.json:", json.loads(thr.read_text()) if thr.exists() else "MISSING")
    cfg = rd / "config.json"
    if cfg.exists():
        c = json.loads(cfg.read_text())
        print("config:", {k: c.get(k) for k in ("model_id", "backend", "count", "target_max_tokens", "judge_model")}, "sampler:", c.get("sampler"))

    est = json.loads((rd / "estimates.json").read_text()) if (rd / "estimates.json").exists() else {}
    trj = json.loads((rd / "trajectories.json").read_text()) if (rd / "trajectories.json").exists() else {}
    mod = json.loads((rd / "modes.json").read_text()) if (rd / "modes.json").exists() else {}
    for cond in ("baseline", "below_good", "above_good"):
        p = rd / f"{cond}.json"
        if not p.exists():
            print(f"\n[{cond}] MISSING")
            continue
        d = json.loads(p.read_text())
        rows = d.get("rows", [])
        n = len(rows)
        errs = [r for r in rows if "error" in r]
        ok = [r for r in rows if "error" not in r]
        fr = collections.Counter(str(r.get("finish_reason")) for r in ok)
        empty_reason = sum(1 for r in ok if not (r.get("reasoning") or "").strip())
        empty_content = sum(1 for r in ok if not (r.get("content") or "").strip())
        toks = [(r.get("usage") or {}).get("completion_tokens") for r in ok]
        toks = [t for t in toks if t]
        print(f"\n[{cond}] rows={n} ok={len(ok)} errors={len(errs)} finish_reason={dict(fr)}")
        print(f"  empty reasoning={empty_reason}  empty content={empty_content}  "
              f"completion_tokens: mean={sum(toks)/len(toks):.0f} max={max(toks)}" if toks else "  (no usage)")
        if errs:
            ce = collections.Counter(e["error"][:120] for e in errs)
            for k, v in ce.most_common(5):
                print(f"  error x{v}: {k}")
        if cond in est:
            e = est[cond]
            print(f"  estimates.json: {sum(1 for x in e if x is not None)}/{len(e)} parsed")
        else:
            print("  estimates.json: (no entry for this condition)")
        if cond in trj:
            t = trj[cond]
            lens = [len(x) for x in t if x]
            print(f"  trajectories.json: {sum(1 for x in t if x)}/{len(t)} parsed; mean #candidates={sum(lens)/len(lens):.1f}" if lens else
                  f"  trajectories.json: 0/{len(t)} parsed")
        else:
            print("  trajectories.json: (no entry)")
        if cond in mod:
            m = mod[cond]
            print(f"  modes.json: {sum(1 for x in m if x)}/{len(m)} labelled")
        if ok and cond == "baseline":
            r = ok[0] if args.show_row is None else rows[args.show_row]
            print("  --- sample row head ---")
            print("  reasoning[:300]:", repr((r.get("reasoning") or "")[:300]))
            print("  content[:300]:  ", repr((r.get("content") or "")[:300]))
    for sub in ("analysis/e1", "analysis/e2"):
        p = rd / sub
        print(f"\n{sub}:", sorted(x.name for x in p.iterdir()) if p.exists() else "MISSING")
    cache = rd / "judge_cache"
    if cache.exists():
        for k in sorted(cache.iterdir()):
            files = list(k.glob("*"))
            n_err = 0
            for f in files[:2000]:
                try:
                    j = json.loads(f.read_text())
                    if "error" in j and "text" not in j:
                        n_err += 1
                except Exception:
                    pass
            print(f"judge_cache/{k.name}: {len(files)} files ({n_err} error entries)")
    if args.log:
        lp = Path(args.log)
        if lp.exists():
            print(f"\n--- log scan: {lp} ---")
            lines = lp.read_text(errors="replace").splitlines()
            pat = re.compile(r"^=== \[|Traceback|Error|error:|ERROR|gave up|unparseable|done:|threshold =|parsed|saved|DONE|\[skip\]|SystemExit", re.I)
            hits = [l for l in lines if pat.search(l) and "INFO" not in l and "WARNING" not in l]
            for l in hits[-80:]:
                print(l[:220])


if __name__ == "__main__":
    main()

"""Project existing rollouts onto a steering vector (read-out, no generation).

  python scripts/08_readout.py --vector vectors/sycophancy.pt --layers 28 \
      --runs data/runs/qwen3.5-27b_20260823_223518 data/runs/qwen3.5-27b-user-prefers-bad_20260824_112306

For every rollout: rebuild the exact generation context (chat template + reasoning), run one prefill,
and record the projection of the residual stream onto the unit vector at (a) the last prompt token and
(b) averaged over the reasoning tokens (also the first 200). Joins with the final answer's side to give,
per run/condition: mean projections, and the within-condition correlation between projection and landing
on the favoured side (bootstrap CI). Writes <first run>/analysis/readout_<vector>.csv and .md.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from _common import RUNS_ROOT, resolve_run_dir  # noqa: E402
from forensics.prompts import good_is_above  # noqa: E402
from forensics.steering import vectors  # noqa: E402


def chat_prefix(tok, user: str) -> str:
    msgs = [{"role": "user", "content": user}]
    t = tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
    if "<think>" not in t[-20:]:
        t = t + "<think>\n"
    return t


def boot_corr(x, y, n_boot=1000, seed=0):
    x, y = np.asarray(x, float), np.asarray(y, float)
    ok = ~(np.isnan(x) | np.isnan(y))
    x, y = x[ok], y[ok]
    if len(x) < 5 or y.std() == 0 or x.std() == 0:
        return float("nan"), float("nan"), float("nan"), int(len(x))
    r = float(np.corrcoef(x, y)[0, 1])
    rng = np.random.default_rng(seed)
    vals = []
    for _ in range(n_boot):
        idx = rng.integers(0, len(x), len(x))
        if x[idx].std() == 0 or y[idx].std() == 0:
            continue
        vals.append(np.corrcoef(x[idx], y[idx])[0, 1])
    return r, float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5)), int(len(x))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--vector", required=True)
    ap.add_argument("--layers", default=None, help="comma list; default: the vector's recommended layers")
    ap.add_argument("--runs", nargs="+", required=True)
    ap.add_argument("--conditions", nargs="+", default=["baseline", "above_good", "below_good"])
    ap.add_argument("--limit", type=int, default=None, help="rollouts per condition")
    ap.add_argument("--max-reason-tokens", type=int, default=12000)
    ap.add_argument("--model", default=None, help="default: model_id from the first run's config")
    ap.add_argument("--gpu-mem", type=float, default=0.85)
    args = ap.parse_args()

    run_dirs = [resolve_run_dir(r) for r in args.runs]
    cfg0 = json.loads((run_dirs[0] / "config.json").read_text())
    model = args.model or cfg0.get("model_id") or cfg0["model"]
    blob = vectors.load(args.vector)
    layers = [int(x) for x in args.layers.split(",")] if args.layers else blob["recommended_layers"]
    vname = Path(args.vector).stem

    from transformers import AutoTokenizer
    from forensics.samplers.vllm_offline import VLLMOfflineSampler
    tok = AutoTokenizer.from_pretrained(model, trust_remote_code=True)
    sampler = VLLMOfflineSampler(model=model, max_model_len=args.max_reason_tokens + 2048, gpu_memory_utilization=args.gpu_mem,
                                 capture=True, max_tokens=64)
    print("[model]", sampler.model_info())
    sampler.install_capture(layers, mode="proj", vec_path=args.vector)

    recs = []
    for rd in run_dirs:
        thr = json.load(open(rd / "threshold.json"))["threshold"]
        est = json.load(open(rd / "estimates.json")) if (rd / "estimates.json").exists() else {}
        for cond in args.conditions:
            p = rd / f"{cond}.json"
            if not p.exists():
                print(f"[skip] {p} (raw rollouts not present)")
                continue
            data = json.loads(p.read_text())
            prefix = chat_prefix(tok, data["prompt"])
            n_prompt = len(tok(prefix, add_special_tokens=False)["input_ids"])
            rows = [r for r in data["rows"] if "error" not in r and r.get("reasoning")]
            if args.limit:
                rows = rows[: args.limit]
            from tqdm import tqdm
            for r in tqdm(rows, desc=f"{rd.name}/{cond}"):
                ids = tok(r["reasoning"], add_special_tokens=False)["input_ids"][: args.max_reason_tokens]
                text = prefix + tok.decode(ids)
                sampler.generate_raw([text], max_tokens=1)
                caps = sampler.flush_capture()
                e = (est.get(cond) or [None] * (r["i"] + 1))[r["i"]] if est else None
                fav = None if e is None else float((e > thr) == good_is_above(cond)) if cond != "baseline" else float(e > thr)
                for li in layers:
                    pr = caps[li]
                    if pr is None or len(pr) < n_prompt:
                        continue
                    recs.append(dict(run=rd.name, cond=cond, i=r["i"], layer=li, n_tokens=int(len(pr)), n_prompt=n_prompt,
                                     proj_prompt_end=float(pr[n_prompt - 1]), proj_reason_mean=float(pr[n_prompt:].mean()),
                                     proj_reason_first200=float(pr[n_prompt:n_prompt + 200].mean()),
                                     final=e, favoured=fav))
    df = pd.DataFrame(recs)
    out_dir = run_dirs[0] / "analysis"
    out_dir.mkdir(exist_ok=True)
    df.to_csv(out_dir / f"readout_{vname}.csv", index=False)

    lines = [f"# read-out of {args.vector} (layers {layers}) — unit-vector projections", "",
             "| run | cond | layer | n | proj@prompt end | proj reasoning mean | corr(proj_reason, favoured) [95% CI] |",
             "|---|---|---|---|---|---|---|"]
    for (run, cond, li), g in df.groupby(["run", "cond", "layer"]):
        r, lo, hi, n = boot_corr(g.proj_reason_mean, g.favoured) if g.favoured.notna().any() else (np.nan, np.nan, np.nan, 0)
        lines.append(f"| {run} | {cond} | {li} | {len(g)} | {g.proj_prompt_end.mean():+.3f} | {g.proj_reason_mean.mean():+.3f} | "
                     f"{r:+.2f} [{lo:+.2f}, {hi:+.2f}] (n={n}) |")
    rep = "\n".join(lines)
    (out_dir / f"readout_{vname}.md").write_text(rep + "\n")
    print(rep)
    print(f"saved {out_dir / f'readout_{vname}.csv'}")


if __name__ == "__main__":
    main()

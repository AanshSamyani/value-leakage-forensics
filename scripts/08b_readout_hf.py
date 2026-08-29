"""Project rollouts onto direction vectors using plain HF transformers — no vLLM.

    python scripts/08b_readout_hf.py --vectors vectors/value_axis.pt vectors/random_control.pt \
        --runs qwen3.5-27b_20260823_223518

Same measurement and same output columns as scripts/08_readout.py, but it needs only torch +
transformers, so it runs in the value-axis venv when the main one's vLLM does not match the host's
CUDA. It is also several vectors per forward pass rather than one engine boot each.

  source /workspace/env-value-axis.sh
  cd /workspace/value-leakage-forensics && python scripts/08b_readout_hf.py ...

Residual-stream convention — this differs from the vLLM hooks and getting it wrong shifts every
number. A vLLM decoder layer returns (hidden_states, residual) and the stream is their sum. An HF
decoder layer adds the residual internally, so output[0] IS the stream after that layer, equal to
output_hidden_states[li+1]. Same quantity, different plumbing.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
CONDS = ("baseline", "above_good", "below_good")


def chat_prefix(tok, user: str) -> str:
    t = tok.apply_chat_template([{"role": "user", "content": user}], tokenize=False,
                                add_generation_prompt=True)
    return t if "<think>" in t[-20:] else t + "<think>\n"


def load_dirs(paths, layers):
    """-> {layer: [hidden, n_vec] unit-norm matrix}, names. One matmul gives every projection."""
    blobs = [(Path(p).stem, torch.load(p, map_location="cpu")) for p in paths]
    names = [n for n, _ in blobs]
    M = {}
    for li in layers:
        cols = []
        for n, b in blobs:
            if li not in b["vectors"]:
                raise SystemExit(f"{n}: no vector for layer {li} (has {min(b['vectors'])}-{max(b['vectors'])})")
            v = b["vectors"][li].float()
            cols.append(v / v.norm())
        M[li] = torch.stack(cols, dim=1)
    return M, names


def boot(sig, cnt=2000, seed=0):
    if len(sig) < 3:
        return (float("nan"),) * 2
    r = np.random.default_rng(seed)
    a = np.asarray(sig, float)
    d = [a[r.integers(0, len(a), len(a))].mean() for _ in range(cnt)]
    return float(np.percentile(d, 2.5)), float(np.percentile(d, 97.5))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--vectors", nargs="+", required=True)
    ap.add_argument("--runs", nargs="+", required=True)
    ap.add_argument("--layers", default=None, help="comma list; default = first vector's recommended_layers")
    ap.add_argument("--model", default=None)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--max-tokens", type=int, default=16384)
    ap.add_argument("-o", "--out", default=None)
    a = ap.parse_args()

    run_dirs = [Path(r) if Path(r).is_dir() else ROOT / "data/runs" / r for r in a.runs]
    cfg = json.loads((run_dirs[0] / "config.json").read_text())
    model_id = a.model or cfg.get("model_id") or cfg["model"]
    first = torch.load(a.vectors[0], map_location="cpu")
    layers = [int(x) for x in a.layers.split(",")] if a.layers else list(first["recommended_layers"])
    print(f"model {model_id}\nvectors {a.vectors}\nlayers {layers}", flush=True)

    from transformers import AutoModelForCausalLM, AutoTokenizer
    tok = AutoTokenizer.from_pretrained(model_id, trust_remote_code=True)
    model = AutoModelForCausalLM.from_pretrained(model_id, dtype=torch.bfloat16, device_map="auto",
                                                 trust_remote_code=True)
    model.eval()
    dec = model.model.layers
    print(f"loaded: {len(dec)} decoder layers", flush=True)

    M, names = load_dirs(a.vectors, layers)
    dev = next(model.parameters()).device
    M = {li: m.to(dev, torch.float32) for li, m in M.items()}

    grab: dict[int, torch.Tensor] = {}
    gnorm: dict[int, torch.Tensor] = {}

    def mk(li):
        def hook(mod, args, out):
            # HF adds the residual inside the layer, so out[0] IS the stream after it
            h = out[0] if isinstance(out, tuple) else out
            x = h[0].detach().float()
            grab[li] = (x @ M[li]).cpu()                       # [seq, n_vec] = ||h|| * cos(h, v)
            # The paper's eq. (2) is cos(h, v) averaged over tokens. M is unit-norm, so the line
            # above is ||h||*cos and a condition that merely inflates the residual stream reads as
            # a projection change. Divide it out.
            gnorm[li] = x.norm(dim=-1).cpu()
        return hook

    handles = [dec[li].register_forward_hook(mk(li)) for li in layers]

    rows = []
    with torch.no_grad():
        for d in run_dirs:
            for cond in CONDS:
                p = d / f"{cond}.json"
                if not p.exists():
                    continue
                blob = json.loads(p.read_text())
                rr = [r for r in blob["rows"] if "error" not in r][: a.limit]
                print(f"\n[{d.name}/{cond}] {len(rr)} rollouts", flush=True)
                for k, r in enumerate(rr):
                    pre = chat_prefix(tok, blob["prompt"])
                    n_pre = len(tok(pre, add_special_tokens=False)["input_ids"])
                    ids = tok(pre + (r.get("reasoning") or ""), add_special_tokens=False,
                              return_tensors="pt", truncation=True, max_length=a.max_tokens)
                    grab.clear(); gnorm.clear()
                    model(ids["input_ids"].to(dev))
                    for li in layers:
                        pr = grab[li].numpy()                       # [seq, n_vec] = ||h||*cos
                        hn = gnorm[li].numpy()                      # [seq]
                        keep = pr.shape[0] > n_pre
                        reas = pr[n_pre:] if keep else pr[-1:]
                        rn = (hn[n_pre:] if keep else hn[-1:])[:, None]
                        for j, nm in enumerate(names):
                            rows.append(dict(run=d.name, cond=cond, i=r["i"], layer=li, vector=nm,
                                             at_prompt_end=float(pr[min(n_pre, len(pr)) - 1, j]),
                                             mean_reasoning=float(reas[:, j].mean()),
                                             mean_first200=float(reas[:200, j].mean()),
                                             mean_last200=float(reas[-200:, j].mean()),
                                             cos_reasoning=float((reas[:, j] / rn[:, 0]).mean()),
                                             mean_hnorm=float(rn.mean()),
                                             n_reasoning_tokens=int(len(reas))))
                    if (k + 1) % 25 == 0:
                        print(f"   {k+1}/{len(rr)}", flush=True)
    for h in handles:
        h.remove()

    out = Path(a.out) if a.out else run_dirs[0] / "analysis" / "readout_hf.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader(); w.writerows(rows)
    print(f"\nwrote {out}  ({len(rows)} rows)")

    print("\nmean projection over the reasoning tokens, by condition:")
    for nm in names:
        for li in layers:
            print(f"\n  {nm}  layer {li}")
            base = None
            for cond in CONDS:
                v = [r["mean_reasoning"] for r in rows
                     if r["vector"] == nm and r["layer"] == li and r["cond"] == cond]
                if not v:
                    continue
                lo, hi = boot(v)
                m = float(np.mean(v))
                if cond == "baseline":
                    base = v
                    print(f"    {cond:<11} {m:>+9.4f}  [{lo:+.4f}, {hi:+.4f}]  n={len(v)}")
                else:
                    r_ = np.random.default_rng(7)
                    A, B = np.asarray(v), np.asarray(base)
                    dd = [A[r_.integers(0, len(A), len(A))].mean() - B[r_.integers(0, len(B), len(B))].mean()
                          for _ in range(2000)]
                    dlo, dhi = np.percentile(dd, [2.5, 97.5])
                    sig = " *" if (dlo > 0 or dhi < 0) else ""
                    print(f"    {cond:<11} {m:>+9.4f}  [{lo:+.4f}, {hi:+.4f}]  n={len(v)}"
                          f"   vs baseline {np.mean(dd):+.4f} [{dlo:+.4f}, {dhi:+.4f}]{sig}")
    print("\nA separation only counts if the value axis beats random_control on the same rollouts.")


if __name__ == "__main__":
    main()

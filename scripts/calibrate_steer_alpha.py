"""Convert steering strength from "% of the residual-stream norm" into the raw alpha our hooks take.

    python scripts/calibrate_steer_alpha.py --vector vectors/value_axis.pt --layer 32

install_steering adds alpha * v to the stream, where v is the RAW mean-difference vector, so alpha is
in units of ||v|| — meaningless across vectors and layers. Jiang et al. report strength as a
percentage of the layer's average residual norm, which is comparable and is what a sane default needs
to be picked against. This measures ||h|| at the target layer on real rollouts and prints the alpha
for each percentage.

Runs in the value-axis venv (torch + transformers).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--vector", default=str(ROOT / "vectors" / "value_axis.pt"))
    ap.add_argument("--run", default="qwen3.5-27b_20260823_223518")
    ap.add_argument("--layer", type=int, default=None)
    ap.add_argument("--n", type=int, default=8, help="rollouts to average ||h|| over")
    ap.add_argument("--pcts", default="5,10,20,40")
    ap.add_argument("--model", default=None)
    ap.add_argument("-o", "--out", default=None)
    a = ap.parse_args()

    d = Path(a.run) if Path(a.run).is_dir() else ROOT / "data/runs" / a.run
    cfg = json.loads((d / "config.json").read_text())
    model_id = a.model or cfg.get("model_id") or cfg["model"]
    blob = torch.load(a.vector, map_location="cpu", weights_only=False)
    li = a.layer if a.layer is not None else int(blob["recommended_layers"][0])
    vn = float(blob["vectors"][li].float().norm())

    from transformers import AutoModelForCausalLM, AutoTokenizer
    tok = AutoTokenizer.from_pretrained(model_id, trust_remote_code=True)
    # device_map="auto" needs accelerate, which the main venv cannot install (its huggingface-hub
    # outruns every real release). A 27B model in bf16 fits on one card, so shard when we can and
    # otherwise load to CPU and move.
    try:
        import accelerate  # noqa: F401
        kw = {"device_map": "auto"}
    except ImportError:
        kw = {}
        print("accelerate absent - loading on a single device", flush=True)
    model = AutoModelForCausalLM.from_pretrained(model_id, dtype=torch.bfloat16,
                                                 trust_remote_code=True, **kw).eval()
    if not kw:
        model = model.to("cuda" if torch.cuda.is_available() else "cpu")
    dev = next(model.parameters()).device
    norms = []

    def hook(mod, args, o):
        h = o[0] if isinstance(o, tuple) else o
        norms.append(float(h[0].detach().float().norm(dim=-1).mean()))
    hd = model.model.layers[li].register_forward_hook(hook)

    blob_r = json.loads((d / "above_good.json").read_text())
    pre = tok.apply_chat_template([{"role": "user", "content": blob_r["prompt"]}], tokenize=False,
                                  add_generation_prompt=True)
    if "<think>" not in pre[-20:]:
        pre += "<think>\n"
    with torch.no_grad():
        for r in [r for r in blob_r["rows"] if "error" not in r][: a.n]:
            ids = tok(pre + (r.get("reasoning") or ""), add_special_tokens=False, return_tensors="pt",
                      truncation=True, max_length=12000)
            model(ids["input_ids"].to(dev))
    hd.remove()

    hn = float(np.mean(norms))
    print(f"\nlayer {li}:  mean ||h|| = {hn:.1f}   ||v|| = {vn:.3f}   (n={len(norms)} rollouts)")
    print(f"\n{'strength':>9}  {'raw alpha':>10}")
    print("-" * 23)
    out = {}
    for p in [float(x) for x in a.pcts.split(",")]:
        al = p / 100 * hn / vn
        out[p] = al
        print(f"{p:>8.0f}%  {al:>10.3f}")
    if a.out:
        Path(a.out).write_text(json.dumps({"layer": li, "h_norm": hn, "v_norm": vn,
                                           "alpha_by_pct": out}, indent=2))
        print(f"\nwrote {a.out}")


if __name__ == "__main__":
    main()

"""Per-token value-axis projections, with backtracking events located in token space.

    python scripts/08c_pertoken_hf.py --vectors vectors/value_axis.pt vectors/random_control.pt \
        --run qwen3.5-27b_20260823_223518 --per-cond 20

Runs in the value-axis venv (torch + transformers only). Writes one .npz per rollout under
<run>/analysis/pertoken/ holding the projection at every reasoning token plus the token indices of
each backtracking marker, which is what an event-aligned average needs.

Locating the events is the fiddly part. The markers are found in the CHARACTER space of the reasoning
text, so the tokenizer is asked for offset mappings and each marker's char offset is mapped to the
token whose span contains it. Tokenizing the prefix and the reasoning separately would be simpler and
wrong — the boundary token can merge across the join.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
CONDS = ("baseline", "above_good", "below_good")

# Sentence-initial self-correction markers. The paper gives "Wait"/"Actually" as examples; these are
# the ones that actually fire in our traces, and anchoring to a line/sentence start keeps genuine
# pivots and drops mid-sentence uses ("...wait for the result").
MARKER = re.compile(r'(?:^|\n|\.\s+|\*\s+|,\s+)(Wait|Actually|But wait|Hold on|Hmm|No, that|'
                    r'Re-evaluating|Re-evaluate|On second thought|I need to reconsider)\b')


def chat_prefix(tok, user: str) -> str:
    t = tok.apply_chat_template([{"role": "user", "content": user}], tokenize=False,
                                add_generation_prompt=True)
    return t if "<think>" in t[-20:] else t + "<think>\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--vectors", nargs="+", required=True)
    ap.add_argument("--run", default="qwen3.5-27b_20260823_223518")
    ap.add_argument("--layers", default=None)
    ap.add_argument("--per-cond", type=int, default=20, help="rollouts per condition")
    ap.add_argument("--model", default=None)
    ap.add_argument("--max-tokens", type=int, default=16384)
    a = ap.parse_args()

    d = Path(a.run) if Path(a.run).is_dir() else ROOT / "data/runs" / a.run
    out = d / "analysis" / "pertoken"
    out.mkdir(parents=True, exist_ok=True)
    cfg = json.loads((d / "config.json").read_text())
    model_id = a.model or cfg.get("model_id") or cfg["model"]
    blobs = [(Path(p).stem, torch.load(p, map_location="cpu")) for p in a.vectors]
    names = [n for n, _ in blobs]
    layers = [int(x) for x in a.layers.split(",")] if a.layers else list(blobs[0][1]["recommended_layers"])
    print(f"model {model_id}\nvectors {names}\nlayers {layers}", flush=True)

    from transformers import AutoModelForCausalLM, AutoTokenizer
    tok = AutoTokenizer.from_pretrained(model_id, trust_remote_code=True)
    # device_map="auto" needs accelerate, which is not installable in the main venv (its
    # huggingface-hub 1.x outruns every real accelerate release, so pip resolves back to the 0.0.1
    # stub). A 27B model in bf16 is ~54GB and fits on one 80GB card, so shard only when we can, and
    # otherwise load to CPU and move it. The move needs ~54GB of system RAM transiently.
    try:
        import accelerate  # noqa: F401
        kw = {"device_map": "auto"}
    except ImportError:
        kw = {}
        print("accelerate absent — loading on a single device", flush=True)
    model = AutoModelForCausalLM.from_pretrained(model_id, dtype=torch.bfloat16,
                                                 trust_remote_code=True, **kw).eval()
    if not kw:
        model = model.to("cuda" if torch.cuda.is_available() else "cpu")
    dev = next(model.parameters()).device
    M = {}
    for li in layers:
        M[li] = torch.stack([(b["vectors"][li].float() / b["vectors"][li].float().norm())
                             for _, b in blobs], dim=1).to(dev, torch.float32)

    grab: dict[int, torch.Tensor] = {}
    gnorm: dict[int, torch.Tensor] = {}

    def mk(li):
        def hook(mod, args, o):
            h = o[0] if isinstance(o, tuple) else o     # HF: output[0] IS the post-layer stream
            x = h[0].detach().float()
            grab[li] = (x @ M[li]).cpu()
            # ||h|| per token, so the paper's quantity can be recovered offline. Their eq. (2) is
            # cos(h, v) averaged over tokens; M is unit-norm, so `grab` is ||h||*cos, and without
            # the norm a condition that merely inflates the residual stream reads as a projection
            # change. At layer 40 that is exactly what happens: the value axis and a norm-matched
            # random direction both scale by ~1.05 between the no-bet and bet conditions.
            gnorm[li] = x.norm(dim=-1).cpu()
        return hook
    handles = [model.model.layers[li].register_forward_hook(mk(li)) for li in layers]

    n_done = 0
    with torch.no_grad():
        for cond in CONDS:
            p = d / f"{cond}.json"
            if not p.exists():
                continue
            blob = json.loads(p.read_text())
            rr = [r for r in blob["rows"] if "error" not in r][: a.per_cond]
            print(f"\n[{cond}] {len(rr)} rollouts", flush=True)
            pre = chat_prefix(tok, blob["prompt"])
            n_pre = len(tok(pre, add_special_tokens=False)["input_ids"])
            for r in rr:
                reasoning = r.get("reasoning") or ""
                full = pre + reasoning
                enc = tok(full, add_special_tokens=False, return_tensors="pt",
                          return_offsets_mapping=True, truncation=True, max_length=a.max_tokens)
                offs = enc.pop("offset_mapping")[0].tolist()
                grab.clear(); gnorm.clear()   # keep the two dicts in step
                model(enc["input_ids"].to(dev))
                # char offset of each marker -> index of the token whose span contains it
                starts = np.array([s for s, _ in offs])
                ev = []
                for m in MARKER.finditer(reasoning):
                    c = len(pre) + m.start(1)
                    t_i = int(np.searchsorted(starts, c, side="right") - 1)
                    if n_pre <= t_i < len(offs):
                        ev.append(t_i - n_pre)          # index within the reasoning
                np.savez_compressed(
                    out / f"{cond}_{r['i']:03d}.npz",
                    proj=np.stack([grab[li].numpy()[n_pre:] for li in layers]).astype(np.float16),
                    hnorm=np.stack([gnorm[li].numpy()[n_pre:] for li in layers]).astype(np.float32),
                    layers=np.array(layers), vectors=np.array(names), events=np.array(ev, dtype=np.int32),
                    n_pre=n_pre, cond=cond, i=r["i"])
                n_done += 1
                if n_done % 10 == 0:
                    print(f"   {n_done} done ({len(ev)} events in the last one)", flush=True)
    for h in handles:
        h.remove()
    print(f"\nwrote {n_done} files to {out}")


if __name__ == "__main__":
    main()

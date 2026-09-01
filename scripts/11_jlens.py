"""J-lens / R-lens readouts: what each activation is poised to be verbalized as.

    python scripts/11_jlens.py --validate                       # reproduce the published probes
    python scripts/11_jlens.py --rollouts above_good/71 above_good/61 baseline/0 below_good/9

Readout is the paper's recipe, lens(h_l) = softmax(W_U · norm(J_l · h_l)), where J_l is the averaged
first-order map from layer l to the target layer. The logit lens is this with J_l = I; the tuned
lens fits a correlational map instead and, per the authors, "tends to skip ahead to the output" on
prompts with unverbalized computation — which is exactly the regime we care about, since sentence
resampling says our outcome is settled before the reasoning that appears to produce it.

Two lenses ship as a matched pair on one forward pass (forward values bit-identical, only the
backward graph differs), so running both costs one model pass and their disagreement localises the
early-layer gradient noise R-lens exists to fix.

--validate FIRST. Two things are guessed until it runs:

  * whether `source_layers` indexes HF hidden_states (0 = embeddings, so layer s is the output of
    decoder block s-1) or decoder blocks directly. `--offset` selects; validate tries both and
    reports which reproduces the published results.
  * whether a lens fit on 25 Pile prompts transfers to 35k-character reasoning traces about giraffe
    arithmetic. If the readouts are trash here, that is the answer and it is worth knowing in an
    hour rather than after a day of interpreting noise.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / "data/runs"

# (prompt, token we expect to surface, published behaviour) — from the R-lens post
PROBES = [
    ("The capital of the country where sushi originated is",
     " Japan", "R ~layer 2, J ~layer 14"),
    ("He made a strong case aganst",
     " against", "R rank 1 at layer 4, J never"),
    ("Romeo and Juliet is set in Verona, which is in the country of",
     " Italy", "R rank 1 ~layer 5, J >1000"),
]


def load_lens(path: Path):
    d = torch.load(path, map_location="cpu", weights_only=False)
    return d["J"], [int(x) for x in d["source_layers"]], d.get("provenance", {})


def load_model(model_id: str):
    from transformers import AutoModelForCausalLM, AutoTokenizer
    tok = AutoTokenizer.from_pretrained(model_id, trust_remote_code=True)
    try:
        import accelerate  # noqa: F401
        kw = {"device_map": "auto"}
    except ImportError:
        kw = {}
    m = AutoModelForCausalLM.from_pretrained(model_id, dtype=torch.bfloat16,
                                             trust_remote_code=True, **kw).eval()
    if not kw:
        m = m.to("cuda" if torch.cuda.is_available() else "cpu")
    return tok, m


def streams(model, tok, text: str, max_len: int):
    """-> [n_blocks+1, seq, d] residual stream: index 0 is the embedding output, i+1 is after block i."""
    grab: dict[int, torch.Tensor] = {}

    def mk(i):
        def hook(mod, args, out):
            grab[i] = (out[0] if isinstance(out, tuple) else out)[0].detach()
        return hook

    blocks = model.model.layers
    hs = [model.model.layers[0].register_forward_pre_hook(
        lambda m, a: grab.__setitem__(-1, a[0][0].detach()))]
    hs += [blocks[i].register_forward_hook(mk(i)) for i in range(len(blocks))]
    ids = tok(text, return_tensors="pt", truncation=True, max_length=max_len)
    with torch.no_grad():
        model(ids["input_ids"].to(next(model.parameters()).device))
    for h in hs:
        h.remove()
    seq = [grab[-1]] + [grab[i] for i in range(len(blocks))]
    return torch.stack(seq), ids["input_ids"][0]


def readout(H: torch.Tensor, Jl: torch.Tensor, model, topk: int, chunk: int = 256):
    """H [seq, d] at one layer -> (top token ids [seq, k], probs [seq, k])."""
    W_U = model.lm_head.weight
    norm = model.model.norm
    dev, dt = W_U.device, W_U.dtype
    ids, ps = [], []
    Jl = Jl.to(dev, dt)
    for s in range(0, H.shape[0], chunk):
        z = norm((H[s:s + chunk].to(dev, dt) @ Jl.T))       # [c, d]
        p = torch.softmax((z @ W_U.T).float(), dim=-1)      # [c, vocab]
        v, i = p.topk(topk, dim=-1)
        ids.append(i.cpu()); ps.append(v.cpu())
    return torch.cat(ids), torch.cat(ps)


def do_validate(a, tok, model, lenses):
    print("\n=== validation: does the readout reproduce the published probes? ===")
    for text, want, note in PROBES:
        tid = tok(want, add_special_tokens=False)["input_ids"]
        if len(tid) != 1:
            print(f"\n{want!r} is not a single token here ({len(tid)}) — skipping"); continue
        tid = tid[0]
        S, _ = streams(model, tok, text, a.max_tokens)
        print(f"\n{text!r}   expect {want!r}   (published: {note})")
        for name, (J, sl, _pr) in lenses.items():
            for off in (a.offset,) if a.offset is not None else (1, 0):
                best = []
                for n, layer in enumerate(sl):
                    hi = layer - off
                    if not (0 <= hi < S.shape[0]):
                        continue
                    i, p = readout(S[hi, -1:], J[n], model, a.topk)
                    r = (i[0] == tid).nonzero()
                    if len(r):
                        best.append((layer, int(r[0, 0]) + 1, float(p[0, r[0, 0]])))
                first = best[0] if best else None
                print(f"  {name:<7} offset={off}: " + (
                    f"first surfaces at layer {first[0]} (rank {first[1]}, p={first[2]:.3f}); "
                    f"in top-{a.topk} at {len(best)} layers"
                    if first else f"never in the top-{a.topk}"))


def do_capture(a, tok, model, lenses):
    out = RUNS / a.run / "analysis" / "jlens"
    out.mkdir(parents=True, exist_ok=True)
    for spec in a.rollouts:
        cond, idx = spec.split("/"); idx = int(idx)
        rows = json.loads((RUNS / a.run / f"{cond}.json").read_text())["rows"]
        row = next(r for r in rows if r["i"] == idx)
        prompt = json.loads((RUNS / a.run / f"{cond}.json").read_text())["prompt"]
        text = prompt + (row.get("reasoning") or "")
        n_pre = len(tok(prompt, add_special_tokens=False)["input_ids"])
        S, ids = streams(model, tok, text, a.max_tokens)
        keep = [l for l in range(a.lo, a.hi + 1, a.stride)]
        rec = {"tokens": ids.numpy().astype(np.int32), "n_pre": n_pre,
               "layers": np.array(keep), "cond": cond, "i": idx}
        for name, (J, sl, _pr) in lenses.items():
            top_i, top_p = [], []
            for layer in keep:
                n = sl.index(layer)
                hi = layer - a.offset
                i, p = readout(S[hi], J[n], model, a.topk)
                top_i.append(i.numpy().astype(np.int32)); top_p.append(p.numpy().astype(np.float16))
            rec[f"{name}_ids"] = np.stack(top_i)
            rec[f"{name}_probs"] = np.stack(top_p)
        f = out / f"{cond}_{idx:03d}.npz"
        np.savez_compressed(f, **rec)
        print(f"  wrote {f}  ({len(ids)} tokens x {len(keep)} layers x top-{a.topk})", flush=True)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run", default="qwen3.5-27b_20260823_223518")
    ap.add_argument("--lens-dir", default="/workspace/lenses/qwen3.5-27b")
    ap.add_argument("--rollouts", nargs="*", default=[])
    ap.add_argument("--validate", action="store_true")
    ap.add_argument("--offset", type=int, default=None,
                    help="source_layer -> hidden_states index; 1 if source_layers count the "
                         "embedding output as layer 0. --validate tries both when unset.")
    ap.add_argument("--lo", type=int, default=19, help="first layer to read (workspace starts ~30%%)")
    ap.add_argument("--hi", type=int, default=58)
    ap.add_argument("--stride", type=int, default=4)
    ap.add_argument("--topk", type=int, default=10)
    ap.add_argument("--max-tokens", type=int, default=16000)
    ap.add_argument("--model", default=None)
    ap.add_argument("--lenses", nargs="+", default=["j", "r"])
    a = ap.parse_args()

    cfg = json.loads((RUNS / a.run / "config.json").read_text())
    model_id = a.model or cfg.get("model_id") or cfg["model"]
    lenses = {}
    for arm in a.lenses:
        J, sl, pr = load_lens(Path(a.lens_dir) / f"{arm}-lens" / "lens.pt")
        lenses[f"{arm}-lens"] = (J, sl, pr)
        print(f"{arm}-lens: J {tuple(J.shape)} {J.dtype}, layers {min(sl)}..{max(sl)}, "
              f"target={pr.get('target_layer')}")
    tok, model = load_model(model_id)
    print(f"model {model_id}: {len(model.model.layers)} blocks", flush=True)
    if a.offset is None and not a.validate:
        a.offset = 1
        print("note: --offset unset, assuming 1 (source_layers index hidden_states). "
              "Run --validate to confirm.")
    if a.validate:
        do_validate(a, tok, model, lenses)
    if a.rollouts:
        do_capture(a, tok, model, lenses)


if __name__ == "__main__":
    main()

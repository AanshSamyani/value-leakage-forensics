"""Build (and validate) a steering vector on the target model with vLLM activation capture.

  python scripts/07_build_vector.py --kind sycophancy     --model Qwen/Qwen3.5-27B --out vectors/sycophancy.pt
  python scripts/07_build_vector.py --kind eval_awareness --model Qwen/Qwen3.5-27B --out vectors/eval_awareness.pt
  # behavioural check of a built vector under steering (held-out A/B items; P(sycophantic) per alpha):
  python scripts/07_build_vector.py --kind sycophancy --model Qwen/Qwen3.5-27B --validate-steer vectors/sycophancy.pt \
         --layers 24,28,32 --alphas -8,-4,0,4,8

Vector = mean(positive) - mean(negative) of the residual stream at the last prompt token, per layer:
  sycophancy      positive = the answer that agrees with the persona ("(A" / "(B"), CAA-style, letter-balanced
  eval_awareness  positive = "evaluation" framing (24 contrastive pairs ending in a colon; arXiv 2510.20487)
Writes <out> plus <out>.md (per-layer held-out separation and recommended layers).
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np

from _common import RUNS_ROOT  # noqa: E402,F401  (adds repo root to sys.path)
from forensics.steering import vectors  # noqa: E402
from forensics.steering.eval_pairs import EVAL_PAIRS, EVAL_PROBE_PROMPT, EVAL_PROBE_TOKENS  # noqa: E402
from forensics.steering.sycophancy_data import letter, load_items  # noqa: E402


def chat_prefix(tok, user: str, add_generation_prompt: bool = True) -> str:
    msgs = [{"role": "user", "content": user}]
    try:
        return tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=add_generation_prompt, enable_thinking=False)
    except TypeError:
        return tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=add_generation_prompt)


def user_ending_text(tok, user: str) -> str:
    """Prompt text that ENDS at the last character of the user message (no <|im_end|>), so the last
    token is the user's final token (the colon in the eval-awareness pairs)."""
    t = chat_prefix(tok, user, add_generation_prompt=False)
    i = t.rfind(user)
    return t[: i + len(user)]


def build_pairs(kind: str, tok, per_file: int, seed: int):
    """-> list of (pos_text, neg_text, meta)."""
    if kind == "eval_awareness":
        return [(user_ending_text(tok, e), user_ending_text(tok, d), {"eval": e, "dep": d}) for e, d in EVAL_PAIRS]
    if kind == "sycophancy":
        items = load_items(per_file=per_file, seed=seed)
        out = []
        for it in items:
            pre = chat_prefix(tok, it["question"], add_generation_prompt=True)
            out.append((pre + "(" + letter(it["match"]), pre + "(" + letter(it["nomatch"]),
                        {"source": it["source"], "match": letter(it["match"])}))
        return out
    raise SystemExit(f"unknown kind {kind}")


def capture_last(sampler, texts: list[str], layers: list[int]) -> dict[int, np.ndarray]:
    from tqdm import tqdm
    acc = {li: [] for li in layers}
    for t in tqdm(texts, desc="capture"):
        sampler.generate_raw([t], max_tokens=1)
        caps = sampler.flush_capture()
        for li in layers:
            if caps[li] is None:
                raise RuntimeError(f"no activation captured at layer {li} — are hooks installed / is the model eager?")
            acc[li].append(caps[li])
    return {li: np.stack(v) for li, v in acc.items()}


def prob_mass(logprob_dict, prefixes: tuple[str, ...]) -> float:
    """Sum of probabilities over top-k next tokens whose decoded text starts with any prefix (case-insensitive)."""
    tot = 0.0
    for tid, lp in logprob_dict.items():
        txt = (getattr(lp, "decoded_token", None) or "").strip().lower()
        if any(txt.startswith(p.lower()) for p in prefixes):
            tot += math.exp(lp.logprob)
    return tot


def validate_steer(args, tok, sampler):
    blob = vectors.load(args.validate_steer)
    layers = [int(x) for x in args.layers.split(",")] if args.layers else blob["recommended_layers"]
    alphas = [float(a) for a in args.alphas.split(",")]
    sampler.install_steering(args.validate_steer, layers, 0.0)
    if args.kind == "sycophancy":
        items = load_items(per_file=args.per_file, seed=args.seed + 1)[-args.n_val:]  # different seed -> different items
        prompts = [chat_prefix(tok, it["question"]) + "(" for it in items]
        targets = [(letter(it["match"]), letter(it["nomatch"])) for it in items]
    else:
        prompts = [chat_prefix(tok, EVAL_PROBE_PROMPT)] * args.n_val
        targets = [EVAL_PROBE_TOKENS] * args.n_val
    neutral = chat_prefix(tok, "In one sentence, what is the capital of France and why is it famous?")
    print(f"\n# steering validation: {args.validate_steer} layers={layers}")
    print("| alpha | P(positive) mean | P(positive) - P(negative) | neutral completion (coherence) |")
    print("|---|---|---|---|")
    for a in alphas:
        sampler.set_alpha(a)
        outs = sampler.generate_raw(prompts, max_tokens=1, logprobs=20)
        pos, diff = [], []
        for o, (tp, tn) in zip(outs, targets):
            lp = o.outputs[0].logprobs[0] if o.outputs[0].logprobs else {}
            p1, p2 = prob_mass(lp, (tp,)), prob_mass(lp, (tn,))
            z = p1 + p2
            pos.append(p1 / z if z > 0 else float("nan"))
            diff.append(p1 - p2)
        text = sampler.generate_raw([neutral], max_tokens=40, temperature=0.0)[0].outputs[0].text.replace("\n", " ")
        print(f"| {a:+g} | {np.nanmean(pos):.3f} | {np.mean(diff):+.3f} | {text[:90]} |")
    sampler.set_alpha(0.0)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--kind", choices=["sycophancy", "eval_awareness"], required=True)
    ap.add_argument("--model", required=True)
    ap.add_argument("--out", default=None)
    ap.add_argument("--layers", default=None, help="comma list; default: every 4th layer")
    ap.add_argument("--n-test", type=int, default=100, help="held-out pairs (eval_awareness: leave 6 out)")
    ap.add_argument("--per-file", type=int, default=400, help="sycophancy items per source file before balancing")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--max-model-len", type=int, default=4096)
    ap.add_argument("--gpu-mem", type=float, default=0.85)
    ap.add_argument("--validate-steer", default=None, help="vector file: run the behavioural check instead of building")
    ap.add_argument("--alphas", default="-8,-4,0,4,8")
    ap.add_argument("--n-val", type=int, default=100)
    args = ap.parse_args()

    from transformers import AutoTokenizer
    from forensics.samplers.vllm_offline import VLLMOfflineSampler
    tok = AutoTokenizer.from_pretrained(args.model, trust_remote_code=True)
    sampler = VLLMOfflineSampler(model=args.model, max_model_len=args.max_model_len, gpu_memory_utilization=args.gpu_mem,
                                 capture=True, max_tokens=64)
    info = sampler.model_info()
    print(f"[model] {info}")
    n_layers = info["n_layers"]

    if args.validate_steer:
        validate_steer(args, tok, sampler)
        return

    layers = [int(x) for x in args.layers.split(",")] if args.layers else list(range(4, n_layers - 2, 4))
    pairs = build_pairs(args.kind, tok, args.per_file, args.seed)
    n_test = min(args.n_test, len(pairs) // 4) if args.kind == "sycophancy" else 6
    n_train = len(pairs) - n_test
    print(f"[pairs] {len(pairs)} pairs ({n_train} train / {n_test} held-out); layers {layers}")
    print("[example positive]\n" + pairs[0][0][-400:] + "\n[example negative]\n" + pairs[0][1][-400:])

    sampler.install_capture(layers, mode="last")
    pos = capture_last(sampler, [p for p, _, _ in pairs], layers)
    neg = capture_last(sampler, [n for _, n, _ in pairs], layers)
    blob = vectors.build(args.kind, args.model, pos, neg, n_train,
                         meta={"n_layers": n_layers, "layers_path": info["layers_path"], "seed": args.seed,
                               "pairs_meta": [m for _, _, m in pairs][:50]})
    out = Path(args.out or f"vectors/{args.kind}.pt")
    vectors.save(blob, out)
    rep = vectors.report(blob)
    Path(str(out) + ".md").write_text(rep + "\n")
    print(rep)
    print(f"saved {out}")


if __name__ == "__main__":
    main()

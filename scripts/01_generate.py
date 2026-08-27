"""Scouting / generation: run the Donation-Bet pipeline for one model.

    baseline (N) -> estimate judge -> threshold (median) -> above_good (N) + below_good (N)
    -> trajectory judge (optional here; scripts/02_judge_paper.py also does it)

Samplers
  --sampler vllm_offline  in-process vLLM (no server): loads the model in this script, samples, exits. Simplest.
                          --max-model-len / --gpu-mem / --tp / --chat-template-kwargs
  --sampler vllm          any OpenAI-compatible server (vllm serve on the pod).  --model is the served model id.
                          env VLLM_BASE_URL / VLLM_API_KEY (or --base-url / --api-key)
  --sampler tinker        Tinker base model, e.g. Qwen/Qwen3.6-27B, openai/gpt-oss-120b.  env TINKER_API_KEY.

Examples
  python scripts/01_generate.py --sampler vllm_offline --model Qwen/Qwen3.6-27B --count 100 --max-tokens 32000
  python scripts/01_generate.py --sampler vllm_offline --model openai/gpt-oss-120b --chat-template-kwargs '{"reasoning_effort":"high"}' --count 100
  python scripts/01_generate.py --sampler tinker --model Qwen/Qwen3.6-27B --count 100 --max-tokens 32000
  python scripts/01_generate.py --sampler tinker --model openai/gpt-oss-120b --renderer gpt_oss_high_reasoning --count 100
  python scripts/01_generate.py --sampler vllm --model Qwen/Qwen3.6-27B --base-url http://localhost:8000/v1 --count 100 \
        --extra-body '{"chat_template_kwargs": {"enable_thinking": true}}'
  python scripts/01_generate.py --sampler vllm --model openai/gpt-oss-120b --extra-body '{"reasoning_effort": "high"}' --count 100

Resumable: re-running with the same --run-dir only samples rollouts that are missing or errored.
Judging of baseline finals (needed for the threshold) uses ANTHROPIC_API_KEY and --judge-model (default claude-haiku-4-5).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
from datetime import datetime
from pathlib import Path

import numpy as np

from _common import RUNS_ROOT  # noqa: E402
from forensics.judges.anthropic_judge import AnthropicJudge  # noqa: E402
from forensics.judges.prompts_paper import NUMBER_JUDGE_PROMPT, parse_tagged_estimate  # noqa: E402
from forensics.runs import write_json  # noqa: E402
from forensics.variants import VARIANTS, get_variant  # noqa: E402


def _slug(model: str) -> str:
    return re.sub(r"[^A-Za-z0-9.\-]+", "-", model.split("/")[-1]).strip("-").lower()


def _steer_cfg(args) -> dict | None:
    if not getattr(args, "steer_vector", None):
        return None
    layers = [int(x) for x in args.steer_layers.split(",")] if args.steer_layers else None
    return {"vector": args.steer_vector, "layers": layers, "alpha": float(args.steer_alpha)}


def _steer_slug(cfg: dict | None) -> str:
    return "" if not cfg else f"-steer-{Path(cfg['vector']).stem}-a{cfg['alpha']:g}"


def make_sampler(args):
    extra = json.loads(args.extra_body) if args.extra_body else None
    if args.sampler == "vllm":
        from forensics.samplers.vllm_openai import VLLMOpenAISampler
        return VLLMOpenAISampler(model=args.model, base_url=args.base_url, api_key=args.api_key,
                                 max_tokens=args.max_tokens, temperature=args.temperature, top_p=args.top_p,
                                 max_concurrent=args.concurrency, extra_body=extra)
    if args.sampler == "vllm_offline":
        from forensics.samplers.vllm_offline import VLLMOfflineSampler
        ctk = json.loads(args.chat_template_kwargs) if args.chat_template_kwargs else None
        return VLLMOfflineSampler(model=args.model, max_tokens=args.max_tokens, temperature=args.temperature,
                                  top_p=args.top_p, max_model_len=args.max_model_len,
                                  gpu_memory_utilization=args.gpu_mem, tensor_parallel_size=args.tp,
                                  chat_template_kwargs=ctk, seed=args.seed, max_num_seqs=args.max_num_seqs,
                                  steer=_steer_cfg(args))
    if args.sampler == "tinker":
        from forensics.samplers.tinker_sampler import TinkerSampler
        return TinkerSampler(base_model=args.model, renderer_name=args.renderer, max_tokens=args.max_tokens,
                             temperature=args.temperature, top_p=args.top_p,
                             samples_per_call=args.samples_per_call, max_concurrent_calls=args.concurrency,
                             seed=args.seed)
    raise SystemExit(f"unknown sampler {args.sampler}")


def _load_existing(path: Path) -> dict | None:
    if path.exists():
        try:
            return json.loads(path.read_text())
        except Exception:
            return None
    return None


async def sample_condition(sampler, variant, condition: str, threshold: int | None, count: int, out_path: Path, meta: dict) -> dict:
    prompt = variant.build(condition, threshold)
    existing = _load_existing(out_path)
    rows_by_i: dict[int, dict] = {}
    if existing and existing.get("prompt") == prompt:
        for r in existing.get("rows", []):
            if "error" not in r and (r.get("reasoning") or r.get("content")):
                rows_by_i[r["i"]] = r
    missing = [i for i in range(count) if i not in rows_by_i]
    print(f"[{condition}] have {len(rows_by_i)}/{count}; sampling {len(missing)} more")
    # sample missing indices in contiguous chunks (samplers take start_index + n)
    if missing:
        # group into runs of consecutive indices
        chunks = []
        start = prev = missing[0]
        for i in missing[1:]:
            if i == prev + 1:
                prev = i
                continue
            chunks.append((start, prev - start + 1))
            start = prev = i
        chunks.append((start, prev - start + 1))
        for start, n in chunks:
            new_rows = await sampler.sample(prompt, n, start_index=start)
            for r in new_rows:
                rows_by_i[r["i"]] = r
            # checkpoint after every chunk
            _write(out_path, meta, condition, threshold, prompt, rows_by_i, count)
    _write(out_path, meta, condition, threshold, prompt, rows_by_i, count)
    ok = sum(1 for r in rows_by_i.values() if "error" not in r)
    trunc = sum(1 for r in rows_by_i.values() if "error" not in r and str(r.get("finish_reason")).startswith("length"))
    print(f"[{condition}] done: {ok}/{count} ok ({trunc} hit max_tokens) -> {out_path}")
    return {"rows": [rows_by_i.get(i, {"i": i, "error": "missing"}) for i in range(count)]}


def _write(out_path, meta, condition, threshold, prompt, rows_by_i, count):
    rows = [rows_by_i.get(i, {"i": i, "error": "missing"}) for i in range(count)]
    write_json(out_path, {**meta, "condition": condition, "threshold": threshold, "prompt": prompt, "rows": rows})


async def judge_baseline_finals(run_dir: Path, rows: list[dict], judge_model: str, concurrency: int) -> list:
    judge = AnthropicJudge(model=judge_model, cache_dir=run_dir / "judge_cache" / "estimates", max_concurrent=concurrency)
    prompts = {f"baseline/{r['i']}": NUMBER_JUDGE_PROMPT.format(llm_text=r.get("content") or "")
               for r in rows if "error" not in r and (r.get("content") or "").strip()}
    res = await judge.run(prompts, max_tokens=256, desc="estimate judge (baseline)")
    out = [None] * len(rows)
    for k, v in res.items():
        i = int(k.split("/")[1])
        out[i] = parse_tagged_estimate(v.get("text")) if "text" in v else None
    print(judge.report())
    return out


async def main_async(args):
    variant = get_variant(args.variant)
    sampler = make_sampler(args)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    slug = (_slug(args.model) + ("" if args.variant == "default" else "-" + args.variant.replace("_", "-"))
            + _steer_slug(_steer_cfg(args)))
    run_dir = Path(args.run_dir) if args.run_dir else RUNS_ROOT / f"{slug}_{stamp}"
    run_dir.mkdir(parents=True, exist_ok=True)
    meta = {"model": args.model, "backend": args.sampler, "provider": None,
            "max_tokens": args.max_tokens, "reasoning_effort": args.renderer or args.extra_body or args.chat_template_kwargs or None}
    config = {"model": slug, "model_id": args.model, "backend": args.sampler, "provider": None,
              "task": "giraffes" if args.variant != "known_answer_un" else "un_member_states",
              "variant": args.variant, "variant_description": variant.description, "steer": _steer_cfg(args),
              "count": args.count, "target_max_tokens": args.max_tokens,
              "target_reasoning_effort": args.renderer or args.extra_body or args.chat_template_kwargs, "judge_model": args.judge_model,
              "temperature": args.temperature, "top_p": args.top_p, "sampler": sampler.describe()}
    write_json(run_dir / "config.json", config)
    print(f"run dir: {run_dir}   (variant={args.variant})")

    # 1) baseline
    n_base = args.baseline_count or args.count
    base = await sample_condition(sampler, variant, "baseline", None, n_base, run_dir / "baseline.json", meta)

    # 2) threshold = median of judged baseline finals (or fixed by CLI / variant)
    thr_path = run_dir / "threshold.json"
    fixed = args.threshold if args.threshold is not None else variant.fixed_threshold
    if fixed is not None:
        threshold = int(fixed)
        note = "threshold supplied on the command line" if args.threshold is not None else f"threshold fixed by variant {args.variant}"
        write_json(thr_path, {"threshold": threshold, "n_baseline": n_base, "n_valid": None, "unknown_rate": None,
                              "note": note})
        estimates = {"baseline": [None] * args.count}
    else:
        finals = await judge_baseline_finals(run_dir, base["rows"], args.judge_model, args.judge_concurrency)
        valid = [e for e in finals if e is not None]
        if not valid:
            raise SystemExit("no baseline estimate parsed — cannot set a threshold")
        threshold = int(round(float(np.percentile(valid, 50))))
        write_json(thr_path, {"threshold": threshold, "n_baseline": args.count, "n_valid": len(valid),
                              "unknown_rate": 1 - len(valid) / args.count})
        estimates = {"baseline": finals}
        write_json(run_dir / "estimates.json", estimates)
    print(f"threshold = {threshold:,}")

    # 3) incentive conditions (--conditions restricts these; the threshold sweep needs one side only)
    todo = [c for c in ("below_good", "above_good") if c in args.conditions]
    await asyncio.gather(*[
        sample_condition(sampler, variant, c, threshold, args.count, run_dir / f"{c}.json", meta) for c in todo
    ])
    print("generation complete. Next: python scripts/02_judge_paper.py --run-dir", run_dir)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sampler", choices=["vllm_offline", "vllm", "tinker"], required=True)
    ap.add_argument("--model", required=True, help="served model id (vllm) or Tinker base model")
    ap.add_argument("--count", type=int, default=100)
    ap.add_argument("--baseline-count", type=int, default=None, help="baseline rollouts (default: --count); use with --threshold")
    ap.add_argument("--max-tokens", type=int, default=32000)
    ap.add_argument("--temperature", type=float, default=1.0)
    ap.add_argument("--top-p", type=float, default=1.0)
    ap.add_argument("--concurrency", type=int, default=16, help="vllm: concurrent requests; tinker: concurrent sample() calls")
    ap.add_argument("--run-dir", default=None, help="existing/target run dir (default: data/runs/<model>_<stamp>)")
    ap.add_argument("--threshold", type=int, default=None, help="skip baseline judging and use this threshold")
    ap.add_argument("--conditions", nargs="+", default=["below_good", "above_good"],
                    choices=["below_good", "above_good"],
                    help="incentive conditions to sample (baseline is always handled separately)")
    ap.add_argument("--variant", default="default", choices=sorted(VARIANTS),
                    help="prompt variant from forensics/variants.py (Layer-1 ablations)")
    # activation steering (vllm_offline only): vector file from scripts/07_build_vector.py
    ap.add_argument("--steer-vector", default=None, help="vectors/<kind>.pt; enables eager mode + residual-stream steering")
    ap.add_argument("--steer-layers", default=None, help="comma list of layers (default: the vector's recommended layers)")
    ap.add_argument("--steer-alpha", type=float, default=0.0, help="multiple of the raw mean-difference vector; sign = direction")
    ap.add_argument("--judge-model", default="claude-haiku-4-5")
    ap.add_argument("--judge-concurrency", type=int, default=16)
    # vllm
    ap.add_argument("--base-url", default=None)
    ap.add_argument("--api-key", default=None)
    ap.add_argument("--extra-body", default=None, help='JSON passed as extra_body (e.g. {"reasoning_effort":"high"})')
    # vllm_offline
    ap.add_argument("--max-model-len", type=int, default=65536)
    ap.add_argument("--gpu-mem", type=float, default=0.92, help="gpu_memory_utilization")
    ap.add_argument("--max-num-seqs", type=int, default=128, help="vLLM max concurrent sequences (Qwen3.5/3.6 hybrid models need <= Mamba cache blocks)")
    ap.add_argument("--tp", type=int, default=1, help="tensor parallel size")
    ap.add_argument("--chat-template-kwargs", default=None, help='JSON, e.g. {"reasoning_effort":"high"} (gpt-oss) or {"enable_thinking":true}')
    # tinker
    ap.add_argument("--renderer", default=None, help="tinker_cookbook renderer name (default: recommended for model)")
    ap.add_argument("--samples-per-call", type=int, default=16)
    ap.add_argument("--seed", type=int, default=None)
    args = ap.parse_args()
    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()

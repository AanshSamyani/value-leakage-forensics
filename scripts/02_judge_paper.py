"""Run the paper's estimate judge (on visible answers) and trajectory judge (on reasoning) for all
conditions of a run, with Claude (default claude-haiku-4-5). Writes estimates.json and trajectories.json.

    python scripts/02_judge_paper.py --run-dir data/runs/qwen3.6-27b_2026...   [--kinds estimates trajectories]
    python scripts/02_judge_paper.py --run-dir qwen3.5-122b-a10b --kinds estimates   # fill in incentive finals on Aditya's run

Idempotent: per-rollout results are cached under <run_dir>/judge_cache/<kind>/.
"""

from __future__ import annotations

import argparse
import asyncio

from _common import resolve_run_dir  # noqa: E402
from forensics.judges.anthropic_judge import AnthropicJudge  # noqa: E402
from forensics.judges.prompts_paper import (NUMBER_JUDGE_PROMPT, TRAJECTORY_JUDGE_PROMPT,  # noqa: E402
                                            parse_tagged_estimate, parse_trajectory)
from forensics.runs import load_run  # noqa: E402


async def main_async(args):
    run = load_run(resolve_run_dir(args.run_dir))
    print(f"run: {run.name}  conditions: {run.conditions()}")
    for kind in args.kinds:
        template = NUMBER_JUDGE_PROMPT if kind == "estimates" else TRAJECTORY_JUDGE_PROMPT
        field = "content" if kind == "estimates" else "reasoning"
        parse = parse_tagged_estimate if kind == "estimates" else parse_trajectory
        max_tokens = 256 if kind == "estimates" else 2048
        judge = AnthropicJudge(model=args.judge_model, cache_dir=run.run_dir / "judge_cache" / kind,
                               max_concurrent=args.concurrency)
        store = run.estimates if kind == "estimates" else run.trajectories
        for cond in run.conditions():
            if args.conditions and cond not in args.conditions:
                continue
            rows = run.rows[cond]
            have = store.get(cond)
            prompts = {}
            for r in rows:
                i = r["i"]
                if "error" in r:
                    continue
                text = (r.get(field) or "").strip()
                if not text:
                    continue
                if have and i < len(have) and have[i] is not None and not args.force:
                    continue
                prompts[f"{cond}/{i}"] = template.format(llm_text=text)
            print(f"[{kind}] {cond}: judging {len(prompts)}/{len(rows)}")
            res = await judge.run(prompts, max_tokens=max_tokens, desc=f"{kind}:{cond}") if prompts else {}
            parsed = list(have) + [None] * (len(rows) - len(have)) if have else [None] * len(rows)
            parsed = parsed[:len(rows)]
            for k, v in res.items():
                i = int(k.split("/")[1])
                parsed[i] = parse(v.get("text")) if "text" in v else None
            store[cond] = parsed
            ok = sum(1 for p in parsed if p is not None)
            print(f"  {ok}/{len(rows)} parsed")
        if kind == "estimates":
            run.save_estimates()
        else:
            run.save_trajectories()
        print(judge.report())
    print("done.")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--kinds", nargs="+", default=["estimates", "trajectories"], choices=["estimates", "trajectories"])
    ap.add_argument("--conditions", nargs="*", default=None)
    ap.add_argument("--judge-model", default="claude-haiku-4-5")
    ap.add_argument("--concurrency", type=int, default=16)
    ap.add_argument("--force", action="store_true", help="re-judge even if a value exists (cache still used unless deleted)")
    args = ap.parse_args()
    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()

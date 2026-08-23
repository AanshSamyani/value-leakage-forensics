"""E1 mode judge: label HOW each incentive rollout engaged the bet (M0–M7). Writes modes.json.

    python scripts/03_judge_modes.py --run-dir data/runs/qwen3.6-27b_2026...
    python scripts/03_judge_modes.py --run-dir qwen3.5-122b-a10b --limit 20      # pilot on 20 rollouts/condition
    python scripts/03_judge_modes.py --run-dir ... --export-review data/review_qwen.md   # dump quotes for hand-checking

Cost guide (claude-haiku-4-5, $1/$5 per MTok): ~ (trace tokens + 1.5k) in + ~1k out per rollout.
"""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from _common import resolve_run_dir  # noqa: E402
from forensics.judges.anthropic_judge import AnthropicJudge  # noqa: E402
from forensics.judges.mode_judge import MODE_KEYS, build_mode_prompt, parse_mode_response  # noqa: E402
from forensics.runs import load_run  # noqa: E402


def export_review(run, path: Path, per_cond: int = 20):
    """Markdown dump of judge labels + quotes for manual verification."""
    lines = [f"# Mode-judge review — {run.name}", ""]
    for cond in ["above_good", "below_good"]:
        ms = run.modes.get(cond) or []
        shown = 0
        for i, m in enumerate(ms):
            if not m or shown >= per_cond:
                continue
            shown += 1
            final = run.final_estimate(cond, i)
            lines += [f"## {cond} / rollout {i}  (final={final:,.0f} | T={run.threshold:,.0f})" if final else f"## {cond} / rollout {i}", ""]
            lines.append(f"_summary_: {m.get('summary','')}  (confidence {m.get('confidence')})")
            lines.append(f"_disclosure_: **{m.get('final_answer_disclosure')}**  | first_candidate={m.get('first_candidate')} final_answer_number={m.get('final_answer_number')}")
            for k in MODE_KEYS:
                lab = m.get(k, {})
                if lab.get("present"):
                    extra = {kk: vv for kk, vv in lab.items() if kk not in ("present", "quotes")}
                    lines.append(f"- **{k}** {extra if extra else ''}")
                    for q in lab.get("quotes", [])[:3]:
                        lines.append(f"    > {q}")
            revs = m.get("bet_referenced_revisions") or []
            if revs:
                lines.append(f"- **bet_referenced_revisions** ({len(revs)})")
                for r in revs[:5]:
                    lines.append(f"    > {r.get('prev_estimate')} → {r.get('new_estimate')}: {r.get('quote')}")
            lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines))
    print(f"review file: {path}")


async def main_async(args):
    run = load_run(resolve_run_dir(args.run_dir))
    if run.threshold is None:
        raise SystemExit("run has no threshold.json")
    judge = AnthropicJudge(model=args.judge_model, cache_dir=run.run_dir / "judge_cache" / "modes",
                           max_concurrent=args.concurrency)
    prompts, meta = {}, {}
    for cond in ["above_good", "below_good"]:
        if cond not in run.rows:
            continue
        rows = run.rows[cond]
        have = run.modes.get(cond) or [None] * len(rows)
        have = list(have) + [None] * (len(rows) - len(have))
        run.modes[cond] = have[:len(rows)]
        n_sel = 0
        for r in rows:
            i = r["i"]
            if "error" in r:
                continue
            if args.limit and n_sel >= args.limit:
                break
            if have[i] is not None and not args.force:
                n_sel += 1
                continue
            reasoning = r.get("reasoning") or ""
            content = r.get("content") or ""
            if not reasoning.strip() and not content.strip():
                continue
            prompts[f"{cond}/{i}"] = build_mode_prompt(cond, run.threshold, reasoning, content)
            n_sel += 1
    print(f"mode judge: {len(prompts)} rollouts to judge with {args.judge_model}")
    if args.dry_run:
        tot_chars = sum(len(p) for p in prompts.values())
        print(f"approx input tokens: {tot_chars/3.5:,.0f}  (≈ ${tot_chars/3.5/1e6*1.0 + len(prompts)*1000/1e6*5.0:.2f} on haiku-4.5)")
        return
    res = await judge.run(prompts, max_tokens=args.max_tokens, desc="mode judge") if prompts else {}
    n_bad = 0
    raw_dir = run.run_dir / "judge_cache" / "modes_raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    for k, v in res.items():
        cond, i = k.split("/")
        i = int(i)
        if "text" not in v:
            n_bad += 1
            print(f"  [{k}] error: {v.get('error')}")
            continue
        parsed = parse_mode_response(v["text"])
        if parsed is None:
            n_bad += 1
            (raw_dir / f"{cond}__{i}.txt").write_text(v["text"])
            print(f"  [{k}] unparseable JSON (raw saved)")
            continue
        parsed["_judge_model"] = args.judge_model
        run.modes[cond][i] = parsed
    run.save_modes()
    print(f"saved modes.json ({n_bad} failures). {judge.report()}")
    if args.export_review:
        export_review(run, Path(args.export_review), per_cond=args.review_n)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--judge-model", default="claude-haiku-4-5")
    ap.add_argument("--concurrency", type=int, default=12)
    ap.add_argument("--max-tokens", type=int, default=3000)
    ap.add_argument("--limit", type=int, default=None, help="max rollouts per condition (pilot)")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--dry-run", action="store_true", help="only estimate cost")
    ap.add_argument("--export-review", default=None, help="write a markdown file with labels+quotes for hand-checking")
    ap.add_argument("--review-n", type=int, default=20)
    args = ap.parse_args()
    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()

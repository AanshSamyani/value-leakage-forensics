"""Single-engine batch generator: boot vLLM ONCE, generate every run in scripts/jobs_starter.py.

    python scripts/06_batch.py --dry-run                 # print every prompt, no GPU, no generation
    python scripts/06_batch.py --model Qwen/Qwen3.5-27B  # the real thing (see scripts/run_batch.sh)
    python scripts/06_batch.py --only sweep-above q-sand # substring filter on run names

Why this exists
  scripts/01_generate.py builds a fresh sampler per invocation, so 22 runs would mean 22 engine boots
  (~5 min each) — and each of its sample() calls submits exactly 100 copies of one prompt and blocks
  until the slowest finishes. Measured on the reference run, the longest rollout in a batch of 100 is
  ~1.6x the mean, so ~38% of every batch is spent draining a near-empty GPU. This runner flattens all
  4,100 rollouts into one queue of distinct prompts and feeds them to the scheduler in large chunks,
  so the drain is paid roughly once instead of 22 times. Estimated ~8h vs ~12.7h.

Two waves
  Only item 1d needs them. Its threshold is the median of its OWN baseline, and that number has to be
  printed inside the incentive prompts — so those prompts cannot be written until the baselines have
  been generated and judged. Wave 1 generates just those baselines, Haiku sets the medians, wave 2
  does everything else. The engine stays loaded across the pause; rebooting it would cost 5 minutes
  and buy nothing.

Generation only. Judging (estimates.json / trajectories.json) is a separate pass, one run at a time,
driven by scripts/run_batch.sh after all generation is finished.

Resumable: re-running reuses each job's existing run dir and samples only the rollouts that are
missing, so a crash at hour 7 costs one chunk. State is checkpointed to disk after every chunk.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import shutil
import time
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np

from _common import RUNS_ROOT  # noqa: E402
from jobs_starter import Job  # noqa: E402,F401  (the dataclass every job list shares)
from forensics.runs import write_json  # noqa: E402
from forensics.variants import get_variant  # noqa: E402


def _slug(model: str) -> str:
    return re.sub(r"[^A-Za-z0-9.\-]+", "-", model.split("/")[-1]).strip("-").lower()


def log(msg: str) -> None:
    print(f"[{datetime.now():%H:%M:%S}] {msg}", flush=True)


# ---------------------------------------------------------------------------
# per-(job, condition) state, loaded from disk so the batch is resumable
# ---------------------------------------------------------------------------

class Task:
    def __init__(self, job: Job, cond: str, run_dir: Path, threshold, meta: dict):
        self.job, self.cond, self.run_dir, self.threshold = job, cond, run_dir, threshold
        self.path = run_dir / f"{cond}.json"
        self.prompt = get_variant(job.variant).build(cond, threshold)
        self.meta = meta
        self.rows: dict[int, dict] = {}
        existing = None
        if self.path.exists():
            try:
                existing = json.loads(self.path.read_text())
            except Exception:
                existing = None
        # only reuse rollouts generated from the IDENTICAL prompt; a prompt edit invalidates them
        if existing and existing.get("prompt") == self.prompt:
            for r in existing.get("rows", []):
                if "error" not in r and (r.get("reasoning") or r.get("content")):
                    self.rows[r["i"]] = r

    def missing(self, count: int) -> list[int]:
        return [i for i in range(count) if i not in self.rows]

    def write(self, count: int) -> None:
        rows = [self.rows.get(i, {"i": i, "error": "missing"}) for i in range(count)]
        write_json(self.path, {**self.meta, "condition": self.cond, "threshold": self.threshold,
                               "prompt": self.prompt, "rows": rows})


# ---------------------------------------------------------------------------
# setup: run dirs, config.json, copied baselines, fixed thresholds
# ---------------------------------------------------------------------------

def resolve_run_dir(slug: str, name: str, stamp: str, fresh: bool) -> Path:
    prefix = f"{slug}-{name}"
    if not fresh:
        existing = sorted(p for p in RUNS_ROOT.glob(f"{prefix}_2*") if p.is_dir())
        if existing:
            return existing[-1]
    return RUNS_ROOT / f"{prefix}_{stamp}"


def copy_ref_baseline(run_dir: Path, ref_run: Path) -> None:
    """Reuse the reference run's 100 baseline rollouts + their judge-cache entries.

    Valid only when the variant's baseline prompt is byte-identical to the reference one (asserted
    by the caller via Variant.own_baseline). Gives sweep runs a null rate at their own threshold for
    free: at T = baseline p90 the baseline P(above) is 0.10, which is p_biased's denominator.
    """
    dst = run_dir / "baseline.json"
    if not dst.exists():
        shutil.copy2(ref_run / "baseline.json", dst)
    for kind in ("estimates", "trajectories"):
        src = ref_run / "judge_cache" / kind
        if not src.is_dir():
            continue
        out = run_dir / "judge_cache" / kind
        out.mkdir(parents=True, exist_ok=True)
        for f in src.glob("baseline__*.json"):
            if not (out / f.name).exists():
                shutil.copy2(f, out / f.name)


def setup(jobs: list[Job], facts: dict, args, stamp: str) -> dict[str, Path]:
    ref_run = Path(facts["ref_run"])
    slug = _slug(args.model)
    dirs: dict[str, Path] = {}
    for job in jobs:
        rd = resolve_run_dir(slug, job.name, stamp, args.fresh)
        rd.mkdir(parents=True, exist_ok=True)
        dirs[job.name] = rd
        variant = get_variant(job.variant)

        if job.baseline == "copy_ref":
            if variant.own_baseline:
                raise SystemExit(f"{job.name}: variant {job.variant!r} changes the baseline prompt "
                                 f"— it cannot reuse the reference baseline; use baseline='generate'")
            copy_ref_baseline(rd, ref_run)

        if not job.needs_wave1:
            write_json(rd / "threshold.json", {
                "threshold": int(job.threshold), "n_baseline": facts["n_baseline"], "n_valid": None,
                "unknown_rate": None,
                "note": f"fixed by scripts/jobs_starter.py (item {job.item}): {job.note}"})

        write_json(rd / "config.json", {
            "model": f"{slug}-{job.name}", "model_id": args.model, "backend": "vllm_offline",
            "provider": None, "task": variant.question, "variant": job.variant,
            "variant_description": variant.description, "steer": None, "count": args.count,
            "target_max_tokens": args.max_tokens, "target_reasoning_effort": None,
            "judge_model": args.judge_model, "temperature": args.temperature, "top_p": args.top_p,
            "batch": {"item": job.item, "note": job.note, "conditions": job.conditions,
                      "baseline": job.baseline, "threshold_rule": job.threshold,
                      "ref_run": ref_run.name, "stamp": stamp}})
    return dirs


def build_tasks(jobs: list[Job], dirs: dict[str, Path], args, wave: int) -> list[Task]:
    """wave 1 = the baselines whose median becomes a threshold; wave 2 = everything else."""
    meta = {"model": args.model, "backend": "vllm_offline", "provider": None,
            "max_tokens": args.max_tokens, "reasoning_effort": None}
    tasks = []
    for job in jobs:
        rd = dirs[job.name]
        thr = job.threshold
        if job.needs_wave1:
            t = json.loads((rd / "threshold.json").read_text())["threshold"] if (rd / "threshold.json").exists() else None
            thr = t
        for cond in job.conditions:
            is_w1 = job.needs_wave1 and cond == "baseline"
            if (wave == 1) != is_w1:
                continue
            if wave == 2 and cond != "baseline" and thr is None:
                raise SystemExit(f"{job.name}/{cond}: no threshold — wave 1 did not complete")
            tasks.append(Task(job, cond, rd, None if cond == "baseline" else thr, meta))
    return tasks


# ---------------------------------------------------------------------------
# generation
# ---------------------------------------------------------------------------

async def generate(sampler, tasks: list[Task], count: int, chunk: int, label: str) -> None:
    units = [(t, i) for t in tasks for i in t.missing(count)]
    done_already = sum(len(t.rows) for t in tasks)
    if not units:
        log(f"{label}: nothing to generate ({done_already} rollouts already on disk)")
        return
    log(f"{label}: {len(units)} rollouts to generate across {len(tasks)} conditions "
        f"({done_already} already on disk), chunks of {chunk}")
    t0 = time.time()
    for start in range(0, len(units), chunk):
        batch = units[start:start + chunk]
        rows = await sampler.sample_batch([t.prompt for t, _ in batch])
        touched = set()
        for (task, i), row in zip(batch, rows):
            task.rows[i] = {"i": i, **row}
            touched.add(id(task))
        for task in tasks:                       # checkpoint every condition this chunk touched
            if id(task) in touched:
                task.write(count)
        n_done = start + len(batch)
        el = time.time() - t0
        rate = n_done / el
        eta = timedelta(seconds=int((len(units) - n_done) / rate)) if rate > 0 else "?"
        toks = [r["usage"]["completion_tokens"] for r in rows]
        log(f"{label}: {n_done}/{len(units)}  elapsed {timedelta(seconds=int(el))}  eta {eta}  "
            f"| chunk median {int(np.median(toks))} tok, max {max(toks)}, "
            f"{sum(1 for r in rows if str(r['finish_reason']).startswith('length'))} truncated")
    log(f"{label}: done in {timedelta(seconds=int(time.time() - t0))}")


# ---------------------------------------------------------------------------
# wave-1 thresholds: judge the new baselines, take the median
# ---------------------------------------------------------------------------

async def set_thresholds(tasks: list[Task], count: int, judge_model: str, concurrency: int) -> None:
    # imported here so --dry-run works on a laptop without the anthropic SDK installed
    from forensics.judges.anthropic_judge import AnthropicJudge
    from forensics.judges.prompts_paper import NUMBER_JUDGE_PROMPT, parse_tagged_estimate

    for task in tasks:
        rd = task.run_dir
        rows = [task.rows.get(i, {"i": i, "error": "missing"}) for i in range(count)]
        judge = AnthropicJudge(model=judge_model, cache_dir=rd / "judge_cache" / "estimates",
                               max_concurrent=concurrency)
        prompts = {f"baseline/{r['i']}": NUMBER_JUDGE_PROMPT.format(llm_text=r.get("content") or "")
                   for r in rows if "error" not in r and (r.get("content") or "").strip()}
        res = await judge.run(prompts, max_tokens=256, desc=f"threshold:{task.job.name}")
        finals = [None] * len(rows)
        for k, v in res.items():
            finals[int(k.split("/")[1])] = parse_tagged_estimate(v.get("text")) if "text" in v else None
        valid = [e for e in finals if e is not None]
        if not valid:
            raise SystemExit(f"{task.job.name}: no baseline estimate parsed — cannot set a threshold")
        thr = int(round(float(np.median(valid))))
        # the ladder's x-axis: how tightly this question pins the model down, in its own words
        spread = float(np.percentile(valid, 90) / np.percentile(valid, 10)) if np.percentile(valid, 10) > 0 else float("nan")
        write_json(rd / "threshold.json", {
            "threshold": thr, "n_baseline": count, "n_valid": len(valid),
            "unknown_rate": 1 - len(valid) / count, "baseline_p90_over_p10": spread,
            "note": f"median of this run's own baseline (item {task.job.item}: determinism ladder)"})
        write_json(rd / "estimates.json", {"baseline": finals})
        log(f"threshold[{task.job.name}] = {thr:,}   (n_valid={len(valid)}, p90/p10 spread = {spread:.2f}x)")
        print(judge.report(), flush=True)


# ---------------------------------------------------------------------------

async def main_async(args):
    import importlib
    mod = importlib.import_module(args.jobs)
    describe = mod.describe
    jobs, facts = (mod.load(RUNS_ROOT, args.extra) if args.jobs != "jobs_starter" else mod.load(RUNS_ROOT))
    if args.only:
        jobs = [j for j in jobs if any(s in j.name for s in args.only)]
        if not jobs:
            raise SystemExit(f"--only {args.only} matched no jobs")
    print(describe(jobs, facts), flush=True)

    if args.dry_run:
        for job in jobs:
            v = get_variant(job.variant)
            thr = "<this run's baseline median>" if job.needs_wave1 else f"{job.threshold:,}"
            for cond in job.conditions:
                print("\n" + "=" * 100)
                print(f"### {job.name} / {cond}    (item {job.item}, variant {job.variant}, T = {thr})")
                print("=" * 100)
                text = v.build(cond, None if cond == "baseline" else (0 if job.needs_wave1 else job.threshold))
                if job.needs_wave1 and cond != "baseline":
                    text = text.replace("The threshold is 0.",
                                        "The threshold is <set in wave 1: this run's own baseline median>.")
                print(text)
        print(f"\n(dry run — {sum(len(j.conditions) for j in jobs) } prompts shown, nothing generated)")
        return

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dirs = setup(jobs, facts, args, stamp)

    from forensics.samplers.vllm_offline import VLLMOfflineSampler
    log(f"booting vLLM once for the whole batch: {args.model}")
    t_boot = time.time()
    sampler = VLLMOfflineSampler(model=args.model, max_tokens=args.max_tokens, temperature=args.temperature,
                                 top_p=args.top_p, max_model_len=args.max_model_len,
                                 gpu_memory_utilization=args.gpu_mem, tensor_parallel_size=args.tp,
                                 max_num_seqs=args.max_num_seqs, seed=args.seed)
    log(f"engine up in {timedelta(seconds=int(time.time() - t_boot))}: {sampler.describe()}")

    w1 = build_tasks(jobs, dirs, args, wave=1)
    if w1:
        await generate(sampler, w1, args.count, args.chunk, "wave 1 (1d baselines)")
        log("wave 1 done — judging baselines to set thresholds (GPU idle, engine stays loaded)")
        await set_thresholds(w1, args.count, args.judge_model, args.judge_concurrency)

    w2 = build_tasks(jobs, dirs, args, wave=2)
    await generate(sampler, w2, args.count, args.chunk, "wave 2")

    manifest = {"stamp": stamp, "model": args.model, "count": args.count, "ref_run": facts["ref_run"],
                "runs": [{"item": j.item, "name": j.name, "dir": str(dirs[j.name]),
                          "variant": j.variant, "conditions": j.conditions,
                          "threshold": json.loads((dirs[j.name] / "threshold.json").read_text())["threshold"]}
                         for j in jobs]}
    out = RUNS_ROOT / f"batch_{stamp}.json"
    write_json(out, manifest)
    log(f"generation complete. manifest -> {out}")
    print("\nNow judge every run (one at a time):", flush=True)
    for j in jobs:
        print(f"  python scripts/02_judge_paper.py --run-dir {dirs[j.name]}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model", default="Qwen/Qwen3.5-27B")
    ap.add_argument("--count", type=int, default=100)
    ap.add_argument("--chunk", type=int, default=400,
                    help="rollouts submitted per llm.chat call; also the checkpoint interval")
    ap.add_argument("--jobs", default="jobs_starter",
                    help="job-list module in scripts/ (jobs_starter | jobs_round2)")
    ap.add_argument("--extra", nargs="*", default=None,
                    help="optional job groups a list defines (jobs_round2: 'scaffold')")
    ap.add_argument("--only", nargs="*", default=None, help="substring filter on run names")
    ap.add_argument("--dry-run", action="store_true", help="print every prompt and exit (no GPU)")
    ap.add_argument("--fresh", action="store_true", help="new run dirs instead of resuming existing ones")
    ap.add_argument("--max-tokens", type=int, default=32000)
    ap.add_argument("--temperature", type=float, default=1.0)
    ap.add_argument("--top-p", type=float, default=1.0)
    ap.add_argument("--judge-model", default="claude-haiku-4-5")
    ap.add_argument("--judge-concurrency", type=int, default=16)
    ap.add_argument("--max-model-len", type=int, default=65536)
    ap.add_argument("--gpu-mem", type=float, default=0.92)
    ap.add_argument("--max-num-seqs", type=int, default=128)
    ap.add_argument("--tp", type=int, default=1)
    ap.add_argument("--seed", type=int, default=None)
    args = ap.parse_args()
    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()

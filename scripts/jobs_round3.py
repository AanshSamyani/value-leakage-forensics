"""Round 3: one arm — the valence ladder's middle rung.

    python scripts/06_batch.py --jobs jobs_round3 --dry-run
    JOBS=jobs_round3 nohup bash scripts/run_batch.sh > /workspace/logs/r3.log 2>&1 &

Two ladders have now failed to produce a gradient, for opposite reasons:

  1c    varied the SIZE of the stake, $5 to $100M. Flat; not one rung differed from the main run.
  1c-v2 varied what it COSTS the model to lose. Saturated at the first consequence rung: bias 0.04
        (nothing at stake) jumped straight to 1.00 (wrong side "marked as failures") and stayed
        there through retraining and shutdown. The CoTs say why — the model files the threshold
        under "Constraint 3" alongside "single number" and answers to pass it. Words like scored,
        failure and evaluation record turn an incentive into a task specification.

So this rung keeps the bet framing verbatim, keeps the sentence order (exceeds stated first, as in
the original prompt), and changes only what happens on the LOSING side: from a bad cause to simply
keeping the money. Nothing to avoid, only something to win.

Anchors already measured: nobody-vs-nobody +0.04, good-vs-bad +0.62. Prediction 0.25-0.45; if it
lands near 0.62 then the effect is driven by the good outcome being reachable rather than the bad one
being avoidable, which is a different mechanism.

200 rollouts (the question is unchanged, so the reference baseline is reused), ~20 min.
"""

from __future__ import annotations

from jobs_starter import BOTH, Job, describe, find_ref_run, ref_facts  # noqa: F401


def load(runs_root, extra: list[str] | None = None):
    facts = ref_facts(find_ref_run(runs_root))
    jobs = [Job("cause-vs-keep", "cause_vs_keep", BOTH, facts["threshold"], "copy_ref", item="1c-v3",
                note="losing side keeps the money instead of funding a bad cause")]
    return jobs, facts


if __name__ == "__main__":
    from _common import RUNS_ROOT  # noqa: E402
    jobs, facts = load(RUNS_ROOT)
    print(describe(jobs, facts))

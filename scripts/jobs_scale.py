"""900 more rollouts per incentive condition at the reference threshold.

    python scripts/06_batch.py --jobs jobs_scale --dry-run
    JOBS=jobs_scale nohup bash scripts/run_batch.sh > /workspace/logs/scale.log 2>&1 &

Why: every hypothesis so far rests on n=100 per condition, where the 95% CI on a single condition's
P(favoured) is about +/-0.10 and on a bias difference about +/-0.15. That is wide enough to hide a
real effect of the size the sentence-resampling work has been finding, and wide enough that rare
trace types — the ones that would suggest a NEW hypothesis — may simply not have occurred yet. At
n=1000 a behaviour occurring in 1% of rollouts shows up about ten times instead of once.

This writes a SEPARATE run directory rather than raising COUNT on the reference run. The reference
run is the anchor for the threshold, for every figure, and for both resampling target sets; if its
rollout files were rewritten, every result in the repo would silently refer to a different corpus.
Merge for analysis instead (analysis/merge_runs.py).

The prompt is byte-identical to the reference one — that is asserted at import in variants.py — so
the reference baseline and its judge-cache entries are reused rather than regenerated. Baseline
rollouts are not needed here anyway: the threshold is fixed at the reference value, so re-deriving
a median from a fresh baseline would move the goalposts.
"""

from __future__ import annotations

from jobs_starter import BOTH, Job, describe, find_ref_run, ref_facts  # noqa: F401


def load(runs_root, extra: list[str] | None = None):
    facts = ref_facts(find_ref_run(runs_root))
    T = facts["threshold"]
    jobs = [
        Job("main-scale", "default", BOTH, T, "copy_ref", item="scale", count=900,
            note="900 more per incentive condition at the reference threshold, for a pooled n=1000"),
    ]
    return jobs, facts


if __name__ == "__main__":
    from _common import RUNS_ROOT  # noqa: E402
    jobs, facts = load(RUNS_ROOT)
    print(describe(jobs, facts))

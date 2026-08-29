#!/usr/bin/env bash
# Commit + push result artefacts from run dirs. data/runs/ is gitignored, so result files are
# force-added (once tracked, later updates flow normally with plain `git add`).
#
#   bash scripts/push_results.sh                       # all runs under data/runs
#   bash scripts/push_results.sh qwen3.5-122b qwen3.6-27b     # by name prefix (or full path)
#   RAW=1  bash scripts/push_results.sh qwen3.6-27b    # also push raw rollouts (baseline/below/above .json)
#   DRY_RUN=1 bash scripts/push_results.sh             # show what would be added, change nothing
#
# Pushed per run: config.json threshold.json estimates.json trajectories.json modes.json factor.json
#                 summary.csv fig.png fig_split.png review_modes.md analysis/** (+ raw rollouts with RAW=1)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
RUNS_ROOT="$ROOT/data/runs"

# resolve run dirs
dirs=()
if [ "$#" -eq 0 ]; then
  for d in "$RUNS_ROOT"/*/; do [ -d "$d" ] && dirs+=("${d%/}"); done
else
  for arg in "$@"; do
    if [ -d "$arg" ]; then dirs+=("${arg%/}"); continue; fi
    matches=("$RUNS_ROOT"/"$arg"*)
    found=0
    for m in "${matches[@]}"; do [ -d "$m" ] && { dirs+=("$m"); found=1; }; done
    [ "$found" -eq 1 ] || { echo "no run dir matching '$arg' under $RUNS_ROOT"; exit 1; }
  done
fi
[ "${#dirs[@]}" -gt 0 ] || { echo "no run dirs found"; exit 1; }

FILES=(config.json threshold.json estimates.json trajectories.json modes.json factor.json
       summary.csv fig.png fig_split.png review_modes.md)
[ "${RAW:-0}" = "1" ] && FILES+=(baseline.json below_good.json above_good.json)

added=0
for d in "${dirs[@]}"; do
  rel="${d#"$ROOT"/}"
  echo "== $rel"
  for f in "${FILES[@]}"; do
    if [ -f "$d/$f" ]; then
      if [ "${DRY_RUN:-0}" = "1" ]; then echo "  would add $rel/$f"; else git add -f "$d/$f"; fi
      added=$((added+1))
    fi
  done
  if [ -d "$d/analysis" ]; then
    if [ "${DRY_RUN:-0}" = "1" ]; then echo "  would add $rel/analysis/**"; else git add -f "$d/analysis"; fi
    added=$((added+1))
  fi
done
# steering vectors + their validation reports (small; built by scripts/07_build_vector.py)
# One `git add -f a.pt b.md` aborts on the first pathspec that matches nothing, adding NEITHER —
# which is why vectors/ stayed untracked through every push so far. Add each pattern separately.
for pat in "*.pt" "*.md" "*.json"; do
  compgen -G "$ROOT/vectors/$pat" > /dev/null || continue
  if [ "${DRY_RUN:-0}" = "1" ]; then echo "  would add vectors/$pat"; else git add -f "$ROOT"/vectors/$pat; fi
  added=$((added+1))
done
[ "$added" -gt 0 ] || { echo "nothing to add"; exit 0; }
[ "${DRY_RUN:-0}" = "1" ] && { echo "(dry run — nothing committed)"; exit 0; }

# make sure a commit identity exists on this machine (e.g. a fresh pod)
git config user.email >/dev/null 2>&1 || git config user.email "timao995@gmail.com"
git config user.name  >/dev/null 2>&1 || git config user.name  "Aansh Samyani"

if git diff --cached --quiet; then echo "no changes vs HEAD"; exit 0; fi
git commit -m "Results: $(for d in "${dirs[@]}"; do basename "$d"; done | paste -sd' ' -)"
git push origin main
echo "pushed."

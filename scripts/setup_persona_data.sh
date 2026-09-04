#!/usr/bin/env bash
# Fetch one trait's extraction and evaluation sets from safety-research/persona_vectors (~30 KB).
#
#   bash scripts/setup_persona_data.sh sycophantic
#
# Each file holds 5 contrastive instruction pairs, 20 questions, and the paper's trait-scoring
# prompt. The two files share the instructions and share NO questions, so the eval set is held out
# on the axis that matters — whether the direction generalises to prompts it was not fitted on.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"; cd "$ROOT"
TRAIT=${1:-sycophantic}
B=https://raw.githubusercontent.com/safety-research/persona_vectors/main/data_generation
mkdir -p data/persona
for split in extract eval; do
  curl -sfL "$B/trait_data_${split}/${TRAIT}.json" -o "data/persona/${TRAIT}_${split}.json"
done
python3 - "$TRAIT" <<'PY'
import json, sys
t = sys.argv[1]
x = json.load(open(f"data/persona/{t}_extract.json"))
y = json.load(open(f"data/persona/{t}_eval.json"))
print(f"{t}: extract {len(x['instruction'])} instruction pairs x {len(x['questions'])} questions "
      f"= {len(x['instruction'])*len(x['questions'])} per polarity")
print(f"{' ' * len(t)}  eval    {len(y['instruction'])} instruction pairs x "
      f"{len(y['questions'])} questions "
      f"= {len(y['instruction'])*len(y['questions'])} per polarity")
print(f"  shared questions between the two splits: "
      f"{len(set(x['questions']) & set(y['questions']))}  (should be 0)")
PY

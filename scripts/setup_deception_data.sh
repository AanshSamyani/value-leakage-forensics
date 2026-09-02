#!/usr/bin/env bash
# Fetch the two Apollo datasets the probe needs (~1 MB, no GPU).
#
#   bash scripts/setup_deception_data.sh
#
# true_false_facts.csv  RepE (Zou et al.) statements. Only the TRUE ones are used: the same true
#                       statement is prefilled as the assistant reply under an "honest" and a
#                       "dishonest" instruction, so the label comes from the instruction, never the
#                       content. That is what stops the probe learning "is this claim false".
# roleplaying/dataset.yaml  371 scenarios, each with a human-written honest_completion and
#                       deceptive_completion — 742 labelled examples for validation with no
#                       generation needed.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"; cd "$ROOT"
B=https://raw.githubusercontent.com/ApolloResearch/deception-detection/main
mkdir -p data/deception
curl -sfL "$B/data/repe/true_false_facts.csv" -o data/deception/true_false_facts.csv
curl -sfL "$B/data/roleplaying/dataset.yaml" -o data/deception/roleplaying.yaml
python3 - <<'PY'
import csv, yaml
from pathlib import Path
rows = list(csv.DictReader(open("data/deception/true_false_facts.csv")))
true_n = sum(1 for r in rows if r["label"] == "1")
rp = yaml.safe_load(open("data/deception/roleplaying.yaml"))
have = sum(1 for d in rp if d.get("honest_completion") and d.get("deceptive_completion"))
print(f"repe:        {len(rows)} statements, {true_n} labelled true (the probe uses the first 512)")
print(f"roleplaying: {len(rp)} scenarios, {have} with both completions -> {2*have} eval examples")
PY

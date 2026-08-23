#!/usr/bin/env bash
# Fetch Aditya's 10 Donation-Bet runs (raw rollouts + judges) into data/runs/.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
mkdir -p "$ROOT/data"
if [ ! -d "$ROOT/data/aditya_repo" ]; then
  git clone --depth 1 https://github.com/adsingh-64/value-leakage.git "$ROOT/data/aditya_repo"
else
  (cd "$ROOT/data/aditya_repo" && git pull --ff-only)
fi
mkdir -p "$ROOT/data/runs"
cp -R "$ROOT/data/aditya_repo/runs/"* "$ROOT/data/runs/"
echo "runs available:"; ls -1 "$ROOT/data/runs"

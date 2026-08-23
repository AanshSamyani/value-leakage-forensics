"""Shared CLI helpers: repo-root on sys.path, .env loading, run-dir resolution."""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
except Exception:  # dotenv optional
    pass

RUNS_ROOT = Path(os.environ.get("RUNS_ROOT", ROOT / "data" / "runs"))


def resolve_run_dir(arg: str) -> Path:
    """Accept an absolute/relative path, or a run-dir name (or unique prefix) under RUNS_ROOT."""
    p = Path(arg)
    if p.is_dir():
        return p
    cands = [d for d in RUNS_ROOT.iterdir() if d.is_dir() and d.name.startswith(arg)] if RUNS_ROOT.exists() else []
    if len(cands) == 1:
        return cands[0]
    if not cands:
        raise SystemExit(f"no run dir matching {arg!r} under {RUNS_ROOT}")
    raise SystemExit(f"ambiguous run dir {arg!r}: {[c.name for c in cands]}")

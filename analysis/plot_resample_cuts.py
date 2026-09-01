"""One Figure-2-style PNG per resampled window: the sentences, shaded by resampling score.

    python analysis/plot_resample_cuts.py
    open plots/resample_cuts/

Model Forensics (arXiv 2606.26071) figure 2 prints an excerpt of a chain of thought with each
sentence shaded by its effect on the outcome. Same here, one image per +/-2 window.

Red = the sentence made the model more likely to land on the side that wins the bet (it contributed
to the bias). Green = it pushed the other way. Colour intensity is on a SINGLE scale across every
image in the folder, so a strong red in one is the same effect size as a strong red in another —
which means the flat windows genuinely render flat rather than being stretched to look eventful.

A +/-2 window samples five cut points, which yields four scores: a sentence's score is the
difference between the cut before it and the cut after it, so the last cut has nothing to pair with.
Only those scored sentences are drawn — no surrounding context, and no colour key; the scale is
shared across the folder and printed when the figures are built.

The sweep is excluded — 69 cut points across one rollout is not a window, and it already has its
own viewer.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Rectangle

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "scripts"))
_s = importlib.util.spec_from_file_location("rs", ROOT / "scripts" / "09_resample.py")
rs = importlib.util.module_from_spec(_s); _s.loader.exec_module(rs)

RUN = ROOT / "data/runs/qwen3.5-27b_20260823_223518"
OUT = ROOT / "plots/resample_cuts"
RED, GREEN = (0.70, 0.23, 0.13), (0.18, 0.42, 0.27)
WRAP, FS, WIDTH = 92, 10.5, 9.4
CW = 0.6 * FS / 72 / WIDTH          # monospace advance, as a fraction of figure width
LH = 1.75 * FS / 72                 # line height in inches
MARGIN = 0.055


def load(mode: str):
    blob = json.loads((RUN / "analysis" / f"resample_{mode}.json").read_text())
    ok = [r for r in blob["results"] if r.get("favoured") is not None]
    cuts: dict = {}
    for r in ok:
        cuts.setdefault((r["cond"], r["i"]), {}).setdefault(r["cut"], []).append(bool(r["favoured"]))
    out = []
    for t in blob["targets"]:
        key = (t["cond"], t["i"])
        if key not in cuts:
            continue
        row = next(x for x in json.loads((RUN / f"{key[0]}.json").read_text())["rows"]
                   if x["i"] == key[1])
        sents = rs.split_sentences(row["reasoning"] or "")
        rate = {c: float(np.mean(v)) for c, v in cuts[key].items()}
        score = {a: rate[a + 1] - rate[a] for a in rate if a + 1 in rate}
        for k in (t.get("ks") or [t["k"]]):
            out.append(dict(mode=mode, cond=key[0], i=key[1], k=k, sents=sents,
                            score=score, n={c: len(v) for c, v in cuts[key].items()},
                            T=t["T"], final=t["final"]))
    return out


def wrap(runs: list[tuple[str, int | None]]) -> list[list[tuple[str, int | None]]]:
    """Greedy word wrap that preserves which sentence each fragment came from."""
    lines, cur, col = [], [], 0
    for text, sid in runs:
        for word in text.split():
            w = len(word)
            if col and col + 1 + w > WRAP:
                lines.append(cur); cur, col = [], 0
            piece = (" " if col else "") + word
            if cur and cur[-1][1] == sid:
                cur[-1] = (cur[-1][0] + piece, sid)
            else:
                cur.append((piece if col else word, sid))
            col += len(piece)
    if cur:
        lines.append(cur)
    return lines


def draw(rec: dict, scale: float) -> Path:
    k, sents, score = rec["k"], rec["sents"], rec["score"]
    # only the sentences this window actually scored — no surrounding context
    js = sorted(j for j in score if k - 2 <= j <= k + 2)
    runs = [(sents[j].replace("\n", " "), j) for j in js]
    lines = wrap(runs)

    pad = 0.10
    H = LH * len(lines) + 2 * pad
    fig = plt.figure(figsize=(WIDTH, H), facecolor="white")
    top = 1 - pad / H
    for li, line in enumerate(lines):
        y = top - (li + 0.5) * (LH / H)
        col = 0
        for text, sid in line:
            x = MARGIN + col * CW
            w = len(text) * CW
            sc = score[sid]
            a = min(0.80, 0.06 + 0.74 * min(1.0, abs(sc) / scale))
            fig.add_artist(Rectangle((x, y - LH / H * 0.42), w, LH / H * 0.84,
                                     facecolor=(RED if sc > 0 else GREEN), alpha=a,
                                     edgecolor="none", zorder=1))
            fig.text(x, y, text, family="monospace", fontsize=FS, va="center", ha="left",
                     color="#1A1A1A", zorder=2)
            col += len(text)

    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f"{rec['mode']}_{rec['cond']}_{rec['i']:03d}_cut{k:03d}.png"
    fig.savefig(path, dpi=200, facecolor="white", bbox_inches="tight")
    plt.close(fig)
    return path


def main() -> None:
    recs = load("targets") + load("targets_74_19") + load("brake")
    allv = np.array([abs(v) for r in recs for j, v in r["score"].items()
                     if r["k"] - 3 <= j <= r["k"] + 2])
    # 98th percentile, not the max: one sentence scores -0.526 against a next-highest of 0.210, and
    # scaling to it would render the other sixteen windows nearly white. Anything above the scale
    # clips to full saturation, so that sentence is still unmistakably the darkest in the set.
    scale = float(np.percentile(allv, 98))
    n_clip = int((allv > scale).sum())
    print(f"{len(recs)} windows; shared colour scale +/-{scale:.3f} "
          f"({n_clip} score(s) clip to full saturation)\n")
    print(f"{'file':<44} {'target score':>13} {'window range':>22}")
    print("-" * 82)
    for r in sorted(recs, key=lambda x: (x["mode"], x["cond"], x["i"], x["k"])):
        p = draw(r, scale)
        w = [v for j, v in r["score"].items() if r["k"] - 3 <= j <= r["k"] + 2]
        ts = r["score"].get(r["k"])
        print(f"{p.name:<44} {ts:+13.3f} {f'{min(w):+.3f} to {max(w):+.3f}':>22}")


if __name__ == "__main__":
    main()

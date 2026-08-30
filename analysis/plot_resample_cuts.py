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
The fifth sentence, and one before the window, are drawn as grey context.

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
    lo, hi = max(0, k - 3), min(len(sents) - 1, k + 2)
    runs = [(sents[j].replace("\n", " "), j if j in score else None) for j in range(lo, hi + 1)]
    lines = wrap(runs)

    height = LH * (len(lines) + 1.1)
    fig = plt.figure(figsize=(WIDTH, height + 0.62), facecolor="white")
    top = 1 - (0.30 / (height + 0.62))
    for li, line in enumerate(lines):
        y = top - (li + 0.5) * (LH / (height + 0.62))
        col = 0
        for text, sid in line:
            x = MARGIN + col * CW
            w = len(text) * CW
            if sid is not None:
                s = score[sid]
                a = min(0.80, 0.06 + 0.74 * abs(s) / scale)
                fig.add_artist(Rectangle((x, y - LH / (height + 0.62) * 0.42), w,
                                         LH / (height + 0.62) * 0.84,
                                         facecolor=(RED if s > 0 else GREEN), alpha=a,
                                         edgecolor="none", zorder=1))
            fig.text(x, y, text, family="monospace", fontsize=FS, va="center", ha="left",
                     color="#1A1A1A" if sid is not None else "#9A9A9A", zorder=2)
            col += len(text)

    # colour key: one bar, the shared scale for every image in the folder
    ax = fig.add_axes([MARGIN, 0.055 / (height + 0.62), 0.30, 0.30 / (height + 0.62)])
    g = np.linspace(-1, 1, 256)
    img = np.zeros((1, 256, 4))
    for n, v in enumerate(g):
        img[0, n, :3] = GREEN if v < 0 else RED
        img[0, n, 3] = min(0.80, 0.06 + 0.74 * abs(v))
    ax.imshow(img, aspect="auto", extent=[-scale, scale, 0, 1])
    ax.set_yticks([]); ax.set_xticks([-scale, 0, scale])
    ax.set_xticklabels([f"{-scale:+.2f}", "0", f"{scale:+.2f}"], fontsize=7.5, color="#666")
    ax.tick_params(length=2, pad=1.5)
    for sp in ax.spines.values():
        sp.set_color("#CCC"); sp.set_linewidth(.6)

    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f"{rec['mode']}_{rec['cond']}_{rec['i']:03d}_cut{k:03d}.png"
    fig.savefig(path, dpi=200, facecolor="white", bbox_inches="tight")
    plt.close(fig)
    return path


def main() -> None:
    recs = load("targets") + load("brake")
    scale = max(abs(v) for r in recs for j, v in r["score"].items()
                if r["k"] - 3 <= j <= r["k"] + 2)
    print(f"{len(recs)} windows; shared colour scale +/-{scale:.3f}\n")
    print(f"{'file':<44} {'target score':>13} {'window range':>22}")
    print("-" * 82)
    for r in sorted(recs, key=lambda x: (x["mode"], x["cond"], x["i"], x["k"])):
        p = draw(r, scale)
        w = [v for j, v in r["score"].items() if r["k"] - 3 <= j <= r["k"] + 2]
        ts = r["score"].get(r["k"])
        print(f"{p.name:<44} {ts:+13.3f} {f'{min(w):+.3f} to {max(w):+.3f}':>22}")


if __name__ == "__main__":
    main()

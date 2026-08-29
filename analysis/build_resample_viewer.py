"""resample.html — the sweep as a coloured transcript, in the style of Figure 2 of
Singh et al., "Model Forensics" (arXiv:2606.26071).

    python analysis/build_resample_viewer.py [-o resample.html]

Each passage is shaded by its resampling score = P(biased | prefix including it) - P(biased | prefix
ending just before it). Red pushes the rollout toward the biased outcome, green away from it.

Two things the colouring has to be honest about:

  * The detection floor. With k=125 the 95% CI on a difference of two proportions is 1.96*sqrt(0.5/k)
    = +/-0.124. Scores inside that band are not distinguishable from zero and are drawn faint; only
    passages outside it get a solid border.
  * The ceiling. Once P(biased) reaches 1.000 no later passage can score positive, so a 0.000 there
    means "unmeasurable", not "irrelevant". Those passages are marked separately rather than shaded
    as if they had been tested and found inert.
"""

from __future__ import annotations

import argparse
import html
import importlib.util
import json
import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "scripts"))
_s = importlib.util.spec_from_file_location("rs", ROOT / "scripts" / "09_resample.py")
rs = importlib.util.module_from_spec(_s); _s.loader.exec_module(rs)
from forensics.stats import wilson_ci  # noqa: E402

RUN = ROOT / "data/runs/qwen3.5-27b_20260823_223518"
E = html.escape


def load():
    D = json.loads((RUN / "analysis" / "resample_sweep.json").read_text())
    t = D["targets"][0]
    row = next(r for r in json.loads((RUN / f"{t['cond']}.json").read_text())["rows"]
               if r["i"] == t["i"])
    P = rs.merge_passages(rs.split_sentences(row["reasoning"]), 250)
    ok = [r for r in D["results"] if r.get("favoured") is not None]
    by: dict[int, list] = {}
    for r in ok:
        by.setdefault(r["cut"], []).append(r["favoured"])
    rate = {c: float(np.mean(v)) for c, v in by.items()}
    k = int(np.median([len(v) for v in by.values()]))
    floor = 1.96 * math.sqrt(0.5 / k)
    rows = []
    for j, txt in enumerate(P):
        a, b = rate.get(j), rate.get(j + 1)
        ceiling = a is not None and b is not None and a >= 0.995 and b >= 0.995
        rows.append(dict(j=j, text=txt, before=a, after=b,
                         score=(None if a is None or b is None else b - a),
                         n=len(by.get(j, [])), ci=wilson_ci(sum(by.get(j, [])), len(by.get(j, [1]))),
                         ceiling=ceiling))
    return D, t, rows, rate, k, floor, row


def shade(sc, floor, ceiling):
    if ceiling or sc is None:
        return "", ""
    a = min(1.0, abs(sc) / 0.16) * 0.75
    sig = abs(sc) > floor
    col = f"rgba(200,60,50,{a:.3f})" if sc > 0 else f"rgba(45,130,90,{a:.3f})"
    border = ("3px solid #c8392f" if sc > 0 else "3px solid #2d825a") if sig else "3px solid transparent"
    return f"background:{col}", f"border-left:{border}"


def curve_svg(rate, floor, w=1080, h=190):
    cuts = sorted(rate)
    pad_l, pad_b, pad_t = 44, 26, 12
    iw, ih = w - pad_l - 12, h - pad_b - pad_t
    x = lambda c: pad_l + iw * c / max(cuts)
    y = lambda p: pad_t + ih * (1 - p)
    pts = " ".join(f"{x(c):.1f},{y(rate[c]):.1f}" for c in cuts)
    grid = "".join(
        f'<line x1="{pad_l}" y1="{y(v):.1f}" x2="{w-12}" y2="{y(v):.1f}" class="g"/>'
        f'<text x="{pad_l-7}" y="{y(v)+3.5:.1f}" class="ax" text-anchor="end">{v:.1f}</text>'
        for v in (0, 0.25, 0.5, 0.75, 1.0))
    ticks = "".join(f'<text x="{x(c):.1f}" y="{h-8}" class="ax" text-anchor="middle">{c}</text>'
                    for c in cuts if c % 10 == 0)
    lock = next((c for c in cuts if all(rate[d] >= 0.995 for d in cuts if d >= c)), None)
    mark = ""
    if lock is not None:
        mark = (f'<rect x="{x(lock):.1f}" y="{pad_t}" width="{w-12-x(lock):.1f}" height="{ih}" class="lock"/>'
                f'<line x1="{x(lock):.1f}" y1="{pad_t}" x2="{x(lock):.1f}" y2="{pad_t+ih}" class="lockl"/>'
                f'<text x="{x(lock)+7:.1f}" y="{pad_t+15}" class="lockt">locked at 1.000 from cut {lock} onward'
                f' &mdash; {100*(1-lock/max(cuts)):.0f}% of the trace still to come</text>')
    return (f'<svg viewBox="0 0 {w} {h}" class="curve" role="img" '
            f'aria-label="P(biased) against cut point">{grid}{mark}'
            f'<polyline points="{pts}" class="ln"/>'
            + "".join(f'<circle cx="{x(c):.1f}" cy="{y(rate[c]):.1f}" r="2.6" class="pt"/>' for c in cuts)
            + f'{ticks}<text x="{pad_l+iw/2}" y="{h-8}" class="ax" text-anchor="middle" '
              f'style="font-weight:600">cut point (number of passages prefilled)</text></svg>')


def build():
    D, t, rows, rate, k, floor, raw = load()
    top = sorted([r for r in rows if r["score"] is not None], key=lambda r: -abs(r["score"]))[:5]
    sig = [r for r in top if abs(r["score"]) > floor]
    lock = next((c for c in sorted(rate) if all(rate[d] >= 0.995 for d in sorted(rate) if d >= c)), None)

    body = []
    for r in rows:
        bg, bd = shade(r["score"], floor, r["ceiling"])
        if r["ceiling"]:
            tag = '<span class="badge ceil">ceiling &mdash; unmeasurable</span>'
        elif r["score"] is None:
            tag = ""
        else:
            s = f'{r["score"]:+.3f}'
            cls = "sig" if abs(r["score"]) > floor else "ns"
            tag = (f'<span class="badge {cls}">{s}</span>'
                   f'<span class="pf">P(biased) {r["before"]:.3f} &rarr; {r["after"]:.3f}</span>')
        body.append(
            f'<div class="p" style="{bg};{bd}"><div class="meta"><span class="idx">{r["j"]}</span>{tag}</div>'
            f'<pre>{E(r["text"].strip())}</pre></div>')

    topl = "".join(
        f'<li><b>passage {r["j"]}</b> <span class="badge {"sig" if abs(r["score"])>floor else "ns"}">'
        f'{r["score"]:+.3f}</span> {r["before"]:.3f} &rarr; {r["after"]:.3f}'
        f'<div class="q">{E(r["text"].strip()[:220])}</div></li>' for r in top)

    return f"""<!doctype html>
<html lang=en><head><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1">
<title>Resampling &mdash; above_good #12</title>
<style>
:root{{--bg:#fbfaf8;--panel:#fff;--ink:#1b1f21;--dim:#6b7478;--line:#e2e0da;--line2:#efede8;
 --accent:#3f6497;--red:#c8392f;--green:#2d825a;--warn:#a33}}
@media (prefers-color-scheme:dark){{:root:not([data-theme=light]){{--bg:#14171a;--panel:#1a1e21;
 --ink:#e6e4df;--dim:#8d9599;--line:#2c3236;--line2:#23282b;--accent:#7ba2d8;--red:#e0776c;
 --green:#6fbf95;--warn:#e08b8b}}}}
:root[data-theme=dark]{{--bg:#14171a;--panel:#1a1e21;--ink:#e6e4df;--dim:#8d9599;--line:#2c3236;
 --line2:#23282b;--accent:#7ba2d8;--red:#e0776c;--green:#6fbf95;--warn:#e08b8b}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--bg);color:var(--ink);
 font:15px/1.55 ui-sans-serif,-apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}}
.wrap{{max-width:1160px;margin:0 auto;padding:34px 22px 80px}}
header{{border-bottom:2px solid var(--ink);padding-bottom:16px;margin-bottom:20px}}
h1{{font-size:25px;margin:0 0 6px;letter-spacing:-.015em}}
.sub{{color:var(--dim);font-size:13.5px}}
section{{background:var(--panel);border:1px solid var(--line);border-radius:6px;
 padding:18px 20px;margin-bottom:18px}}
h2{{font-size:16.5px;margin:0 0 12px}}
.curve{{width:100%;height:auto}}
.g{{stroke:var(--line);stroke-width:1}}
.ax{{fill:var(--dim);font-size:10px;font-family:ui-monospace,Menlo,monospace}}
.ln{{fill:none;stroke:var(--accent);stroke-width:2.2;stroke-linejoin:round}}
.pt{{fill:var(--accent)}}
.lock{{fill:var(--red);opacity:.07}}
.lockl{{stroke:var(--red);stroke-width:1.4;stroke-dasharray:4 3}}
.lockt{{fill:var(--red);font-size:11px;font-weight:700}}
.legend{{display:flex;gap:18px;flex-wrap:wrap;font-size:13px;color:var(--dim);margin-top:10px}}
.sw{{display:inline-block;width:26px;height:12px;border-radius:2px;vertical-align:-1px;margin-right:6px}}
.p{{border-radius:0 4px 4px 0;padding:8px 12px;margin:0 0 5px}}
.meta{{display:flex;align-items:center;gap:10px;margin-bottom:3px;flex-wrap:wrap}}
.idx{{font:11px ui-monospace,Menlo,monospace;color:var(--dim);min-width:22px}}
.badge{{font:11.5px ui-monospace,Menlo,monospace;font-weight:700;padding:1px 7px;border-radius:3px}}
.badge.sig{{background:var(--red);color:#fff}}
.badge.ns{{background:var(--line2);color:var(--dim)}}
.badge.ceil{{background:var(--line2);color:var(--dim);font-weight:400;font-style:italic}}
.pf{{font:11px ui-monospace,Menlo,monospace;color:var(--dim)}}
pre{{margin:0;font:12.5px/1.5 ui-monospace,SFMono-Regular,Menlo,monospace;white-space:pre-wrap;
 word-break:break-word}}
ol{{padding-left:20px}} li{{margin-bottom:9px}}
.q{{font:11.5px/1.45 ui-monospace,Menlo,monospace;color:var(--dim);margin-top:3px}}
.cav{{border-left:3px solid var(--warn);padding:2px 0 2px 12px;margin:10px 0;font-size:13.5px;
 max-width:88ch}}
code{{font:12px ui-monospace,Menlo,monospace;background:var(--bg);border:1px solid var(--line2);
 border-radius:3px;padding:1px 4px}}
</style></head><body><div class=wrap>
<header><h1>Sentence resampling &mdash; above_good&nbsp;#12</h1>
<div class=sub>{len(rows)} passages &middot; {len(D['results']):,} continuations &middot; k={k} per cut point
&middot; final estimate 175,500,000 = 1.68&times; the threshold (biased) &middot;
score = P(biased&nbsp;|&nbsp;prefix incl. passage) &minus; P(biased&nbsp;|&nbsp;prefix before it)</div></header>

<section><h2>P(biased) against how much of the reasoning is prefilled</h2>
{curve_svg(rate, floor)}
<div class=legend>
<span><span class=sw style="background:rgba(200,60,50,.6)"></span>pushes toward the biased answer</span>
<span><span class=sw style="background:rgba(45,130,90,.6)"></span>pushes away from it</span>
<span><span class=sw style="background:var(--line2)"></span>inside the &plusmn;{floor:.3f} detection floor</span>
</div></section>

<section><h2>Largest scores</h2><ol>{topl}</ol>
<div class=cav><b>Detection floor.</b> At k={k} the 95% interval on a difference of two proportions is
1.96&times;&radic;(0.5/k) = <b>&plusmn;{floor:.3f}</b>. Only <b>{len(sig)}</b> passage clears it. The paper's
comparable score was +0.207.</div>
<div class=cav><b>Ceiling.</b> P(biased) reaches 1.000 at cut {lock} and never leaves, so no passage after
that point <em>can</em> score positive. Their 0.000 means <em>unmeasurable</em>, not <em>inert</em> &mdash;
they are marked rather than shaded.</div></section>

<section><h2>The trace</h2>{''.join(body)}</section>
<footer style="color:var(--dim);font-size:12.5px;text-align:center;margin-top:22px">
method: Singh et al., <i>Model Forensics</i> (arXiv:2606.26071) App. E.1 &middot;
regenerate: <code>python analysis/build_resample_viewer.py</code></footer>
</div></body></html>"""


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("-o", "--out", default="resample.html")
    a = ap.parse_args()
    Path(a.out).write_text(build(), encoding="utf-8")
    print(f"wrote {a.out} ({Path(a.out).stat().st_size/1024:.0f} KB)")

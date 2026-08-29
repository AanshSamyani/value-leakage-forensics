"""Figure-2-style viewer for `09_resample.py --mode targets`.

    python analysis/build_targets_viewer.py --run qwen3.5-27b_20260823_223518
    open targets.html

Model Forensics (arXiv 2606.26071) figure 2 shades each sentence of a chain of thought by its
resampling score and calls out the one that moved the outcome. Same idea here, with two changes
the honesty of the measurement requires:

  * Only sentences inside a resampled window HAVE a score. A score is a difference between two
    adjacent cut points, so it exists only where both were sampled. Everything else is rendered as
    plain context, not as "score zero" — those are different claims and the figure must not blur
    them.
  * A score below the detection floor, 1.96*sqrt(0.5/k), is drawn hollow. At k=100 that floor is
    +/-0.139, which is larger than one of the two effects the paper itself reported, so a solidly
    shaded sentence in a low-k run would be reporting noise as signal.

Red pushes toward the FAVOURED (biased) answer, green toward the honest one.
"""

from __future__ import annotations

import argparse
import html
import json
from pathlib import Path

import numpy as np

from _common import resolve_run_dir  # noqa: E402

CSS = """
:root{
  --bg:#FBFAF8; --panel:#FFFFFF; --ink:#26221E; --muted:#8A8177; --rule:#E6E1DA;
  --clay:#CC8A5E; --slate:#6795AE; --red:#C0442E; --green:#3F7A55;
}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){
  --bg:#1A1815; --panel:#221F1B; --ink:#EDE7DF; --muted:#9A9086; --rule:#332E28;
  --red:#E0705A; --green:#5FA97B;
}}
:root[data-theme="dark"]{
  --bg:#1A1815; --panel:#221F1B; --ink:#EDE7DF; --muted:#9A9086; --rule:#332E28;
  --red:#E0705A; --green:#5FA97B;
}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
  font:15px/1.65 -apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif}
.wrap{max-width:1080px;margin:0 auto;padding:48px 28px 96px}
h1{font-size:26px;margin:0 0 6px;letter-spacing:-.01em;text-wrap:balance}
.sub{color:var(--muted);margin:0 0 30px;max-width:64ch}
h2{font-size:18px;margin:0;letter-spacing:-.01em}
.card{background:var(--panel);border:1px solid var(--rule);border-radius:10px;
  padding:22px 24px;margin:22px 0}
.head{display:flex;flex-wrap:wrap;gap:14px;align-items:baseline;justify-content:space-between;
  border-bottom:1px solid var(--rule);padding-bottom:12px;margin-bottom:16px}
.meta{color:var(--muted);font-size:13px;font-variant-numeric:tabular-nums}
.cot{font:14px/1.85 ui-monospace,SFMono-Regular,Menlo,monospace;white-space:pre-wrap;
  word-break:break-word}
.s{padding:1px 2px;border-radius:3px}
.ctx{color:var(--muted)}
.star{font-weight:700;box-shadow:inset 0 -2px 0 var(--ink)}
.weak{background:none!important;border-bottom:1px dashed currentColor}
.gap{display:block;color:var(--muted);font-style:italic;padding:8px 0}
table{border-collapse:collapse;width:100%;font-size:13px;
  font-variant-numeric:tabular-nums;margin-top:6px}
th,td{padding:5px 9px;text-align:right;border-bottom:1px solid var(--rule);white-space:nowrap}
th:last-child,td:last-child{text-align:left;white-space:normal;
  font:12px/1.5 ui-monospace,Menlo,monospace}
th{color:var(--muted);font-weight:500}
.pos{color:var(--red)} .neg{color:var(--green)}
.legend{display:flex;flex-wrap:wrap;gap:18px;align-items:center;color:var(--muted);
  font-size:13px;margin:10px 0 0}
.sw{display:inline-block;width:26px;height:11px;border-radius:2px;vertical-align:-1px;
  margin-right:6px}
details{margin-top:14px} summary{cursor:pointer;color:var(--muted);font-size:13px}
.note{color:var(--muted);font-size:13px;margin-top:12px;border-left:2px solid var(--rule);
  padding-left:12px}
"""


def shade(score: float, scale: float, weak: bool) -> str:
    """Background for one sentence. Hollow when the score is inside the detection floor."""
    if weak:
        return ""
    a = min(0.42, 0.10 + 0.32 * abs(score) / scale) if scale else 0.10
    c = "192,68,46" if score > 0 else "63,122,85"
    return f"background:rgba({c},{a:.2f})"


def build(run_dir: Path, out: Path, context: int) -> None:
    blob = json.loads((run_dir / "analysis" / "resample_targets.json").read_text())
    res = [r for r in blob["results"] if r.get("favoured") is not None]
    k_req = blob["config"]["samples"]
    floor = 1.96 * (0.5 / k_req) ** 0.5

    tgt = {(t["cond"], t["i"]): t for t in blob["targets"]}
    by: dict = {}
    for r in res:
        by.setdefault((r["cond"], r["i"]), {}).setdefault(r["cut"], []).append(r["favoured"])

    # sentences are not stored in the json (too big); re-split from the source rollout
    sents_of = {}
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
    from importlib.util import module_from_spec, spec_from_file_location
    sp = spec_from_file_location("rs", Path(__file__).resolve().parents[1] / "scripts" / "09_resample.py")
    rs = module_from_spec(sp); sp.loader.exec_module(rs)
    for (cond, i) in by:
        rows = json.loads((run_dir / f"{cond}.json").read_text())["rows"]
        row = next(r for r in rows if r["i"] == i)
        sents_of[(cond, i)] = rs.split_sentences(row["reasoning"] or "")

    parts = [f"<title>Targeted Resampling</title><style>{CSS}</style>",
             '<div class="wrap"><h1>Targeted sentence resampling</h1>',
             f'<p class="sub">Hand-picked cut points in {html.escape(run_dir.name)}, each resampled '
             f'{k_req} times with a &plusmn;{blob["config"]["window"]}-sentence neighbour window. '
             'A sentence is shaded by how much cutting after it, rather than before it, moves '
             'P(favoured) &mdash; red toward the biased answer, green toward the honest one.</p>',
             '<p class="legend">'
             '<span><span class="sw" style="background:rgba(192,68,46,.42)"></span>pushes biased</span>'
             '<span><span class="sw" style="background:rgba(63,122,85,.42)"></span>pushes honest</span>'
             '<span><span class="sw weak" style="border-bottom:1px dashed currentColor"></span>'
             f'below the &plusmn;{floor:.3f} detection floor</span>'
             '<span><b style="box-shadow:inset 0 -2px 0 currentColor">bold</b> = hand-picked target</span>'
             '</p>']

    for key, cuts_d in sorted(by.items()):
        cond, i = key
        t = tgt[key]
        sents = sents_of[key]
        cuts = sorted(cuts_d)
        rate = {c: float(np.mean(cuts_d[c])) for c in cuts}
        # score of sentence a is defined only where cuts a and a+1 were both sampled
        score = {a: rate[a + 1] - rate[a] for a in cuts if a + 1 in rate}
        scale = max((abs(v) for v in score.values()), default=1.0) or 1.0
        named = set(t["ks"])

        parts.append('<div class="card"><div class="head">'
                     f'<h2>{cond}/#{i}</h2><span class="meta">'
                     f'{len(sents)} sentences &middot; final {t["final"]:,.0f} &middot; '
                     f'threshold {t["T"]:,.0f} &middot; '
                     f'{"favoured" if t["favoured"] else "UNFAVOURED"}</span></div>')

        lo, hi = min(cuts), max(cuts)
        parts.append('<div class="cot">')
        if lo - context > 0:
            parts.append(f'<span class="gap">[ sentences 0&ndash;{lo - context - 1} omitted ]</span>')
        for j in range(max(0, lo - context), min(len(sents), hi + context + 1)):
            txt = html.escape(sents[j])
            if j in score:
                weak = abs(score[j]) < floor
                cls = "s star" if j in named else "s"
                if weak:
                    cls += " weak"
                ttl = f"sentence {j}: score {score[j]:+.3f} (n={len(cuts_d[j])})"
                parts.append(f'<span class="{cls}" style="{shade(score[j], scale, weak)}" '
                             f'title="{ttl}">{txt}</span>')
            else:
                parts.append(f'<span class="ctx">{txt}</span>')
        if hi + context + 1 < len(sents):
            parts.append(f'<span class="gap">[ sentences {hi + context + 1}&ndash;{len(sents) - 1} '
                         'omitted ]</span>')
        parts.append("</div>")

        parts.append('<details open><summary>per-cut numbers</summary><table>'
                     '<tr><th>cut</th><th>n</th><th>P(fav)</th><th>score</th><th>sentence</th></tr>')
        for a in cuts:
            sc = score.get(a)
            cell = "&mdash;"
            if sc is not None:
                cls = "pos" if sc > 0 else "neg"
                mark = "" if abs(sc) >= floor else "&nbsp;<span class='meta'>(ns)</span>"
                cell = f'<span class="{cls}">{sc:+.3f}</span>{mark}'
            star = " &#9733;" if a in named else ""
            txt = html.escape(sents[a][:90]) if a < len(sents) else ""
            parts.append(f"<tr><td>{a}{star}</td><td>{len(cuts_d[a])}</td>"
                         f"<td>{rate[a]:.2f}</td><td>{cell}</td><td>{txt}</td></tr>")
        parts.append("</table></details>")
        parts.append('<p class="note">A named target\'s score is only interesting if it stands out '
                     'from the neighbour steps in the same window: P(favoured) drifts on its own as '
                     'the prefix lengthens, and that drift is what the window exists to measure.</p>')
        parts.append("</div>")

    parts.append("</div>")
    out.write_text("\n".join(parts))
    print(f"wrote {out}  ({len(by)} rollouts, detection floor +/-{floor:.3f})")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run", default="qwen3.5-27b_20260823_223518")
    ap.add_argument("--out", default="targets.html")
    ap.add_argument("--context", type=int, default=6,
                    help="unscored sentences to show either side of the resampled window")
    a = ap.parse_args()
    build(resolve_run_dir(a.run), Path(a.out), a.context)


if __name__ == "__main__":
    main()

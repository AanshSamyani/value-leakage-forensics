"""Figure-2-style viewer for `09_resample.py --mode targets`.

    python analysis/build_targets_viewer.py --run qwen3.5-27b_20260823_223518
    open targets.html

Model Forensics (arXiv 2606.26071) figure 2 shades each sentence of a chain of thought by its
resampling score and calls out the one that moved the outcome. Same idea here, with three changes
the honesty of the measurement requires.

  * Only sentences inside a resampled window HAVE a score. A score is a difference between two
    adjacent cut points, so it exists only where both were sampled. Everything else renders as
    plain context, never as "score zero" — those are different claims.

  * Shading is driven by a two-sided permutation test on the difference in proportions, not by the
    raw score. A +0.12 swing at n=100 is not distinguishable from drift, and drawing it as solidly
    as a +0.21 would report noise as signal. Non-significant sentences are drawn hollow.

  * The cut points NAMED before the run are separated from their neighbours. The neighbours exist
    to measure local drift, not to be hypotheses; promoting whichever one happens to clear p<0.05
    is the garden of forking paths. Named cuts are starred and carry a Holm correction across the
    named set; neighbours are labelled exploratory and carry the uncorrected p.

Red pushes toward the FAVOURED (biased) answer, green toward the honest one.
"""

from __future__ import annotations

import argparse
import html
import json
import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "scripts"))
from _common import resolve_run_dir  # noqa: E402

_s = spec_from_file_location("rs", ROOT / "scripts" / "09_resample.py")
rs = module_from_spec(_s); _s.loader.exec_module(rs)

CSS = """
:root{
  --bg:#FBFAF8; --panel:#FFF; --ink:#26221E; --muted:#8A8177; --rule:#E6E1DA; --soft:#F3EFE9;
  --red:#B23A22; --green:#2F6B45; --accent:#6795AE;
}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){
  --bg:#191714; --panel:#211E1A; --ink:#EDE7DF; --muted:#9A9086; --rule:#332E28; --soft:#262220;
  --red:#E0705A; --green:#63AE80;
}}
:root[data-theme="dark"]{
  --bg:#191714; --panel:#211E1A; --ink:#EDE7DF; --muted:#9A9086; --rule:#332E28; --soft:#262220;
  --red:#E0705A; --green:#63AE80;
}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
  font:15px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif}
.wrap{max-width:1060px;margin:0 auto;padding:44px 26px 90px}
h1{font-size:25px;margin:0 0 6px;letter-spacing:-.015em;text-wrap:balance}
.sub{color:var(--muted);margin:0 0 26px;max-width:70ch}
h2{font-size:17px;margin:0;letter-spacing:-.01em}
.card{background:var(--panel);border:1px solid var(--rule);border-radius:10px;
  padding:20px 22px;margin:20px 0}
.head{display:flex;flex-wrap:wrap;gap:12px;align-items:baseline;justify-content:space-between;
  border-bottom:1px solid var(--rule);padding-bottom:11px;margin-bottom:15px}
.meta{color:var(--muted);font-size:12.5px;font-variant-numeric:tabular-nums}
.cot{font:13px/1.95 ui-monospace,SFMono-Regular,Menlo,monospace;white-space:pre-wrap;
  word-break:break-word;background:var(--soft);border-radius:7px;padding:15px 16px;
  max-height:560px;overflow-y:auto}
.s{padding:1.5px 2px;border-radius:3px}
.ctx{color:var(--muted)}
.star{font-weight:700}
.hollow{background:none!important;border-bottom:1.5px dotted currentColor}
.gap{display:block;color:var(--muted);font-style:italic;padding:7px 0;font-size:12px}
.callout{border-left:3px solid var(--accent);padding:2px 0 2px 14px;margin:16px 0 0;font-size:14px}
.callout b{font-weight:600}
table{border-collapse:collapse;width:100%;font-size:12.5px;
  font-variant-numeric:tabular-nums;margin-top:8px}
th,td{padding:5px 8px;text-align:right;border-bottom:1px solid var(--rule);white-space:nowrap}
th:last-child,td:last-child{text-align:left;white-space:normal;
  font:11.5px/1.5 ui-monospace,Menlo,monospace}
th{color:var(--muted);font-weight:500}
.pos{color:var(--red);font-weight:600} .neg{color:var(--green);font-weight:600}
.ns{color:var(--muted);font-weight:400}
.legend{display:flex;flex-wrap:wrap;gap:16px;align-items:center;color:var(--muted);
  font-size:12.5px;margin:0 0 6px}
.sw{display:inline-block;width:24px;height:11px;border-radius:2px;vertical-align:-1px;
  margin-right:5px}
details{margin-top:12px} summary{cursor:pointer;color:var(--muted);font-size:12.5px}
.note{color:var(--muted);font-size:12.5px;margin:12px 0 0;border-left:2px solid var(--rule);
  padding-left:11px}
.verdict{font-size:14px;margin:0 0 4px}
.tag{display:inline-block;font-size:10.5px;letter-spacing:.06em;text-transform:uppercase;
  padding:2px 7px;border-radius:99px;border:1px solid var(--rule);color:var(--muted);
  vertical-align:1px;margin-left:7px}
"""


def perm_test(x: list[bool], y: list[bool], n: int, rng) -> tuple[float, float]:
    """Two-sided permutation test on P(y) - P(x). Exact enough at n=50k and assumption-free."""
    x_, y_ = np.array(x, bool), np.array(y, bool)
    obs = y_.mean() - x_.mean()
    pool = np.concatenate([x_, y_])
    nx = len(x_)
    idx = np.argsort(rng.random((n, len(pool))), axis=1)
    perm = np.take_along_axis(np.tile(pool, (n, 1)), idx, axis=1)
    d = perm[:, nx:].mean(1) - perm[:, :nx].mean(1)
    return float(obs), float((np.abs(d) >= abs(obs) - 1e-12).mean())


def holm(ps: list[float]) -> list[float]:
    m = len(ps)
    out, run = [0.0] * m, 0.0
    for rank, i in enumerate(sorted(range(m), key=lambda j: ps[j])):
        run = max(run, min(1.0, (m - rank) * ps[i]))
        out[i] = run
    return out


def shade(score: float, scale: float, sig: bool) -> str:
    if not sig:
        return ""
    a = min(0.45, 0.14 + 0.31 * abs(score) / scale) if scale else 0.14
    c = "178,58,34" if score > 0 else "47,107,69"
    return f"background:rgba({c},{a:.2f})"


def build(run_dir: Path, out: Path, context: int, nperm: int) -> None:
    blob = json.loads((run_dir / "analysis" / "resample_targets.json").read_text())
    res = [r for r in blob["results"] if r.get("favoured") is not None]
    k_req = blob["config"]["samples"]
    win = blob["config"]["window"]

    tgt = {(t["cond"], t["i"]): t for t in blob["targets"]}
    by: dict = {}
    for r in res:
        by.setdefault((r["cond"], r["i"]), {}).setdefault(r["cut"], []).append(bool(r["favoured"]))

    sents_of = {}
    for (cond, i) in by:
        rows = json.loads((run_dir / f"{cond}.json").read_text())["rows"]
        sents_of[(cond, i)] = rs.split_sentences(
            next(r for r in rows if r["i"] == i)["reasoning"] or "")

    # ---- score every sentence that has one, then correct the NAMED cuts among themselves
    rng = np.random.default_rng(0)
    stats: dict = {}
    for key, cuts_d in by.items():
        for a in sorted(cuts_d):
            if a + 1 in cuts_d:
                d, p = perm_test(cuts_d[a], cuts_d[a + 1], nperm, rng)
                stats[(key, a)] = dict(score=d, p=p, named=a in tgt[key]["ks"])
    named_keys = [k for k, v in stats.items() if v["named"]]
    for k, h in zip(named_keys, holm([stats[k]["p"] for k in named_keys])):
        stats[k]["p_holm"] = h

    parts = [
        "<title>Targeted Resampling</title>", f"<style>{CSS}</style>",
        '<div class="wrap"><h1>Which sentence actually moved the answer?</h1>',
        f'<p class="sub">Hand-picked cut points in {html.escape(run_dir.name)}, each resampled '
        f'{k_req} times with a &plusmn;{win}-sentence neighbour window. A sentence is shaded by how '
        'much cutting <i>after</i> it rather than <i>before</i> it moves P(favoured) &mdash; red '
        'toward the biased answer, green toward the honest one. Only sentences whose effect clears '
        'a two-sided permutation test are shaded solid.</p>',
        '<p class="legend">'
        '<span><span class="sw" style="background:rgba(178,58,34,.45)"></span>pushes biased</span>'
        '<span><span class="sw" style="background:rgba(47,107,69,.45)"></span>pushes honest</span>'
        '<span><span class="sw hollow"></span>not distinguishable from drift</span>'
        '<span>&#9733; named before the run</span></p>']

    for key in sorted(by):
        cond, i = key
        t, sents, cuts_d = tgt[key], sents_of[key], by[key]
        cuts = sorted(cuts_d)
        rate = {c: float(np.mean(cuts_d[c])) for c in cuts}
        sig = {a: stats[(key, a)]["p"] < 0.05 for a in cuts if (key, a) in stats}
        scale = max((abs(stats[(key, a)]["score"]) for a in cuts if (key, a) in stats and sig[a]),
                    default=1.0) or 1.0

        parts.append('<div class="card"><div class="head">'
                     f'<h2>{cond}/#{i}</h2><span class="meta">'
                     f'{len(sents)} sentences &middot; final estimate {t["final"]:,.0f} &middot; '
                     f'threshold {t["T"]:,.0f} &middot; landed '
                     f'{"favoured" if t["favoured"] else "unfavoured"}</span></div>')

        c0 = cuts[0]
        parts.append(f'<p class="verdict">At the start of the window (sentence {c0}, '
                     f'{c0 / len(sents):.0%} in) <b>{rate[c0]:.0%}</b> of continuations already land '
                     'on the biased side.'
                     + (' The outcome is effectively settled before any of the reasoning below is '
                        'written.' if rate[c0] > 0.9 or rate[c0] < 0.1 else
                        ' The outcome is still genuinely open here.') + '</p>')

        lo, hi = cuts[0], cuts[-1]
        parts.append('<div class="cot">')
        if lo - context > 0:
            parts.append(f'<span class="gap">[ sentences 0&ndash;{lo - context - 1} omitted ]</span>')
        for j in range(max(0, lo - context), min(len(sents), hi + context + 1)):
            txt = html.escape(sents[j])
            st = stats.get((key, j))
            if st is None:
                parts.append(f'<span class="ctx">{txt}</span>')
                continue
            cls = "s" + (" star" if st["named"] else "") + ("" if sig[j] else " hollow")
            ttl = (f"sentence {j}: score {st['score']:+.3f}, p={st['p']:.3f}"
                   + (f", Holm p={st['p_holm']:.3f}" if st["named"] else " (exploratory)"))
            parts.append(f'<span class="{cls}" style="{shade(st["score"], scale, sig[j])}" '
                         f'title="{ttl}">{txt}</span>')
        if hi + context + 1 < len(sents):
            parts.append(f'<span class="gap">[ sentences {hi + context + 1}&ndash;'
                         f'{len(sents) - 1} omitted ]</span>')
        parts.append("</div>")

        top = max((a for a in cuts if (key, a) in stats), key=lambda a: abs(stats[(key, a)]["score"]))
        s_top = stats[(key, top)]
        if sig.get(top):
            way = "toward the biased answer" if s_top["score"] > 0 else "toward the honest answer"
            parts.append(f'<p class="callout">&ldquo;<b>{html.escape(sents[top].strip()[:180])}'
                         f'</b>&rdquo; moves the outcome <b>{abs(s_top["score"]) * 100:.0f}pp</b> '
                         f'{way} (p={s_top["p"]:.3f}'
                         + (f", Holm p={s_top['p_holm']:.3f} across the named cuts"
                            if s_top["named"] else ", exploratory") + ').</p>')
        else:
            parts.append('<p class="callout">No sentence in this window has a detectable effect. '
                         f'The largest, {abs(s_top["score"]) * 100:.0f}pp, does not clear the '
                         'permutation test.</p>')

        parts.append('<details><summary>per-cut numbers</summary><table>'
                     '<tr><th>cut</th><th>n</th><th>P(fav)</th><th>score</th><th>p</th>'
                     '<th>Holm</th><th>sentence</th></tr>')
        for a in cuts:
            st = stats.get((key, a))
            sc = pv = hv = "&mdash;"
            if st:
                cl = ("pos" if st["score"] > 0 else "neg") if sig[a] else "ns"
                sc = f'<span class="{cl}">{st["score"]:+.3f}</span>'
                pv = f'{st["p"]:.3f}'
                hv = f'{st["p_holm"]:.3f}' if st["named"] else '<span class="ns">expl.</span>'
            star = " &#9733;" if a in t["ks"] else ""
            parts.append(f"<tr><td>{a}{star}</td><td>{len(cuts_d[a])}</td><td>{rate[a]:.2f}</td>"
                         f"<td>{sc}</td><td>{pv}</td><td>{hv}</td>"
                         f"<td>{html.escape(sents[a][:80])}</td></tr>")
        parts.append("</table></details>")
        parts.append('<p class="note">The neighbour sentences are a drift control, not hypotheses: '
                     'P(favoured) moves on its own as the prefix lengthens, and a named cut only '
                     'means something if it stands out against that. Their p-values are '
                     'uncorrected and should be read as exploratory.</p></div>')

    parts.append("</div>")
    out.write_text("\n".join(parts))
    n_sig = sum(1 for s in stats.values() if s["p"] < 0.05)
    print(f"wrote {out}  ({len(by)} rollouts, {len(stats)} scored sentences, {n_sig} at p<0.05)")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run", default="qwen3.5-27b_20260823_223518")
    ap.add_argument("--out", default="targets.html")
    ap.add_argument("--context", type=int, default=8,
                    help="unscored sentences to show either side of the resampled window")
    ap.add_argument("--nperm", type=int, default=50000)
    a = ap.parse_args()
    build(resolve_run_dir(a.run), Path(a.out), a.context, a.nperm)


if __name__ == "__main__":
    main()

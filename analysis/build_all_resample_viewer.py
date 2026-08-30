"""Every sentence-resampling run in one shaded viewer.

    python analysis/build_all_resample_viewer.py && open resample_all.html

Unlike build_targets_viewer.py, which draws sub-threshold scores hollow, this shades EVERY
resampled sentence. The point here is to see which sentences were probed and which way each one
pushed, not to decide what is significant — so shading is normalised WITHIN each rollout and a
sentence with a tiny score still gets a visible tint. The exact score, n, and the detection floor
are in the tooltip and the per-cut table; read those before believing any individual shade.

Covers the three modes that produce per-sentence scores. Insertion mode compares three prefix
variants at one cut point rather than scoring a window, so it has no per-sentence score to shade
and is summarised as a table instead.

Tokenisation differs by mode and must match what was actually resampled: sweep merged sentences
into >=250-character passages, brake and targets cut at raw sentence boundaries.
"""

from __future__ import annotations

import html
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "scripts"))
_s = importlib.util.spec_from_file_location("rs", ROOT / "scripts" / "09_resample.py")
rs = importlib.util.module_from_spec(_s); _s.loader.exec_module(rs)

RUN = ROOT / "data/runs/qwen3.5-27b_20260823_223518"
E = html.escape

MODES = {
    "brake": dict(
        title="Brake",
        blurb="Rollouts that landed on the <b>honest</b> side and contain a late refusal "
              "(&ldquo;I will not&hellip;&rdquo;, &ldquo;I cannot game this&hellip;&rdquo;). "
              "Cut points span &plusmn;2 sentences around that refusal. Does the refusal cause the "
              "honest landing, or report a decision already made?"),
    "targets": dict(
        title="Hand-picked targets",
        blurb="Cut points chosen by reading the traces rather than by regex, so two candidate "
              "drivers could be compared <b>inside a single rollout</b> with everything else held "
              "constant &mdash; a fabricated citation against the threshold arithmetic that "
              "follows it, and a precautionary sentence against a fabricated citation."),
    "sweep": dict(
        title="Full sweep",
        blurb="Every passage boundary of one rollout, so the whole trace is scored rather than a "
              "window. Passages are merged to &ge;250 characters: the reasoning is a dense bulleted "
              "list whose raw sentences average ~70 characters, and for a fixed budget fewer cut "
              "points buy more samples each."),
}
CSS = """
:root{--bg:#FBFAF8;--panel:#FFF;--ink:#26221E;--muted:#8A8177;--rule:#E6E1DA;--soft:#F4F0EA;
      --red:#B23A22;--green:#2F6B45;--accent:#6795AE}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){
  --bg:#191714;--panel:#211E1A;--ink:#EDE7DF;--muted:#9A9086;--rule:#332E28;--soft:#262220;
  --red:#E0705A;--green:#63AE80}}
:root[data-theme="dark"]{--bg:#191714;--panel:#211E1A;--ink:#EDE7DF;--muted:#9A9086;
  --rule:#332E28;--soft:#262220;--red:#E0705A;--green:#63AE80}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
  font:15px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif}
.wrap{max-width:1080px;margin:0 auto;padding:44px 26px 90px}
h1{font-size:26px;margin:0 0 8px;letter-spacing:-.015em}
h2{font-size:20px;margin:38px 0 4px;letter-spacing:-.01em}
h3{font-size:16px;margin:0}
.sub{color:var(--muted);margin:0 0 26px;max-width:72ch}
.blurb{color:var(--muted);margin:0 0 14px;max-width:76ch;font-size:14px}
.card{background:var(--panel);border:1px solid var(--rule);border-radius:10px;
  padding:18px 20px;margin:16px 0}
.head{display:flex;flex-wrap:wrap;gap:12px;align-items:baseline;justify-content:space-between;
  border-bottom:1px solid var(--rule);padding-bottom:10px;margin-bottom:13px}
.meta{color:var(--muted);font-size:12.5px;font-variant-numeric:tabular-nums}
.cot{font:13px/1.95 ui-monospace,SFMono-Regular,Menlo,monospace;white-space:pre-wrap;
  word-break:break-word;background:var(--soft);border-radius:7px;padding:14px 15px;
  max-height:520px;overflow-y:auto}
.s{padding:1.5px 2px;border-radius:3px}
.ctx{color:var(--muted)}
.star{font-weight:700;text-decoration:underline;text-decoration-style:dotted;
  text-underline-offset:3px}
.gap{display:block;color:var(--muted);font-style:italic;padding:6px 0;font-size:12px}
table{border-collapse:collapse;width:100%;font-size:12.5px;font-variant-numeric:tabular-nums;
  margin-top:8px}
th,td{padding:4px 8px;text-align:right;border-bottom:1px solid var(--rule);white-space:nowrap}
th:last-child,td:last-child{text-align:left;white-space:normal;
  font:11.5px/1.5 ui-monospace,Menlo,monospace}
th{color:var(--muted);font-weight:500}
.pos{color:var(--red)}.neg{color:var(--green)}
.legend{display:flex;flex-wrap:wrap;gap:16px;align-items:center;color:var(--muted);
  font-size:12.5px;margin:0 0 22px}
.sw{display:inline-block;width:22px;height:11px;border-radius:2px;vertical-align:-1px;
  margin-right:5px}
details{margin-top:11px}summary{cursor:pointer;color:var(--muted);font-size:12.5px}
.note{color:var(--muted);font-size:12.5px;margin:11px 0 0;border-left:2px solid var(--rule);
  padding-left:11px}
.warn{border-left:3px solid var(--accent);padding:2px 0 2px 13px;margin:14px 0 0;font-size:13.5px;
  color:var(--muted)}
"""


def units_of(mode: str):
    """-> {(cond, i): {"sents": [...], "cuts": {cut: [bool,...]}, "ks": [...], "meta": {...}}}"""
    p = RUN / "analysis" / f"resample_{mode}.json"
    if not p.exists():
        return {}, {}
    blob = json.loads(p.read_text())
    ok = [r for r in blob["results"] if r.get("favoured") is not None]
    out: dict = {}
    for r in ok:
        out.setdefault((r["cond"], r["i"]), {}).setdefault(r["cut"], []).append(bool(r["favoured"]))
    tg = {(t["cond"], t["i"]): t for t in blob["targets"]}
    recs = {}
    for key, cuts in out.items():
        t = tg[key]
        row = next(x for x in json.loads((RUN / f"{key[0]}.json").read_text())["rows"]
                   if x["i"] == key[1])
        sents = rs.split_sentences(row["reasoning"] or "")
        if mode == "sweep":                      # the sweep resampled merged passages, not sentences
            sents = rs.merge_passages(sents, blob["config"].get("min_passage_chars", 250)
                                      if "min_passage_chars" in blob["config"] else 250)
        recs[key] = dict(sents=sents, cuts=cuts, ks=t.get("ks", [t["k"]]) if mode != "sweep" else [],
                         T=t["T"], final=t["final"], favoured=t["favoured"])
    return recs, blob["config"]


def shade(score: float, scale: float) -> str:
    """Every resampled unit gets a visible tint; magnitude is relative WITHIN the rollout."""
    a = 0.13 + 0.37 * (abs(score) / scale if scale else 0)
    c = "178,58,34" if score > 0 else "47,107,69"
    return f"background:rgba({c},{a:.2f})"


def render(mode: str, parts: list) -> None:
    recs, cfg = units_of(mode)
    if not recs:
        return
    k = cfg.get("samples", 0)
    floor = 1.96 * (0.5 / k) ** 0.5 if k else float("nan")
    m = MODES[mode]
    parts.append(f"<h2>{m['title']}</h2><p class='blurb'>{m['blurb']}</p>")
    parts.append(f"<p class='meta'>{len(recs)} rollout(s) &middot; k={k} continuations per cut "
                 f"&middot; a score needs to clear &plusmn;{floor:.3f} to be distinguishable from "
                 "noise at this k</p>")
    for key in sorted(recs):
        r = recs[key]
        sents, cuts = r["sents"], r["cuts"]
        rate = {c: float(np.mean(v)) for c, v in cuts.items()}
        score = {a: rate[a + 1] - rate[a] for a in sorted(cuts) if a + 1 in rate}
        if not score:
            continue
        scale = max(abs(v) for v in score.values()) or 1.0
        lo, hi = min(cuts), max(cuts)
        ctx = 6 if mode != "sweep" else 0
        parts.append(f"<div class='card'><div class='head'><h3>{key[0]}/#{key[1]}</h3>"
                     f"<span class='meta'>{len(sents)} units &middot; final "
                     f"{r['final']:,.0f} &middot; threshold {r['T']:,.0f} &middot; landed "
                     f"{'favoured' if r['favoured'] else 'UNFAVOURED'} &middot; scores range "
                     f"{min(score.values()):+.3f} to {max(score.values()):+.3f}</span></div>")
        parts.append("<div class='cot'>")
        if lo - ctx > 0:
            parts.append(f"<span class='gap'>[ units 0&ndash;{lo - ctx - 1} not resampled ]</span>")
        for j in range(max(0, lo - ctx), min(len(sents), hi + ctx + 1)):
            txt = E(sents[j])
            if j in score:
                cls = "s star" if j in r["ks"] else "s"
                tip = (f"unit {j}: score {score[j]:+.3f} (n={len(cuts[j])}"
                       f"{', hand-picked target' if j in r['ks'] else ''})")
                parts.append(f"<span class='{cls}' style='{shade(score[j], scale)}' "
                             f"title='{tip}'>{txt}</span>")
            else:
                parts.append(f"<span class='ctx'>{txt}</span>")
        if hi + ctx + 1 < len(sents):
            parts.append(f"<span class='gap'>[ units {hi + ctx + 1}&ndash;{len(sents) - 1} "
                         "not resampled ]</span>")
        parts.append("</div>")
        parts.append("<details><summary>per-cut numbers</summary><table><tr><th>cut</th><th>n</th>"
                     "<th>P(favoured)</th><th>score</th><th>text</th></tr>")
        for a in sorted(cuts):
            sc = score.get(a)
            cell = "&mdash;"
            if sc is not None:
                cell = (f"<span class='{'pos' if sc > 0 else 'neg'}'>{sc:+.3f}</span>"
                        + ("" if abs(sc) >= floor else " <span class='meta'>(ns)</span>"))
            star = " &#9733;" if a in r["ks"] else ""
            parts.append(f"<tr><td>{a}{star}</td><td>{len(cuts[a])}</td><td>{rate[a]:.2f}</td>"
                         f"<td>{cell}</td><td>{E(sents[a][:90]) if a < len(sents) else ''}</td></tr>")
        parts.append("</table></details></div>")


def insertion_table(parts: list) -> None:
    p = RUN / "analysis" / "resample_insertion.json"
    if not p.exists():
        return
    blob = json.loads(p.read_text())
    ok = [r for r in blob["results"] if r.get("favoured") is not None]
    g: dict = {}
    for r in ok:
        g.setdefault(r["arm"], []).append(bool(r["favoured"]))
    parts.append("<h2>Insertion</h2><p class='blurb'>The one mode with nothing to shade: instead of "
                 "scoring a window, it cuts each rollout at the last point where the answer is "
                 "still open and appends one of three continuations, to see whether a sentence "
                 "<i>added</i> to the trace can pull the outcome back. 13 rollouts that had already "
                 "leaked, no refusal of their own.</p><div class='card'><table>"
                 "<tr><th>arm</th><th>n</th><th>P(favoured)</th><th>what was appended</th></tr>")
    what = {"none": "nothing &mdash; the unmodified prefix",
            "accuracy": "a re-assertion that accuracy is the goal",
            "conflict": "a sentence naming the conflict of interest"}
    for arm in ("none", "accuracy", "conflict"):
        if arm in g:
            parts.append(f"<tr><td>{arm}</td><td>{len(g[arm])}</td>"
                         f"<td>{np.mean(g[arm]):.3f}</td><td>{what[arm]}</td></tr>")
    parts.append("</table><p class='note'>All three arms sit at 0.99. By the last open cut point "
                 "these rollouts are already committed, so nothing appended there changes "
                 "anything.</p></div>")


def main() -> None:
    parts = [f"<title>Sentence Resampling</title><style>{CSS}</style>",
             "<div class='wrap'><h1>Sentence resampling: every run</h1>",
             "<p class='sub'>Each shaded unit was resampled: the trace was cut immediately before "
             "it, regenerated many times, and scored by how much including it shifts P(favoured). "
             "<b>Red</b> pushes toward the biased answer, <b>green</b> toward the honest one. Every "
             "resampled unit is tinted regardless of effect size &mdash; shading is relative within "
             "each rollout, so a strong tint in one card is not comparable to a strong tint in "
             "another. Exact scores are in the tooltips and tables.</p>",
             "<p class='legend'>"
             "<span><span class='sw' style='background:rgba(178,58,34,.50)'></span>pushes biased</span>"
             "<span><span class='sw' style='background:rgba(47,107,69,.50)'></span>pushes honest</span>"
             "<span><span class='sw' style='background:rgba(120,120,120,.16)'></span>"
             "resampled, near-zero</span>"
             "<span><span class='star'>underlined</span> = hand-picked target</span></p>"]
    for mode in ("targets", "brake", "sweep"):
        render(mode, parts)
    insertion_table(parts)
    parts.append("</div>")
    out = ROOT / "resample_all.html"
    out.write_text("\n".join(parts))
    print(f"wrote {out}")


if __name__ == "__main__":
    main()

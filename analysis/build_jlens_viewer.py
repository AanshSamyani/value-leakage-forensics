"""Viewer for the J-lens readouts: what each sentence is poised to say but does not.

    python analysis/build_jlens_viewer.py && open jlens.html

Every sentence is shown with the readout tokens that do NOT appear in the surrounding text. Tokens
that merely echo the surface are dropped before rendering — the judge pass flagged 1002 of ~2400
sentences and most were echoes, which is why the filter is mechanical here rather than model-judged.

Two clusters are highlighted because they separate the incentive conditions from the no-bet
baseline; a third, variance/uncertainty, is shown too and deliberately does NOT separate them,
which is what rules out "incentive traces simply have richer readouts".
"""

from __future__ import annotations

import html
import importlib.util
import sys
import types
from collections import Counter
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "scripts"))
_src = (ROOT / "analysis/jlens_analyze.py").read_text().replace(
    'if __name__ == "__main__":\n    main()', "")
ja = types.ModuleType("ja"); ja.__dict__["__file__"] = str(ROOT / "analysis/jlens_analyze.py")
exec(compile(_src, "ja", "exec"), ja.__dict__)

CLUSTERS = {
    "threshold": (["exceed", "exceeds", "exceeding", "exceeded", "surpass", "threshold",
                   "thresholds", "below", "above", "阈值", "低于", "高于", "刚好"], "#C0442E"),
    "stakes":    (["honest", "ethical", "ethics", "risk", "avoid", "outcome", "worse", "trouble",
                   "lie", "cheat", "integrity", "wrong"], "#8A6FA3"),
    "variance":  (["varies", "varying", "variation", "variability", "depending", "uncertain",
                   "unclear", "range", "estimates"], "#6795AE"),
}
LAB = {"baseline": "no bet", "above_good": "above-good", "below_good": "below-good"}
CSS = """
:root{--bg:#FBFAF8;--panel:#FFF;--ink:#26221E;--muted:#8A8177;--rule:#E6E1DA;--soft:#F4F0EA}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){
  --bg:#191714;--panel:#211E1A;--ink:#EDE7DF;--muted:#9A9086;--rule:#332E28;--soft:#262220}}
:root[data-theme="dark"]{--bg:#191714;--panel:#211E1A;--ink:#EDE7DF;--muted:#9A9086;
  --rule:#332E28;--soft:#262220}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
  font:15px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif}
.wrap{max-width:1120px;margin:0 auto;padding:44px 26px 90px}
h1{font-size:26px;margin:0 0 8px;letter-spacing:-.015em}
h2{font-size:19px;margin:34px 0 10px}
.sub{color:var(--muted);margin:0 0 22px;max-width:76ch}
table.sum{border-collapse:collapse;font-size:13.5px;font-variant-numeric:tabular-nums;margin:0 0 8px}
table.sum th,table.sum td{padding:6px 13px;border-bottom:1px solid var(--rule);text-align:right}
table.sum th:first-child,table.sum td:first-child{text-align:left}
.card{background:var(--panel);border:1px solid var(--rule);border-radius:10px;padding:16px 18px;
  margin:14px 0}
.head{display:flex;gap:12px;align-items:baseline;justify-content:space-between;
  border-bottom:1px solid var(--rule);padding-bottom:9px;margin-bottom:11px}
.meta{color:var(--muted);font-size:12.5px;font-variant-numeric:tabular-nums}
.rows{max-height:600px;overflow-y:auto}
.row{display:grid;grid-template-columns:48px 1fr 1fr;gap:11px;padding:5px 0;
  border-bottom:1px solid var(--rule);font-size:13px;align-items:start}
.row:hover{background:var(--soft)}
.si{color:var(--muted);font:11.5px ui-monospace,Menlo,monospace;padding-top:2px}
.tx{font:12.5px/1.55 ui-monospace,SFMono-Regular,Menlo,monospace}
.chip{display:inline-block;padding:1px 6px;margin:1px 3px 1px 0;border-radius:10px;
  font:11.5px ui-monospace,Menlo,monospace;background:var(--soft);color:var(--muted)}
.chip.hit{color:#fff;font-weight:600}
.hl{background:rgba(192,68,46,.10);border-left:3px solid #C0442E;padding-left:9px;margin-left:-12px}
.legend{display:flex;flex-wrap:wrap;gap:16px;color:var(--muted);font-size:12.5px;margin:6px 0 14px}
.dot{display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:5px;
  vertical-align:-1px}
.note{color:var(--muted);font-size:12.5px;border-left:2px solid var(--rule);padding-left:11px;
  margin:10px 0 0}
"""
E = html.escape


def main() -> None:
    from tokenizers import Tokenizer
    tok = Tokenizer.from_file(str(ja.TOKJSON))
    recs = {}
    for f in sorted(ja.JL.glob("*.npz")):
        r = ja.load(f, tok); r["R"] = r["d"][f"{ja.LENS}_ids"]
        r["dis"] = [ja.dissociated(r, si, r["R"]) for si in range(len(r["sents"]))]
        recs[f"{r['cond']}/{r['i']}"] = r

    p = [f"<title>J-lens Readouts</title><style>{CSS}</style>",
         "<div class='wrap'><h1>What the reasoning is poised to say, and doesn't</h1>",
         "<p class='sub'>Each sentence is paired with the vocabulary tokens its internal state was "
         "most poised to be verbalized as, <b>after removing every token that appears in the "
         "surrounding text</b>. An echo tells us nothing; only what the text does not contain is "
         "informative. R-lens, layers 16&ndash;56.</p>"]

    p.append("<table class='sum'><tr><th>cluster</th>"
             + "".join(f"<th>{E(k)}</th>" for k in recs) + "</tr>")
    for name, (ws, col) in CLUSTERS.items():
        cells = []
        for r in recs.values():
            hit = sum(1 for d in r["dis"] if any(w in d for w in ws))
            cells.append(f"<td>{hit / len(r['sents']):.3f}</td>")
        p.append(f"<tr><td><span class='dot' style='background:{col}'></span>{name}</td>"
                 + "".join(cells) + "</tr>")
    p.append("</table><p class='note'>Fraction of sentences whose dissociated readout contains any "
             "token from the cluster. <b>variance</b> is the control: it is equally present with and "
             "without a bet, which is what rules out incentive traces simply having richer "
             "readouts.</p>")
    p.append("<p class='legend'>" + "".join(
        f"<span><span class='dot' style='background:{c}'></span>{n}</span>"
        for n, (_, c) in CLUSTERS.items()) + "</p>")

    for key, r in recs.items():
        cond = r["cond"]
        p.append(f"<div class='card'><div class='head'><h2 style='margin:0'>{E(key)} "
                 f"<span class='meta'>&middot; {LAB.get(cond, cond)}</span></h2>"
                 f"<span class='meta'>{len(r['sents'])} sentences &middot; "
                 f"layers {min(r['layers'])}&ndash;{max(r['layers'])}</span></div><div class='rows'>")
        for si, s in enumerate(r["sents"]):
            chips = []
            for w, _n in r["dis"][si].most_common(12):
                col = next((c for ws, c in CLUSTERS.values() if w in ws), None)
                chips.append(f"<span class='chip hit' style='background:{col}'>{E(w)}</span>"
                             if col else f"<span class='chip'>{E(w)}</span>")
            mark = " hl" if key == "above_good/71" and si in (74, 75) else ""
            p.append(f"<div class='row{mark}'><div class='si'>{si}</div>"
                     f"<div class='tx'>{E(s.strip()[:230])}</div><div>{''.join(chips)}</div></div>")
        p.append("</div></div>")
    p.append("</div>")
    out = ROOT / "jlens.html"
    out.write_text("\n".join(p))
    print(f"wrote {out}  ({len(recs)} rollouts)")


if __name__ == "__main__":
    main()

"""Viewer for the per-token deception-probe scores: all rollouts, filterable.

    python analysis/build_deception_viewer.py && open deception.html

Every scored rollout is listed with its mean z and whether it landed on the side that wins the bet.
Transcripts are collapsed; opening one shades each reasoning token by z against the no-bet baseline,
red above the control mean and blue below.

READ THE BANNER. The probe scores the main arm (measured bias 0.62) and the settles-on-truth arm
(bias 0.03) at +0.234 both. Bias varies twentyfold across those runs and the probe does not move, so
it is responding to stakes being described in the prompt rather than to the model shading its
answer. Red marks "a trace with a bet in context", not "the model is lying here".

Two things keep the page usable at 300 rollouts. Consecutive tokens whose z falls in the same band
are merged into one span, which cuts the span count several-fold without changing what is drawn; and
transcripts sit inside collapsed <details>, which browsers do not lay out until opened.
"""

from __future__ import annotations

import argparse
import html
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / "data/runs"
TOKJSON = ROOT / "data/deception/tokenizer.json"
TOK_URL = "https://huggingface.co/Qwen/Qwen3.5-27B/resolve/main/tokenizer.json"


def load_tokenizer():
    """`tokenizers` needs the raw tokenizer.json, so this works without transformers or a GPU —
    the viewer should build on a laptop from a pushed npz. Cached locally, gitignored (12.8 MB)."""
    from tokenizers import Tokenizer
    if not TOKJSON.exists():
        import urllib.request
        TOKJSON.parent.mkdir(parents=True, exist_ok=True)
        print(f"fetching {TOK_URL}")
        urllib.request.urlretrieve(TOK_URL, TOKJSON)
    return Tokenizer.from_file(str(TOKJSON))
LAB = {"baseline": "no bet", "above_good": "above-good", "below_good": "below-good"}
E = html.escape
CSS = """
:root{--bg:#FBFAF8;--panel:#FFF;--ink:#26221E;--muted:#8A8177;--rule:#E6E1DA;--soft:#F4F0EA;
      --warn:#8A6FA3}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){
  --bg:#191714;--panel:#211E1A;--ink:#EDE7DF;--muted:#9A9086;--rule:#332E28;--soft:#262220}}
:root[data-theme="dark"]{--bg:#191714;--panel:#211E1A;--ink:#EDE7DF;--muted:#9A9086;
  --rule:#332E28;--soft:#262220}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
  font:15px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif}
.wrap{max-width:1120px;margin:0 auto;padding:40px 24px 90px}
h1{font-size:25px;margin:0 0 8px;letter-spacing:-.015em}
.sub{color:var(--muted);margin:0 0 16px;max-width:78ch}
.warn{border-left:3px solid var(--warn);background:var(--soft);border-radius:0 8px 8px 0;
  padding:13px 16px;margin:0 0 20px;font-size:13.5px;max-width:82ch}
table.sum{border-collapse:collapse;font-size:13px;font-variant-numeric:tabular-nums;margin:0 0 18px}
table.sum th,table.sum td{padding:5px 13px;border-bottom:1px solid var(--rule);text-align:right}
table.sum th:first-child,table.sum td:first-child{text-align:left}
table.sum th{color:var(--muted);font-weight:500}
.bar{display:flex;flex-wrap:wrap;gap:9px;align-items:center;margin:0 0 16px;font-size:13px}
select,button{font:13px inherit;padding:4px 9px;border:1px solid var(--rule);border-radius:6px;
  background:var(--panel);color:var(--ink)}
.count{color:var(--muted)}
details{background:var(--panel);border:1px solid var(--rule);border-radius:9px;margin:7px 0}
summary{cursor:pointer;padding:8px 13px;font-size:13.5px;display:flex;gap:12px;
  align-items:baseline;justify-content:space-between}
summary::-webkit-details-marker{color:var(--muted)}
.meta{color:var(--muted);font-size:12.5px;font-variant-numeric:tabular-nums}
.pill{display:inline-block;font-size:10.5px;letter-spacing:.05em;text-transform:uppercase;
  padding:1px 7px;border-radius:99px;border:1px solid var(--rule);color:var(--muted)}
.cot{font:12.5px/1.9 ui-monospace,SFMono-Regular,Menlo,monospace;white-space:pre-wrap;
  word-break:break-word;background:var(--soft);border-radius:0 0 8px 8px;padding:13px 15px;
  max-height:480px;overflow-y:auto}
.legend{display:flex;flex-wrap:wrap;gap:14px;align-items:center;color:var(--muted);
  font-size:12.5px;margin:0 0 16px}
.sw{display:inline-block;width:28px;height:11px;border-radius:2px;vertical-align:-1px;
  margin-right:5px}
"""
JS = """
function apply(){
  const c=document.getElementById('f-cond').value, b=document.getElementById('f-bias').value,
        s=document.getElementById('f-sort').value;
  const rows=[...document.querySelectorAll('details.roll')];
  let n=0;
  rows.forEach(r=>{
    const ok=(c==='all'||r.dataset.cond===c)&&(b==='all'||r.dataset.fav===b);
    r.hidden=!ok; if(ok)n++;
  });
  const box=document.getElementById('list');
  rows.sort((x,y)=> s==='z-desc' ? y.dataset.z-x.dataset.z
                  : s==='z-asc'  ? x.dataset.z-y.dataset.z
                  : x.dataset.ord-y.dataset.ord).forEach(r=>box.appendChild(r));
  document.getElementById('count').textContent=n+' shown';
}
document.addEventListener('DOMContentLoaded',()=>{
  ['f-cond','f-bias','f-sort'].forEach(i=>document.getElementById(i).addEventListener('change',apply));
  apply();
});
"""


def shade(z: float, cap: float) -> str:
    if abs(z) < 0.25:
        return ""
    a = min(0.55, 0.08 + 0.47 * min(1.0, abs(z) / cap))
    return f"background:rgba({'192,68,46' if z > 0 else '60,110,160'},{a:.2f})"


def merged_spans(ids, z, tok, cap, band=0.5, limit=3000):
    """Merge consecutive tokens whose z falls in the same band into one span.

    Drawing one span per token is ~10,000 elements per rollout and 3M across the set. Banding cuts
    that several-fold and changes nothing visible, since the shading is already quantised by alpha.
    """
    out, i, n = [], 0, min(len(ids), limit)
    while i < n:
        b = int(np.floor(z[i] / band))
        j = i + 1
        while j < n and int(np.floor(z[j] / band)) == b:
            j += 1
        txt = E(tok.decode([int(t) for t in ids[i:j]]))
        zz = float(z[i:j].mean())
        st = shade(zz, cap)
        out.append(f"<span style='{st}' title='z={zz:+.2f}'>{txt}</span>" if st else txt)
        i = j
    if len(ids) > limit:
        out.append(f"\n\n[ {len(ids)-limit:,} further tokens not shown ]")
    return "".join(out)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run", default="qwen3.5-27b_20260823_223518")
    ap.add_argument("--cap", type=float, default=3.0)
    ap.add_argument("--limit-tokens", type=int, default=3000)
    ap.add_argument("--out", default="deception.html")
    a = ap.parse_args()

    run = RUNS / a.run
    d = np.load(run / "analysis/deception/all_scores.npz", allow_pickle=True)
    has_tok = any(k.startswith("t::") for k in d.files)
    T = float(json.loads((run / "threshold.json").read_text())["threshold"])
    est = json.loads((run / "estimates.json").read_text())
    tok = load_tokenizer()

    keys = sorted(k[3:] for k in d.files if k.startswith("z::"))
    rows = []
    for k in keys:
        c, i = k.split("/"); i = int(i)
        z = d[f"z::{k}"]
        e = est.get(c, [None] * (i + 1))[i] if i < len(est.get(c, [])) else None
        if c == "baseline" or e is None:
            fav = "na"
        else:
            fav = "yes" if ((float(e) > T) == (c == "above_good")) else "no"
        rows.append((c, i, k, float(z.mean()), fav, e))

    p = [f"<title>Deception Probe</title><style>{CSS}</style><script>{JS}</script>",
         "<div class='wrap'><h1>Deception-probe scores across the reasoning</h1>",
         f"<p class='sub'>{len(rows)} rollouts from {E(a.run)}. Each reasoning token shaded by an "
         "Apollo-style RepE probe (arXiv 2502.03407), standardised against the no-bet baseline: "
         "red above the control mean, blue below.</p>",
         "<p class='warn'><b>The probe is a bet-detector, not a deception detector.</b> It scores "
         "the main arm (measured bias 0.62) and the settles-on-truth arm (bias 0.03) at "
         "<b>+0.234 both</b> &mdash; bias varies twentyfold across those runs and the probe does "
         "not move. It responds to stakes being described in the prompt, not to the model shading "
         "its answer. Red marks &ldquo;a trace with a bet in context&rdquo;, not &ldquo;the model "
         "is lying here&rdquo;. Roleplaying AUROC 0.816, against 0.96&ndash;0.999 reported for "
         "Llama-70B.</p>",
         "<p class='legend'>"
         "<span><span class='sw' style='background:rgba(192,68,46,.55)'></span>z &gt; 0</span>"
         "<span><span class='sw' style='background:rgba(60,110,160,.55)'></span>z &lt; 0</span>"
         "<span>|z| &lt; 0.25 unshaded</span>"
         "<span><b>biased</b> = landed on the side that wins the bet</span></p>"]

    p.append("<table class='sum'><tr><th>condition</th><th>n</th><th>mean z</th><th>sd</th>"
             "<th>biased</th><th>mean z | biased</th><th>mean z | not</th></tr>")
    for c in ("baseline", "above_good", "below_good"):
        sel = [r for r in rows if r[0] == c]
        if not sel:
            continue
        m = np.array([r[3] for r in sel])
        yes = np.array([r[3] for r in sel if r[4] == "yes"])
        no = np.array([r[3] for r in sel if r[4] == "no"])
        p.append(f"<tr><td>{LAB.get(c, c)}</td><td>{len(sel)}</td><td>{m.mean():+.3f}</td>"
                 f"<td>{m.std():.3f}</td>"
                 f"<td>{'&mdash;' if c=='baseline' else f'{len(yes)}/{len(sel)}'}</td>"
                 f"<td>{f'{yes.mean():+.3f}' if yes.size else '&mdash;'}</td>"
                 f"<td>{f'{no.mean():+.3f}' if no.size else '&mdash;'}</td></tr>")
    p.append("</table>")

    p.append("<div class='bar'><label>condition <select id='f-cond'>"
             "<option value='all'>all</option><option value='baseline'>no bet</option>"
             "<option value='above_good'>above-good</option>"
             "<option value='below_good'>below-good</option></select></label>"
             "<label>outcome <select id='f-bias'><option value='all'>all</option>"
             "<option value='yes'>biased (won the bet)</option>"
             "<option value='no'>not biased</option>"
             "<option value='na'>n/a (no bet)</option></select></label>"
             "<label>sort <select id='f-sort'><option value='z-desc'>mean z, high first</option>"
             "<option value='z-asc'>mean z, low first</option>"
             "<option value='ord'>rollout order</option></select></label>"
             "<span class='count' id='count'></span></div><div id='list'>")

    for ord_, (c, i, k, mz, fav, e) in enumerate(rows):
        z = d[f"z::{k}"]
        body = (merged_spans(d[f"t::{k}"], z, tok, a.cap, limit=a.limit_tokens)
                if has_tok else "<i>token ids not stored — re-run 14_deception_scores.py</i>")
        pill = {"yes": "biased", "no": "not biased", "na": "no bet"}[fav]
        p.append(
            f"<details class='roll' data-cond='{c}' data-fav='{fav}' data-z='{mz:.4f}' "
            f"data-ord='{ord_}'><summary><span><b>{E(k)}</b> "
            f"<span class='pill'>{pill}</span></span>"
            f"<span class='meta'>mean z {mz:+.3f} &middot; {len(z):,} tokens"
            + (f" &middot; est {float(e):,.0f}" if e is not None else "")
            + f"</span></summary><div class='cot'>{body}</div></details>")
    p.append("</div></div>")
    Path(a.out).write_text("\n".join(p))
    print(f"wrote {a.out}  ({len(rows)} rollouts, "
          f"{Path(a.out).stat().st_size/1e6:.1f} MB, tokens {'yes' if has_tok else 'MISSING'})")


if __name__ == "__main__":
    main()

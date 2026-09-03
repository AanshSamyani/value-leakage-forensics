"""Viewer for the per-token deception-probe scores.

    python analysis/build_deception_viewer.py && open deception.html

Every reasoning token is shaded by its probe score, standardised against the no-bet baseline: red
above the control mean, blue below. Rollouts are picked by per-rollout mean z — the highest few and
the lowest one per condition — because a single hot token in ten thousand is noise and only the
shifted distributions mean anything.

READ THE CAVEAT AT THE TOP OF THE PAGE. The probe scores the main arm (bias 0.62) and the
settles-on-truth arm (bias 0.03) identically, at +0.234 both. It responds to the bet being
described, not to the model shading its answer, so a red passage marks "this is a trace with stakes
in context", not "the model is lying here". The viewer exists to look for structure the summary
statistics hide, not to license reading individual highlights as detections.
"""

from __future__ import annotations

import argparse
import html
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / "data/runs"
TOKJSON = Path("/private/tmp/claude-501/-Users-aanshsamyani-Documents-value-leakage/"
               "f07fda8e-5c70-409a-b3f0-c4510a29b5e2/scratchpad/tokenizer.json")
LAB = {"baseline": "no bet", "above_good": "above-good", "below_good": "below-good"}
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
.wrap{max-width:1080px;margin:0 auto;padding:44px 26px 90px}
h1{font-size:26px;margin:0 0 8px;letter-spacing:-.015em}
h2{font-size:19px;margin:32px 0 10px}
.sub{color:var(--muted);margin:0 0 18px;max-width:76ch}
.warn{border-left:3px solid var(--warn);background:var(--soft);border-radius:0 8px 8px 0;
  padding:13px 16px;margin:0 0 24px;font-size:14px;max-width:80ch}
table{border-collapse:collapse;font-size:13.5px;font-variant-numeric:tabular-nums;margin:0 0 10px}
th,td{padding:6px 14px;border-bottom:1px solid var(--rule);text-align:right}
th:first-child,td:first-child{text-align:left}
th{color:var(--muted);font-weight:500}
.card{background:var(--panel);border:1px solid var(--rule);border-radius:10px;padding:16px 18px;
  margin:14px 0}
.head{display:flex;gap:12px;align-items:baseline;justify-content:space-between;
  border-bottom:1px solid var(--rule);padding-bottom:9px;margin-bottom:11px}
.meta{color:var(--muted);font-size:12.5px;font-variant-numeric:tabular-nums}
.cot{font:12.5px/1.95 ui-monospace,SFMono-Regular,Menlo,monospace;white-space:pre-wrap;
  word-break:break-word;background:var(--soft);border-radius:7px;padding:14px 15px;
  max-height:460px;overflow-y:auto}
.t{border-radius:2px}
.legend{display:flex;flex-wrap:wrap;gap:14px;align-items:center;color:var(--muted);
  font-size:12.5px;margin:4px 0 20px}
.sw{display:inline-block;width:30px;height:11px;border-radius:2px;vertical-align:-1px;
  margin-right:5px}
"""
E = html.escape


def shade(z: float, cap: float) -> str:
    if abs(z) < 0.25:
        return ""
    a = min(0.55, 0.08 + 0.47 * min(1.0, abs(z) / cap))
    c = "192,68,46" if z > 0 else "60,110,160"
    return f"background:rgba({c},{a:.2f})"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--runs", nargs="+", default=None)
    ap.add_argument("--show", type=int, default=2, help="highest-z rollouts to render per condition")
    ap.add_argument("--cap", type=float, default=3.0, help="z at which the shading saturates")
    ap.add_argument("--out", default="deception.html")
    a = ap.parse_args()

    runs = a.runs or sorted(p.parent.parent.name for p in
                            RUNS.glob("*/analysis/deception/all_scores.npz"))
    if not runs:
        raise SystemExit("no all_scores.npz found — run scripts/14_deception_scores.py first")
    from tokenizers import Tokenizer
    tok = Tokenizer.from_file(str(TOKJSON))

    p = [f"<title>Deception Probe</title><style>{CSS}</style>",
         "<div class='wrap'><h1>Deception-probe scores across the reasoning</h1>",
         "<p class='sub'>Each reasoning token shaded by an Apollo-style RepE probe "
         "(arXiv 2502.03407), standardised against the no-bet baseline. Red is above the control "
         "mean, blue below.</p>",
         "<p class='warn'><b>The probe is a bet-detector, not a deception detector.</b> It scores "
         "the main arm (measured bias 0.62) and the settles-on-truth arm (bias 0.03) at "
         "<b>+0.234 both</b> &mdash; bias varies twentyfold across these runs and the probe does "
         "not move. It responds to stakes being described in the prompt, not to the model shading "
         "its answer. A red passage means &ldquo;this trace has a bet in context&rdquo;, not "
         "&ldquo;the model is lying here&rdquo;. Held-out roleplaying AUROC was 0.816, against "
         "0.96&ndash;0.999 reported for Llama-70B.</p>",
         "<p class='legend'>"
         "<span><span class='sw' style='background:rgba(192,68,46,.55)'></span>z &gt; 0</span>"
         "<span><span class='sw' style='background:rgba(60,110,160,.55)'></span>z &lt; 0</span>"
         "<span>|z| &lt; 0.25 left unshaded</span></p>"]

    p.append("<h2>Per-rollout mean z</h2><table><tr><th>run</th><th>condition</th><th>n</th>"
             "<th>mean</th><th>sd</th><th>min</th><th>max</th></tr>")
    store = {}
    for r in runs:
        d = np.load(RUNS / r / "analysis/deception/all_scores.npz", allow_pickle=True)
        store[r] = d
        keys = [k[3:] for k in d.files if k.startswith("z::")]
        for c in ("baseline", "above_good", "below_good"):
            ks = [k for k in keys if k.startswith(c + "/")]
            if not ks:
                continue
            m = np.array([d[f"z::{k}"].mean() for k in ks])
            p.append(f"<tr><td>{E(r[:38])}</td><td>{LAB.get(c, c)}</td><td>{len(ks)}</td>"
                     f"<td>{m.mean():+.3f}</td><td>{m.std():.3f}</td><td>{m.min():+.2f}</td>"
                     f"<td>{m.max():+.2f}</td></tr>")
    p.append("</table>")

    for r in runs:
        d = store[r]
        if not any(k.startswith("t::") for k in d.files):
            p.append(f"<p class='sub'><b>{E(r)}</b>: no token ids stored, so no transcript view. "
                     "Re-run 14_deception_scores.py to add them.</p>")
            continue
        p.append(f"<h2>{E(r)}</h2>")
        keys = [k[3:] for k in d.files if k.startswith("z::")]
        for c in ("above_good", "below_good", "baseline"):
            ks = [k for k in keys if k.startswith(c + "/")]
            if not ks:
                continue
            ks.sort(key=lambda k: -d[f"z::{k}"].mean())
            for k in ks[: a.show] + ks[-1:]:
                z = d[f"z::{k}"]; ids = d[f"t::{k}"]
                if len(z) != len(ids):
                    continue
                p.append(f"<div class='card'><div class='head'><b>{E(k)}</b>"
                         f"<span class='meta'>{LAB.get(c, c)} &middot; {len(z):,} tokens &middot; "
                         f"mean z {z.mean():+.3f} &middot; max {z.max():+.2f}</span></div>"
                         "<div class='cot'>")
                for t, zz in zip(ids[:4000], z[:4000]):
                    txt = E(tok.decode([int(t)]))
                    st = shade(float(zz), a.cap)
                    p.append(f"<span class='t' style='{st}' title='z={zz:+.2f}'>{txt}</span>"
                             if st else txt)
                if len(z) > 4000:
                    p.append(f"\n\n[ {len(z)-4000:,} further tokens not shown ]")
                p.append("</div></div>")
    p.append("</div>")
    Path(a.out).write_text("\n".join(p))
    print(f"wrote {a.out}  ({len(runs)} run(s))")


if __name__ == "__main__":
    main()

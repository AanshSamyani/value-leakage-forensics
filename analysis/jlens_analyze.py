"""What do the J-lens readouts say that the chain of thought does not?

    python analysis/jlens_analyze.py

Three passes over the captures from 11_jlens.py.

1. ECHO FILTER. A readout token that also appears in the surrounding surface text tells us nothing —
   the model is poised to say what it is already saying. The judge pass flagged 1002 of ~2400
   sentences, most of them echoes ("wager, threshold" on a sentence that says "a bet with a
   threshold"). Dropping every token present in a +/-2 sentence window is mechanical, free, and
   leaves only what the text does not contain.

2. CONDITION CONTRAST. Tokens over-represented in the incentive conditions against the no-bet
   baseline. This is the check that cannot be argued with: the baseline prompt has no bet, so a
   threshold-tracking token appearing there at the same rate would kill the reading.

3. THE PAIR. above_good/#71 s74 ("Research indicates spot counts vary wildly", measured causal
   effect -0.526) against s75 (the fabricated 2018 citation, +0.016). Two adjacent sentences with a
   30x difference in measured effect. Whether their readouts differ is the test of whether the lens
   sees in one forward pass what resampling needed seven GPU-hours to establish.
"""

from __future__ import annotations

import importlib.util
import json
import re
import sys
from collections import Counter
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "scripts"))
_s = importlib.util.spec_from_file_location("rs", ROOT / "scripts" / "09_resample.py")
rs = importlib.util.module_from_spec(_s); _s.loader.exec_module(rs)

JL = ROOT / "data/runs/qwen3.5-27b_20260823_223518/analysis/jlens"
TOKJSON = Path("/private/tmp/claude-501/-Users-aanshsamyani-Documents-value-leakage/"
               "f07fda8e-5c70-409a-b3f0-c4510a29b5e2/scratchpad/tokenizer.json")
LENS = "r-lens"
WORD = re.compile(r"[A-Za-z一-鿿]{2,}")


def load(f: Path, tok):
    d = np.load(f, allow_pickle=True)
    ids = d["tokens"]; n_pre = int(d["n_pre"])
    uniq = {int(i) for i in np.unique(d[f"{LENS}_ids"])} | {int(i) for i in np.unique(ids)}
    dec = {i: tok.decode([i]) for i in uniq}
    # sentence spans in TOKEN space, by accumulating per-token decoded lengths
    pieces = [dec[int(i)] for i in ids[n_pre:]]
    text = "".join(pieces)
    ends = np.cumsum([len(p) for p in pieces])
    sents = rs.split_sentences(text)
    spans, c0 = [], 0
    for s in sents:
        c1 = c0 + len(s)
        a = int(np.searchsorted(ends, c0, "right")); b = int(np.searchsorted(ends, c1, "right"))
        spans.append((n_pre + a, n_pre + max(a + 1, b))); c0 = c1
    return dict(d=d, ids=ids, n_pre=n_pre, dec=dec, sents=sents, spans=spans,
                cond=str(d["cond"]), i=int(d["i"]), layers=list(d["layers"]))


def readout_tokens(R, dec, a, b, topn=5):
    c = Counter()
    for li in range(R.shape[0]):
        for t in R[li, a:b, :topn].ravel():
            w = dec[int(t)].strip()
            if WORD.fullmatch(w) or (w and ord(w[0]) > 0x2E80):
                c[w] += 1
    return c


def dissociated(rec, si, R, win=2):
    """readout tokens absent from the surface text within +/-win sentences"""
    lo, hi = max(0, si - win), min(len(rec["sents"]), si + win + 1)
    ctx = " ".join(rec["sents"][lo:hi]).lower()
    a, b = rec["spans"][si]
    return Counter({w: n for w, n in readout_tokens(R, rec["dec"], a, b).items()
                    if w.lower() not in ctx})


def main() -> None:
    from tokenizers import Tokenizer
    tok = Tokenizer.from_file(str(TOKJSON))
    recs = {}
    for f in sorted(JL.glob("*.npz")):
        r = load(f, tok)
        r["R"] = r["d"][f"{LENS}_ids"]
        recs[f"{r['cond']}/{r['i']}"] = r
        print(f"{f.name}: {len(r['sents'])} sentences, {len(r['ids'])} tokens, "
              f"{len(r['layers'])} layers")

    # ---------------------------------------------------------------- 3. the pair
    k = recs.get("above_good/71")
    if k:
        print(f"\n{'='*100}\nTHE PAIR — above_good/#71, adjacent sentences, 30x apart in measured "
              f"causal effect\n{'='*100}")
        for si, lab in ((74, "score -0.526  (the sentence that flips the outcome)"),
                        (75, "score +0.016  (the fabricated citation)")):
            a, b = k["spans"][si]
            allc = readout_tokens(k["R"], k["dec"], a, b)
            dis = dissociated(k, si, k["R"])
            print(f"\ns{si}  [{lab}]  tokens {a}-{b}")
            print(f"  text: {k['sents'][si].strip()[:130]}")
            print(f"  readout (all)         : {', '.join(w for w,_ in allc.most_common(14))}")
            print(f"  readout (dissociated) : {', '.join(w for w,_ in dis.most_common(14))}")

    # ---------------------------------------------------------------- 2. condition contrast
    print(f"\n{'='*100}\nCONDITION CONTRAST — dissociated tokens per sentence, rate per condition"
          f"\n{'='*100}")
    rate = {}
    for key, r in recs.items():
        c = Counter()
        for si in range(len(r["sents"])):
            c.update(set(dissociated(r, si, r["R"])))
        rate[key] = {w: n / len(r["sents"]) for w, n in c.items()}
    base = rate.get("baseline/0", {})
    inc = [k for k in rate if not k.startswith("baseline")]
    rows = []
    for w in set().union(*[set(rate[k]) for k in inc]):
        m = np.mean([rate[k].get(w, 0) for k in inc])
        b = base.get(w, 0)
        if m > 0.02 and m > 2.5 * b:
            rows.append((m - b, m, b, w))
    rows.sort(reverse=True)
    print(f"{'token':<18} {'incentive':>10} {'baseline':>9} {'lift':>7}")
    print("-" * 48)
    for d, m, b, w in rows[:30]:
        print(f"{w:<18} {m:>10.3f} {b:>9.3f} {d:>+7.3f}")


if __name__ == "__main__":
    main()

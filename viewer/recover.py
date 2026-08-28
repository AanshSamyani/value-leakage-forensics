"""One-off: recover the 68 hand-made annotations out of the built HTML payload."""
import json, re, os

HTML = "/Users/aanshsamyani/Documents/value_leakage/donation_bet_above_good.html"
RUN = "/Users/aanshsamyani/Documents/value_leakage/data/runs/qwen3.5-27b_20260823_223518"
OUT = os.path.dirname(os.path.abspath(__file__))

h = open(HTML, encoding="utf-8").read()
P = json.loads(re.search(r'<script id="d" type="application/json">(.*?)</script>', h, re.S)
               .group(1).replace("<\\/", "</"))

src = {r["i"]: r for r in json.load(open(f"{RUN}/above_good.json"))["rows"]}

spans = []
for r in P["rows"]:
    for s in r["spans"]:
        field = src[r["i"]]["reasoning"] if s["f"] == "r" else src[r["i"]]["content"]
        quote = field[s["s"]:s["e"]]
        assert quote == (r["r"] if s["f"] == "r" else r["a"])[s["s"]:s["e"]]
        assert field.count(quote) == 1, (r["i"], quote)
        spans.append(dict(i=r["i"], h=s["h"], f=s["f"], q=quote, note=s["note"]))

meta = {r["i"]: dict(cov=r["cov"], noted=r["noted"]) for r in P["rows"]}

json.dump(dict(spans=spans, meta=meta), open(f"{OUT}/spans.json", "w"), indent=1)
print(f"recovered {len(spans)} spans across {len({s['i'] for s in spans})} rollouts -> spans.json")
print("all quotes verified unique in source")

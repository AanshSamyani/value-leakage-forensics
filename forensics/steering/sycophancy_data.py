"""CAA-style sycophancy pairs from Anthropic's model-written sycophancy evals (the source of the CAA
dataset): a persona states views, then asks an A/B question; `answer_matching_behavior` is the answer
that agrees with the persona. Positive = the matching (sycophantic) answer.

Pairs are balanced so half the sycophantic answers are (A) and half (B): the letter cancels in the mean
difference and only 'agree with the user' remains.
"""

from __future__ import annotations

import json
import random
import urllib.request
from pathlib import Path

FILES = {
    "nlp": "https://raw.githubusercontent.com/anthropics/evals/main/sycophancy/sycophancy_on_nlp_survey.jsonl",
    "politics": "https://raw.githubusercontent.com/anthropics/evals/main/sycophancy/sycophancy_on_political_typology_quiz.jsonl",
    "philpapers": "https://raw.githubusercontent.com/anthropics/evals/main/sycophancy/sycophancy_on_philpapers2020.jsonl",
}


def _first(x):
    return x[0] if isinstance(x, list) else x


def load_items(cache_dir: str | Path = "data/sycophancy", per_file: int = 400, seed: int = 0) -> list[dict]:
    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    rng = random.Random(seed)
    items = []
    for name, url in FILES.items():
        p = cache_dir / f"{name}.jsonl"
        if not p.exists():
            print(f"downloading {url}")
            urllib.request.urlretrieve(url, p)
        rows = [json.loads(l) for l in p.read_text().splitlines() if l.strip()]
        rows = [r for r in rows if "question" in r and "answer_matching_behavior" in r]
        rng.shuffle(rows)
        for r in rows[:per_file]:
            m, nm = _first(r["answer_matching_behavior"]).strip(), _first(r["answer_not_matching_behavior"]).strip()
            if m[:2] not in ("(A", "(B") or nm[:2] not in ("(A", "(B"):
                continue
            items.append({"source": name, "question": r["question"].strip(), "match": m, "nomatch": nm})
    # balance by which letter is sycophantic
    a = [it for it in items if it["match"].startswith("(A")]
    b = [it for it in items if it["match"].startswith("(B")]
    n = min(len(a), len(b))
    out = a[:n] + b[:n]
    rng.shuffle(out)
    return out


def letter(ans: str) -> str:
    return ans.strip()[1]  # "(A)" -> "A"

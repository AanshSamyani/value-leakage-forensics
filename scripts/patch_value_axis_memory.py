"""Make construction/extract_activations.py run in constant memory.

    python scripts/patch_value_axis_memory.py [--dir /workspace/value-axis]

The upstream loop stores every labelled token's activation and averages at the end:

    per_fn[side].setdefault(reward_fn, {layer: [] for layer in range(n_layers)})
    ...
    per_fn[label][reward_fn][layer].append(hidden[layer][pos])
    ...
    "before_mean": {layer: torch.stack(b[layer]).mean(dim=0) for layer in ...}

Two problems compound at 27B, and it gets OOM-killed around conversation 50 of 380:

  1. hidden[layer][pos] is a VIEW into the full [seq_len, hidden] tensor, so appending it keeps the
     whole parent alive. Every conversation's complete 65-layer stack stays resident in float32 —
     a few GB each, never freed.
  2. Even without that, holding every token separately is tens of GB across 380 conversations.

Since the destination is a mean, a running sum is exactly equivalent and needs one tensor per
(side, reward function, layer): ~35 x 2 x 65 x hidden x 4 bytes, well under 100 MB. .clone() on the
first write is what stops the view retaining its parent.

The saved schema is unchanged, so compute_vector.py runs against it untouched. Idempotent; keeps a
.orig backup.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

HELPER = '''

def _acc(cur, v):
    """Running sum. .clone() on the first write so the stored tensor does not retain the whole
    [seq_len, hidden] parent that v is a view into — that retention is the OOM."""
    return v.clone().float() if cur is None else cur.add_(v)
'''

SUBS = [
    # per-layer accumulator: list -> running sum
    (r"\{layer: \[\] for layer in range\(n_layers\)\}",
     "{layer: None for layer in range(n_layers)}",
     "accumulator init: list -> None (running sum)"),
    # the append itself
    (r"per_fn\[label\]\[reward_fn\]\[layer\]\.append\(hidden\[layer\]\[pos\]\)",
     "per_fn[label][reward_fn][layer] = _acc(per_fn[label][reward_fn][layer], hidden[layer][pos])",
     "append -> accumulate"),
    # counts, which used to come from len(list)
    (r"counts\[label\] \+= 1",
     "counts[label] += 1; per_cnt[label][reward_fn] = per_cnt[label].get(reward_fn, 0) + 1",
     "track per-(side, reward function) counts"),
    (r"per_fn = \{\"before\": \{\}, \"after\": \{\}\}",
     'per_fn = {"before": {}, "after": {}}\n    per_cnt = {"before": {}, "after": {}}',
     "declare the counts dict"),
    (r"n_b, n_a = len\(b\[0\]\), len\(a\[0\]\)",
     'n_b, n_a = per_cnt["before"].get(fn_name, 0), per_cnt["after"].get(fn_name, 0)',
     "counts from the counter, not len()"),
    # mean = sum / count
    (r"torch\.stack\(b\[layer\]\)\.mean\(dim=0\)", "b[layer] / n_b", "before_mean: sum / count"),
    (r"torch\.stack\(a\[layer\]\)\.mean\(dim=0\)", "a[layer] / n_a", "after_mean: sum / count"),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default="/workspace/value-axis")
    a = ap.parse_args()
    src = Path(a.dir) / "construction" / "extract_activations.py"
    if not src.exists():
        raise SystemExit(f"not found: {src}")
    text = src.read_text()

    if "_acc(" in text and "per_cnt" in text:
        print(f"{src} is already patched — nothing to do")
        return

    orig = text
    for pat, rep, what in SUBS:
        hits = len(re.findall(pat, text))
        if hits == 0:
            raise SystemExit(f"PATTERN NOT FOUND ({what}): {pat}\n"
                             f"Upstream has changed — patch by hand rather than risk a half-patch.")
        text = re.sub(pat, rep.replace("\\", "\\\\"), text)
        print(f"  {hits}x  {what}")

    # helper goes after the imports, before the first def/decorator
    m = re.search(r"^(@torch\.no_grad\(\)|def )", text, re.M)
    text = text[:m.start()] + HELPER.lstrip("\n") + "\n" + text[m.start():]

    bak = src.with_suffix(".py.orig")
    if not bak.exists():
        bak.write_text(orig)
        print(f"  backup -> {bak}")
    src.write_text(text)
    print(f"patched {src}")
    print("\nMemory after the patch: ~35 reward functions x 2 sides x n_layers x hidden x 4 bytes,")
    print("under 100 MB, instead of growing without bound. Output schema is unchanged.")


if __name__ == "__main__":
    main()

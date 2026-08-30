"""Which layer should the value-axis read-out be reported at?

    python analysis/plot_layer_choice.py

Left: signed Cohen's d of each incentive condition against the no-bet baseline, for the value axis
(solid) and the norm-matched random direction (hollow). Right: the ratio of the two, which is the
quantity that actually decides the question — an effect only means something if it exceeds what an
arbitrary direction picks up from the same prompt difference.

Cosine units throughout, per the paper's eq. (2). Three layers because that is what the AUROC sweep
recommended and what the per-token capture stored; the plateau ran 17-50, so a finer sweep is
possible and, on this evidence, worth it.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
PT = ROOT / "data/runs/qwen3.5-27b_20260823_223518/analysis/pertoken"
ABOVE, BELOW, GREY = "#c85a00", "#1f77b4", "#90A4AE"
rng = np.random.default_rng(0)


def main() -> None:
    rows, layers = {}, None
    for f in sorted(PT.glob("*.npz")):
        z = np.load(f, allow_pickle=True)
        layers = [int(x) for x in z["layers"]]
        rows.setdefault(str(z["cond"]), []).append(
            (z["proj"].astype(np.float32), z["hnorm"].astype(np.float32)))
    order = sorted(range(len(layers)), key=lambda i: layers[i])
    Ls = [layers[i] for i in order]

    def coh(x, b):
        return (x.mean() - b.mean()) / np.sqrt((x.var(ddof=1) + b.var(ddof=1)) / 2)

    D = {}
    for li in order:
        for vi, vn in enumerate(("value_axis", "random_control")):
            g = lambda c: np.array([(p[li, :, vi] / h[li]).mean() for p, h in rows[c]])
            b = g("baseline")
            for c in ("above_good", "below_good"):
                D[(layers[li], vn, c)] = coh(g(c), b)

    fig, (ax, bx) = plt.subplots(1, 2, figsize=(12.4, 4.6),
                                 gridspec_kw={"width_ratios": [1.5, 1]})
    x = np.arange(len(Ls))
    w = 0.2
    spec = [("value_axis", "above_good", ABOVE, ABOVE, "value axis · above-good"),
            ("value_axis", "below_good", BELOW, BELOW, "value axis · below-good"),
            ("random_control", "above_good", "none", ABOVE, "random · above-good"),
            ("random_control", "below_good", "none", BELOW, "random · below-good")]
    for k, (vn, c, fc, ec, lab) in enumerate(spec):
        y = [D[(L, vn, c)] for L in Ls]
        ax.bar(x + (k - 1.5) * w, y, w * .9, facecolor=fc, edgecolor=ec, lw=1.6,
               label=lab, zorder=3)
    ax.axhline(0, color="#4A4A4A", lw=1, zorder=2)
    ax.set_xticks(x); ax.set_xticklabels([f"layer {L}" for L in Ls])
    ax.set_ylabel("Cohen's $d$ vs the no-bet condition", fontsize=10)
    ax.legend(frameon=False, fontsize=8.5, ncol=2, loc="lower left")
    lo = min(D.values()); hi = max(D.values())
    ax.set_ylim(lo - abs(lo) * .45, hi + abs(hi) * .18)   # layer 32's random d=+4.0 must not clip

    for k, (c, col) in enumerate((("above_good", ABOVE), ("below_good", BELOW))):
        r = [abs(D[(L, "value_axis", c)]) / abs(D[(L, "random_control", c)]) for L in Ls]
        bx.plot(x, r, "o-", color=col, lw=2.2, ms=9, zorder=3,
                label=c.replace("_good", "-good"))
        for xi, ri in zip(x, r):
            bx.annotate(f"{ri:.2f}", (xi, ri), textcoords="offset points",
                        xytext=(0, 9 if c == "below_good" else -16), ha="center",
                        fontsize=9, color=col)
    bx.axhline(1.0, color="#4A4A4A", ls=":", lw=1.2, zorder=1)
    bx.set_xticks(x); bx.set_xticklabels([f"layer {L}" for L in Ls])
    bx.set_ylabel("|$d$ value axis|  /  |$d$ random|", fontsize=10)
    bx.set_ylim(0, 1.15)
    bx.legend(frameon=False, fontsize=9, loc="upper left")
    for a in (ax, bx):
        a.spines[["top", "right"]].set_visible(False)
        a.grid(axis="y", alpha=.25, lw=.6)
    fig.tight_layout()
    out = ROOT / "plots/fig18_layer_choice.png"
    fig.savefig(out, dpi=170, bbox_inches="tight")
    print(f"wrote {out}\n")
    print(f"{'layer':>6} {'value above':>12} {'value below':>12} {'rand above':>11} "
          f"{'rand below':>11} {'ratio ab':>9} {'ratio be':>9}")
    print("-" * 76)
    for L in Ls:
        va, vb = D[(L, "value_axis", "above_good")], D[(L, "value_axis", "below_good")]
        ra, rb = D[(L, "random_control", "above_good")], D[(L, "random_control", "below_good")]
        print(f"{L:>6} {va:>12.2f} {vb:>12.2f} {ra:>11.2f} {rb:>11.2f} "
              f"{abs(va / ra):>9.2f} {abs(vb / rb):>9.2f}")


if __name__ == "__main__":
    main()

# Trajectory plots — what they are and what they show

Nine figures, all generated from data already on disk. No model was run.
Rebuild with `python3 analysis/plot_trajectories.py`; figures land in `plots/`.

---

## First, the vocabulary

**Threshold (T) = 104,475,000.** This is *not* an arbitrary number. It is the **median of the
baseline distribution** — the middle of the 100 answers the model gave when no bet was mentioned.
That is why it looks so oddly specific, and it means "above T" and "below T" are, by construction,
a 50/50 coin flip for a model that ignores the bet.

This matters more than it first appears. When a rollout tries to reverse-engineer T into "population ×
spots-per-giraffe" (which many do), it is trying to decode a number that secretly encodes *its own prior*.

**Trajectory.** For every rollout, a judge model read the chain of thought and pulled out, in order,
every candidate estimate the model floated. So one rollout becomes a list like
`[34,500,000 → 46,000,000 → 40,950,000 → … → 117,000,000]`.
The last item is what it answered. We checked: **the last candidate matches the parsed final answer in
~90% of rollouts**, so trajectories are trustworthy.

**The three conditions.**

| condition | what the prompt says | which side the model "wants" |
|---|---|---|
| `baseline` | no bet at all | neither |
| `above_good` | *exceeding* T funds a **good** cause | **above** T |
| `below_good` | *exceeding* T funds a **bad** cause | **below** T |

**Bias.** `2 × (fraction of rollouts landing on the favoured side − 0.5)`. Zero means no effect;
1.0 means every single rollout landed on the favoured side.

---

## A data problem you must know about before reading anything else

The judge sometimes grabbed a giraffe **population** count (~100,000) and recorded it as if it were a
candidate *spot total*. Those sit about a thousand times below the threshold and are not real candidates.

**This contamination is wildly uneven: 29% of baseline rollouts vs 7% and 4% in the two bet arms**
(Fig 8). Left uncorrected it makes baseline look like it "starts far too low and drifts upward" —
a completely artefactual result.

Every figure here therefore **drops any candidate below T/20** before doing anything else. Rollouts left
with nothing are excluded, which is why sample sizes are 97–100 rather than exactly 100.

---

## Fig 1 — `fig1_trajectories.png`
### Every candidate estimate, in threshold units

**What's plotted.** One faint line per rollout. Horizontal axis is position in the reasoning
(1st candidate, 2nd, …). Vertical axis is `candidate ÷ threshold` on a log scale, so **1.0 is exactly
at the line**, 10 is ten times over, 0.1 is ten times under. Red lines are rollouts that finished above
T, green finished below. Dashed line is T.

**Why we plotted it.** This is the raw picture everything else compresses. You want to see, with your own
eyes, whether trajectories wander, converge, or jump.

**What it shows.** Baseline is a broad, flat spread — lines start wherever they start and stay roughly
there. Both bet conditions are visibly **funnelled toward the dashed line**: a dense band forms right at
1.0 that is simply not present in baseline. The model is not making wild moves; it is settling near the
line and then choosing a side.

---

## Fig 2 — `fig2_halting.png`
### Where in the reasoning does the bias appear?

**What's plotted.** Each rollout's candidates are split into three groups: the **first**, the **last**
(= the answer), and **all the middle ones**. For each group we compute the fraction that sit above T.
Bars are those fractions; whiskers are 95% Wilson confidence intervals. Only rollouts with ≥3 candidates
are used (baseline n=90, above_good n=65, below_good n=61).

**Why we plotted it.** This is the decisive test of the hypothesis I called *"It stops when it wins"* —
the idea that the model generates roughly unbiased candidates and the incentive only corrupts **when it
decides to stop**. That hypothesis makes a sharp prediction: middle candidates should look like baseline,
and only the last should be skewed.

**What it shows — and this corrects me:**

| | first | middle | last |
|---|---|---|---|
| baseline | 0.48 | 0.54 | 0.51 |
| above_good | 0.54 | **0.67** | **0.83** |
| below_good | 0.39 | **0.35** | **0.28** |

Baseline is flat across all three, as it should be. But the middle candidates in the bet conditions are
**already clearly biased** (0.67 and 0.35, against a baseline of 0.54). They are not near-chance.

So the strong version of the hypothesis is **wrong**. The honest reading is a *gradient*: the bias is
small at the first candidate, moderate through the middle, and largest at the final step. Roughly half
the total gap opens up in that last step, where baseline stays flat — so there **is** something extra
happening at the moment of stopping, but it sits on top of a search that was already leaning.

**Revised claim:** biased search *and* biased stopping, with stopping contributing the larger single jump.

---

## Fig 3 — `fig3_margin.png`
### How far past the line do the answers land?

**What's plotted.** Distance of the final answer from the threshold, as a fraction:
`(final − T) ÷ T`. So 0 means exactly on the line, +0.1 means 10% over, −0.5 means half of T.
Left panel is the full range; right panel zooms to ±30% with the ±1% band shaded.

**Why we plotted it.** To test the *deniability* hypothesis — that the model deliberately avoids landing
just barely over the line because that would look targeted, and pushes out to a "natural-looking" margin
instead. That predicts a **hole** immediately next to the threshold.

**What it shows — this hypothesis is disconfirmed.** There is no hole. There is a **spike**:

| | within ±1% of T | within ±5% of T |
|---|---|---|
| baseline | 2 / 100 | 5 / 100 |
| above_good | **23 / 98** | 36 / 98 |
| below_good | 5 / 97 | 26 / 97 |

Nearly a quarter of `above_good` rollouts land within one percent of the line. That is extreme
threshold-hugging, the opposite of avoidance.

There is a real asymmetry though: `above_good` hugs tightly from above (23 within 1%), while `below_good`
sits further away (only 4 within 1% below, but 24 within 5% below). That fits the *anchor* account —
the model's default answer (~117M) sits just above T, so `above_good` barely has to move, whereas
`below_good` has to travel and overshoots.

**Caveat.** A handful of individual rollouts *do* explicitly reason about not looking like they targeted
the line. That reasoning is real; it just does not dominate the distribution.

---

## Fig 4 — `fig4_prior_gating.png`
### The opening guess

**Left panel.** Horizontal axis: the *first* candidate ÷ T, log scale. Vertical: whether the rollout
finished above or below T (points jittered so they don't overlap).
**Right panel.** Horizontal axis: `|log10(first candidate ÷ T)|` — a measure of *how far the opening
guess is from the line*, in either direction, where 0 means it opened right at the line. Vertical: how
many candidates the trace contained. Thick lines are binned medians.

**Why we plotted it.** Two hypotheses at once. First: does the opening guess largely determine the
outcome? Second: is the *most* reasoning done when the opening guess is near the line — where the
reasoning actually changes the payoff — producing an inverted-U?

**How to read it.** In the left panel, if the opening guess decided everything you would see a clean
split at the dashed vertical line. In the right panel, an inverted-U in the median line supports the
"hardest thinking near the line" idea.

**Caveat.** The first candidate is *not* independent of the condition — Fig 2 shows first candidates are
already slightly skewed (0.54 vs 0.39). So the opening guess is partly an effect, not purely a cause.
Treat this as descriptive, not causal.

---

## Fig 5 — `fig5_deliberation.png`
### Does the bet make the model think more, or less?

**What's plotted.** A violin (a smoothed distribution) of how many candidates each rollout contained.
Wider means more rollouts at that count. Median marked and labelled.

**Why we plotted it.** The intuitive guess is that a bet makes the model deliberate *more*. If it
deliberates *less*, that is evidence the incentive supplies a stopping condition the model otherwise lacks.

**What it shows.** Median candidates: **baseline 11, above_good 5, below_good 6.** The bet roughly
**halves** the amount of deliberation. The model does not agonise more when there is something at stake —
it settles sooner.

---

## Fig 6 — `fig6_drift.png`
### Median path through the reasoning

**What's plotted.** Every trace is stretched onto a common 0→1 axis (0 = first candidate, 1 = final
answer) so traces of different lengths can be averaged. The thick line is the median candidate value in
threshold units at each point; the shaded band is the interquartile range. Only traces with ≥4 candidates.

**Why we plotted it.** To ask whether the two conditions *start together and drift apart* (which would
mean the value creeps in during reasoning) or *start apart and stay apart* (which would mean the
condition affects the answer from the very first thought).

**What it shows.** The median paths are strikingly **flat**. `above_good` sits slightly above 1.0 for the
whole trace, `below_good` slightly below, baseline between them. The separation is present at the start
and barely grows.

**Reconciling this with Fig 2** (which showed the gap growing): these measure different things. Fig 6
tracks the *median value*; Fig 2 tracks *which side of the line* candidates fall on. Because values
converge tightly onto T (Fig 1), a very small movement flips the side without moving the median. That is
the signature of threshold-hugging: the model isn't changing its estimate much, it's making a small final
adjustment that crosses the line.

---

## Fig 7 — `fig7_first_vs_last.png`
### Where it started vs where it ended

**What's plotted.** One dot per rollout. Horizontal: first candidate ÷ T. Vertical: final answer ÷ T.
Both log. The dotted diagonal is "didn't move". Dashed lines mark T on both axes. Red dots moved up
over the trace, green moved down.

**Why we plotted it.** Fig 6 gives medians; this gives every rollout individually and shows the
*direction* each one travelled. The quadrants are meaningful: bottom-right = started above the line and
ended below it (a rollout that talked itself out of the favoured answer), top-left = the reverse.

**What it shows.** `above_good` moved up in 44/98 (45%); `below_good` moved up in 34/97 (35%). Most
of the action is near the diagonal — again, the model mostly stays where it started and makes a small
final correction.

---

## Fig 8 — `fig8_parse_artifact.png`
### The parse artifact, quantified

**What's plotted.** Fraction of rollouts whose *first* candidate is below T/20 — i.e. small enough that
it is almost certainly a giraffe population count, not a spot total. Whiskers are 95% Wilson intervals.

**Why we plotted it.** Not a result about the model — a result about the **data pipeline**, and a
warning. Any analysis of "where trajectories start" or "how they drift" is invalid until this is fixed.

**What it shows.** Baseline **29%** contaminated, versus **7%** (above_good) and **4%** (below_good).
The intervals do not overlap. Fix the judge's extraction prompt (or filter as we do here) before
trusting any start-point or drift claim.

---

## Fig 9 — `fig9_ablations.png`
### What removes the effect?

**What's plotted.** Bias for every variant already on disk, sorted. Not from trajectories — from each
run's `summary.csv`.

**Why we plotted it.** These runs exist but had not been read as a set. Together they answer several
open questions directly.

**What it shows.**

| variant | bias | reading |
|---|---|---|
| MAIN | **+0.62** | the baseline effect |
| stakes_low ($5) | +0.61 | naming a small sum changes almost nothing |
| stakes_high ($1M) | +0.49 | **more money → *less* bias** |
| user_prefers_bad | +0.27 | reversing the user's wish removes ~half — so it is **not mostly sycophancy** |
| no_consequence (bet already settled) | +0.17 | removing causal control removes ~73% |
| known_answer (UN states = 193) | **0.00** | with a *knowable* answer the effect vanishes entirely |
| hidden_threshold | **−0.11** | hide the number and the effect **disappears** |

Two of these are strong results on their own. **`known_answer` at exactly zero** says values only
intervene where the evidence genuinely underdetermines the answer — the model never states a number it
knows to be wrong. **`hidden_threshold` at −0.11** says the entire effect runs through the *visible*
threshold; without a number to reason about, there is nothing to reason toward.

**Caveat.** These runs saved only estimates and trajectories — **no chains of thought**. Re-running them
with rollouts persisted is the cheapest high-value thing available, and unblocks all mechanism-level
analysis of the ablations.

---

## Summary of what changed my mind

| claim | verdict |
|---|---|
| The model deliberates *less* under a bet | **supported** (Fig 5: 11 → 5/6 candidates) |
| Bias is concentrated at the stopping step | **partly** — real extra jump at the end, but middle candidates are already biased (Fig 2) |
| The model avoids landing just past the line | **disconfirmed** — it hugs the line hard (Fig 3: 23/98 within 1%) |
| Conditions start together and drift apart | **disconfirmed** — they start apart and stay apart (Fig 6) |
| There is a default answer the incentive pushes you off | **supported** — explains the above/below asymmetry in Fig 3 |
| Effect requires genuine uncertainty | **supported** — `known_answer` bias exactly 0 (Fig 9) |
| Effect requires a visible threshold | **supported** — `hidden_threshold` bias −0.11 (Fig 9) |

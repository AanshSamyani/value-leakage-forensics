# E2 — qwen3.5-27b-known-answer-un (qwen3.5-27b-known-answer-un_20260824_184505)

threshold = 193; length column = tokens

## T1 start shift

- P(first > T) [baseline]: 0.000 [0.000, 0.037] (n=100)
- P(first > T) [above_good]: 0.000 [0.000, 0.037] (n=100)
- P(first > T) [below_good]: 0.000 [0.000, 0.037] (n=99)
- P(first>T|above_good) - P(first>T|below_good) [diff]: 0.000 [0.000, 0.000] (n=199)
- P(first>T|above_good) - P(first>T|baseline) [diff_vs_base]: 0.000 [0.000, 0.000] (n=200)
- P(first>T|baseline) - P(first>T|below_good) [diff_vs_base]: 0.000 [0.000, 0.000] (n=199)
- P(first on favoured side) [pooled]: 0.497 [0.429, 0.566] (n=199)

## T2 length by first side (interaction = Δ_incentive − Δ_baseline, Δ = bad − good)

- above_good / incentive / first=bad: mean=2736 median=2698 (n=100.0)
- above_good / incentive / first=good: mean=nan median=nan (n=0.0)
- above_good / baseline / first=bad: mean=656 median=648 (n=100.0)
- above_good / baseline / first=good: mean=nan median=nan (n=0.0)
- below_good / incentive / first=bad: mean=nan median=nan (n=0.0)
- below_good / incentive / first=good: mean=1701 median=1566 (n=99.0)
- below_good / baseline / first=bad: mean=nan median=nan (n=0.0)
- below_good / baseline / first=good: mean=656 median=648 (n=100.0)
- INTERACTION above_good [logL]: Δinc=+nan Δbase=+nan interaction=+nan [+nan, +nan]
- INTERACTION above_good [tokens]: Δinc=+nan Δbase=+nan interaction=+nan [+nan, +nan]
- INTERACTION below_good [logL]: Δinc=+nan Δbase=+nan interaction=+nan [+nan, +nan]
- INTERACTION below_good [tokens]: Δinc=+nan Δbase=+nan interaction=+nan [+nan, +nan]

## T3 transitions


## T3 stopping hazard

- above_good / good: hazard P(stop | side) = nan (steps=0)
- above_good / good: hazard P(stop | side), K>=2 = nan (steps=0)
- above_good / bad: hazard P(stop | side) = 1.000 [1.00, 1.00] (steps=100)
- above_good / bad: hazard P(stop | side), K>=2 = nan (steps=0)
- baseline[good=above] / good: hazard P(stop | side) = nan (steps=0)
- baseline[good=above] / good: hazard P(stop | side), K>=2 = nan (steps=0)
- baseline[good=above] / bad: hazard P(stop | side) = 1.000 [1.00, 1.00] (steps=100)
- baseline[good=above] / bad: hazard P(stop | side), K>=2 = nan (steps=0)
- baseline[good=below] / good: hazard P(stop | side) = 1.000 [1.00, 1.00] (steps=100)
- baseline[good=below] / good: hazard P(stop | side), K>=2 = nan (steps=0)
- baseline[good=below] / bad: hazard P(stop | side) = nan (steps=0)
- baseline[good=below] / bad: hazard P(stop | side), K>=2 = nan (steps=0)
- below_good / good: hazard P(stop | side) = 1.000 [1.00, 1.00] (steps=99)
- below_good / good: hazard P(stop | side), K>=2 = nan (steps=0)
- below_good / bad: hazard P(stop | side) = nan (steps=0)
- below_good / bad: hazard P(stop | side), K>=2 = nan (steps=0)
- above_good / both: hazard(good) - hazard(bad) = nan
- above_good / both: hazard ratio good/bad = nan
- baseline[good=above] / both: hazard(good) - hazard(bad) = nan
- baseline[good=above] / both: hazard ratio good/bad = nan
- baseline[good=below] / both: hazard(good) - hazard(bad) = nan
- baseline[good=below] / both: hazard ratio good/bad = nan
- below_good / both: hazard(good) - hazard(bad) = nan
- below_good / both: hazard ratio good/bad = nan
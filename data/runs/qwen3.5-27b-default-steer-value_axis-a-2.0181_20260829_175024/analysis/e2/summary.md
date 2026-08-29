# E2 — qwen3.5-27b-steer-value_axis-a-2.0181 (qwen3.5-27b-default-steer-value_axis-a-2.0181_20260829_175024)

threshold = 104,475,000; length column = tokens

## T1 start shift

- P(first > T) [baseline]: 0.714 [0.576, 0.822] (n=49)
- P(first > T) [above_good]: 0.776 [0.653, 0.864] (n=58)
- P(first > T) [below_good]: 0.333 [0.220, 0.470] (n=51)
- P(first>T|above_good) - P(first>T|below_good) [diff]: 0.443 [0.276, 0.607] (n=109)
- P(first>T|above_good) - P(first>T|baseline) [diff_vs_base]: 0.062 [-0.109, 0.222] (n=107)
- P(first>T|baseline) - P(first>T|below_good) [diff_vs_base]: 0.381 [0.185, 0.560] (n=100)
- P(first on favoured side) [pooled]: 0.725 [0.634, 0.800] (n=109)

## T2 length by first side (interaction = Δ_incentive − Δ_baseline, Δ = bad − good)

- above_good / incentive / first=bad: mean=22097 median=21855 (n=13.0)
- above_good / incentive / first=good: mean=21807 median=21875 (n=45.0)
- above_good / baseline / first=bad: mean=21941 median=21934 (n=14.0)
- above_good / baseline / first=good: mean=20302 median=21503 (n=35.0)
- below_good / incentive / first=bad: mean=18659 median=22139 (n=17.0)
- below_good / incentive / first=good: mean=21769 median=22601 (n=34.0)
- below_good / baseline / first=bad: mean=20302 median=21503 (n=35.0)
- below_good / baseline / first=good: mean=21941 median=21934 (n=14.0)
- INTERACTION above_good [logL]: Δinc=+0.053 Δbase=+0.097 interaction=-0.044 [-0.288, +0.187]
- INTERACTION above_good [tokens]: Δinc=+289.692 Δbase=+1639.543 interaction=-1349.851 [-6126.369, +3148.262]
- INTERACTION below_good [logL]: Δinc=-0.205 Δbase=-0.097 interaction=-0.108 [-0.400, +0.161]
- INTERACTION below_good [tokens]: Δinc=-3109.618 Δbase=-1639.543 interaction=-1470.075 [-6294.469, +3036.579]

## T3 transitions

- above_good: P(toward_good | on bad side) = 0.800 [0.73, 0.91] (steps=65)
- above_good: P(toward_bad | on good side) = 0.515 [0.49, 0.54] (steps=897)
- baseline[good=above]: P(toward_good | on bad side) = 0.536 [0.49, 0.62] (steps=416)
- baseline[good=above]: P(toward_bad | on good side) = 0.483 [0.47, 0.50] (steps=1208)
- baseline[good=below]: P(toward_good | on bad side) = 0.483 [0.47, 0.50] (steps=1208)
- baseline[good=below]: P(toward_bad | on good side) = 0.536 [0.49, 0.62] (steps=416)
- below_good: P(toward_good | on bad side) = 0.533 [0.47, 0.63] (steps=261)
- below_good: P(toward_bad | on good side) = 0.649 [0.52, 0.80] (steps=111)
- above_good: asymmetry: P(toward good|bad) - P(toward bad|good) = 0.285
- baseline[good=above]: asymmetry: P(toward good|bad) - P(toward bad|good) = 0.053
- baseline[good=below]: asymmetry: P(toward good|bad) - P(toward bad|good) = -0.053
- below_good: asymmetry: P(toward good|bad) - P(toward bad|good) = -0.116

## T3 stopping hazard

- above_good / good: hazard P(stop | side) = 0.060 [0.04, 0.09] (steps=954)
- above_good / good: hazard P(stop | side), K>=2 = 0.047 (steps=941)
- above_good / bad: hazard P(stop | side) = 0.015 [0.00, 0.03] (steps=66)
- above_good / bad: hazard P(stop | side), K>=2 = 0.015 (steps=66)
- baseline[good=above] / good: hazard P(stop | side) = 0.031 [0.02, 0.05] (steps=1247)
- baseline[good=above] / good: hazard P(stop | side), K>=2 = 0.028 (steps=1243)
- baseline[good=above] / bad: hazard P(stop | side) = 0.023 [0.01, 0.04] (steps=426)
- baseline[good=above] / bad: hazard P(stop | side), K>=2 = 0.021 (steps=425)
- baseline[good=below] / good: hazard P(stop | side) = 0.023 [0.01, 0.04] (steps=426)
- baseline[good=below] / good: hazard P(stop | side), K>=2 = 0.021 (steps=425)
- baseline[good=below] / bad: hazard P(stop | side) = 0.031 [0.02, 0.05] (steps=1247)
- baseline[good=below] / bad: hazard P(stop | side), K>=2 = 0.028 (steps=1243)
- below_good / good: hazard P(stop | side) = 0.229 [0.16, 0.36] (steps=144)
- below_good / good: hazard P(stop | side), K>=2 = 0.133 (steps=128)
- below_good / bad: hazard P(stop | side) = 0.065 [0.04, 0.10] (steps=279)
- below_good / bad: hazard P(stop | side), K>=2 = 0.061 (steps=278)
- above_good / both: hazard(good) - hazard(bad) = 0.045
- above_good / both: hazard ratio good/bad = 3.943
- baseline[good=above] / both: hazard(good) - hazard(bad) = 0.008
- baseline[good=above] / both: hazard ratio good/bad = 1.332
- baseline[good=below] / both: hazard(good) - hazard(bad) = -0.008
- baseline[good=below] / both: hazard ratio good/bad = 0.751
- below_good / both: hazard(good) - hazard(bad) = 0.165
- below_good / both: hazard ratio good/bad = 3.552
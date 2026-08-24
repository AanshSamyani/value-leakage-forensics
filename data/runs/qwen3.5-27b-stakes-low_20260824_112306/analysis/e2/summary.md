# E2 — qwen3.5-27b-stakes-low (qwen3.5-27b-stakes-low_20260824_112306)

threshold = 104,475,000; length column = tokens

## T1 start shift

- P(first > T) [baseline]: 0.412 [0.303, 0.530] (n=68)
- P(first > T) [above_good]: 0.736 [0.637, 0.816] (n=91)
- P(first > T) [below_good]: 0.402 [0.308, 0.504] (n=92)
- P(first>T|above_good) - P(first>T|below_good) [diff]: 0.334 [0.192, 0.465] (n=183)
- P(first>T|above_good) - P(first>T|baseline) [diff_vs_base]: 0.324 [0.170, 0.464] (n=159)
- P(first>T|baseline) - P(first>T|below_good) [diff_vs_base]: 0.010 [-0.144, 0.163] (n=160)
- P(first on favoured side) [pooled]: 0.667 [0.596, 0.731] (n=183)

## T2 length by first side (interaction = Δ_incentive − Δ_baseline, Δ = bad − good)

- above_good / incentive / first=bad: mean=11558 median=11458 (n=24.0)
- above_good / incentive / first=good: mean=10007 median=9784 (n=67.0)
- above_good / baseline / first=bad: mean=8870 median=8777 (n=40.0)
- above_good / baseline / first=good: mean=8955 median=8689 (n=28.0)
- below_good / incentive / first=bad: mean=11416 median=11393 (n=37.0)
- below_good / incentive / first=good: mean=9375 median=9298 (n=55.0)
- below_good / baseline / first=bad: mean=8955 median=8689 (n=28.0)
- below_good / baseline / first=good: mean=8870 median=8777 (n=40.0)
- INTERACTION above_good [logL]: Δinc=+0.141 Δbase=+0.015 interaction=+0.126 [-0.033, +0.268]
- INTERACTION above_good [tokens]: Δinc=+1551.308 Δbase=-84.504 interaction=+1635.811 [+305.048, +2938.434]
- INTERACTION below_good [logL]: Δinc=+0.192 Δbase=-0.015 interaction=+0.207 [+0.078, +0.341]
- INTERACTION below_good [tokens]: Δinc=+2040.690 Δbase=+84.504 interaction=+1956.187 [+820.635, +3123.309]

## T3 transitions

- above_good: P(toward_good | on bad side) = 0.704 [0.65, 0.79] (steps=199)
- above_good: P(toward_bad | on good side) = 0.543 [0.50, 0.59] (steps=335)
- baseline[good=above]: P(toward_good | on bad side) = 0.513 [0.48, 0.55] (steps=520)
- baseline[good=above]: P(toward_bad | on good side) = 0.481 [0.45, 0.52] (steps=424)
- baseline[good=below]: P(toward_good | on bad side) = 0.481 [0.45, 0.52] (steps=424)
- baseline[good=below]: P(toward_bad | on good side) = 0.513 [0.48, 0.55] (steps=520)
- below_good: P(toward_good | on bad side) = 0.686 [0.62, 0.77] (steps=236)
- below_good: P(toward_bad | on good side) = 0.603 [0.57, 0.64] (steps=373)
- above_good: asymmetry: P(toward good|bad) - P(toward bad|good) = 0.160
- baseline[good=above]: asymmetry: P(toward good|bad) - P(toward bad|good) = 0.032
- baseline[good=below]: asymmetry: P(toward good|bad) - P(toward bad|good) = -0.032
- below_good: asymmetry: P(toward good|bad) - P(toward bad|good) = 0.083

## T3 stopping hazard

- above_good / good: hazard P(stop | side) = 0.191 [0.15, 0.25] (steps=414)
- above_good / good: hazard P(stop | side), K>=2 = 0.125 (steps=383)
- above_good / bad: hazard P(stop | side) = 0.057 [0.04, 0.09] (steps=211)
- above_good / bad: hazard P(stop | side), K>=2 = 0.039 (steps=207)
- baseline[good=above] / good: hazard P(stop | side) = 0.066 [0.05, 0.09] (steps=454)
- baseline[good=above] / good: hazard P(stop | side), K>=2 = 0.060 (steps=451)
- baseline[good=above] / bad: hazard P(stop | side) = 0.068 [0.06, 0.09] (steps=558)
- baseline[good=above] / bad: hazard P(stop | side), K>=2 = 0.060 (steps=553)
- baseline[good=below] / good: hazard P(stop | side) = 0.068 [0.06, 0.09] (steps=558)
- baseline[good=below] / good: hazard P(stop | side), K>=2 = 0.060 (steps=553)
- baseline[good=below] / bad: hazard P(stop | side) = 0.066 [0.05, 0.09] (steps=454)
- baseline[good=below] / bad: hazard P(stop | side), K>=2 = 0.060 (steps=451)
- below_good / good: hazard P(stop | side) = 0.156 [0.12, 0.21] (steps=442)
- below_good / good: hazard P(stop | side), K>=2 = 0.106 (steps=417)
- below_good / bad: hazard P(stop | side) = 0.089 [0.06, 0.13] (steps=259)
- below_good / bad: hazard P(stop | side), K>=2 = 0.045 (steps=247)
- above_good / both: hazard(good) - hazard(bad) = 0.134
- above_good / both: hazard ratio good/bad = 3.355
- baseline[good=above] / both: hazard(good) - hazard(bad) = -0.002
- baseline[good=above] / both: hazard ratio good/bad = 0.970
- baseline[good=below] / both: hazard(good) - hazard(bad) = 0.002
- baseline[good=below] / both: hazard ratio good/bad = 1.031
- below_good / both: hazard(good) - hazard(bad) = 0.067
- below_good / both: hazard ratio good/bad = 1.758
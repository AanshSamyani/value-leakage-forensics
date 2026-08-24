# E2 — qwen3.5-27b-hidden-threshold (qwen3.5-27b-hidden-threshold_20260824_112306)

threshold = 104,475,000; length column = tokens

## T1 start shift

- P(first > T) [baseline]: 0.412 [0.303, 0.530] (n=68)
- P(first > T) [above_good]: 0.400 [0.305, 0.503] (n=90)
- P(first > T) [below_good]: 0.517 [0.414, 0.619] (n=87)
- P(first>T|above_good) - P(first>T|below_good) [diff]: -0.117 [-0.263, 0.030] (n=177)
- P(first>T|above_good) - P(first>T|baseline) [diff_vs_base]: -0.012 [-0.171, 0.146] (n=158)
- P(first>T|baseline) - P(first>T|below_good) [diff_vs_base]: -0.105 [-0.263, 0.054] (n=155)
- P(first on favoured side) [pooled]: 0.441 [0.370, 0.514] (n=177)

## T2 length by first side (interaction = Δ_incentive − Δ_baseline, Δ = bad − good)

- above_good / incentive / first=bad: mean=7862 median=7807 (n=54.0)
- above_good / incentive / first=good: mean=8658 median=8514 (n=36.0)
- above_good / baseline / first=bad: mean=8870 median=8777 (n=40.0)
- above_good / baseline / first=good: mean=8955 median=8689 (n=28.0)
- below_good / incentive / first=bad: mean=8121 median=8091 (n=45.0)
- below_good / incentive / first=good: mean=7948 median=7772 (n=42.0)
- below_good / baseline / first=bad: mean=8955 median=8689 (n=28.0)
- below_good / baseline / first=good: mean=8870 median=8777 (n=40.0)
- INTERACTION above_good [logL]: Δinc=-0.094 Δbase=+0.015 interaction=-0.109 [-0.239, +0.012]
- INTERACTION above_good [tokens]: Δinc=-796.843 Δbase=-84.504 interaction=-712.339 [-1704.543, +276.102]
- INTERACTION below_good [logL]: Δinc=+0.009 Δbase=-0.015 interaction=+0.024 [-0.112, +0.169]
- INTERACTION below_good [tokens]: Δinc=+173.057 Δbase=+84.504 interaction=+88.554 [-935.765, +1130.506]

## T3 transitions

- above_good: P(toward_good | on bad side) = 0.532 [0.51, 0.56] (steps=583)
- above_good: P(toward_bad | on good side) = 0.464 [0.43, 0.50] (steps=330)
- baseline[good=above]: P(toward_good | on bad side) = 0.513 [0.48, 0.55] (steps=520)
- baseline[good=above]: P(toward_bad | on good side) = 0.481 [0.45, 0.52] (steps=424)
- baseline[good=below]: P(toward_good | on bad side) = 0.481 [0.45, 0.52] (steps=424)
- baseline[good=below]: P(toward_bad | on good side) = 0.513 [0.48, 0.55] (steps=520)
- below_good: P(toward_good | on bad side) = 0.532 [0.49, 0.58] (steps=316)
- below_good: P(toward_bad | on good side) = 0.523 [0.49, 0.56] (steps=407)
- above_good: asymmetry: P(toward good|bad) - P(toward bad|good) = 0.068
- baseline[good=above]: asymmetry: P(toward good|bad) - P(toward bad|good) = 0.032
- baseline[good=below]: asymmetry: P(toward good|bad) - P(toward bad|good) = -0.032
- below_good: asymmetry: P(toward good|bad) - P(toward bad|good) = 0.008

## T3 stopping hazard

- above_good / good: hazard P(stop | side) = 0.096 [0.07, 0.15] (steps=365)
- above_good / good: hazard P(stop | side), K>=2 = 0.065 (steps=353)
- above_good / bad: hazard P(stop | side) = 0.086 [0.07, 0.11] (steps=638)
- above_good / bad: hazard P(stop | side), K>=2 = 0.078 (steps=632)
- baseline[good=above] / good: hazard P(stop | side) = 0.066 [0.05, 0.09] (steps=454)
- baseline[good=above] / good: hazard P(stop | side), K>=2 = 0.060 (steps=451)
- baseline[good=above] / bad: hazard P(stop | side) = 0.068 [0.06, 0.09] (steps=558)
- baseline[good=above] / bad: hazard P(stop | side), K>=2 = 0.060 (steps=553)
- baseline[good=below] / good: hazard P(stop | side) = 0.068 [0.06, 0.09] (steps=558)
- baseline[good=below] / good: hazard P(stop | side), K>=2 = 0.060 (steps=553)
- baseline[good=below] / bad: hazard P(stop | side) = 0.066 [0.05, 0.09] (steps=454)
- baseline[good=below] / bad: hazard P(stop | side), K>=2 = 0.060 (steps=451)
- below_good / good: hazard P(stop | side) = 0.100 [0.08, 0.13] (steps=452)
- below_good / good: hazard P(stop | side), K>=2 = 0.079 (steps=442)
- below_good / bad: hazard P(stop | side) = 0.117 [0.09, 0.17] (steps=358)
- below_good / bad: hazard P(stop | side), K>=2 = 0.089 (steps=347)
- above_good / both: hazard(good) - hazard(bad) = 0.010
- above_good / both: hazard ratio good/bad = 1.112
- baseline[good=above] / both: hazard(good) - hazard(bad) = -0.002
- baseline[good=above] / both: hazard ratio good/bad = 0.970
- baseline[good=below] / both: hazard(good) - hazard(bad) = 0.002
- baseline[good=below] / both: hazard ratio good/bad = 1.031
- below_good / both: hazard(good) - hazard(bad) = -0.018
- below_good / both: hazard ratio good/bad = 0.849
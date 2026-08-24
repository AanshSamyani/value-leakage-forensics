# E2 — qwen3.5-27b-stakes-high (qwen3.5-27b-stakes-high_20260824_112306)

threshold = 104,475,000; length column = tokens

## T1 start shift

- P(first > T) [baseline]: 0.412 [0.303, 0.530] (n=68)
- P(first > T) [above_good]: 0.622 [0.519, 0.715] (n=90)
- P(first > T) [below_good]: 0.400 [0.305, 0.503] (n=90)
- P(first>T|above_good) - P(first>T|below_good) [diff]: 0.222 [0.089, 0.367] (n=180)
- P(first>T|above_good) - P(first>T|baseline) [diff_vs_base]: 0.210 [0.056, 0.362] (n=158)
- P(first>T|baseline) - P(first>T|below_good) [diff_vs_base]: 0.012 [-0.136, 0.163] (n=158)
- P(first on favoured side) [pooled]: 0.611 [0.538, 0.679] (n=180)

## T2 length by first side (interaction = Δ_incentive − Δ_baseline, Δ = bad − good)

- above_good / incentive / first=bad: mean=10689 median=10778 (n=34.0)
- above_good / incentive / first=good: mean=10073 median=9790 (n=56.0)
- above_good / baseline / first=bad: mean=8870 median=8777 (n=40.0)
- above_good / baseline / first=good: mean=8955 median=8689 (n=28.0)
- below_good / incentive / first=bad: mean=10932 median=10964 (n=36.0)
- below_good / incentive / first=good: mean=10111 median=9906 (n=54.0)
- below_good / baseline / first=bad: mean=8955 median=8689 (n=28.0)
- below_good / baseline / first=good: mean=8870 median=8777 (n=40.0)
- INTERACTION above_good [logL]: Δinc=+0.065 Δbase=+0.015 interaction=+0.050 [-0.092, +0.183]
- INTERACTION above_good [tokens]: Δinc=+616.103 Δbase=-84.504 interaction=+700.607 [-424.613, +1817.202]
- INTERACTION below_good [logL]: Δinc=+0.103 Δbase=-0.015 interaction=+0.118 [-0.033, +0.284]
- INTERACTION below_good [tokens]: Δinc=+820.898 Δbase=+84.504 interaction=+736.395 [-484.467, +1980.300]

## T3 transitions

- above_good: P(toward_good | on bad side) = 0.746 [0.70, 0.81] (steps=213)
- above_good: P(toward_bad | on good side) = 0.580 [0.53, 0.63] (steps=381)
- baseline[good=above]: P(toward_good | on bad side) = 0.513 [0.48, 0.55] (steps=520)
- baseline[good=above]: P(toward_bad | on good side) = 0.481 [0.45, 0.52] (steps=424)
- baseline[good=below]: P(toward_good | on bad side) = 0.481 [0.45, 0.52] (steps=424)
- baseline[good=below]: P(toward_bad | on good side) = 0.513 [0.48, 0.55] (steps=520)
- below_good: P(toward_good | on bad side) = 0.656 [0.60, 0.71] (steps=311)
- below_good: P(toward_bad | on good side) = 0.627 [0.58, 0.67] (steps=437)
- above_good: asymmetry: P(toward good|bad) - P(toward bad|good) = 0.166
- baseline[good=above]: asymmetry: P(toward good|bad) - P(toward bad|good) = 0.032
- baseline[good=below]: asymmetry: P(toward good|bad) - P(toward bad|good) = -0.032
- below_good: asymmetry: P(toward good|bad) - P(toward bad|good) = 0.029

## T3 stopping hazard

- above_good / good: hazard P(stop | side) = 0.155 [0.12, 0.22] (steps=451)
- above_good / good: hazard P(stop | side), K>=2 = 0.104 (steps=425)
- above_good / bad: hazard P(stop | side) = 0.086 [0.05, 0.13] (steps=233)
- above_good / bad: hazard P(stop | side), K>=2 = 0.041 (steps=222)
- baseline[good=above] / good: hazard P(stop | side) = 0.066 [0.05, 0.09] (steps=454)
- baseline[good=above] / good: hazard P(stop | side), K>=2 = 0.060 (steps=451)
- baseline[good=above] / bad: hazard P(stop | side) = 0.068 [0.06, 0.09] (steps=558)
- baseline[good=above] / bad: hazard P(stop | side), K>=2 = 0.060 (steps=553)
- baseline[good=below] / good: hazard P(stop | side) = 0.068 [0.06, 0.09] (steps=558)
- baseline[good=below] / good: hazard P(stop | side), K>=2 = 0.060 (steps=553)
- baseline[good=below] / bad: hazard P(stop | side) = 0.066 [0.05, 0.09] (steps=454)
- baseline[good=below] / bad: hazard P(stop | side), K>=2 = 0.060 (steps=451)
- below_good / good: hazard P(stop | side) = 0.126 [0.10, 0.17] (steps=500)
- below_good / good: hazard P(stop | side), K>=2 = 0.090 (steps=480)
- below_good / bad: hazard P(stop | side) = 0.080 [0.06, 0.11] (steps=338)
- below_good / bad: hazard P(stop | side), K>=2 = 0.072 (steps=335)
- above_good / both: hazard(good) - hazard(bad) = 0.069
- above_good / both: hazard ratio good/bad = 1.808
- baseline[good=above] / both: hazard(good) - hazard(bad) = -0.002
- baseline[good=above] / both: hazard ratio good/bad = 0.970
- baseline[good=below] / both: hazard(good) - hazard(bad) = 0.002
- baseline[good=below] / both: hazard ratio good/bad = 1.031
- below_good / both: hazard(good) - hazard(bad) = 0.046
- below_good / both: hazard ratio good/bad = 1.577
# E2 — qwen3.5-27b-user-prefers-bad (qwen3.5-27b-user-prefers-bad_20260824_112306)

threshold = 104,475,000; length column = tokens

## T1 start shift

- P(first > T) [baseline]: 0.412 [0.303, 0.530] (n=68)
- P(first > T) [above_good]: 0.587 [0.485, 0.682] (n=92)
- P(first > T) [below_good]: 0.387 [0.294, 0.489] (n=93)
- P(first>T|above_good) - P(first>T|below_good) [diff]: 0.200 [0.059, 0.340] (n=185)
- P(first>T|above_good) - P(first>T|baseline) [diff_vs_base]: 0.175 [0.015, 0.329] (n=160)
- P(first>T|baseline) - P(first>T|below_good) [diff_vs_base]: 0.025 [-0.124, 0.179] (n=161)
- P(first on favoured side) [pooled]: 0.600 [0.528, 0.668] (n=185)

## T2 length by first side (interaction = Δ_incentive − Δ_baseline, Δ = bad − good)

- above_good / incentive / first=bad: mean=9453 median=9518 (n=38.0)
- above_good / incentive / first=good: mean=9241 median=9210 (n=54.0)
- above_good / baseline / first=bad: mean=8870 median=8777 (n=40.0)
- above_good / baseline / first=good: mean=8955 median=8689 (n=28.0)
- below_good / incentive / first=bad: mean=8875 median=8848 (n=36.0)
- below_good / incentive / first=good: mean=9117 median=8572 (n=57.0)
- below_good / baseline / first=bad: mean=8955 median=8689 (n=28.0)
- below_good / baseline / first=good: mean=8870 median=8777 (n=40.0)
- INTERACTION above_good [logL]: Δinc=+0.018 Δbase=+0.015 interaction=+0.003 [-0.147, +0.133]
- INTERACTION above_good [tokens]: Δinc=+212.184 Δbase=-84.504 interaction=+296.688 [-810.536, +1312.255]
- INTERACTION below_good [logL]: Δinc=-0.040 Δbase=-0.015 interaction=-0.025 [-0.172, +0.114]
- INTERACTION below_good [tokens]: Δinc=-241.855 Δbase=+84.504 interaction=-326.359 [-1460.516, +750.605]

## T3 transitions

- above_good: P(toward_good | on bad side) = 0.692 [0.63, 0.76] (steps=357)
- above_good: P(toward_bad | on good side) = 0.632 [0.57, 0.70] (steps=269)
- baseline[good=above]: P(toward_good | on bad side) = 0.513 [0.48, 0.55] (steps=520)
- baseline[good=above]: P(toward_bad | on good side) = 0.481 [0.45, 0.52] (steps=424)
- baseline[good=below]: P(toward_good | on bad side) = 0.481 [0.45, 0.52] (steps=424)
- baseline[good=below]: P(toward_bad | on good side) = 0.513 [0.48, 0.55] (steps=520)
- below_good: P(toward_good | on bad side) = 0.598 [0.55, 0.66] (steps=194)
- below_good: P(toward_bad | on good side) = 0.607 [0.53, 0.69] (steps=178)
- above_good: asymmetry: P(toward good|bad) - P(toward bad|good) = 0.060
- baseline[good=above]: asymmetry: P(toward good|bad) - P(toward bad|good) = 0.032
- baseline[good=below]: asymmetry: P(toward good|bad) - P(toward bad|good) = -0.032
- below_good: asymmetry: P(toward good|bad) - P(toward bad|good) = -0.009

## T3 stopping hazard

- above_good / good: hazard P(stop | side) = 0.180 [0.14, 0.24] (steps=328)
- above_good / good: hazard P(stop | side), K>=2 = 0.106 (steps=301)
- above_good / bad: hazard P(stop | side) = 0.085 [0.06, 0.11] (steps=390)
- above_good / bad: hazard P(stop | side), K>=2 = 0.068 (steps=383)
- baseline[good=above] / good: hazard P(stop | side) = 0.066 [0.05, 0.09] (steps=454)
- baseline[good=above] / good: hazard P(stop | side), K>=2 = 0.060 (steps=451)
- baseline[good=above] / bad: hazard P(stop | side) = 0.068 [0.06, 0.09] (steps=558)
- baseline[good=above] / bad: hazard P(stop | side), K>=2 = 0.060 (steps=553)
- baseline[good=below] / good: hazard P(stop | side) = 0.068 [0.06, 0.09] (steps=558)
- baseline[good=below] / good: hazard P(stop | side), K>=2 = 0.060 (steps=553)
- baseline[good=below] / bad: hazard P(stop | side) = 0.066 [0.05, 0.09] (steps=454)
- baseline[good=below] / bad: hazard P(stop | side), K>=2 = 0.060 (steps=451)
- below_good / good: hazard P(stop | side) = 0.243 [0.17, 0.37] (steps=235)
- below_good / good: hazard P(stop | side), K>=2 = 0.119 (steps=202)
- below_good / bad: hazard P(stop | side) = 0.157 [0.12, 0.22] (steps=230)
- below_good / bad: hazard P(stop | side), K>=2 = 0.118 (steps=220)
- above_good / both: hazard(good) - hazard(bad) = 0.095
- above_good / both: hazard ratio good/bad = 2.126
- baseline[good=above] / both: hazard(good) - hazard(bad) = -0.002
- baseline[good=above] / both: hazard ratio good/bad = 0.970
- baseline[good=below] / both: hazard(good) - hazard(bad) = 0.002
- baseline[good=below] / both: hazard ratio good/bad = 1.031
- below_good / both: hazard(good) - hazard(bad) = 0.086
- below_good / both: hazard ratio good/bad = 1.550
# E2 — qwen3.5-27b-no-consequence (qwen3.5-27b-no-consequence_20260824_112306)

threshold = 104,475,000; length column = tokens

## T1 start shift

- P(first > T) [baseline]: 0.412 [0.303, 0.530] (n=68)
- P(first > T) [above_good]: 0.581 [0.476, 0.680] (n=86)
- P(first > T) [below_good]: 0.505 [0.407, 0.603] (n=97)
- P(first>T|above_good) - P(first>T|below_good) [diff]: 0.076 [-0.066, 0.212] (n=183)
- P(first>T|above_good) - P(first>T|baseline) [diff_vs_base]: 0.170 [0.008, 0.325] (n=154)
- P(first>T|baseline) - P(first>T|below_good) [diff_vs_base]: -0.093 [-0.238, 0.058] (n=165)
- P(first on favoured side) [pooled]: 0.536 [0.463, 0.606] (n=183)

## T2 length by first side (interaction = Δ_incentive − Δ_baseline, Δ = bad − good)

- above_good / incentive / first=bad: mean=10354 median=10430 (n=36.0)
- above_good / incentive / first=good: mean=10155 median=10241 (n=50.0)
- above_good / baseline / first=bad: mean=8870 median=8777 (n=40.0)
- above_good / baseline / first=good: mean=8955 median=8689 (n=28.0)
- below_good / incentive / first=bad: mean=10209 median=10139 (n=49.0)
- below_good / incentive / first=good: mean=9727 median=9958 (n=48.0)
- below_good / baseline / first=bad: mean=8955 median=8689 (n=28.0)
- below_good / baseline / first=good: mean=8870 median=8777 (n=40.0)
- INTERACTION above_good [logL]: Δinc=+0.020 Δbase=+0.015 interaction=+0.005 [-0.131, +0.125]
- INTERACTION above_good [tokens]: Δinc=+199.282 Δbase=-84.504 interaction=+283.786 [-788.777, +1310.850]
- INTERACTION below_good [logL]: Δinc=+0.055 Δbase=-0.015 interaction=+0.069 [-0.060, +0.211]
- INTERACTION below_good [tokens]: Δinc=+481.715 Δbase=+84.504 interaction=+397.212 [-707.484, +1485.742]

## T3 transitions

- above_good: P(toward_good | on bad side) = 0.693 [0.64, 0.76] (steps=410)
- above_good: P(toward_bad | on good side) = 0.551 [0.51, 0.60] (steps=719)
- baseline[good=above]: P(toward_good | on bad side) = 0.513 [0.48, 0.55] (steps=520)
- baseline[good=above]: P(toward_bad | on good side) = 0.481 [0.45, 0.52] (steps=424)
- baseline[good=below]: P(toward_good | on bad side) = 0.481 [0.45, 0.52] (steps=424)
- baseline[good=below]: P(toward_bad | on good side) = 0.513 [0.48, 0.55] (steps=520)
- below_good: P(toward_good | on bad side) = 0.608 [0.56, 0.67] (steps=441)
- below_good: P(toward_bad | on good side) = 0.602 [0.57, 0.64] (steps=450)
- above_good: asymmetry: P(toward good|bad) - P(toward bad|good) = 0.142
- baseline[good=above]: asymmetry: P(toward good|bad) - P(toward bad|good) = 0.032
- baseline[good=below]: asymmetry: P(toward good|bad) - P(toward bad|good) = -0.032
- below_good: asymmetry: P(toward good|bad) - P(toward bad|good) = 0.005

## T3 stopping hazard

- above_good / good: hazard P(stop | side) = 0.077 [0.06, 0.10] (steps=779)
- above_good / good: hazard P(stop | side), K>=2 = 0.058 (steps=763)
- above_good / bad: hazard P(stop | side) = 0.060 [0.04, 0.09] (steps=436)
- above_good / bad: hazard P(stop | side), K>=2 = 0.044 (steps=429)
- baseline[good=above] / good: hazard P(stop | side) = 0.066 [0.05, 0.09] (steps=454)
- baseline[good=above] / good: hazard P(stop | side), K>=2 = 0.060 (steps=451)
- baseline[good=above] / bad: hazard P(stop | side) = 0.068 [0.06, 0.09] (steps=558)
- baseline[good=above] / bad: hazard P(stop | side), K>=2 = 0.060 (steps=553)
- baseline[good=below] / good: hazard P(stop | side) = 0.068 [0.06, 0.09] (steps=558)
- baseline[good=below] / good: hazard P(stop | side), K>=2 = 0.060 (steps=553)
- baseline[good=below] / bad: hazard P(stop | side) = 0.066 [0.05, 0.09] (steps=454)
- baseline[good=below] / bad: hazard P(stop | side), K>=2 = 0.060 (steps=451)
- below_good / good: hazard P(stop | side) = 0.100 [0.08, 0.14] (steps=500)
- below_good / good: hazard P(stop | side), K>=2 = 0.074 (steps=486)
- below_good / bad: hazard P(stop | side) = 0.096 [0.07, 0.13] (steps=488)
- below_good / bad: hazard P(stop | side), K>=2 = 0.074 (steps=476)
- above_good / both: hazard(good) - hazard(bad) = 0.017
- above_good / both: hazard ratio good/bad = 1.292
- baseline[good=above] / both: hazard(good) - hazard(bad) = -0.002
- baseline[good=above] / both: hazard ratio good/bad = 0.970
- baseline[good=below] / both: hazard(good) - hazard(bad) = 0.002
- baseline[good=below] / both: hazard ratio good/bad = 1.031
- below_good / both: hazard(good) - hazard(bad) = 0.004
- below_good / both: hazard ratio good/bad = 1.038
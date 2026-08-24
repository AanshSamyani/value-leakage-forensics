# E2 — qwen3.5-27b (qwen3.5-27b_20260823_223518)

threshold = 104,475,000; length column = tokens

## T1 start shift

- P(first > T) [baseline]: 0.412 [0.303, 0.530] (n=68)
- P(first > T) [above_good]: 0.648 [0.544, 0.739] (n=88)
- P(first > T) [below_good]: 0.326 [0.239, 0.427] (n=92)
- P(first>T|above_good) - P(first>T|below_good) [diff]: 0.322 [0.188, 0.463] (n=180)
- P(first>T|above_good) - P(first>T|baseline) [diff_vs_base]: 0.236 [0.083, 0.389] (n=156)
- P(first>T|baseline) - P(first>T|below_good) [diff_vs_base]: 0.086 [-0.061, 0.235] (n=160)
- P(first on favoured side) [pooled]: 0.661 [0.589, 0.726] (n=180)

## T2 length by first side (interaction = Δ_incentive − Δ_baseline, Δ = bad − good)

- above_good / incentive / first=bad: mean=11082 median=11018 (n=31.0)
- above_good / incentive / first=good: mean=10363 median=10351 (n=57.0)
- above_good / baseline / first=bad: mean=8870 median=8777 (n=40.0)
- above_good / baseline / first=good: mean=8955 median=8689 (n=28.0)
- below_good / incentive / first=bad: mean=11093 median=10928 (n=30.0)
- below_good / incentive / first=good: mean=10156 median=9905 (n=62.0)
- below_good / baseline / first=bad: mean=8955 median=8689 (n=28.0)
- below_good / baseline / first=good: mean=8870 median=8777 (n=40.0)
- INTERACTION above_good [logL]: Δinc=+0.071 Δbase=+0.015 interaction=+0.056 [-0.074, +0.174]
- INTERACTION above_good [tokens]: Δinc=+718.449 Δbase=-84.504 interaction=+802.953 [-280.513, +1861.987]
- INTERACTION below_good [logL]: Δinc=+0.089 Δbase=-0.015 interaction=+0.104 [-0.027, +0.246]
- INTERACTION below_good [tokens]: Δinc=+937.383 Δbase=+84.504 interaction=+852.879 [-385.617, +2072.411]

## T3 transitions

- above_good: P(toward_good | on bad side) = 0.735 [0.68, 0.80] (steps=219)
- above_good: P(toward_bad | on good side) = 0.527 [0.48, 0.58] (steps=427)
- baseline[good=above]: P(toward_good | on bad side) = 0.513 [0.48, 0.55] (steps=520)
- baseline[good=above]: P(toward_bad | on good side) = 0.481 [0.45, 0.52] (steps=424)
- baseline[good=below]: P(toward_good | on bad side) = 0.481 [0.45, 0.52] (steps=424)
- baseline[good=below]: P(toward_bad | on good side) = 0.513 [0.48, 0.55] (steps=520)
- below_good: P(toward_good | on bad side) = 0.635 [0.60, 0.69] (steps=255)
- below_good: P(toward_bad | on good side) = 0.605 [0.57, 0.64] (steps=468)
- above_good: asymmetry: P(toward good|bad) - P(toward bad|good) = 0.208
- baseline[good=above]: asymmetry: P(toward good|bad) - P(toward bad|good) = 0.032
- baseline[good=below]: asymmetry: P(toward good|bad) - P(toward bad|good) = -0.032
- below_good: asymmetry: P(toward good|bad) - P(toward bad|good) = 0.031

## T3 stopping hazard

- above_good / good: hazard P(stop | side) = 0.151 [0.11, 0.21] (steps=503)
- above_good / good: hazard P(stop | side), K>=2 = 0.109 (steps=479)
- above_good / bad: hazard P(stop | side) = 0.052 [0.03, 0.07] (steps=231)
- above_good / bad: hazard P(stop | side), K>=2 = 0.048 (steps=230)
- baseline[good=above] / good: hazard P(stop | side) = 0.066 [0.05, 0.09] (steps=454)
- baseline[good=above] / good: hazard P(stop | side), K>=2 = 0.060 (steps=451)
- baseline[good=above] / bad: hazard P(stop | side) = 0.068 [0.06, 0.09] (steps=558)
- baseline[good=above] / bad: hazard P(stop | side), K>=2 = 0.060 (steps=553)
- baseline[good=below] / good: hazard P(stop | side) = 0.068 [0.06, 0.09] (steps=558)
- baseline[good=below] / good: hazard P(stop | side), K>=2 = 0.060 (steps=553)
- baseline[good=below] / bad: hazard P(stop | side) = 0.066 [0.05, 0.09] (steps=454)
- baseline[good=below] / bad: hazard P(stop | side), K>=2 = 0.060 (steps=451)
- below_good / good: hazard P(stop | side) = 0.128 [0.10, 0.17] (steps=537)
- below_good / good: hazard P(stop | side), K>=2 = 0.089 (steps=514)
- below_good / bad: hazard P(stop | side) = 0.083 [0.06, 0.12] (steps=278)
- below_good / bad: hazard P(stop | side), K>=2 = 0.059 (steps=271)
- above_good / both: hazard(good) - hazard(bad) = 0.099
- above_good / both: hazard ratio good/bad = 2.909
- baseline[good=above] / both: hazard(good) - hazard(bad) = -0.002
- baseline[good=above] / both: hazard ratio good/bad = 0.970
- baseline[good=below] / both: hazard(good) - hazard(bad) = 0.002
- baseline[good=below] / both: hazard ratio good/bad = 1.031
- below_good / both: hazard(good) - hazard(bad) = 0.046
- below_good / both: hazard ratio good/bad = 1.553
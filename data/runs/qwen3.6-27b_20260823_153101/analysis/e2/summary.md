# E2 — qwen3.6-27b (qwen3.6-27b_20260823_153101)

threshold = 84,621,000; length column = tokens

## T1 start shift

- P(first > T) [baseline]: 0.554 [0.453, 0.652] (n=92)
- P(first > T) [above_good]: 0.546 [0.447, 0.642] (n=97)
- P(first > T) [below_good]: 0.516 [0.416, 0.615] (n=93)
- P(first>T|above_good) - P(first>T|below_good) [diff]: 0.030 [-0.107, 0.169] (n=190)
- P(first>T|above_good) - P(first>T|baseline) [diff_vs_base]: -0.008 [-0.155, 0.129] (n=189)
- P(first>T|baseline) - P(first>T|below_good) [diff_vs_base]: 0.038 [-0.102, 0.189] (n=185)
- P(first on favoured side) [pooled]: 0.516 [0.445, 0.586] (n=190)

## T2 length by first side (interaction = Δ_incentive − Δ_baseline, Δ = bad − good)

- above_good / incentive / first=bad: mean=4344 median=4197 (n=44.0)
- above_good / incentive / first=good: mean=4088 median=3981 (n=53.0)
- above_good / baseline / first=bad: mean=3731 median=3778 (n=41.0)
- above_good / baseline / first=good: mean=3649 median=3632 (n=51.0)
- below_good / incentive / first=bad: mean=4565 median=4695 (n=48.0)
- below_good / incentive / first=good: mean=4053 median=4025 (n=45.0)
- below_good / baseline / first=bad: mean=3649 median=3632 (n=51.0)
- below_good / baseline / first=good: mean=3731 median=3778 (n=41.0)
- INTERACTION above_good [logL]: Δinc=+0.057 Δbase=+0.033 interaction=+0.024 [-0.091, +0.136]
- INTERACTION above_good [tokens]: Δinc=+256.271 Δbase=+81.822 interaction=+174.449 [-287.724, +635.811]
- INTERACTION below_good [logL]: Δinc=+0.102 Δbase=-0.033 interaction=+0.135 [+0.016, +0.261]
- INTERACTION below_good [tokens]: Δinc=+511.053 Δbase=-81.822 interaction=+592.875 [+126.280, +1076.852]

## T3 transitions

- above_good: P(toward_good | on bad side) = 0.569 [0.53, 0.61] (steps=459)
- above_good: P(toward_bad | on good side) = 0.577 [0.54, 0.62] (steps=452)
- baseline[good=above]: P(toward_good | on bad side) = 0.501 [0.47, 0.53] (steps=359)
- baseline[good=above]: P(toward_bad | on good side) = 0.525 [0.50, 0.55] (steps=444)
- baseline[good=below]: P(toward_good | on bad side) = 0.525 [0.50, 0.55] (steps=444)
- baseline[good=below]: P(toward_bad | on good side) = 0.501 [0.47, 0.53] (steps=359)
- below_good: P(toward_good | on bad side) = 0.604 [0.57, 0.64] (steps=510)
- below_good: P(toward_bad | on good side) = 0.563 [0.51, 0.63] (steps=318)
- above_good: asymmetry: P(toward good|bad) - P(toward bad|good) = -0.009
- baseline[good=above]: asymmetry: P(toward good|bad) - P(toward bad|good) = -0.023
- baseline[good=below]: asymmetry: P(toward good|bad) - P(toward bad|good) = 0.023
- below_good: asymmetry: P(toward good|bad) - P(toward bad|good) = 0.041

## T3 stopping hazard

- above_good / good: hazard P(stop | side) = 0.105 [0.09, 0.13] (steps=505)
- above_good / good: hazard P(stop | side), K>=2 = 0.085 (steps=494)
- above_good / bad: hazard P(stop | side) = 0.087 [0.07, 0.11] (steps=503)
- above_good / bad: hazard P(stop | side), K>=2 = 0.073 (steps=495)
- baseline[good=above] / good: hazard P(stop | side) = 0.101 [0.08, 0.12] (steps=494)
- baseline[good=above] / good: hazard P(stop | side), K>=2 = 0.086 (steps=486)
- baseline[good=above] / bad: hazard P(stop | side) = 0.105 [0.09, 0.12] (steps=401)
- baseline[good=above] / bad: hazard P(stop | side), K>=2 = 0.098 (steps=398)
- baseline[good=below] / good: hazard P(stop | side) = 0.105 [0.09, 0.12] (steps=401)
- baseline[good=below] / good: hazard P(stop | side), K>=2 = 0.098 (steps=398)
- baseline[good=below] / bad: hazard P(stop | side) = 0.101 [0.08, 0.12] (steps=494)
- baseline[good=below] / bad: hazard P(stop | side), K>=2 = 0.086 (steps=486)
- below_good / good: hazard P(stop | side) = 0.131 [0.10, 0.17] (steps=366)
- below_good / good: hazard P(stop | side), K>=2 = 0.097 (steps=352)
- below_good / bad: hazard P(stop | side) = 0.081 [0.07, 0.10] (steps=555)
- below_good / bad: hazard P(stop | side), K>=2 = 0.071 (steps=549)
- above_good / both: hazard(good) - hazard(bad) = 0.017
- above_good / both: hazard ratio good/bad = 1.200
- baseline[good=above] / both: hazard(good) - hazard(bad) = -0.004
- baseline[good=above] / both: hazard ratio good/bad = 0.966
- baseline[good=below] / both: hazard(good) - hazard(bad) = 0.004
- baseline[good=below] / both: hazard ratio good/bad = 1.035
- below_good / both: hazard(good) - hazard(bad) = 0.050
- below_good / both: hazard ratio good/bad = 1.617
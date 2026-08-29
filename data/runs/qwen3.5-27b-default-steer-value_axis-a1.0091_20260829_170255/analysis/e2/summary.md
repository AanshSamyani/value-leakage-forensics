# E2 — qwen3.5-27b-steer-value_axis-a1.0091 (qwen3.5-27b-default-steer-value_axis-a1.0091_20260829_170255)

threshold = 104,475,000; length column = tokens

## T1 start shift

- P(first > T) [baseline]: 0.361 [0.260, 0.476] (n=72)
- P(first > T) [above_good]: 0.594 [0.494, 0.687] (n=96)
- P(first > T) [below_good]: 0.330 [0.243, 0.430] (n=94)
- P(first>T|above_good) - P(first>T|below_good) [diff]: 0.264 [0.117, 0.392] (n=190)
- P(first>T|above_good) - P(first>T|baseline) [diff_vs_base]: 0.233 [0.090, 0.372] (n=168)
- P(first>T|baseline) - P(first>T|below_good) [diff_vs_base]: 0.031 [-0.113, 0.178] (n=166)
- P(first on favoured side) [pooled]: 0.632 [0.561, 0.697] (n=190)

## T2 length by first side (interaction = Δ_incentive − Δ_baseline, Δ = bad − good)

- above_good / incentive / first=bad: mean=9473 median=9458 (n=39.0)
- above_good / incentive / first=good: mean=8945 median=8768 (n=57.0)
- above_good / baseline / first=bad: mean=7628 median=7705 (n=46.0)
- above_good / baseline / first=good: mean=7565 median=7442 (n=26.0)
- below_good / incentive / first=bad: mean=10162 median=10317 (n=31.0)
- below_good / incentive / first=good: mean=8014 median=8063 (n=63.0)
- below_good / baseline / first=bad: mean=7565 median=7442 (n=26.0)
- below_good / baseline / first=good: mean=7628 median=7705 (n=46.0)
- INTERACTION above_good [logL]: Δinc=+0.063 Δbase=+0.010 interaction=+0.053 [-0.047, +0.156]
- INTERACTION above_good [tokens]: Δinc=+528.217 Δbase=+62.229 interaction=+465.988 [-375.248, +1315.713]
- INTERACTION below_good [logL]: Δinc=+0.238 Δbase=-0.010 interaction=+0.248 [+0.141, +0.359]
- INTERACTION below_good [tokens]: Δinc=+2147.906 Δbase=-62.229 interaction=+2210.135 [+1312.840, +3105.050]

## T3 transitions

- above_good: P(toward_good | on bad side) = 0.768 [0.71, 0.87] (steps=177)
- above_good: P(toward_bad | on good side) = 0.561 [0.52, 0.61] (steps=294)
- baseline[good=above]: P(toward_good | on bad side) = 0.536 [0.50, 0.57] (steps=539)
- baseline[good=above]: P(toward_bad | on good side) = 0.475 [0.42, 0.53] (steps=236)
- baseline[good=below]: P(toward_good | on bad side) = 0.475 [0.42, 0.53] (steps=236)
- baseline[good=below]: P(toward_bad | on good side) = 0.536 [0.50, 0.57] (steps=539)
- below_good: P(toward_good | on bad side) = 0.819 [0.76, 0.87] (steps=204)
- below_good: P(toward_bad | on good side) = 0.589 [0.55, 0.63] (steps=545)
- above_good: asymmetry: P(toward good|bad) - P(toward bad|good) = 0.207
- baseline[good=above]: asymmetry: P(toward good|bad) - P(toward bad|good) = 0.062
- baseline[good=below]: asymmetry: P(toward good|bad) - P(toward bad|good) = -0.062
- below_good: asymmetry: P(toward good|bad) - P(toward bad|good) = 0.230

## T3 stopping hazard

- above_good / good: hazard P(stop | side) = 0.218 [0.18, 0.28] (steps=376)
- above_good / good: hazard P(stop | side), K>=2 = 0.169 (steps=354)
- above_good / bad: hazard P(stop | side) = 0.073 [0.04, 0.11] (steps=191)
- above_good / bad: hazard P(stop | side), K>=2 = 0.059 (steps=188)
- baseline[good=above] / good: hazard P(stop | side) = 0.106 [0.08, 0.14] (steps=264)
- baseline[good=above] / good: hazard P(stop | side), K>=2 = 0.089 (steps=259)
- baseline[good=above] / bad: hazard P(stop | side) = 0.075 [0.06, 0.10] (steps=583)
- baseline[good=above] / bad: hazard P(stop | side), K>=2 = 0.059 (steps=573)
- baseline[good=below] / good: hazard P(stop | side) = 0.075 [0.06, 0.10] (steps=583)
- baseline[good=below] / good: hazard P(stop | side), K>=2 = 0.059 (steps=573)
- baseline[good=below] / bad: hazard P(stop | side) = 0.106 [0.08, 0.14] (steps=264)
- baseline[good=below] / bad: hazard P(stop | side), K>=2 = 0.089 (steps=259)
- below_good / good: hazard P(stop | side) = 0.134 [0.11, 0.17] (steps=629)
- below_good / good: hazard P(stop | side), K>=2 = 0.104 (steps=608)
- below_good / bad: hazard P(stop | side) = 0.047 [0.02, 0.07] (steps=214)
- below_good / bad: hazard P(stop | side), K>=2 = 0.042 (steps=213)
- above_good / both: hazard(good) - hazard(bad) = 0.145
- above_good / both: hazard ratio good/bad = 2.975
- baseline[good=above] / both: hazard(good) - hazard(bad) = 0.031
- baseline[good=above] / both: hazard ratio good/bad = 1.405
- baseline[good=below] / both: hazard(good) - hazard(bad) = -0.031
- baseline[good=below] / both: hazard ratio good/bad = 0.712
- below_good / both: hazard(good) - hazard(bad) = 0.087
- below_good / both: hazard ratio good/bad = 2.858
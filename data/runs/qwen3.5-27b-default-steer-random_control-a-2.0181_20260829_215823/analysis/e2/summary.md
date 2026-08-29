# E2 — qwen3.5-27b-steer-random_control-a-2.0181 (qwen3.5-27b-default-steer-random_control-a-2.0181_20260829_215823)

threshold = 104,475,000; length column = tokens

## T1 start shift

- P(first > T) [baseline]: 0.298 [0.210, 0.402] (n=84)
- P(first > T) [above_good]: 0.462 [0.363, 0.563] (n=91)
- P(first > T) [below_good]: 0.231 [0.156, 0.327] (n=91)
- P(first>T|above_good) - P(first>T|below_good) [diff]: 0.231 [0.088, 0.363] (n=182)
- P(first>T|above_good) - P(first>T|baseline) [diff_vs_base]: 0.164 [0.027, 0.310] (n=175)
- P(first>T|baseline) - P(first>T|below_good) [diff_vs_base]: 0.067 [-0.071, 0.203] (n=175)
- P(first on favoured side) [pooled]: 0.615 [0.543, 0.683] (n=182)

## T2 length by first side (interaction = Δ_incentive − Δ_baseline, Δ = bad − good)

- above_good / incentive / first=bad: mean=8323 median=8254 (n=49.0)
- above_good / incentive / first=good: mean=8115 median=8054 (n=42.0)
- above_good / baseline / first=bad: mean=6757 median=6904 (n=59.0)
- above_good / baseline / first=good: mean=6984 median=6572 (n=25.0)
- below_good / incentive / first=bad: mean=9084 median=9150 (n=21.0)
- below_good / incentive / first=good: mean=7927 median=7962 (n=70.0)
- below_good / baseline / first=bad: mean=6984 median=6572 (n=25.0)
- below_good / baseline / first=good: mean=6757 median=6904 (n=59.0)
- INTERACTION above_good [logL]: Δinc=+0.008 Δbase=-0.020 interaction=+0.028 [-0.089, +0.146]
- INTERACTION above_good [tokens]: Δinc=+207.575 Δbase=-226.622 interaction=+434.197 [-445.899, +1352.181]
- INTERACTION below_good [logL]: Δinc=+0.142 Δbase=+0.020 interaction=+0.122 [-0.003, +0.241]
- INTERACTION below_good [tokens]: Δinc=+1157.562 Δbase=+226.622 interaction=+930.940 [-21.210, +1868.501]

## T3 transitions

- above_good: P(toward_good | on bad side) = 0.668 [0.63, 0.72] (steps=404)
- above_good: P(toward_bad | on good side) = 0.592 [0.54, 0.65] (steps=395)
- baseline[good=above]: P(toward_good | on bad side) = 0.508 [0.48, 0.54] (steps=785)
- baseline[good=above]: P(toward_bad | on good side) = 0.513 [0.47, 0.57] (steps=353)
- baseline[good=below]: P(toward_good | on bad side) = 0.513 [0.47, 0.57] (steps=353)
- baseline[good=below]: P(toward_bad | on good side) = 0.508 [0.48, 0.54] (steps=785)
- below_good: P(toward_good | on bad side) = 0.687 [0.64, 0.75] (steps=182)
- below_good: P(toward_bad | on good side) = 0.601 [0.57, 0.63] (steps=591)
- above_good: asymmetry: P(toward good|bad) - P(toward bad|good) = 0.076
- baseline[good=above]: asymmetry: P(toward good|bad) - P(toward bad|good) = -0.004
- baseline[good=below]: asymmetry: P(toward good|bad) - P(toward bad|good) = 0.004
- below_good: asymmetry: P(toward good|bad) - P(toward bad|good) = 0.086

## T3 stopping hazard

- above_good / good: hazard P(stop | side) = 0.141 [0.12, 0.18] (steps=460)
- above_good / good: hazard P(stop | side), K>=2 = 0.114 (steps=446)
- above_good / bad: hazard P(stop | side) = 0.060 [0.05, 0.08] (steps=430)
- above_good / bad: hazard P(stop | side), K>=2 = 0.056 (steps=428)
- baseline[good=above] / good: hazard P(stop | side) = 0.076 [0.06, 0.10] (steps=382)
- baseline[good=above] / good: hazard P(stop | side), K>=2 = 0.071 (steps=380)
- baseline[good=above] / bad: hazard P(stop | side) = 0.065 [0.05, 0.08] (steps=840)
- baseline[good=above] / bad: hazard P(stop | side), K>=2 = 0.058 (steps=833)
- baseline[good=below] / good: hazard P(stop | side) = 0.065 [0.05, 0.08] (steps=840)
- baseline[good=below] / good: hazard P(stop | side), K>=2 = 0.058 (steps=833)
- baseline[good=below] / bad: hazard P(stop | side) = 0.076 [0.06, 0.10] (steps=382)
- baseline[good=below] / bad: hazard P(stop | side), K>=2 = 0.071 (steps=380)
- below_good / good: hazard P(stop | side) = 0.115 [0.09, 0.14] (steps=668)
- below_good / good: hazard P(stop | side), K>=2 = 0.079 (steps=642)
- below_good / bad: hazard P(stop | side) = 0.071 [0.05, 0.10] (steps=196)
- below_good / bad: hazard P(stop | side), K>=2 = 0.057 (steps=193)
- above_good / both: hazard(good) - hazard(bad) = 0.081
- above_good / both: hazard ratio good/bad = 2.337
- baseline[good=above] / both: hazard(good) - hazard(bad) = 0.010
- baseline[good=above] / both: hazard ratio good/bad = 1.159
- baseline[good=below] / both: hazard(good) - hazard(bad) = -0.010
- baseline[good=below] / both: hazard ratio good/bad = 0.862
- below_good / both: hazard(good) - hazard(bad) = 0.044
- below_good / both: hazard ratio good/bad = 1.614
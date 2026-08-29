# E2 — qwen3.5-27b-steer-value_axis-a2.0181 (qwen3.5-27b-default-steer-value_axis-a2.0181_20260829_205854)

threshold = 104,475,000; length column = tokens

## T1 start shift

- P(first > T) [baseline]: 0.273 [0.186, 0.381] (n=77)
- P(first > T) [above_good]: 0.380 [0.288, 0.483] (n=92)
- P(first > T) [below_good]: 0.136 [0.080, 0.223] (n=88)
- P(first>T|above_good) - P(first>T|below_good) [diff]: 0.244 [0.122, 0.365] (n=180)
- P(first>T|above_good) - P(first>T|baseline) [diff_vs_base]: 0.108 [-0.031, 0.248] (n=169)
- P(first>T|baseline) - P(first>T|below_good) [diff_vs_base]: 0.136 [0.010, 0.253] (n=165)
- P(first on favoured side) [pooled]: 0.617 [0.544, 0.685] (n=180)

## T2 length by first side (interaction = Δ_incentive − Δ_baseline, Δ = bad − good)

- above_good / incentive / first=bad: mean=8290 median=8301 (n=57.0)
- above_good / incentive / first=good: mean=7911 median=7825 (n=35.0)
- above_good / baseline / first=bad: mean=6317 median=6258 (n=56.0)
- above_good / baseline / first=good: mean=6784 median=6385 (n=21.0)
- below_good / incentive / first=bad: mean=10222 median=7678 (n=12.0)
- below_good / incentive / first=good: mean=7041 median=6962 (n=76.0)
- below_good / baseline / first=bad: mean=6784 median=6385 (n=21.0)
- below_good / baseline / first=good: mean=6317 median=6258 (n=56.0)
- INTERACTION above_good [logL]: Δinc=+0.019 Δbase=-0.068 interaction=+0.087 [-0.035, +0.215]
- INTERACTION above_good [tokens]: Δinc=+378.968 Δbase=-467.321 interaction=+846.289 [+45.400, +1738.908]
- INTERACTION below_good [logL]: Δinc=+0.305 Δbase=+0.068 interaction=+0.237 [+0.011, +0.512]
- INTERACTION below_good [tokens]: Δinc=+3181.711 Δbase=+467.321 interaction=+2714.389 [+7.714, +6989.214]

## T3 transitions

- above_good: P(toward_good | on bad side) = 0.777 [0.73, 0.83] (steps=431)
- above_good: P(toward_bad | on good side) = 0.594 [0.56, 0.64] (steps=313)
- baseline[good=above]: P(toward_good | on bad side) = 0.502 [0.48, 0.53] (steps=821)
- baseline[good=above]: P(toward_bad | on good side) = 0.498 [0.45, 0.55] (steps=203)
- baseline[good=below]: P(toward_good | on bad side) = 0.498 [0.45, 0.55] (steps=203)
- baseline[good=below]: P(toward_bad | on good side) = 0.502 [0.48, 0.53] (steps=821)
- below_good: P(toward_good | on bad side) = 0.859 [0.80, 0.93] (steps=92)
- below_good: P(toward_bad | on good side) = 0.619 [0.59, 0.65] (steps=649)
- above_good: asymmetry: P(toward good|bad) - P(toward bad|good) = 0.183
- baseline[good=above]: asymmetry: P(toward good|bad) - P(toward bad|good) = 0.004
- baseline[good=below]: asymmetry: P(toward good|bad) - P(toward bad|good) = -0.004
- below_good: asymmetry: P(toward good|bad) - P(toward bad|good) = 0.239

## T3 stopping hazard

- above_good / good: hazard P(stop | side) = 0.206 [0.16, 0.27] (steps=394)
- above_good / good: hazard P(stop | side), K>=2 = 0.168 (steps=376)
- above_good / bad: hazard P(stop | side) = 0.025 [0.01, 0.04] (steps=442)
- above_good / bad: hazard P(stop | side), K>=2 = 0.023 (steps=441)
- baseline[good=above] / good: hazard P(stop | side) = 0.081 [0.06, 0.11] (steps=221)
- baseline[good=above] / good: hazard P(stop | side), K>=2 = 0.081 (steps=221)
- baseline[good=above] / bad: hazard P(stop | side) = 0.067 [0.06, 0.08] (steps=880)
- baseline[good=above] / bad: hazard P(stop | side), K>=2 = 0.065 (steps=878)
- baseline[good=below] / good: hazard P(stop | side) = 0.067 [0.06, 0.08] (steps=880)
- baseline[good=below] / good: hazard P(stop | side), K>=2 = 0.065 (steps=878)
- baseline[good=below] / bad: hazard P(stop | side) = 0.081 [0.06, 0.11] (steps=221)
- baseline[good=below] / bad: hazard P(stop | side), K>=2 = 0.081 (steps=221)
- below_good / good: hazard P(stop | side) = 0.116 [0.10, 0.14] (steps=734)
- below_good / good: hazard P(stop | side), K>=2 = 0.095 (steps=717)
- below_good / bad: hazard P(stop | side) = 0.032 [0.00, 0.06] (steps=95)
- below_good / bad: hazard P(stop | side), K>=2 = 0.032 (steps=95)
- above_good / both: hazard(good) - hazard(bad) = 0.181
- above_good / both: hazard ratio good/bad = 8.261
- baseline[good=above] / both: hazard(good) - hazard(bad) = 0.014
- baseline[good=above] / both: hazard ratio good/bad = 1.215
- baseline[good=below] / both: hazard(good) - hazard(bad) = -0.014
- baseline[good=below] / both: hazard ratio good/bad = 0.823
- below_good / both: hazard(good) - hazard(bad) = 0.084
- below_good / both: hazard ratio good/bad = 3.667
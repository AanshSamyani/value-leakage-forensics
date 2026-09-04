# E2 — qwen3.5-27b-steer-persona_sycophantic-a0.4964 (qwen3.5-27b-default-steer-persona_sycophantic-a0.4964_20260904_185235)

threshold = 104,475,000; length column = tokens

## T1 start shift

- P(first > T) [baseline]: 0.562 [0.453, 0.666] (n=80)
- P(first > T) [above_good]: 0.798 [0.706, 0.867] (n=94)
- P(first > T) [below_good]: 0.355 [0.265, 0.456] (n=93)
- P(first>T|above_good) - P(first>T|below_good) [diff]: 0.443 [0.314, 0.571] (n=187)
- P(first>T|above_good) - P(first>T|baseline) [diff_vs_base]: 0.235 [0.099, 0.371] (n=174)
- P(first>T|baseline) - P(first>T|below_good) [diff_vs_base]: 0.208 [0.059, 0.354] (n=173)
- P(first on favoured side) [pooled]: 0.722 [0.654, 0.781] (n=187)

## T2 length by first side (interaction = Δ_incentive − Δ_baseline, Δ = bad − good)

- above_good / incentive / first=bad: mean=9610 median=9491 (n=19.0)
- above_good / incentive / first=good: mean=9369 median=9231 (n=75.0)
- above_good / baseline / first=bad: mean=7486 median=7576 (n=35.0)
- above_good / baseline / first=good: mean=7858 median=7767 (n=45.0)
- below_good / incentive / first=bad: mean=10883 median=10350 (n=33.0)
- below_good / incentive / first=good: mean=8709 median=8624 (n=60.0)
- below_good / baseline / first=bad: mean=7858 median=7767 (n=45.0)
- below_good / baseline / first=good: mean=7486 median=7576 (n=35.0)
- INTERACTION above_good [logL]: Δinc=+0.022 Δbase=-0.051 interaction=+0.073 [-0.055, +0.197]
- INTERACTION above_good [tokens]: Δinc=+240.549 Δbase=-371.479 interaction=+612.028 [-497.096, +1689.381]
- INTERACTION below_good [logL]: Δinc=+0.209 Δbase=+0.051 interaction=+0.159 [+0.028, +0.304]
- INTERACTION below_good [tokens]: Δinc=+2173.594 Δbase=+371.479 interaction=+1802.115 [+381.507, +3580.884]

## T3 transitions

- above_good: P(toward_good | on bad side) = 0.711 [0.61, 0.85] (steps=90)
- above_good: P(toward_bad | on good side) = 0.507 [0.47, 0.55] (steps=276)
- baseline[good=above]: P(toward_good | on bad side) = 0.589 [0.53, 0.67] (steps=304)
- baseline[good=above]: P(toward_bad | on good side) = 0.497 [0.45, 0.54] (steps=354)
- baseline[good=below]: P(toward_good | on bad side) = 0.497 [0.45, 0.54] (steps=354)
- baseline[good=below]: P(toward_bad | on good side) = 0.589 [0.53, 0.67] (steps=304)
- below_good: P(toward_good | on bad side) = 0.679 [0.62, 0.76] (steps=159)
- below_good: P(toward_bad | on good side) = 0.578 [0.53, 0.63] (steps=287)
- above_good: asymmetry: P(toward good|bad) - P(toward bad|good) = 0.204
- baseline[good=above]: asymmetry: P(toward good|bad) - P(toward bad|good) = 0.092
- baseline[good=below]: asymmetry: P(toward good|bad) - P(toward bad|good) = -0.092
- below_good: asymmetry: P(toward good|bad) - P(toward bad|good) = 0.101

## T3 stopping hazard

- above_good / good: hazard P(stop | side) = 0.244 [0.18, 0.34] (steps=365)
- above_good / good: hazard P(stop | side), K>=2 = 0.143 (steps=322)
- above_good / bad: hazard P(stop | side) = 0.053 [0.02, 0.09] (steps=95)
- above_good / bad: hazard P(stop | side), K>=2 = 0.043 (steps=94)
- baseline[good=above] / good: hazard P(stop | side) = 0.119 [0.10, 0.15] (steps=402)
- baseline[good=above] / good: hazard P(stop | side), K>=2 = 0.097 (steps=392)
- baseline[good=above] / bad: hazard P(stop | side) = 0.095 [0.07, 0.14] (steps=336)
- baseline[good=above] / bad: hazard P(stop | side), K>=2 = 0.079 (steps=330)
- baseline[good=below] / good: hazard P(stop | side) = 0.095 [0.07, 0.14] (steps=336)
- baseline[good=below] / good: hazard P(stop | side), K>=2 = 0.079 (steps=330)
- baseline[good=below] / bad: hazard P(stop | side) = 0.119 [0.10, 0.15] (steps=402)
- baseline[good=below] / bad: hazard P(stop | side), K>=2 = 0.097 (steps=392)
- below_good / good: hazard P(stop | side) = 0.185 [0.14, 0.27] (steps=352)
- below_good / good: hazard P(stop | side), K>=2 = 0.106 (steps=321)
- below_good / bad: hazard P(stop | side) = 0.150 [0.10, 0.23] (steps=187)
- below_good / bad: hazard P(stop | side), K>=2 = 0.091 (steps=175)
- above_good / both: hazard(good) - hazard(bad) = 0.191
- above_good / both: hazard ratio good/bad = 4.633
- baseline[good=above] / both: hazard(good) - hazard(bad) = 0.024
- baseline[good=above] / both: hazard ratio good/bad = 1.254
- baseline[good=below] / both: hazard(good) - hazard(bad) = -0.024
- baseline[good=below] / both: hazard ratio good/bad = 0.798
- below_good / both: hazard(good) - hazard(bad) = 0.035
- below_good / both: hazard ratio good/bad = 1.233
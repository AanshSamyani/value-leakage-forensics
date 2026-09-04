# E2 — qwen3.5-27b-steer-persona_sycophantic-a-0.4964 (qwen3.5-27b-default-steer-persona_sycophantic-a-0.4964_20260904_174924)

threshold = 104,475,000; length column = tokens

## T1 start shift

- P(first > T) [baseline]: 0.529 [0.412, 0.643] (n=68)
- P(first > T) [above_good]: 0.632 [0.527, 0.726] (n=87)
- P(first > T) [below_good]: 0.385 [0.291, 0.487] (n=91)
- P(first>T|above_good) - P(first>T|below_good) [diff]: 0.248 [0.100, 0.382] (n=178)
- P(first>T|above_good) - P(first>T|baseline) [diff_vs_base]: 0.103 [-0.061, 0.252] (n=155)
- P(first>T|baseline) - P(first>T|below_good) [diff_vs_base]: 0.145 [-0.013, 0.295] (n=159)
- P(first on favoured side) [pooled]: 0.624 [0.551, 0.691] (n=178)

## T2 length by first side (interaction = Δ_incentive − Δ_baseline, Δ = bad − good)

- above_good / incentive / first=bad: mean=11759 median=11918 (n=32.0)
- above_good / incentive / first=good: mean=11256 median=11826 (n=55.0)
- above_good / baseline / first=bad: mean=8907 median=8838 (n=32.0)
- above_good / baseline / first=good: mean=9394 median=9304 (n=36.0)
- below_good / incentive / first=bad: mean=12013 median=12367 (n=35.0)
- below_good / incentive / first=good: mean=10814 median=10480 (n=56.0)
- below_good / baseline / first=bad: mean=9394 median=9304 (n=36.0)
- below_good / baseline / first=good: mean=8907 median=8838 (n=32.0)
- INTERACTION above_good [logL]: Δinc=+0.042 Δbase=-0.063 interaction=+0.105 [-0.075, +0.270]
- INTERACTION above_good [tokens]: Δinc=+503.214 Δbase=-486.566 interaction=+989.780 [-561.007, +2410.584]
- INTERACTION below_good [logL]: Δinc=+0.098 Δbase=+0.063 interaction=+0.036 [-0.140, +0.204]
- INTERACTION below_good [tokens]: Δinc=+1199.546 Δbase=+486.566 interaction=+712.980 [-876.160, +2269.330]

## T3 transitions

- above_good: P(toward_good | on bad side) = 0.696 [0.65, 0.75] (steps=289)
- above_good: P(toward_bad | on good side) = 0.538 [0.50, 0.59] (steps=463)
- baseline[good=above]: P(toward_good | on bad side) = 0.513 [0.48, 0.54] (steps=548)
- baseline[good=above]: P(toward_bad | on good side) = 0.499 [0.47, 0.53] (steps=810)
- baseline[good=below]: P(toward_good | on bad side) = 0.499 [0.47, 0.53] (steps=810)
- baseline[good=below]: P(toward_bad | on good side) = 0.513 [0.48, 0.54] (steps=548)
- below_good: P(toward_good | on bad side) = 0.695 [0.64, 0.75] (steps=370)
- below_good: P(toward_bad | on good side) = 0.604 [0.57, 0.64] (steps=756)
- above_good: asymmetry: P(toward good|bad) - P(toward bad|good) = 0.158
- baseline[good=above]: asymmetry: P(toward good|bad) - P(toward bad|good) = 0.014
- baseline[good=below]: asymmetry: P(toward good|bad) - P(toward bad|good) = -0.014
- below_good: asymmetry: P(toward good|bad) - P(toward bad|good) = 0.090

## T3 stopping hazard

- above_good / good: hazard P(stop | side) = 0.130 [0.10, 0.17] (steps=532)
- above_good / good: hazard P(stop | side), K>=2 = 0.097 (steps=513)
- above_good / bad: hazard P(stop | side) = 0.059 [0.04, 0.08] (steps=307)
- above_good / bad: hazard P(stop | side), K>=2 = 0.043 (steps=302)
- baseline[good=above] / good: hazard P(stop | side) = 0.050 [0.04, 0.06] (steps=853)
- baseline[good=above] / good: hazard P(stop | side), K>=2 = 0.046 (steps=849)
- baseline[good=above] / bad: hazard P(stop | side) = 0.044 [0.04, 0.06] (steps=573)
- baseline[good=above] / bad: hazard P(stop | side), K>=2 = 0.040 (steps=571)
- baseline[good=below] / good: hazard P(stop | side) = 0.044 [0.04, 0.06] (steps=573)
- baseline[good=below] / good: hazard P(stop | side), K>=2 = 0.040 (steps=571)
- baseline[good=below] / bad: hazard P(stop | side) = 0.050 [0.04, 0.06] (steps=853)
- baseline[good=below] / bad: hazard P(stop | side), K>=2 = 0.046 (steps=849)
- below_good / good: hazard P(stop | side) = 0.083 [0.07, 0.11] (steps=824)
- below_good / good: hazard P(stop | side), K>=2 = 0.070 (steps=813)
- below_good / bad: hazard P(stop | side) = 0.059 [0.04, 0.08] (steps=393)
- below_good / bad: hazard P(stop | side), K>=2 = 0.054 (steps=391)
- above_good / both: hazard(good) - hazard(bad) = 0.071
- above_good / both: hazard ratio good/bad = 2.212
- baseline[good=above] / both: hazard(good) - hazard(bad) = 0.007
- baseline[good=above] / both: hazard ratio good/bad = 1.155
- baseline[good=below] / both: hazard(good) - hazard(bad) = -0.007
- baseline[good=below] / both: hazard ratio good/bad = 0.865
- below_good / both: hazard(good) - hazard(bad) = 0.024
- below_good / both: hazard ratio good/bad = 1.410
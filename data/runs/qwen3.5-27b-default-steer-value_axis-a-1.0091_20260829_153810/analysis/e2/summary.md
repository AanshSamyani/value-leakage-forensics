# E2 — qwen3.5-27b-steer-value_axis-a-1.0091 (qwen3.5-27b-default-steer-value_axis-a-1.0091_20260829_153810)

threshold = 104,475,000; length column = tokens

## T1 start shift

- P(first > T) [baseline]: 0.667 [0.530, 0.780] (n=51)
- P(first > T) [above_good]: 0.728 [0.623, 0.813] (n=81)
- P(first > T) [below_good]: 0.375 [0.281, 0.479] (n=88)
- P(first>T|above_good) - P(first>T|below_good) [diff]: 0.353 [0.222, 0.502] (n=169)
- P(first>T|above_good) - P(first>T|baseline) [diff_vs_base]: 0.062 [-0.093, 0.224] (n=132)
- P(first>T|baseline) - P(first>T|below_good) [diff_vs_base]: 0.292 [0.125, 0.449] (n=139)
- P(first on favoured side) [pooled]: 0.675 [0.601, 0.741] (n=169)

## T2 length by first side (interaction = Δ_incentive − Δ_baseline, Δ = bad − good)

- above_good / incentive / first=bad: mean=14494 median=14466 (n=22.0)
- above_good / incentive / first=good: mean=13117 median=12482 (n=59.0)
- above_good / baseline / first=bad: mean=11178 median=11076 (n=17.0)
- above_good / baseline / first=good: mean=11459 median=10934 (n=34.0)
- below_good / incentive / first=bad: mean=14479 median=13240 (n=33.0)
- below_good / incentive / first=good: mean=13772 median=12811 (n=55.0)
- below_good / baseline / first=bad: mean=11459 median=10934 (n=34.0)
- below_good / baseline / first=good: mean=11178 median=11076 (n=17.0)
- INTERACTION above_good [logL]: Δinc=+0.019 Δbase=-0.025 interaction=+0.044 [-0.231, +0.284]
- INTERACTION above_good [tokens]: Δinc=+1377.050 Δbase=-281.382 interaction=+1658.432 [-1036.680, +4349.795]
- INTERACTION below_good [logL]: Δinc=+0.048 Δbase=+0.025 interaction=+0.023 [-0.141, +0.182]
- INTERACTION below_good [tokens]: Δinc=+706.388 Δbase=+281.382 interaction=+425.006 [-1801.120, +2661.970]

## T3 transitions

- above_good: P(toward_good | on bad side) = 0.718 [0.64, 0.87] (steps=220)
- above_good: P(toward_bad | on good side) = 0.517 [0.49, 0.55] (steps=784)
- baseline[good=above]: P(toward_good | on bad side) = 0.507 [0.46, 0.56] (steps=381)
- baseline[good=above]: P(toward_bad | on good side) = 0.495 [0.46, 0.54] (steps=568)
- baseline[good=below]: P(toward_good | on bad side) = 0.495 [0.46, 0.54] (steps=568)
- baseline[good=below]: P(toward_bad | on good side) = 0.507 [0.46, 0.56] (steps=381)
- below_good: P(toward_good | on bad side) = 0.587 [0.52, 0.67] (steps=332)
- below_good: P(toward_bad | on good side) = 0.562 [0.54, 0.59] (steps=628)
- above_good: asymmetry: P(toward good|bad) - P(toward bad|good) = 0.202
- baseline[good=above]: asymmetry: P(toward good|bad) - P(toward bad|good) = 0.012
- baseline[good=below]: asymmetry: P(toward good|bad) - P(toward bad|good) = -0.012
- below_good: asymmetry: P(toward good|bad) - P(toward bad|good) = 0.025

## T3 stopping hazard

- above_good / good: hazard P(stop | side) = 0.082 [0.06, 0.12] (steps=854)
- above_good / good: hazard P(stop | side), K>=2 = 0.058 (steps=832)
- above_good / bad: hazard P(stop | side) = 0.048 [0.03, 0.08] (steps=231)
- above_good / bad: hazard P(stop | side), K>=2 = 0.035 (steps=228)
- baseline[good=above] / good: hazard P(stop | side) = 0.060 [0.04, 0.09] (steps=604)
- baseline[good=above] / good: hazard P(stop | side), K>=2 = 0.053 (steps=600)
- baseline[good=above] / bad: hazard P(stop | side) = 0.038 [0.03, 0.06] (steps=396)
- baseline[good=above] / bad: hazard P(stop | side), K>=2 = 0.038 (steps=396)
- baseline[good=below] / good: hazard P(stop | side) = 0.038 [0.03, 0.06] (steps=396)
- baseline[good=below] / good: hazard P(stop | side), K>=2 = 0.038 (steps=396)
- baseline[good=below] / bad: hazard P(stop | side) = 0.060 [0.04, 0.09] (steps=604)
- baseline[good=below] / bad: hazard P(stop | side), K>=2 = 0.053 (steps=600)
- below_good / good: hazard P(stop | side) = 0.081 [0.06, 0.11] (steps=683)
- below_good / good: hazard P(stop | side), K>=2 = 0.053 (steps=663)
- below_good / bad: hazard P(stop | side) = 0.090 [0.07, 0.13] (steps=365)
- below_good / bad: hazard P(stop | side), K>=2 = 0.078 (steps=360)
- above_good / both: hazard(good) - hazard(bad) = 0.034
- above_good / both: hazard ratio good/bad = 1.721
- baseline[good=above] / both: hazard(good) - hazard(bad) = 0.022
- baseline[good=above] / both: hazard ratio good/bad = 1.574
- baseline[good=below] / both: hazard(good) - hazard(bad) = -0.022
- baseline[good=below] / both: hazard ratio good/bad = 0.636
- below_good / both: hazard(good) - hazard(bad) = -0.010
- below_good / both: hazard ratio good/bad = 0.891
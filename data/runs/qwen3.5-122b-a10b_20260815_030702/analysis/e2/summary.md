# E2 — qwen3.5-122b-a10b (qwen3.5-122b-a10b_20260815_030702)

threshold = 41,000,000; length column = tokens

## T1 start shift

- P(first > T) [baseline]: 0.526 [0.427, 0.624] (n=95)
- P(first > T) [above_good]: 0.670 [0.572, 0.756] (n=97)
- P(first > T) [below_good]: 0.505 [0.406, 0.605] (n=93)
- P(first>T|above_good) - P(first>T|below_good) [diff]: 0.165 [0.026, 0.292] (n=190)
- P(first>T|above_good) - P(first>T|baseline) [diff_vs_base]: 0.144 [0.008, 0.279] (n=192)
- P(first>T|baseline) - P(first>T|below_good) [diff_vs_base]: 0.021 [-0.117, 0.160] (n=188)
- P(first on favoured side) [pooled]: 0.584 [0.513, 0.652] (n=190)

## T2 length by first side (interaction = Δ_incentive − Δ_baseline, Δ = bad − good)

- above_good / incentive / first=bad: mean=9621 median=9294 (n=32.0)
- above_good / incentive / first=good: mean=8896 median=8793 (n=65.0)
- above_good / baseline / first=bad: mean=7319 median=7436 (n=45.0)
- above_good / baseline / first=good: mean=7424 median=7029 (n=50.0)
- below_good / incentive / first=bad: mean=9618 median=9675 (n=47.0)
- below_good / incentive / first=good: mean=8425 median=8332 (n=46.0)
- below_good / baseline / first=bad: mean=7424 median=7029 (n=50.0)
- below_good / baseline / first=good: mean=7319 median=7436 (n=45.0)
- INTERACTION above_good [logL]: Δinc=+0.076 Δbase=-0.046 interaction=+0.121 [-0.005, +0.277]
- INTERACTION above_good [tokens]: Δinc=+725.138 Δbase=-105.076 interaction=+830.214 [-27.772, +1735.958]
- INTERACTION below_good [logL]: Δinc=+0.124 Δbase=+0.046 interaction=+0.079 [-0.070, +0.215]
- INTERACTION below_good [tokens]: Δinc=+1193.604 Δbase=+105.076 interaction=+1088.529 [+149.487, +1969.979]

## T3 transitions

- above_good: P(toward_good | on bad side) = 0.709 [0.66, 0.75] (steps=817)
- above_good: P(toward_bad | on good side) = 0.606 [0.58, 0.64] (steps=1364)
- baseline[good=above]: P(toward_good | on bad side) = 0.557 [0.53, 0.58] (steps=1200)
- baseline[good=above]: P(toward_bad | on good side) = 0.521 [0.50, 0.55] (steps=1048)
- baseline[good=below]: P(toward_good | on bad side) = 0.521 [0.50, 0.55] (steps=1048)
- baseline[good=below]: P(toward_bad | on good side) = 0.557 [0.53, 0.58] (steps=1200)
- below_good: P(toward_good | on bad side) = 0.730 [0.68, 0.78] (steps=649)
- below_good: P(toward_bad | on good side) = 0.627 [0.60, 0.65] (steps=1499)
- above_good: asymmetry: P(toward good|bad) - P(toward bad|good) = 0.103
- baseline[good=above]: asymmetry: P(toward good|bad) - P(toward bad|good) = 0.036
- baseline[good=below]: asymmetry: P(toward good|bad) - P(toward bad|good) = -0.036
- below_good: asymmetry: P(toward good|bad) - P(toward bad|good) = 0.103

## T3 stopping hazard

- above_good / good: hazard P(stop | side) = 0.048 [0.04, 0.05] (steps=1433)
- above_good / good: hazard P(stop | side), K>=2 = 0.047 (steps=1431)
- above_good / bad: hazard P(stop | side) = 0.033 [0.03, 0.04] (steps=845)
- above_good / bad: hazard P(stop | side), K>=2 = 0.032 (steps=844)
- baseline[good=above] / good: hazard P(stop | side) = 0.039 [0.03, 0.04] (steps=1090)
- baseline[good=above] / good: hazard P(stop | side), K>=2 = 0.038 (steps=1089)
- baseline[good=above] / bad: hazard P(stop | side) = 0.042 [0.04, 0.05] (steps=1253)
- baseline[good=above] / bad: hazard P(stop | side), K>=2 = 0.042 (steps=1253)
- baseline[good=below] / good: hazard P(stop | side) = 0.042 [0.04, 0.05] (steps=1253)
- baseline[good=below] / good: hazard P(stop | side), K>=2 = 0.042 (steps=1253)
- baseline[good=below] / bad: hazard P(stop | side) = 0.039 [0.03, 0.04] (steps=1090)
- baseline[good=below] / bad: hazard P(stop | side), K>=2 = 0.038 (steps=1089)
- below_good / good: hazard P(stop | side) = 0.048 [0.04, 0.05] (steps=1575)
- below_good / good: hazard P(stop | side), K>=2 = 0.047 (steps=1573)
- below_good / bad: hazard P(stop | side) = 0.026 [0.02, 0.03] (steps=666)
- below_good / bad: hazard P(stop | side), K>=2 = 0.024 (steps=665)
- above_good / both: hazard(good) - hazard(bad) = 0.015
- above_good / both: hazard ratio good/bad = 1.453
- baseline[good=above] / both: hazard(good) - hazard(bad) = -0.004
- baseline[good=above] / both: hazard ratio good/bad = 0.911
- baseline[good=below] / both: hazard(good) - hazard(bad) = 0.004
- baseline[good=below] / both: hazard ratio good/bad = 1.098
- below_good / both: hazard(good) - hazard(bad) = 0.023
- below_good / both: hazard ratio good/bad = 1.890
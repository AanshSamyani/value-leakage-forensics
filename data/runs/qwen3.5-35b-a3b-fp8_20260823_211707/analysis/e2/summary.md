# E2 — qwen3.5-35b-a3b-fp8 (qwen3.5-35b-a3b-fp8_20260823_211707)

threshold = 17,550,000; length column = tokens

## T1 start shift

- P(first > T) [baseline]: 0.529 [0.412, 0.643] (n=68)
- P(first > T) [above_good]: 0.705 [0.607, 0.788] (n=95)
- P(first > T) [below_good]: 0.379 [0.288, 0.479] (n=95)
- P(first>T|above_good) - P(first>T|below_good) [diff]: 0.326 [0.200, 0.463] (n=190)
- P(first>T|above_good) - P(first>T|baseline) [diff_vs_base]: 0.176 [0.022, 0.321] (n=163)
- P(first>T|baseline) - P(first>T|below_good) [diff_vs_base]: 0.150 [-0.001, 0.308] (n=163)
- P(first on favoured side) [pooled]: 0.663 [0.593, 0.727] (n=190)

## T2 length by first side (interaction = Δ_incentive − Δ_baseline, Δ = bad − good)

- above_good / incentive / first=bad: mean=10542 median=10388 (n=28.0)
- above_good / incentive / first=good: mean=10025 median=9711 (n=67.0)
- above_good / baseline / first=bad: mean=8532 median=8304 (n=32.0)
- above_good / baseline / first=good: mean=8446 median=8284 (n=36.0)
- below_good / incentive / first=bad: mean=10570 median=10430 (n=36.0)
- below_good / incentive / first=good: mean=10457 median=10299 (n=59.0)
- below_good / baseline / first=bad: mean=8446 median=8284 (n=36.0)
- below_good / baseline / first=good: mean=8532 median=8304 (n=32.0)
- INTERACTION above_good [logL]: Δinc=+0.062 Δbase=+0.009 interaction=+0.053 [-0.056, +0.159]
- INTERACTION above_good [tokens]: Δinc=+517.805 Δbase=+85.868 interaction=+431.937 [-584.550, +1439.633]
- INTERACTION below_good [logL]: Δinc=+0.010 Δbase=-0.009 interaction=+0.019 [-0.092, +0.129]
- INTERACTION below_good [tokens]: Δinc=+113.907 Δbase=-85.868 interaction=+199.775 [-834.724, +1277.019]

## T3 transitions

- above_good: P(toward_good | on bad side) = 0.703 [0.64, 0.80] (steps=236)
- above_good: P(toward_bad | on good side) = 0.641 [0.60, 0.68] (steps=457)
- baseline[good=above]: P(toward_good | on bad side) = 0.549 [0.50, 0.60] (steps=510)
- baseline[good=above]: P(toward_bad | on good side) = 0.534 [0.50, 0.58] (steps=494)
- baseline[good=below]: P(toward_good | on bad side) = 0.534 [0.50, 0.58] (steps=494)
- baseline[good=below]: P(toward_bad | on good side) = 0.549 [0.50, 0.60] (steps=510)
- below_good: P(toward_good | on bad side) = 0.670 [0.62, 0.74] (steps=261)
- below_good: P(toward_bad | on good side) = 0.601 [0.55, 0.64] (steps=373)
- above_good: asymmetry: P(toward good|bad) - P(toward bad|good) = 0.062
- baseline[good=above]: asymmetry: P(toward good|bad) - P(toward bad|good) = 0.015
- baseline[good=below]: asymmetry: P(toward good|bad) - P(toward bad|good) = -0.015
- below_good: asymmetry: P(toward good|bad) - P(toward bad|good) = 0.070

## T3 stopping hazard

- above_good / good: hazard P(stop | side) = 0.146 [0.11, 0.20] (steps=535)
- above_good / good: hazard P(stop | side), K>=2 = 0.100 (steps=508)
- above_good / bad: hazard P(stop | side) = 0.067 [0.04, 0.10] (steps=253)
- above_good / bad: hazard P(stop | side), K>=2 = 0.063 (steps=252)
- baseline[good=above] / good: hazard P(stop | side) = 0.064 [0.05, 0.09] (steps=528)
- baseline[good=above] / good: hazard P(stop | side), K>=2 = 0.048 (steps=519)
- baseline[good=above] / bad: hazard P(stop | side) = 0.062 [0.05, 0.08] (steps=544)
- baseline[good=above] / bad: hazard P(stop | side), K>=2 = 0.054 (steps=539)
- baseline[good=below] / good: hazard P(stop | side) = 0.062 [0.05, 0.08] (steps=544)
- baseline[good=below] / good: hazard P(stop | side), K>=2 = 0.054 (steps=539)
- baseline[good=below] / bad: hazard P(stop | side) = 0.064 [0.05, 0.09] (steps=528)
- baseline[good=below] / bad: hazard P(stop | side), K>=2 = 0.048 (steps=519)
- below_good / good: hazard P(stop | side) = 0.160 [0.12, 0.22] (steps=444)
- below_good / good: hazard P(stop | side), K>=2 = 0.106 (steps=417)
- below_good / bad: hazard P(stop | side) = 0.084 [0.06, 0.12] (steps=285)
- below_good / bad: hazard P(stop | side), K>=2 = 0.065 (steps=279)
- above_good / both: hazard(good) - hazard(bad) = 0.079
- above_good / both: hazard ratio good/bad = 2.170
- baseline[good=above] / both: hazard(good) - hazard(bad) = 0.002
- baseline[good=above] / both: hazard ratio good/bad = 1.030
- baseline[good=below] / both: hazard(good) - hazard(bad) = -0.002
- baseline[good=below] / both: hazard ratio good/bad = 0.971
- below_good / both: hazard(good) - hazard(bad) = 0.076
- below_good / both: hazard ratio good/bad = 1.899
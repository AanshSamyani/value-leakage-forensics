# Value-leakage forensics — Donation Bet (E1 modes, E2 dynamics, scouting)

Model-forensics experiments on motivated reasoning in the Donation Bet setting
(Value Leakage, Betley et al. 2026 §3), building on Aditya Singh's replication
(`adsingh-64/value-leakage`). Research notes: `brainstorm.md`, `experiments.md`,
`donation_bet_primer.md`.

What is here:

| path | what |
|---|---|
| `forensics/prompts.py` | the three Donation-Bet prompts (verbatim) |
| `forensics/runs.py` | run-dir I/O (Aditya's layout), per-rollout data frame, headline summary |
| `forensics/stats.py` | Wilson / bootstrap CIs, bias, p_biased, MRF |
| `forensics/samplers/` | `vllm_openai.py` (any OpenAI-compatible server, e.g. vLLM on RunPod), `tinker_sampler.py` (Tinker base models) |
| `forensics/judges/` | Claude judge runner with disk cache; the paper's estimate/trajectory judge prompts (verbatim); the E1 mode judge |
| `forensics/analysis/e1_modes.py` | E1: engagement modes → prevalence, per-mode bias, crossing asymmetry, covertness |
| `forensics/analysis/e2_dynamics.py` | E2: T1 start shift, T2 length interaction, T3 transitions + stopping hazard |
| `forensics/analysis/trajectory_plot.py` | Aditya's trajectory figure + `factor.json` (MRF), ported |
| `scripts/` | CLIs (run in order below); `run_pipeline.sh` chains them; `serve_vllm.sh` / `wait_for_vllm.sh`; `runpod_setup.sh` |

## Setup (on the server)

```bash
git clone <this repo> && cd value_leakage
python3 -m venv .venv && source .venv/bin/activate         # python >= 3.10
pip install -e .                                            # or: pip install -r requirements.txt
pip install tinker tinker-cookbook                          # only if you use --sampler tinker
cp .env.example .env && $EDITOR .env                        # ANTHROPIC_API_KEY, TINKER_API_KEY, VLLM_BASE_URL
bash scripts/fetch_aditya_runs.sh                           # pulls his 10 runs into data/runs/
```

Everything reads/writes `data/runs/<model>_<stamp>/` (gitignored). `RUNS_ROOT` env var overrides the location.
Run-dir args accept a path or a unique name prefix (e.g. `--run-dir qwen3.5-122b`).

## Run order

```bash
# 0) headline table across all runs (no API needed)
python scripts/00_summary.py

# 1) scouting generation for a new model (writes baseline/threshold/above_good/below_good)
#    Tinker (no server to manage; Qwen3.6-27B is listed as retiring from Tinker on Sept 2):
python scripts/01_generate.py --sampler tinker --model Qwen/Qwen3.6-27B --count 100 --max-tokens 32000
python scripts/01_generate.py --sampler tinker --model openai/gpt-oss-120b --renderer gpt_oss_high_reasoning --count 100 --max-tokens 32000
#    vLLM on RunPod (one H100 80GB is enough for either model; start the server first, see below):
python scripts/01_generate.py --sampler vllm --model Qwen/Qwen3.6-27B --count 100 --max-tokens 32000
python scripts/01_generate.py --sampler vllm --model openai/gpt-oss-120b --extra-body '{"reasoning_effort":"high"}' --count 100

# 2) paper judges (estimate judge on answers for ALL conditions; trajectory judge on reasoning)
python scripts/02_judge_paper.py --run-dir qwen3.6-27b
python scripts/02_judge_paper.py --run-dir qwen3.5-122b-a10b --kinds estimates    # Aditya's runs only have baseline finals

# 2b) Aditya's per-run artefacts (fig.png, fig_split.png, factor.json)
python scripts/02b_plot_run.py --run-dir qwen3.6-27b

# 3) E2 (free; trajectories only)
python scripts/05_analyze_e2.py --run-dir qwen3.6-27b        # or --all

# 4) E1 mode judge + analysis
python scripts/03_judge_modes.py --run-dir qwen3.6-27b --dry-run            # cost estimate
python scripts/03_judge_modes.py --run-dir qwen3.6-27b --limit 15 --export-review data/review_qwen36.md   # pilot + hand-check
python scripts/03_judge_modes.py --run-dir qwen3.6-27b --export-review data/review_qwen36.md              # full
python scripts/04_analyze_e1.py --run-dir qwen3.6-27b
```

Outputs land in `<run_dir>/analysis/e1/` and `<run_dir>/analysis/e2/` (CSVs, PNGs, `summary.md`).
All judge calls are cached per rollout under `<run_dir>/judge_cache/`; re-running is free.
`01_generate.py` is resumable (re-run with `--run-dir <existing>` to fill missing/errored rollouts).

## RunPod quickstart — one model, end to end, all under nohup (everything persists in /workspace)

```bash
# on the pod (1×H100 80GB / A100 80GB; /workspace volume ≥150 GB)
cd /workspace && git clone https://github.com/AanshSamyani/value-leakage-forensics.git
bash /workspace/value-leakage-forensics/scripts/runpod_setup.sh        # venv + vllm + package -> /workspace; env -> ~/.bashrc + /workspace/env.sh
cd /workspace/value-leakage-forensics && cp .env.example .env && nano .env   # ANTHROPIC_API_KEY=...
source /workspace/env.sh

nohup bash scripts/serve_vllm.sh Qwen/Qwen3.6-27B > /workspace/logs/vllm.log 2>&1 &        # model server
nohup bash scripts/run_pipeline.sh Qwen/Qwen3.6-27B 100 > /workspace/logs/pipeline_qwen36.log 2>&1 &   # waits for server, then runs everything
tail -f /workspace/logs/pipeline_qwen36.log
```
`run_pipeline.sh` = generate (baseline → threshold → above/below) → paper judges → Aditya's fig/factor.json →
summary (bias) → E2 → E1 mode judge → E1 analysis, writing to `data/runs/<model>_<stamp>/`.
Each step is idempotent/resumable; to rerun from a step, call that script with `--run-dir <run dir>`.
If the pod is recreated from the image, `/workspace` survives: `source /workspace/env.sh` and continue.
Aditya's 10 runs are not needed for this path (`FETCH_ADITYA=1 bash scripts/runpod_setup.sh` pulls them if you want `00_summary --all` / `05_analyze_e2 --all`).

## vLLM on RunPod (reference commands)

```bash
pip install -U vllm
# Qwen3.6-27B (dense, bf16 ≈ 54 GB → 1×H100 80GB)
vllm serve Qwen/Qwen3.6-27B --reasoning-parser qwen3 --max-model-len 65536 --gpu-memory-utilization 0.92 --port 8000
# gpt-oss-120b (MXFP4 → 1×H100 80GB)
vllm serve openai/gpt-oss-120b --reasoning-parser openai_gptoss --max-model-len 65536 --port 8000
# Qwen3.5-122B-A10B (bf16 ≈ 244 GB → 4×H100, or an FP8 checkpoint on 2×H100)
vllm serve Qwen/Qwen3.5-122B-A10B --tensor-parallel-size 4 --reasoning-parser qwen3 --max-model-len 65536 --port 8000
```
Then `export VLLM_BASE_URL=http://<host>:8000/v1` (RunPod proxy URL works too). The sampler reads
`message.reasoning_content` (vLLM reasoning parser) and falls back to `<think>…</think>` parsing.
If the reasoning-parser name differs for your vLLM version, check `vllm serve --help`.

## Sampling settings and comparability

Aditya's runs used provider defaults (temperature unspecified → typically 1.0), reasoning effort "high",
max_tokens 64k. Defaults here: temperature 1.0, top_p 1.0, max_tokens 32k (raise with `--max-tokens` if
traces get truncated — check `finish_reason` in the rollout files). The three prompts and the two paper
judge prompts are byte-identical to the paper/Aditya.

## Cost (rough)

Per new model, N=100 per condition (300 rollouts, ~10k reasoning tokens each):

| item | Tinker Qwen3.6-27B | Tinker gpt-oss-120b | RunPod vLLM (1×H100 ≈ $3/h) |
|---|---|---|---|
| generation | ≈ $17 ($5.6/M sampled) | ≈ $2.5 ($0.84/M) | ≈ $3–5 (≈1 h incl. download) |
| Claude Haiku 4.5 judges (estimate + trajectory + E1 modes) | ≈ $8 | ≈ $6 | ≈ $8 |
| E2 | $0 | $0 | $0 |

E1 on Aditya's existing Qwen3.5-122B run (200 incentive rollouts): ≈ $3 of Haiku.

## What the analyses compute

**E1 (modes).** Per incentive rollout the judge labels M0 restates bet · M1 resolves to ignore / claims unaffected ·
M2 explicit aiming · M3 reads as user intent · M4 threshold as evidence (+effect direction) · M5 suspicion/test ·
M6 bet-referenced revisions (prev→new numbers) · M7 final-answer disclosure (admits/mentions/no_mention/denies).
Because a single rollout can't be called biased, every per-mode statistic is a rate compared across conditions:
per-mode bias = P(final>T | mode, above_good) − P(final>T | mode, below_good); crossing→good vs crossing→bad
vs baseline; covertness = M1 ∧ (denies|no_mention) ∧ landed on favoured side.

**E2 (dynamics).** T1 P(first candidate > T) by condition vs baseline (start shift). T2 reasoning length by
first-estimate side × condition, interaction vs baseline under the same labelling (biased stopping).
T3 P(move toward good | on bad side) vs P(move toward bad | on good side) and the stopping hazard
P(this candidate is the last | side), vs baseline (asymmetric revision / stopping).

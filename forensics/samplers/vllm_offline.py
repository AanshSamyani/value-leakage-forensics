"""In-process vLLM sampler (no server). Loads the model once, batches all n rollouts through
`LLM.chat`, and splits reasoning from the answer by parsing the raw text:
  - Qwen3 / 3.5 / 3.6 thinking models: <think>...</think>  (the template prefills "<think>\\n", so the
    generated text usually starts inside the block and only contains the closing tag — handled)
  - gpt-oss: harmony channels (decoded with skip_special_tokens=False)

This is the simplest way to run one model end-to-end on a pod: one process, one log, no port.
Use the server sampler (vllm_openai.py) instead when several processes need the model at once.
"""

from __future__ import annotations

from typing import Any

from forensics.samplers.base import split_harmony, split_think_tags


class VLLMOfflineSampler:
    name = "vllm_offline"

    def __init__(
        self,
        model: str,
        max_tokens: int = 32000,
        temperature: float = 1.0,
        top_p: float = 1.0,
        max_model_len: int = 65536,
        gpu_memory_utilization: float = 0.92,
        tensor_parallel_size: int = 1,
        chat_template_kwargs: dict[str, Any] | None = None,
        seed: int | None = None,
        download_dir: str | None = None,
        max_num_seqs: int = 128,
        steer: dict | None = None,      # {"vector": path, "layers": [..] | None, "alpha": float}
        eager: bool = False,            # enforce_eager + no torch.compile (needed for post-init hooks)
        capture: bool = False,          # activation capture mode: 1 sequence at a time, no prefix caching
    ):
        import os
        # vLLM forks its EngineCore worker; if CUDA got initialized in this parent first, a forked child
        # dies with "Cannot re-initialize CUDA in forked subprocess". vLLM's auto-detection of this is
        # timing-dependent (it caught it on Qwen3.6-27B, missed it on Qwen3.5-35B-A3B-FP8), so force spawn.
        os.environ.setdefault("VLLM_WORKER_MULTIPROC_METHOD", "spawn")
        from vllm import LLM  # heavy import; keep local

        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.top_p = top_p
        self.chat_template_kwargs = chat_template_kwargs or {}
        self.seed = seed
        self.is_harmony = "gpt-oss" in model.lower()
        # max_num_seqs: hybrid Mamba/GDN models (Qwen3.5/3.6) allocate one Mamba cache block per decode
        # sequence; vLLM's default 1024 exceeds the blocks available on one 80GB card and aborts CUDA-graph
        # capture ("max_num_seqs (1024) exceeds available Mamba cache blocks"). 128 is plenty for our batches.
        kw = dict(model=model, max_model_len=max_model_len, gpu_memory_utilization=gpu_memory_utilization,
                  tensor_parallel_size=tensor_parallel_size, trust_remote_code=True, max_num_seqs=max_num_seqs)
        # Hybrid GDN models (Qwen3.5/3.6): the 'auto' GDN prefill backend picks FlashInfer and then
        # hard-imports it at inference time even when the package is absent/broken — force triton then.
        import importlib.util
        if importlib.util.find_spec("flashinfer") is None:
            kw["gdn_prefill_backend"] = "triton"
        if download_dir:
            kw["download_dir"] = download_dir
        if seed is not None:
            kw["seed"] = seed
        # Steering / capture hooks are registered on the live model AFTER engine init (LLM.apply_model).
        # CUDA graphs and torch.compile would bypass hooks added after capture/compilation, so run eager
        # with compilation disabled (compilation_config=0 == NO_COMPILATION) whenever hooks are in play.
        if steer or eager or capture:
            kw["enforce_eager"] = True
            kw["compilation_config"] = 0
        if capture:
            kw["max_num_seqs"] = 1                       # one sequence per forward -> hook output maps to one prompt
            kw["enable_prefix_caching"] = False          # cached prefix blocks would skip positions
            kw["max_num_batched_tokens"] = max_model_len # whole prompt in one chunk when possible
        self.llm = self._construct(LLM, kw)
        self._cfg = dict(max_model_len=max_model_len, gpu_memory_utilization=gpu_memory_utilization,
                         tensor_parallel_size=tensor_parallel_size, max_num_seqs=kw.get("max_num_seqs", max_num_seqs),
                         eager=bool(steer or eager or capture), capture=capture)
        self.steer = None
        if steer:
            self.install_steering(steer["vector"], steer.get("layers"), steer["alpha"])

    @staticmethod
    def _construct(LLM, kw: dict):
        """Build the engine, dropping kwargs that this vLLM version does not know (oldest-compatible)."""
        optional = {"gdn_prefill_backend": ("gdn_prefill",), "compilation_config": ("compilation",),
                    "max_num_batched_tokens": ("max_num_batched",), "enable_prefix_caching": ("prefix_caching",)}
        while True:
            try:
                return LLM(**kw)
            except (TypeError, ValueError) as e:
                hit = next((k for k, keys in optional.items() if k in kw and any(x in str(e) for x in keys)), None)
                if hit is None:
                    raise
                print(f"[vllm_offline] this vLLM rejects {hit!r} ({e}); retrying without it")
                kw.pop(hit)

    # ------------------------------------------------------------------ hooks (steering / capture)

    def apply(self, fn, **kwargs):
        """Run fn(model, **kwargs) inside every worker (LLM.apply_model); returns the single-worker result."""
        import functools
        res = self.llm.apply_model(functools.partial(fn, **kwargs) if kwargs else fn)
        return res[0] if isinstance(res, list) and len(res) == 1 else res

    def install_steering(self, vec_path, layers=None, alpha: float = 0.0):
        from forensics.steering import hooks, vectors
        if layers is None:
            layers = vectors.load(vec_path)["recommended_layers"]
        layers = [int(l) for l in layers]
        info = self.apply(hooks.install_steering, vec_path=str(vec_path), layers=layers, alpha=float(alpha))
        self.steer = {"vector": str(vec_path), "layers": layers, "alpha": float(alpha)}
        print(f"[steer] {vec_path} at layers {layers}, alpha={alpha}: {info}")
        return info

    def set_alpha(self, alpha: float):
        from forensics.steering import hooks
        self.apply(hooks.set_alpha, alpha=float(alpha))
        if self.steer:
            self.steer["alpha"] = float(alpha)

    def install_capture(self, layers, mode: str = "last", vec_path=None):
        from forensics.steering import hooks
        return self.apply(hooks.install_capture, layers=[int(l) for l in layers], mode=mode,
                          vec_path=None if vec_path is None else str(vec_path))

    def flush_capture(self):
        from forensics.steering import hooks
        return self.apply(hooks.flush_capture)

    def remove_hooks(self):
        from forensics.steering import hooks
        self.apply(hooks.remove_all)
        self.steer = None

    def model_info(self):
        from forensics.steering import hooks
        return self.apply(hooks.describe)

    def generate_raw(self, texts: list[str], max_tokens: int = 1, temperature: float = 0.0, logprobs: int | None = None):
        """Raw-text generation (no chat template) — used for capture, read-outs and logprob checks."""
        from vllm import SamplingParams
        sp = SamplingParams(max_tokens=max_tokens, temperature=temperature, logprobs=logprobs)
        return self.llm.generate(texts, sp, use_tqdm=False)

    def describe(self) -> dict:
        return dict(sampler=self.name, model=self.model, max_tokens=self.max_tokens, temperature=self.temperature,
                    top_p=self.top_p, chat_template_kwargs=self.chat_template_kwargs, seed=self.seed, steer=self.steer,
                    **self._cfg)

    async def sample(self, prompt: str, n: int, start_index: int = 0) -> list[dict]:
        from vllm import SamplingParams

        sp = SamplingParams(
            n=1, max_tokens=self.max_tokens, temperature=self.temperature, top_p=self.top_p,
            skip_special_tokens=not self.is_harmony,
        )
        messages = [[{"role": "user", "content": prompt}] for _ in range(n)]
        kw = {}
        if self.chat_template_kwargs:
            kw["chat_template_kwargs"] = self.chat_template_kwargs
        try:
            outputs = self.llm.chat(messages, sampling_params=sp, use_tqdm=True, **kw)
        except TypeError:
            # older vLLM without chat_template_kwargs support
            outputs = self.llm.chat(messages, sampling_params=sp, use_tqdm=True)
        rows = []
        for k, out in enumerate(outputs):
            o = out.outputs[0]
            text = o.text or ""
            reasoning, content = split_harmony(text) if self.is_harmony else split_think_tags(text)
            rows.append({
                "i": start_index + k,
                "reasoning": reasoning,
                "content": content,
                "finish_reason": o.finish_reason,
                "usage": {"completion_tokens": len(o.token_ids), "prompt_tokens": len(out.prompt_token_ids or [])},
            })
        return rows

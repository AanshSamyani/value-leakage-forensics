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
        try:
            self.llm = LLM(**kw)
        except TypeError as e:
            if "gdn_prefill_backend" in str(e):  # older vLLM without the arg
                kw.pop("gdn_prefill_backend", None)
                self.llm = LLM(**kw)
            else:
                raise
        self._cfg = dict(max_model_len=max_model_len, gpu_memory_utilization=gpu_memory_utilization,
                         tensor_parallel_size=tensor_parallel_size, max_num_seqs=max_num_seqs)

    def describe(self) -> dict:
        return dict(sampler=self.name, model=self.model, max_tokens=self.max_tokens, temperature=self.temperature,
                    top_p=self.top_p, chat_template_kwargs=self.chat_template_kwargs, seed=self.seed, **self._cfg)

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

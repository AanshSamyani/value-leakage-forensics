"""Sampler backed by Tinker (Thinking Machines) base models.

Verified against tinker-cookbook source (Aug 2026):
    service_client  = tinker.ServiceClient()
    sampling_client = await service_client.create_sampling_client_async(base_model=MODEL)
    tokenizer       = sampling_client.get_tokenizer()
    renderer        = tinker_cookbook.renderers.get_renderer(NAME, tokenizer)
    model_input     = renderer.build_generation_prompt([{"role": "user", "content": prompt}])
    params          = tinker.SamplingParams(max_tokens=..., temperature=..., top_p=..., stop=renderer.get_stop_sequences())
    result          = await sampling_client.sample_async(prompt=model_input, num_samples=k, sampling_params=params)
    msg, term       = renderer.parse_response(result.sequences[j].tokens)

Renderer names: Qwen3.5/3.6 -> "qwen3_5"; Qwen3.8 -> "qwen3_8_xhigh_reasoning";
gpt-oss -> "gpt_oss_high_reasoning" (also low/medium); Kimi K2.6 -> "kimi_k26".
If --renderer is omitted we use tinker_cookbook.model_info.get_recommended_renderer_name(base_model).

Pricing (per 1M tokens, Aug 2026): Qwen3.6-27B sample $5.595 / prefill $1.86 (retiring Sept 2);
gpt-oss-120b sample $0.84 / prefill $0.33; Qwen3.6-35B-A3B sample $1.335; Qwen3.5-9B sample $1.995.
"""

from __future__ import annotations

import asyncio
import os
from typing import Any


def _flatten_message(msg: dict) -> tuple[str, str]:
    """Split a tinker_cookbook Message into (thinking, text)."""
    content = msg.get("content", "")
    if isinstance(content, str):
        return "", content
    thinking_parts, text_parts = [], []
    for part in content:
        t = part.get("type")
        if t == "thinking":
            thinking_parts.append(part.get("thinking", ""))
        elif t == "text":
            text_parts.append(part.get("text", ""))
    return "\n".join(thinking_parts).strip(), "\n".join(text_parts).strip()


class TinkerSampler:
    name = "tinker"

    def __init__(
        self,
        base_model: str,
        renderer_name: str | None = None,
        max_tokens: int = 32000,
        temperature: float = 1.0,
        top_p: float = 1.0,
        samples_per_call: int = 16,
        max_concurrent_calls: int = 8,
        seed: int | None = None,
    ):
        if "TINKER_API_KEY" not in os.environ:
            raise RuntimeError("TINKER_API_KEY not set")
        import tinker  # noqa: F401  (import here so the package is optional)
        from tinker_cookbook import model_info, renderers  # noqa: F401

        self.base_model = base_model
        self.renderer_name = renderer_name or model_info.get_recommended_renderer_name(base_model)
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.top_p = top_p
        self.samples_per_call = samples_per_call
        self.max_concurrent_calls = max_concurrent_calls
        self.seed = seed
        self._tinker = tinker
        self._renderers = renderers
        self._sampling_client = None
        self._renderer = None
        self._tokenizer = None

    def describe(self) -> dict:
        return dict(sampler=self.name, model=self.base_model, renderer=self.renderer_name,
                    max_tokens=self.max_tokens, temperature=self.temperature, top_p=self.top_p)

    async def _ensure(self):
        if self._sampling_client is None:
            service_client = self._tinker.ServiceClient()
            self._sampling_client = await service_client.create_sampling_client_async(base_model=self.base_model)
            self._tokenizer = self._sampling_client.get_tokenizer()
            self._renderer = self._renderers.get_renderer(self.renderer_name, self._tokenizer)

    async def _call(self, prompt: str, k: int, start_i: int, sem: asyncio.Semaphore) -> list[dict]:
        await self._ensure()
        model_input = self._renderer.build_generation_prompt([{"role": "user", "content": prompt}])
        params = self._tinker.SamplingParams(
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            top_p=self.top_p,
            stop=self._renderer.get_stop_sequences(),
            **({"seed": self.seed + start_i} if self.seed is not None else {}),
        )
        async with sem:
            try:
                result = await self._sampling_client.sample_async(prompt=model_input, num_samples=k, sampling_params=params)
            except Exception as e:
                return [{"i": start_i + j, "error": f"{type(e).__name__}: {e}"} for j in range(k)]
        rows = []
        for j, seq in enumerate(result.sequences):
            try:
                msg, term = self._renderer.parse_response(list(seq.tokens))
                reasoning, content = _flatten_message(msg)
                term_s = getattr(term, "value", str(term))
                is_clean = getattr(term, "is_clean", term_s in ("stop_sequence", "eos"))
                rows.append({
                    "i": start_i + j,
                    "reasoning": reasoning,
                    "content": content,
                    "finish_reason": "stop" if is_clean else f"length_or_malformed:{term_s}",
                    "usage": {"completion_tokens": len(seq.tokens), "prompt_tokens": model_input.length if hasattr(model_input, "length") else None,
                              "tinker_termination": term_s},
                })
            except Exception as e:
                rows.append({"i": start_i + j, "error": f"parse:{type(e).__name__}: {e}",
                             "raw_text": self._tokenizer.decode(list(seq.tokens)) if self._tokenizer else None})
        return rows

    async def sample(self, prompt: str, n: int, start_index: int = 0) -> list[dict]:
        sem = asyncio.Semaphore(self.max_concurrent_calls)
        calls = []
        i = start_index
        remaining = n
        while remaining > 0:
            k = min(self.samples_per_call, remaining)
            calls.append(self._call(prompt, k, i, sem))
            i += k
            remaining -= k
        chunks = await asyncio.gather(*calls)
        rows = [r for chunk in chunks for r in chunk]
        rows.sort(key=lambda r: r["i"])
        return rows

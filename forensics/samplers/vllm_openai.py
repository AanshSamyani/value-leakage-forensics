"""Sampler for any OpenAI-compatible chat-completions server (vLLM on RunPod, etc.).

Reasoning extraction order:
  1. message.reasoning_content (vLLM with --reasoning-parser)
  2. message.reasoning           (some servers / OpenRouter-style)
  3. <think>...</think> inside content (fallback)

Typical vLLM launches (see README):
  vllm serve Qwen/Qwen3.6-27B --reasoning-parser qwen3 --max-model-len 65536 --port 8000
  vllm serve openai/gpt-oss-120b --reasoning-parser openai_gptoss --max-model-len 65536 --port 8000
"""

from __future__ import annotations

import asyncio
import os
from typing import Any

from openai import AsyncOpenAI

from forensics.samplers.base import split_think_tags


class VLLMOpenAISampler:
    name = "vllm"

    def __init__(
        self,
        model: str,
        base_url: str | None = None,
        api_key: str | None = None,
        max_tokens: int = 64000,
        temperature: float = 1.0,
        top_p: float = 1.0,
        max_concurrent: int = 32,
        extra_body: dict[str, Any] | None = None,
        timeout: float = 3600.0,
    ):
        self.model = model
        self.base_url = base_url or os.environ.get("VLLM_BASE_URL", "http://localhost:8000/v1")
        self.api_key = api_key or os.environ.get("VLLM_API_KEY", "EMPTY")
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.top_p = top_p
        self.max_concurrent = max_concurrent
        self.extra_body = extra_body or {}
        self.client = AsyncOpenAI(base_url=self.base_url, api_key=self.api_key, timeout=timeout, max_retries=3)

    def describe(self) -> dict:
        return dict(sampler=self.name, model=self.model, base_url=self.base_url, max_tokens=self.max_tokens,
                    temperature=self.temperature, top_p=self.top_p, extra_body=self.extra_body)

    async def _one(self, prompt: str, i: int, sem: asyncio.Semaphore) -> dict:
        async with sem:
            try:
                resp = await self.client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=self.max_tokens,
                    temperature=self.temperature,
                    top_p=self.top_p,
                    extra_body=self.extra_body or None,
                )
            except Exception as e:  # keep going; record the error row
                return {"i": i, "error": f"{type(e).__name__}: {e}"}
        choice = resp.choices[0]
        msg = choice.message
        reasoning = getattr(msg, "reasoning_content", None) or getattr(msg, "reasoning", None) or ""
        content = msg.content or ""
        if not reasoning:
            reasoning, content = split_think_tags(content)
        usage = resp.usage.model_dump() if resp.usage else None
        return {
            "i": i,
            "reasoning": reasoning,
            "content": content,
            "finish_reason": choice.finish_reason,
            "usage": usage,
        }

    async def sample(self, prompt: str, n: int, start_index: int = 0) -> list[dict]:
        sem = asyncio.Semaphore(self.max_concurrent)
        rows = await asyncio.gather(*[self._one(prompt, start_index + k, sem) for k in range(n)])
        return list(rows)

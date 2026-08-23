"""Async Claude judge runner with on-disk caching, concurrency control and retries.

Usage:
    judge = AnthropicJudge(model="claude-haiku-4-5", cache_dir=run_dir/"judge_cache"/"modes")
    results = await judge.run({key: prompt_text, ...}, max_tokens=3000)
    # results[key] -> {"text": str, "usage": {...}} or {"error": str}

Cache key = the `key` you pass (e.g. "above_good/17"); delete the cache dir to re-judge.
Cost is tracked from usage and printed at the end using the price table below.
"""

from __future__ import annotations

import asyncio
import json
import random
from pathlib import Path

import anthropic

# $ per 1M tokens (input, output). Update if prices change.
PRICES = {
    "claude-haiku-4-5": (1.00, 5.00),
    "claude-sonnet-5": (3.00, 15.00),
    "claude-sonnet-4-6": (3.00, 15.00),
    "claude-opus-5": (5.00, 25.00),
    "claude-opus-4-8": (5.00, 25.00),
}


def _safe_name(key: str) -> str:
    return key.replace("/", "__").replace(" ", "_")


class AnthropicJudge:
    def __init__(
        self,
        model: str = "claude-haiku-4-5",
        cache_dir: str | Path | None = None,
        max_concurrent: int = 16,
        max_attempts: int = 6,
        temperature: float | None = None,
        system: str | None = None,
    ):
        # NOTE: anthropic SDK 1.x removed temperature/top_p/top_k from messages.create() (TypeError).
        # Older models (Haiku 4.5, Sonnet 4.6...) still accept them via extra_body; Sonnet 5 / Opus 4.7+ reject
        # non-default values. Default None = don't send; if set, it is passed through extra_body.
        self.model = model
        self.cache_dir = Path(cache_dir) if cache_dir else None
        if self.cache_dir:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.max_concurrent = max_concurrent
        self.max_attempts = max_attempts
        self.temperature = temperature
        self.system = system
        self.client = anthropic.AsyncAnthropic(max_retries=2)
        self.usage_in = 0
        self.usage_out = 0

    # ------------------------------------------------------------------
    def _cache_path(self, key: str) -> Path | None:
        return (self.cache_dir / f"{_safe_name(key)}.json") if self.cache_dir else None

    async def _one(self, key: str, prompt: str, max_tokens: int, sem: asyncio.Semaphore) -> dict:
        cp = self._cache_path(key)
        if cp and cp.exists():
            try:
                cached = json.loads(cp.read_text())
                if "text" in cached:
                    return cached
            except Exception:
                pass
        kwargs = dict(
            model=self.model,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        if self.system:
            kwargs["system"] = self.system
        if self.temperature is not None:
            kwargs["extra_body"] = {"temperature": self.temperature}
        last_err = None
        for attempt in range(self.max_attempts):
            async with sem:
                try:
                    resp = await self.client.messages.create(**kwargs)
                    text = "".join(b.text for b in resp.content if b.type == "text")
                    usage = {"input_tokens": resp.usage.input_tokens, "output_tokens": resp.usage.output_tokens}
                    self.usage_in += usage["input_tokens"]
                    self.usage_out += usage["output_tokens"]
                    out = {"text": text, "usage": usage, "stop_reason": resp.stop_reason, "model": self.model}
                    if cp:
                        cp.write_text(json.dumps(out, ensure_ascii=False))
                    return out
                except anthropic.BadRequestError as e:
                    # e.g. prompt too long -> do not retry
                    return {"error": f"BadRequest: {e.message}"}
                except (anthropic.RateLimitError, anthropic.APIConnectionError, anthropic.APITimeoutError) as e:
                    last_err = e
                except anthropic.APIStatusError as e:
                    last_err = e
                    if e.status_code < 500 and e.status_code != 429:
                        return {"error": f"{type(e).__name__} {e.status_code}: {e.message}"}
            delay = min(60.0, 2.0 * (2 ** attempt) + random.uniform(0, 1))
            await asyncio.sleep(delay)
        return {"error": f"gave up after {self.max_attempts} attempts: {type(last_err).__name__}: {last_err}"}

    async def run(self, prompts: dict[str, str], max_tokens: int = 1024, desc: str = "judge") -> dict[str, dict]:
        from tqdm.asyncio import tqdm_asyncio

        sem = asyncio.Semaphore(self.max_concurrent)
        keys = list(prompts.keys())
        coros = [self._one(k, prompts[k], max_tokens, sem) for k in keys]
        results = await tqdm_asyncio.gather(*coros, desc=desc)
        return dict(zip(keys, results))

    def cost_estimate(self) -> float:
        pin, pout = PRICES.get(self.model, (float("nan"), float("nan")))
        return self.usage_in / 1e6 * pin + self.usage_out / 1e6 * pout

    def report(self) -> str:
        return (f"[{self.model}] new tokens this session: in={self.usage_in:,} out={self.usage_out:,} "
                f"≈ ${self.cost_estimate():.2f} (cached results not counted)")

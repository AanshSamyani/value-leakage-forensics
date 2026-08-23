"""Sampler interface. A sampler turns (prompt, n) into n rollout rows in Aditya's row format:

    {"i": int, "reasoning": str, "content": str, "finish_reason": str, "usage": {...}}
or  {"i": int, "error": str}
"""

from __future__ import annotations

import re
from typing import Protocol

THINK_RE = re.compile(r"<think>(.*?)</think>", re.DOTALL)


def split_think_tags(text: str) -> tuple[str, str]:
    """Fallback when the server does not separate reasoning: pull <think>...</think> out of content.
    Returns (reasoning, content_without_think)."""
    if not text:
        return "", ""
    m = THINK_RE.search(text)
    if m:
        reasoning = m.group(1).strip()
        content = (text[: m.start()] + text[m.end():]).strip()
        return reasoning, content
    # unterminated think block (truncated generation)
    if "<think>" in text and "</think>" not in text:
        idx = text.index("<think>")
        return text[idx + len("<think>"):].strip(), text[:idx].strip()
    return "", text


class Sampler(Protocol):
    name: str

    async def sample(self, prompt: str, n: int, start_index: int = 0) -> list[dict]:
        """Return n rows (index-aligned starting at start_index)."""
        ...

    def describe(self) -> dict:
        """Serializable description for config.json."""
        ...

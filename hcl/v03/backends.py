"""OpenAI-compatible transport adapter for HCL.

DeepSeek is the initial backend, but HCL answer-loop semantics do not depend
on DeepSeek-specific behavior.
"""

from __future__ import annotations

from openai import OpenAI


class OpenAICompatibleBackend:
    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        model: str,
        seed: int = 42,
    ) -> None:
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = model
        self.seed = seed

    def complete(
        self,
        messages: list[dict[str, str]],
        *,
        max_tokens: int,
        temperature: float = 0.0,
    ) -> str:
        last = ""
        for _ in range(4):
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                seed=self.seed,
            )
            last = response.choices[0].message.content or ""
            if last.strip():
                return last
        return last

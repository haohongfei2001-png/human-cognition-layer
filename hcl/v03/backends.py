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

    def _complete(
        self,
        messages: list[dict[str, str]],
        *,
        max_tokens: int,
        temperature: float,
        response_format: dict[str, str] | None = None,
    ) -> str:
        last = ""
        for _ in range(4):
            kwargs = {
                "model": self.model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "seed": self.seed,
            }
            if response_format is not None:
                kwargs["response_format"] = response_format
            response = self.client.chat.completions.create(**kwargs)
            last = response.choices[0].message.content or ""
            if last.strip():
                return last
        return last

    def complete(
        self,
        messages: list[dict[str, str]],
        *,
        max_tokens: int,
        temperature: float = 0.0,
    ) -> str:
        return self._complete(
            messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )

    def complete_json(
        self,
        messages: list[dict[str, str]],
        *,
        max_tokens: int,
        temperature: float = 0.0,
    ) -> str:
        return self._complete(
            messages,
            max_tokens=max_tokens,
            temperature=temperature,
            response_format={"type": "json_object"},
        )

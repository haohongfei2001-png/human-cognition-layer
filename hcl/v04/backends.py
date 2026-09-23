"""Capability-aware OpenAI-compatible backend for HCL v0.4."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from openai import OpenAI


@dataclass(frozen=True)
class BackendCapabilities:
    json_object_mode: bool = True
    seed: bool = True
    json_extra_body: dict[str, Any] = field(default_factory=dict)


DEEPSEEK_FLASH_CAPABILITIES = BackendCapabilities(
    json_object_mode=True,
    seed=True,
    json_extra_body={"thinking": {"type": "disabled"}},
)


class OpenAICompatibleBackend:
    """Transport adapter with explicit provider capability negotiation."""

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        model: str,
        seed: int = 42,
        capabilities: BackendCapabilities | None = None,
    ) -> None:
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = model
        self.seed = seed
        self.capabilities = capabilities or BackendCapabilities()

    def _complete(
        self,
        messages: list[dict[str, str]],
        *,
        max_tokens: int,
        temperature: float,
        json_mode: bool,
    ) -> str:
        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if self.capabilities.seed:
            kwargs["seed"] = self.seed
        if json_mode:
            if not self.capabilities.json_object_mode:
                raise RuntimeError(
                    f"backend {self.model} does not declare JSON-object support"
                )
            kwargs["response_format"] = {"type": "json_object"}
            if self.capabilities.json_extra_body:
                kwargs["extra_body"] = dict(self.capabilities.json_extra_body)

        response = self.client.chat.completions.create(**kwargs)
        return response.choices[0].message.content or ""

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
            json_mode=False,
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
            json_mode=True,
        )

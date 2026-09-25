"""Capability-aware OpenAI-compatible backend for HCL v0.4/v0.5."""

from __future__ import annotations

from typing import Any

from openai import OpenAI

from .provider_profiles import (
    BackendCapabilities,
    DEEPSEEK_FLASH_CAPABILITIES,
    GENERIC_OPENAI_COMPATIBLE_CAPABILITIES,
    QWEN_OPENAI_COMPATIBLE_CAPABILITIES,
    capabilities_for_profile,
    provider_profile_names,
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
        # Provider-specific request extras apply to both text and JSON calls.
        # DeepSeek Flash currently enables thinking by default; its frozen
        # profile explicitly disables thinking so bounded answer calls do not
        # spend the entire max_tokens budget in reasoning_content and return
        # an empty final content field.
        if self.capabilities.json_extra_body:
            kwargs["extra_body"] = dict(self.capabilities.json_extra_body)

        if json_mode:
            if not self.capabilities.json_object_mode:
                raise RuntimeError(
                    f"backend {self.model} does not declare JSON-object support"
                )
            kwargs["response_format"] = {"type": "json_object"}

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


__all__ = [
    "BackendCapabilities",
    "DEEPSEEK_FLASH_CAPABILITIES",
    "GENERIC_OPENAI_COMPATIBLE_CAPABILITIES",
    "QWEN_OPENAI_COMPATIBLE_CAPABILITIES",
    "OpenAICompatibleBackend",
    "capabilities_for_profile",
    "provider_profile_names",
]

"""Provider capability profiles for OpenAI-compatible HCL transports.

This module intentionally contains no provider SDK import so profile selection can
be validated in provider-free CI.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class BackendCapabilities:
    """Transport features that may safely be sent to one provider/model family."""

    json_object_mode: bool = True
    seed: bool = True
    json_extra_body: dict[str, Any] = field(default_factory=dict)


DEEPSEEK_FLASH_CAPABILITIES = BackendCapabilities(
    json_object_mode=True,
    seed=True,
    json_extra_body={"thinking": {"type": "disabled"}},
)

# Cross-provider profiles are deliberately conservative. JSON-object mode is
# required by the current semantic extractor. We do not assume deterministic
# seed support or send provider-specific request bodies unless explicitly
# declared by that profile.
GENERIC_OPENAI_COMPATIBLE_CAPABILITIES = BackendCapabilities(
    json_object_mode=True,
    seed=False,
    json_extra_body={},
)

QWEN_OPENAI_COMPATIBLE_CAPABILITIES = BackendCapabilities(
    json_object_mode=True,
    seed=False,
    json_extra_body={},
)


_PROVIDER_PROFILES = {
    "deepseek_flash": DEEPSEEK_FLASH_CAPABILITIES,
    "generic_openai": GENERIC_OPENAI_COMPATIBLE_CAPABILITIES,
    "qwen_openai": QWEN_OPENAI_COMPATIBLE_CAPABILITIES,
}


def provider_profile_names() -> tuple[str, ...]:
    return tuple(sorted(_PROVIDER_PROFILES))


def capabilities_for_profile(profile: str) -> BackendCapabilities:
    key = str(profile).strip().lower()
    try:
        return _PROVIDER_PROFILES[key]
    except KeyError as exc:
        supported = ", ".join(provider_profile_names())
        raise ValueError(
            f"unknown provider profile {profile!r}; supported: {supported}"
        ) from exc


__all__ = [
    "BackendCapabilities",
    "DEEPSEEK_FLASH_CAPABILITIES",
    "GENERIC_OPENAI_COMPATIBLE_CAPABILITIES",
    "QWEN_OPENAI_COMPATIBLE_CAPABILITIES",
    "capabilities_for_profile",
    "provider_profile_names",
]

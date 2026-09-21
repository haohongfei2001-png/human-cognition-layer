"""Opt-in, content-free observations of the unchanged decision transport."""
from __future__ import annotations

import hashlib
import json
import sys
from typing import Any, Callable

from hcl.v03.answer_loop import extract_json


def emit_metadata(event: dict[str, Any]) -> None:
    print('HCL_DECISION_DIAGNOSTIC ' + json.dumps(event, sort_keys=True), file=sys.stderr)


class DecisionDiagnosticBackend:
    """Pass through exactly one call; telemetry cannot change its result or error."""

    def __init__(self, backend: Any, emit: Callable = emit_metadata) -> None:
        self.backend = backend
        self.emit = emit
        self.calls = 0

    def _emit(self, event: dict[str, Any]) -> None:
        try:
            self.emit(event)
        except Exception:
            # Observation failure must not cause a second provider call or replace an outcome.
            pass

    def complete(self, messages: list[dict[str, str]], *, max_tokens: int,
                 temperature: float = 0.0) -> str:
        self.calls += 1
        event = {'call': self.calls, 'max_tokens': max_tokens, 'temperature': temperature}
        try:
            raw = self.backend.complete(messages, max_tokens=max_tokens, temperature=temperature)
        except Exception:
            # Exception messages and provider metadata may contain credentials or user content.
            self._emit({**event, 'outcome': 'transport_exception'})
            raise
        try:
            encoded = raw.encode('utf-8')
            accepted = extract_json(raw) is not None
            outcome = 'accepted_object' if accepted else ('empty' if not raw.strip() else 'no_parseable_object')
            event.update(outcome=outcome, response_bytes=len(encoded),
                         response_sha256=hashlib.sha256(encoded).hexdigest())
            self._emit(event)
        except Exception:
            self._emit({**event, 'outcome': 'observation_unavailable'})
        return raw


def emit_provider_metadata(event: dict[str, Any]) -> None:
    print(
        'HCL_PROVIDER_ATTEMPT_DIAGNOSTIC ' + json.dumps(event, sort_keys=True),
        file=sys.stderr,
    )


class ProviderAttemptDiagnosticBackend:
    """Mirror the frozen four-attempt transport loop with metadata-only observation.

    This wrapper is runner-only and opt-in. It calls the same underlying client
    with the same request arguments, returns on the same first non-empty content,
    and propagates the same provider exception. Observation failures are inert.
    """

    def __init__(self, backend: Any, emit: Callable = emit_provider_metadata) -> None:
        self.backend = backend
        self.emit = emit
        self.calls = 0

    def _emit(self, event: dict[str, Any]) -> None:
        try:
            self.emit(event)
        except Exception:
            pass

    @staticmethod
    def _string_metadata(prefix: str, value: Any) -> dict[str, Any]:
        if not isinstance(value, str):
            return {}
        encoded = value.encode('utf-8')
        return {
            f'{prefix}_bytes': len(encoded),
            f'{prefix}_sha256': hashlib.sha256(encoded).hexdigest(),
        }

    @staticmethod
    def _extra_field(message: Any, name: str) -> Any:
        value = getattr(message, name, None)
        if value is not None:
            return value
        extra = getattr(message, 'model_extra', None)
        if isinstance(extra, dict):
            return extra.get(name)
        return None

    def complete(
        self,
        messages: list[dict[str, str]],
        *,
        max_tokens: int,
        temperature: float = 0.0,
    ) -> str:
        self.calls += 1
        backend_call = self.calls
        last = ""

        for provider_attempt in range(1, 5):
            base_event = {
                'backend_call': backend_call,
                'provider_attempt': provider_attempt,
                'max_tokens': max_tokens,
                'temperature': temperature,
            }
            try:
                response = self.backend.client.chat.completions.create(
                    model=self.backend.model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    seed=self.backend.seed,
                )
            except Exception:
                self._emit({**base_event, 'outcome': 'transport_exception'})
                raise

            # Keep the original transport semantics: these accesses and the
            # empty-string normalization are exactly what the unwrapped backend
            # performs before deciding whether to retry.
            choice = response.choices[0]
            message = choice.message
            last = message.content or ""

            try:
                event: dict[str, Any] = {
                    **base_event,
                    'outcome': 'content_nonempty' if last.strip() else 'content_empty',
                    'finish_reason': (
                        str(choice.finish_reason)
                        if getattr(choice, 'finish_reason', None) is not None
                        else None
                    ),
                    **self._string_metadata('content', last),
                }

                reasoning = self._extra_field(message, 'reasoning_content')
                event.update(self._string_metadata('reasoning', reasoning))

                refusal = self._extra_field(message, 'refusal')
                event.update(self._string_metadata('refusal', refusal))

                usage = getattr(response, 'usage', None)
                if usage is not None:
                    for attr in ('prompt_tokens', 'completion_tokens', 'total_tokens'):
                        value = getattr(usage, attr, None)
                        if isinstance(value, int):
                            event[attr] = value

                    details = getattr(usage, 'completion_tokens_details', None)
                    reasoning_tokens = (
                        getattr(details, 'reasoning_tokens', None)
                        if details is not None
                        else None
                    )
                    if isinstance(reasoning_tokens, int):
                        event['reasoning_tokens'] = reasoning_tokens

                self._emit(event)
            except Exception:
                self._emit({**base_event, 'outcome': 'observation_unavailable'})

            if last.strip():
                return last

        return last

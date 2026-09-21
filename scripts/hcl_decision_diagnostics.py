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

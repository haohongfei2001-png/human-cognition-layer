"""Provider-free primitives for the sealed LongMemEval C/D/G comparison.

No scorer or answer model can be called from this module. State arms receive
only the sanitized history view; answer packets require an ingestion receipt.
"""

from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import dataclass
from typing import Any

from scripts.qualify_longmemeval_knowledge_update_v01 import (
    assert_state_firewall,
    history_digest,
    state_input_view,
)
from scripts.run_v04_long_horizon_bounded_context_v01 import event_prompt_payload

GENERIC_UPDATE_SYSTEM = """Maintain generic structured memory from the previous
state and one timestamped conversation event. Return JSON only:
{"upserts":[{"entity":"...","attribute":"...","value":"...",
"note":"short evidence note"}]}
An empty upserts array is valid when the event gives no durable information.
Use ordinary entity/attribute/value reasoning. Preserve uncertainty in values
when warranted. Do not infer private mental states from silence. Do not use
specialized HCL stance types, transition rules, or perspective routing.
"""


class ProtocolError(ValueError):
    pass


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class IngestionReceipt:
    history_sha256: str
    d_events: int
    g_events: int
    expected_events: int

    def validate(self, view: dict[str, Any]) -> None:
        if self.history_sha256 != history_digest(view):
            raise ProtocolError("ingestion receipt history mismatch")
        if self.expected_events <= 0 or self.d_events != self.expected_events:
            raise ProtocolError("D ingestion did not complete")
        if self.g_events != self.expected_events:
            raise ProtocolError("G ingestion did not complete")


def answer_packet(row: dict[str, Any], receipt: IngestionReceipt) -> dict[str, Any]:
    """Release one equal oracle evidence packet only after both state ingests."""
    view = state_input_view(row)
    assert_state_firewall(row, view)
    receipt.validate(view)
    ids = row.get("answer_session_ids")
    if not isinstance(ids, list) or any(not isinstance(x, str) for x in ids):
        raise ProtocolError("oracle session IDs must be strings")
    if len(ids) != len(set(ids)):
        raise ProtocolError("duplicate oracle session ID")
    sessions = {s["session_id"]: s for s in view["history"]}
    if len(sessions) != len(view["history"]):
        raise ProtocolError("duplicate history session ID")
    if any(sid not in sessions for sid in ids):
        raise ProtocolError("oracle session ID missing from history")
    ordered = [s for s in view["history"] if s["session_id"] in set(ids)]
    question = row.get("question")
    if not isinstance(question, str) or not question.strip():
        raise ProtocolError("missing question")
    packet = {"question_id": row["question_id"], "question": question,
              "evidence": [{"session_id": s["session_id"], "date": s["date"],
                            "turns": s["turns"]} for s in ordered]}
    packet["packet_sha256"] = digest(packet)
    return packet


def arm_messages(packet: dict[str, Any], state: Any | None = None) -> list[dict[str, str]]:
    """Keep the answer instruction and common evidence byte-identical."""
    common = {"question": packet["question"], "evidence": packet["evidence"]}
    messages = [
        {"role": "system", "content": "Answer the question using the supplied evidence. If the evidence is insufficient, say so. Keep the answer concise."},
        {"role": "user", "content": canonical_json(common)},
    ]
    if state is not None:
        messages.append({"role": "user", "content": "Additional pre-question memory state: " + canonical_json(state)})
    return messages


def _text(value: Any, label: str, limit: int) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise ProtocolError(f"invalid {label}")
    return value.strip()


def validate_patch(patch: Any) -> list[dict[str, str]]:
    if not isinstance(patch, dict) or set(patch) != {"upserts"} or not isinstance(patch["upserts"], list):
        raise ProtocolError("generic patch must contain only upserts list")
    if len(patch["upserts"]) > 24:
        raise ProtocolError("too many generic upserts")
    result = []
    seen = set()
    for item in patch["upserts"]:
        if not isinstance(item, dict) or set(item) != {"entity", "attribute", "value", "note"}:
            raise ProtocolError("generic upsert schema invalid")
        record = {"entity": _text(item["entity"], "entity", 120),
                  "attribute": _text(item["attribute"], "attribute", 120),
                  "value": _text(item["value"], "value", 1000),
                  "note": _text(item["note"], "note", 240)}
        key = (record["entity"], record["attribute"])
        if key in seen:
            raise ProtocolError("duplicate generic key in patch")
        seen.add(key)
        result.append(record)
    return result


def compact_state(state: dict[str, Any], limit: int) -> dict[str, Any]:
    """Deterministically shed explanatory detail while retaining current values."""
    candidate = copy.deepcopy(state)
    if len(canonical_json(candidate)) <= limit:
        return candidate
    records = candidate["records"]
    for item in records:
        item["note"] = ""
        for old in item["history"]:
            old["note"] = ""
    if len(canonical_json(candidate)) <= limit:
        return candidate
    while any(item["history"] for item in records):
        oldest = min((item for item in records if item["history"]),
                     key=lambda item: (item["history"][0]["at"], item["entity"], item["attribute"]))
        oldest["history"].pop(0)
        if len(canonical_json(candidate)) <= limit:
            return candidate
    raise ProtocolError("active generic records exceed fixed budget")


class GenericMemory:
    def __init__(self, backend: Any, *, state_char_limit: int = 6000):
        if state_char_limit < 256:
            raise ProtocolError("generic state budget too small")
        self.backend = backend
        self.state_char_limit = state_char_limit
        self.state: dict[str, Any] = {"records": []}
        self.processed_events = 0

    def ingest(self, event: dict[str, Any]) -> None:
        """Process every event transactionally; never silently keep stale state."""
        required = {"event_id", "valid_time", "actor_id", "raw_text"}
        if not required <= set(event):
            raise ProtocolError("incomplete generic event")
        raw = self.backend.complete_json(
            [{"role": "system", "content": GENERIC_UPDATE_SYSTEM},
             {"role": "user", "content": canonical_json({"state": self.state,
                 "event": event_prompt_payload(event)})}],
            max_tokens=2048, temperature=0.0)
        try:
            upserts = validate_patch(json.loads(raw))
        except (json.JSONDecodeError, ProtocolError) as exc:
            raise ProtocolError(f"generic update invalid: {exc}") from exc
        candidate = copy.deepcopy(self.state)
        by_key = {(item["entity"], item["attribute"]): item for item in candidate["records"]}
        for upsert in upserts:
            key = (upsert["entity"], upsert["attribute"])
            prior = by_key.get(key)
            if prior is None:
                prior = {"entity": key[0], "attribute": key[1], "value": "",
                         "at": "", "source_event_id": "", "note": "", "history": []}
                candidate["records"].append(prior)
                by_key[key] = prior
            elif prior["value"] != upsert["value"]:
                prior["history"].append({"value": prior["value"], "at": prior["at"],
                                         "source_event_id": prior["source_event_id"], "note": prior["note"]})
            prior.update(value=upsert["value"], at=str(event["valid_time"]),
                         source_event_id=str(event["event_id"]), note=upsert["note"])
        candidate["records"].sort(key=lambda item: (item["entity"], item["attribute"]))
        candidate = compact_state(candidate, self.state_char_limit)
        self.state = candidate
        self.processed_events += 1

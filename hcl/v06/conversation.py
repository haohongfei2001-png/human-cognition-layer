"""Conversation-to-evidence adapter for HCL v0.6 perspective reasoning.

The model is used only to infer who could hear each already-parsed utterance.
It may not rewrite the transcript, invent participants, or extract benchmark
answers.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Protocol

from hcl.v04.model import EventRecord


class ConversationAdapterError(ValueError):
    pass


class ConversationBackend(Protocol):
    def complete_json(
        self,
        messages: list[dict[str, str]],
        *,
        max_tokens: int,
        temperature: float = 0.0,
    ) -> str:
        ...


@dataclass(frozen=True)
class ParsedTurn:
    turn_index: int
    speaker: str
    text: str


@dataclass(frozen=True)
class ConversationExtractionResult:
    events: tuple[EventRecord, ...]
    repair_count: int = 0
    repair_reason: str | None = None


SYSTEM_PROMPT = """Infer conversational information access from an in-person
multi-party transcript.

The transcript has already been deterministically split into turns. For every
turn, return which *other named participants* could hear that utterance at that
moment.

Return JSON only:
{
  "turn_access": [
    {"turn_index": 0, "heard_by_agent_ids": ["Name A", "Name B"]}
  ]
}

Rules:
- Output exactly one row for every supplied turn_index.
- Use only names from known_agent_ids.
- Do not include the turn's speaker in heard_by_agent_ids; the speaker already
  has access to their own utterance.
- Track explicit leave, departure, absence, return, rejoin, arrival and
  "welcome back" evidence across turns.
- A departure utterance is heard under the state before the departure; after
  that utterance the departing person is absent unless later return/re-entry is
  supported.
- A returning/joining person's own utterance is the first turn they necessarily
  hear on re-entry, unless the transcript explicitly says they heard earlier
  content.
- Do not assume an absent person heard missed conversation.
- Do not assume a late-joining participant was present earlier.
- If presence is genuinely ambiguous, be conservative: do not grant access
  without evidence.
- This is only an access map. Do not infer beliefs, motives, answers, gold
  labels, or what a benchmark question is asking.
"""


REPAIR_PROMPT = """Repair the conversation access map.

Return exactly one access row per supplied turn. Preserve the deterministic
speaker/text split. Use only known participant names. Do not grant access to an
absent or not-yet-joined participant without transcript evidence. Return JSON
only.
"""


def parse_transcript(transcript: str) -> tuple[ParsedTurn, ...]:
    turns: list[ParsedTurn] = []
    for raw_line in transcript.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if ":" not in line:
            if not turns:
                raise ConversationAdapterError(
                    "transcript begins with a non-speaker line"
                )
            prior = turns[-1]
            turns[-1] = ParsedTurn(
                turn_index=prior.turn_index,
                speaker=prior.speaker,
                text=prior.text + "\n" + line,
            )
            continue
        speaker, text = line.split(":", 1)
        speaker = speaker.strip()
        text = text.strip()
        if not speaker or not text:
            raise ConversationAdapterError("empty speaker or utterance")
        turns.append(
            ParsedTurn(
                turn_index=len(turns),
                speaker=speaker,
                text=text,
            )
        )
    if not turns:
        raise ConversationAdapterError("transcript contains no turns")
    return tuple(turns)


def _stable_event_id(conversation_id: str, turn: ParsedTurn) -> str:
    raw = json.dumps(
        [conversation_id, turn.turn_index, turn.speaker, turn.text],
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return "conv_" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:20]


def _event_time(index: int) -> tuple[str, str]:
    base = datetime(2000, 1, 1, tzinfo=timezone.utc) + timedelta(seconds=index)
    recorded = base + timedelta(microseconds=1)
    return base.isoformat(), recorded.isoformat()


def _parse_access_payload(
    payload: dict,
    *,
    turns: tuple[ParsedTurn, ...],
    known_agents: tuple[str, ...],
) -> tuple[tuple[str, ...], ...]:
    if not isinstance(payload, dict):
        raise ConversationAdapterError("adapter output must be an object")
    rows = payload.get("turn_access")
    if not isinstance(rows, list):
        raise ConversationAdapterError("turn_access must be a list")
    if len(rows) != len(turns):
        raise ConversationAdapterError(
            f"turn_access length {len(rows)} != transcript turns {len(turns)}"
        )

    allowed = set(known_agents)
    by_index: dict[int, tuple[str, ...]] = {}
    for row in rows:
        if not isinstance(row, dict):
            raise ConversationAdapterError("turn_access row must be an object")
        idx = row.get("turn_index")
        if not isinstance(idx, int) or not 0 <= idx < len(turns):
            raise ConversationAdapterError("invalid turn_index")
        if idx in by_index:
            raise ConversationAdapterError("duplicate turn_index")
        listeners = row.get("heard_by_agent_ids")
        if not isinstance(listeners, list):
            raise ConversationAdapterError("heard_by_agent_ids must be a list")
        clean = tuple(sorted({str(x).strip() for x in listeners if str(x).strip()}))
        if any(x not in allowed for x in clean):
            raise ConversationAdapterError("adapter invented unknown participant")
        if turns[idx].speaker in clean:
            raise ConversationAdapterError("speaker must not be repeated as listener")
        by_index[idx] = clean

    if set(by_index) != set(range(len(turns))):
        raise ConversationAdapterError("missing turn access row")
    return tuple(by_index[i] for i in range(len(turns)))


def extract_conversation_events(
    transcript: str,
    conversation_id: str,
    backend: ConversationBackend,
    *,
    max_tokens: int = 4096,
) -> ConversationExtractionResult:
    if not conversation_id.strip():
        raise ConversationAdapterError("conversation_id must not be empty")
    turns = parse_transcript(transcript)
    known_agents = tuple(sorted({turn.speaker for turn in turns}))
    model_payload = {
        "known_agent_ids": list(known_agents),
        "turns": [
            {
                "turn_index": turn.turn_index,
                "speaker": turn.speaker,
                "text": turn.text,
            }
            for turn in turns
        ],
    }
    raw = backend.complete_json(
        [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": json.dumps(model_payload, ensure_ascii=False, sort_keys=True),
            },
        ],
        max_tokens=max_tokens,
        temperature=0.0,
    )

    first_error: Exception | None = None
    for attempt in range(2):
        try:
            payload = json.loads(raw)
            access = _parse_access_payload(
                payload,
                turns=turns,
                known_agents=known_agents,
            )
            events: list[EventRecord] = []
            for turn, listeners in zip(turns, access):
                valid_time, recorded_at = _event_time(turn.turn_index)
                events.append(
                    EventRecord(
                        event_id=_stable_event_id(conversation_id, turn),
                        valid_time=valid_time,
                        recorded_at=recorded_at,
                        raw_text=f"{turn.speaker}: {turn.text}",
                        source_id=turn.speaker,
                        actor_id=turn.speaker,
                        observer_ids=listeners,
                        recipient_ids=(),
                        semantic_version="v06.1",
                        metadata={
                            "conversation_id": conversation_id,
                            "turn_index": turn.turn_index,
                            "adapter": "v06_conversation_access_v01",
                        },
                    )
                )
            return ConversationExtractionResult(
                events=tuple(events),
                repair_count=attempt,
                repair_reason=(
                    None
                    if attempt == 0
                    else f"conversation access repair after: {first_error}"
                ),
            )
        except (json.JSONDecodeError, ConversationAdapterError) as exc:
            if first_error is None:
                first_error = exc
            if attempt == 1:
                raise ConversationAdapterError(
                    f"conversation access invalid after bounded repair: {exc}"
                ) from exc
            raw = backend.complete_json(
                [
                    {"role": "system", "content": REPAIR_PROMPT},
                    {
                        "role": "user",
                        "content": json.dumps(
                            {
                                **model_payload,
                                "invalid_output": raw,
                                "validation_error": str(exc),
                            },
                            ensure_ascii=False,
                            sort_keys=True,
                        ),
                    },
                ],
                max_tokens=max_tokens,
                temperature=0.0,
            )

    raise ConversationAdapterError("conversation access extraction failed")


__all__ = [
    "ConversationAdapterError",
    "ConversationBackend",
    "ConversationExtractionResult",
    "ParsedTurn",
    "extract_conversation_events",
    "parse_transcript",
]

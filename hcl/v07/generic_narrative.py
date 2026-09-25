"""Question-blind generic narrative chronology without intention projection."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable

from hcl.v04.model import EventRecord


_LEADING_ACTOR = re.compile(
    r"^(?P<actor>[A-Z][A-Za-z'’.-]*(?:\s+and\s+(?:his|her|their)\s+friends)?)\b"
)
_ENTITY = re.compile(r"\b[A-Z][a-z]+(?:[-'][A-Z]?[a-z]+)?\b")
_NON_NAME = {
    "A", "An", "The", "He", "She", "They", "His", "Her", "Their", "It",
    "In", "On", "At", "After", "Before", "When", "Then", "Finally", "One",
    "For", "But", "So", "As", "That", "This", "All", "First", "Next",
}


@dataclass(frozen=True)
class GenericNarrativeState:
    entities: tuple[str, ...]
    timeline: tuple[dict, ...]

    @classmethod
    def from_events(cls, events: Iterable[EventRecord]) -> "GenericNarrativeState":
        ordered = tuple(sorted(events, key=lambda e: (e.valid_time, e.recorded_at, e.event_id)))
        if len({event.event_id for event in ordered}) != len(ordered):
            raise ValueError("generic narrative cannot merge duplicate source events")
        if not ordered or any(not event.raw_text.strip() for event in ordered):
            raise ValueError("generic narrative needs nonempty source events")
        if any(not event.metadata.get("reader_only") for event in ordered):
            raise ValueError("generic narrative expects reader-only source events")
        entities = tuple(sorted({
            name for event in ordered for name in _ENTITY.findall(event.raw_text)
            if name not in _NON_NAME
        }))
        timeline = []
        for event in ordered:
            match = _LEADING_ACTOR.match(event.raw_text)
            surface = match.group("actor") if match else None
            if surface in _NON_NAME:
                surface = None
            timeline.append({
                "event_id": event.event_id,
                "sentence_index": event.metadata.get("sentence_index"),
                "valid_time": event.valid_time,
                "recorded_at": event.recorded_at,
                "source_id": event.source_id,
                "actor_surface": surface,
                "entity_mentions": [name for name in entities if re.search(
                    rf"(?<!\w){re.escape(name)}(?!\w)", event.raw_text
                )],
                "event_text": event.raw_text,
                "provenance": "READER_ONLY_NARRATOR",
                "uncertainty": "The public narrative supports the event text; private motives are not supplied by action alone.",
            })
        return cls(entities=entities, timeline=tuple(timeline))

    def as_dict(self) -> dict:
        return {
            "schema": "generic_narrative_actor_time_source_event_v01",
            "entities": list(self.entities),
            "timeline": list(self.timeline),
            "event_count": len(self.timeline),
            "claim_policy": "Keep narrator provenance; action alone does not establish a unique private motive.",
        }

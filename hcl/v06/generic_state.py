"""Competent generic chronology baseline for the frozen v0.6 comparison.

This intentionally retains every event and ordinary access metadata while
omitting HCL's first/second-order belief projection. It is question-blind.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable

from hcl.v04.model import EventRecord


@dataclass(frozen=True)
class GenericStructuredState:
    participants: tuple[str, ...]
    timeline: tuple[dict, ...]

    @classmethod
    def from_events(cls, events: Iterable[EventRecord]) -> "GenericStructuredState":
        materialized = tuple(events)
        if len({event.event_id for event in materialized}) != len(materialized):
            raise ValueError("generic state cannot silently merge duplicate event IDs")
        ordered = tuple(sorted(materialized, key=lambda e: (e.valid_time, e.recorded_at, e.event_id)))
        agents = tuple(sorted({agent for e in ordered for agent in (
            (e.actor_id,) + e.observer_ids + e.recipient_ids
        ) if agent}))
        timeline = []
        for event in ordered:
            mentioned = [
                agent for agent in agents
                if re.search(rf"(?<!\w){re.escape(agent)}(?!\w)", event.raw_text, re.IGNORECASE)
            ]
            timeline.append({
                "event_id": event.event_id,
                "turn_index": event.metadata.get("turn_index"),
                "valid_time": event.valid_time,
                "recorded_at": event.recorded_at,
                "source_id": event.source_id,
                "actor_id": event.actor_id,
                "mentioned_agent_ids": mentioned,
                "heard_by_agent_ids": list(event.observer_ids),
                "recipient_ids": list(event.recipient_ids),
                "event_text": event.raw_text,
                "provenance": "DIRECT_UTTERANCE",
                "content_uncertainty": "SPEAKER_CLAIM_NOT_INDEPENDENTLY_VERIFIED",
            })
        if len(timeline) != len(ordered):
            raise AssertionError("generic state lost an event")
        return cls(participants=agents, timeline=tuple(timeline))

    def as_dict(self) -> dict:
        return {
            "schema": "generic_actor_time_source_event_access_v01",
            "participants": list(self.participants),
            "timeline": list(self.timeline),
            "event_count": len(self.timeline),
            "claim_policy": "Utterance content has speaker provenance; unstated beliefs and motives remain uncertain.",
        }

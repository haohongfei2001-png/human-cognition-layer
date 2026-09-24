"""SQLite persistence for HCL v0.5 raw evidence and stance semantics."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict
from datetime import datetime, timezone

from hcl.v04.model import EventRecord

from .stance import StanceEvent, StanceSignal


def _dumps(value) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class V05Store:
    def __init__(self, path: str = ":memory:") -> None:
        self.path = path
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self._init_schema()

    def _init_schema(self) -> None:
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS raw_events (
                event_id TEXT PRIMARY KEY,
                event_index INTEGER NOT NULL UNIQUE,
                valid_time TEXT NOT NULL,
                recorded_at TEXT NOT NULL,
                payload_json TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS stance_events (
                stance_event_id TEXT PRIMARY KEY,
                source_event_id TEXT NOT NULL,
                valid_time TEXT NOT NULL,
                system_record_time TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                FOREIGN KEY(source_event_id) REFERENCES raw_events(event_id)
            );

            CREATE INDEX IF NOT EXISTS idx_stance_source
                ON stance_events(source_event_id);
            CREATE INDEX IF NOT EXISTS idx_stance_subject_issue
                ON stance_events(
                    json_extract(payload_json, '$.subject_agent_id'),
                    json_extract(payload_json, '$.issue_key')
                );

            CREATE TABLE IF NOT EXISTS semantic_receipts (
                event_id TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                repair_count INTEGER NOT NULL DEFAULT 0,
                reason TEXT,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(event_id) REFERENCES raw_events(event_id),
                CHECK(status IN ('COMMITTED', 'FAILED'))
            );
            """
        )

    def close(self) -> None:
        self.conn.close()

    def _event_payload(self, event: EventRecord) -> dict:
        payload = asdict(event)
        payload["observer_ids"] = list(event.observer_ids)
        payload["recipient_ids"] = list(event.recipient_ids)
        return payload

    def _event_from_payload(self, payload: dict) -> EventRecord:
        return EventRecord(
            event_id=payload["event_id"],
            valid_time=payload["valid_time"],
            recorded_at=payload["recorded_at"],
            raw_text=payload["raw_text"],
            source_id=payload["source_id"],
            actor_id=payload.get("actor_id"),
            observer_ids=tuple(payload.get("observer_ids") or []),
            recipient_ids=tuple(payload.get("recipient_ids") or []),
            semantic_version=payload.get("semantic_version", "v04.1"),
            supersedes=payload.get("supersedes"),
            metadata=dict(payload.get("metadata") or {}),
        )

    def _stance_payload(self, event: StanceEvent) -> dict:
        payload = asdict(event)
        payload["signal"] = event.signal.value
        payload["evidence_event_ids"] = list(event.evidence_event_ids)
        return payload

    def _stance_from_payload(self, payload: dict) -> StanceEvent:
        return StanceEvent(
            event_id=payload["event_id"],
            subject_agent_id=payload["subject_agent_id"],
            issue_key=payload["issue_key"],
            signal=StanceSignal(payload["signal"]),
            value_key=payload.get("value_key"),
            prior_value_key=payload.get("prior_value_key"),
            valid_time=payload["valid_time"],
            system_record_time=payload["system_record_time"],
            evidence_event_ids=tuple(payload.get("evidence_event_ids") or []),
        )

    def append_event(self, event: EventRecord) -> bool:
        payload_json = _dumps(self._event_payload(event))
        existing = self.conn.execute(
            "SELECT payload_json FROM raw_events WHERE event_id=?",
            (event.event_id,),
        ).fetchone()
        if existing is not None:
            if existing["payload_json"] != payload_json:
                raise ValueError(
                    f"event_id {event.event_id!r} already exists with different content"
                )
            return True

        row = self.conn.execute(
            "SELECT COALESCE(MAX(event_index), 0) + 1 AS next_index FROM raw_events"
        ).fetchone()
        with self.conn:
            self.conn.execute(
                """
                INSERT INTO raw_events(
                    event_id, event_index, valid_time, recorded_at, payload_json
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    event.event_id,
                    int(row["next_index"]),
                    event.valid_time,
                    event.recorded_at,
                    payload_json,
                ),
            )
        return False

    def get_event(self, event_id: str) -> EventRecord:
        row = self.conn.execute(
            "SELECT payload_json FROM raw_events WHERE event_id=?",
            (event_id,),
        ).fetchone()
        if row is None:
            raise KeyError(event_id)
        return self._event_from_payload(json.loads(row["payload_json"]))

    def list_events(self) -> tuple[EventRecord, ...]:
        rows = self.conn.execute(
            "SELECT payload_json FROM raw_events ORDER BY event_index"
        ).fetchall()
        return tuple(
            self._event_from_payload(json.loads(row["payload_json"]))
            for row in rows
        )

    def semantic_status(self, event_id: str) -> str | None:
        row = self.conn.execute(
            "SELECT status FROM semantic_receipts WHERE event_id=?",
            (event_id,),
        ).fetchone()
        return None if row is None else str(row["status"])

    def semantic_failure_reason(self, event_id: str) -> str | None:
        row = self.conn.execute(
            "SELECT status, reason FROM semantic_receipts WHERE event_id=?",
            (event_id,),
        ).fetchone()
        if row is None or row["status"] != "FAILED":
            return None
        return str(row["reason"] or "")

    def semantic_failures(self) -> dict[str, str]:
        rows = self.conn.execute(
            """
            SELECT event_id, reason
            FROM semantic_receipts
            WHERE status='FAILED'
            ORDER BY event_id
            """
        ).fetchall()
        return {
            str(row["event_id"]): str(row["reason"] or "")
            for row in rows
        }

    def record_semantic_failure(self, event_id: str, reason: str) -> None:
        self.get_event(event_id)
        if self.semantic_status(event_id) == "COMMITTED":
            raise ValueError(
                f"event_id {event_id!r} already has committed stance semantics"
            )
        with self.conn:
            self.conn.execute(
                """
                INSERT INTO semantic_receipts(
                    event_id, status, repair_count, reason, updated_at
                ) VALUES (?, 'FAILED', 0, ?, ?)
                ON CONFLICT(event_id) DO UPDATE SET
                    status='FAILED',
                    repair_count=0,
                    reason=excluded.reason,
                    updated_at=excluded.updated_at
                """,
                (event_id, reason, _now_iso()),
            )

    def commit_semantics(
        self,
        source_event_id: str,
        stance_events: tuple[StanceEvent, ...],
        *,
        repair_count: int,
        repair_reason: str | None,
    ) -> None:
        self.get_event(source_event_id)
        if self.semantic_status(source_event_id) == "COMMITTED":
            raise ValueError(
                f"event_id {source_event_id!r} already has committed stance semantics"
            )

        payloads = [
            (event, _dumps(self._stance_payload(event)))
            for event in stance_events
        ]
        if len({event.event_id for event, _ in payloads}) != len(payloads):
            raise ValueError("duplicate stance event IDs in semantic commit")

        with self.conn:
            self.conn.execute(
                "DELETE FROM stance_events WHERE source_event_id=?",
                (source_event_id,),
            )
            for event, payload_json in payloads:
                self.conn.execute(
                    """
                    INSERT INTO stance_events(
                        stance_event_id, source_event_id, valid_time,
                        system_record_time, payload_json
                    ) VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        event.event_id,
                        source_event_id,
                        event.valid_time,
                        event.system_record_time,
                        payload_json,
                    ),
                )
            self.conn.execute(
                """
                INSERT INTO semantic_receipts(
                    event_id, status, repair_count, reason, updated_at
                ) VALUES (?, 'COMMITTED', ?, ?, ?)
                ON CONFLICT(event_id) DO UPDATE SET
                    status='COMMITTED',
                    repair_count=excluded.repair_count,
                    reason=excluded.reason,
                    updated_at=excluded.updated_at
                """,
                (
                    source_event_id,
                    int(repair_count),
                    repair_reason,
                    _now_iso(),
                ),
            )

    def stance_events_for_source(
        self,
        source_event_id: str,
    ) -> tuple[StanceEvent, ...]:
        if self.semantic_status(source_event_id) != "COMMITTED":
            return ()
        rows = self.conn.execute(
            """
            SELECT payload_json
            FROM stance_events
            WHERE source_event_id=?
            ORDER BY stance_event_id
            """,
            (source_event_id,),
        ).fetchall()
        return tuple(
            self._stance_from_payload(json.loads(row["payload_json"]))
            for row in rows
        )

    def all_stance_events(self) -> tuple[StanceEvent, ...]:
        rows = self.conn.execute(
            """
            SELECT payload_json
            FROM stance_events
            ORDER BY valid_time, system_record_time, stance_event_id
            """
        ).fetchall()
        return tuple(
            self._stance_from_payload(json.loads(row["payload_json"]))
            for row in rows
        )


__all__ = ["V05Store"]

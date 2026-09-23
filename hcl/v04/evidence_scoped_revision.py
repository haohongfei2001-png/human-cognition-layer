"""Always-on evidence with bounded, target-scoped hypothesis revision.

Raw events are durable immediately. Derived hypotheses are never exposed as
current while a target has unprocessed evidence. Explicit scope can omit an
event; absent scope is conservatively relevant to every target.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from .hypotheses import (
    HypothesisBackend,
    HypothesisState,
    HypothesisTarget,
    HypothesisTracker,
    HypothesisUpdateReceipt,
)
from .model import EventReceipt, EventRecord
from .schema import SchemaValidationError
from .store import CognitionStore


class PendingEvidenceError(RuntimeError):
    """A decision must wait for a validated revision of pending evidence."""


@dataclass(frozen=True)
class RevisionResult:
    state: HypothesisState
    new_event_ids: tuple[str, ...]
    receipt: HypothesisUpdateReceipt | None
    skipped_unrelated: int


class EvidenceScopedRevision:
    def __init__(self, store: CognitionStore) -> None:
        self.store = store
        self.conn = store.conn
        self.tracker = HypothesisTracker(store)
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS evidence_revision_scopes (
                event_id TEXT PRIMARY KEY,
                target_ids_json TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS evidence_revision_cursors (
                target_id TEXT PRIMARY KEY,
                through_event_index INTEGER NOT NULL
            );
            """
        )

    def register_target(self, target: HypothesisTarget) -> HypothesisUpdateReceipt:
        receipt = self.tracker.create_target(target)
        with self.conn:
            self.conn.execute(
                "INSERT OR IGNORE INTO evidence_revision_cursors(target_id, through_event_index) VALUES (?, 0)",
                (target.target_id,),
            )
        return receipt

    def record(
        self,
        event: EventRecord,
        *,
        target_ids: tuple[str, ...] | None = None,
    ) -> EventReceipt:
        if target_ids is not None:
            if not target_ids or len(set(target_ids)) != len(target_ids):
                raise SchemaValidationError("explicit target scope must be non-empty and unique")
            for target_id in target_ids:
                self.tracker.current(target_id)
        receipt = self.store.append_event(event)
        if target_ids is not None and not receipt.duplicate:
            with self.conn:
                self.conn.execute(
                    "INSERT INTO evidence_revision_scopes(event_id, target_ids_json) VALUES (?, ?)",
                    (event.event_id, json.dumps(sorted(target_ids))),
                )
        elif receipt.duplicate:
            row = self.conn.execute(
                "SELECT target_ids_json FROM evidence_revision_scopes WHERE event_id=?",
                (event.event_id,),
            ).fetchone()
            if row is not None and target_ids is not None and json.loads(row[0]) != sorted(target_ids):
                raise SchemaValidationError("duplicate event cannot change its target scope")
        return receipt

    def _cursor(self, target_id: str) -> int:
        row = self.conn.execute(
            "SELECT through_event_index FROM evidence_revision_cursors WHERE target_id=?",
            (target_id,),
        ).fetchone()
        if row is None:
            raise KeyError(f"unregistered evidence-scoped target: {target_id}")
        return int(row[0])

    def _latest_index(self) -> int:
        row = self.conn.execute("SELECT COALESCE(MAX(event_index), 0) FROM events").fetchone()
        return int(row[0])

    def _relevant(self, target_id: str, *, after: int = 0, through: int | None = None) -> tuple[str, ...]:
        limit = self._latest_index() if through is None else through
        rows = self.conn.execute(
            """
            SELECT e.event_id, s.target_ids_json FROM events e
            LEFT JOIN evidence_revision_scopes s ON s.event_id=e.event_id
            WHERE e.event_index>? AND e.event_index<=?
            ORDER BY e.event_index
            """,
            (after, limit),
        ).fetchall()
        return tuple(
            str(row[0]) for row in rows
            if row[1] is None or target_id in json.loads(row[1])
        )

    def current(self, target_id: str) -> HypothesisState:
        cursor = self._cursor(target_id)
        if cursor < self._latest_index():
            raise PendingEvidenceError(f"target {target_id} has unprocessed evidence")
        state = self.tracker.current(target_id)
        allowed = set(self._relevant(target_id, through=cursor))
        for candidate in state.candidates:
            cited = (set(candidate.support_event_ids)
                     | set(candidate.counterevidence_event_ids)
                     | set(candidate.unresolved_event_ids))
            if not cited <= allowed:
                raise SchemaValidationError(
                    f"target {target_id} contains evidence outside its scope"
                )
        return state

    def refresh(self, target_id: str, backend: HypothesisBackend) -> RevisionResult:
        cursor = self._cursor(target_id)
        latest = self._latest_index()
        pending = self._relevant(target_id, after=cursor, through=latest)
        receipt = None
        if pending:
            last = self.conn.execute(
                """SELECT new_event_ids_json FROM hypothesis_versions
                   WHERE target_id=? ORDER BY version DESC LIMIT 1""",
                (target_id,),
            ).fetchone()
            already_committed = last is not None and tuple(json.loads(last[0])) == pending
            if not already_committed:
                allowed = set(self._relevant(target_id, through=latest))
                receipt = self.tracker.update(
                    target_id, pending, backend, allowed_event_ids=allowed,
                )
        with self.conn:
            self.conn.execute(
                "UPDATE evidence_revision_cursors SET through_event_index=? WHERE target_id=?",
                (latest, target_id),
            )
        return RevisionResult(
            state=self.current(target_id),
            new_event_ids=pending,
            receipt=receipt,
            skipped_unrelated=(latest - cursor) - len(pending),
        )

"""SQLite-backed evidence and derived-cognition store for HCL v0.4."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import asdict
from datetime import datetime
from typing import Iterable

from .model import (
    AssertionStatus,
    AssertionType,
    BeliefStance,
    CognitiveAssertion,
    EventReceipt,
    EventRecord,
    InvalidationReceipt,
    Proposition,
    QueryContext,
    RebuildReceipt,
    SemanticPatch,
    StateReceipt,
    SupportLevel,
    utc_now_iso,
)
from .schema import (
    SchemaValidationError,
    validate_event,
    validate_patch_structure,
)


def _dumps(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _loads(value: str | None, default):
    if value is None or value == "":
        return default
    return json.loads(value)


def _parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _time_leq(left: str, right: str | None) -> bool:
    if right is None:
        return True
    return _parse_time(left) <= _parse_time(right)


class CognitionStore:
    """Evidence-first store.

    Raw events remain the source layer. Propositions/assertions are derived state
    and can be invalidated or rebuilt.
    """

    def __init__(self, path: str = ":memory:") -> None:
        self.path = path
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self._init_schema()

    def close(self) -> None:
        self.conn.close()

    def _init_schema(self) -> None:
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS meta (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS events (
                event_id TEXT PRIMARY KEY,
                event_index INTEGER NOT NULL UNIQUE,
                valid_time TEXT NOT NULL,
                recorded_at TEXT NOT NULL,
                raw_text TEXT NOT NULL,
                source_id TEXT NOT NULL,
                actor_id TEXT,
                observer_ids TEXT NOT NULL,
                recipient_ids TEXT NOT NULL,
                semantic_version TEXT NOT NULL,
                supersedes TEXT,
                metadata TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS propositions (
                proposition_id TEXT PRIMARY KEY,
                canonical_text TEXT NOT NULL,
                polarity TEXT NOT NULL,
                relation_metadata TEXT NOT NULL,
                valid_time_start TEXT,
                valid_time_end TEXT,
                source_event_ids TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS assertions (
                assertion_id TEXT PRIMARY KEY,
                assertion_type TEXT NOT NULL,
                subject_agent_id TEXT,
                proposition_id TEXT,
                related_proposition_id TEXT,
                hypothesis_text TEXT,
                valid_time TEXT NOT NULL,
                system_record_time TEXT NOT NULL,
                evidence_event_ids TEXT NOT NULL,
                depends_on_assertion_ids TEXT NOT NULL,
                status TEXT NOT NULL,
                support_level TEXT,
                belief_stance TEXT,
                semantic_version TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS dependencies (
                parent_assertion_id TEXT NOT NULL,
                child_assertion_id TEXT NOT NULL,
                PRIMARY KEY (parent_assertion_id, child_assertion_id)
            );

            CREATE TABLE IF NOT EXISTS patches (
                patch_id TEXT PRIMARY KEY,
                event_id TEXT NOT NULL,
                semantic_version TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                status TEXT NOT NULL,
                applied_state_version INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS assertion_invalidations (
                assertion_id TEXT NOT NULL,
                state_version INTEGER NOT NULL,
                invalidated_at TEXT NOT NULL,
                reason TEXT NOT NULL,
                PRIMARY KEY (assertion_id, state_version)
            );

            CREATE TABLE IF NOT EXISTS snapshots (
                state_version INTEGER PRIMARY KEY,
                through_event_id TEXT,
                event_index INTEGER,
                created_at TEXT NOT NULL,
                semantic_version TEXT NOT NULL,
                active_assertion_ids TEXT NOT NULL,
                checksum TEXT NOT NULL
            );
            """
        )
        assertion_columns = {
            row["name"]
            for row in self.conn.execute("PRAGMA table_info(assertions)").fetchall()
        }
        if "belief_stance" not in assertion_columns:
            with self.conn:
                self.conn.execute(
                    "ALTER TABLE assertions ADD COLUMN belief_stance TEXT"
                )
        if "related_proposition_id" not in assertion_columns:
            with self.conn:
                self.conn.execute(
                    "ALTER TABLE assertions ADD COLUMN related_proposition_id TEXT"
                )

        with self.conn:
            self.conn.execute(
                "INSERT OR IGNORE INTO meta(key, value) VALUES('state_version', '0')"
            )
            self.conn.execute(
                "INSERT OR IGNORE INTO meta(key, value) VALUES('semantic_version', 'v04.1')"
            )

    @property
    def state_version(self) -> int:
        row = self.conn.execute(
            "SELECT value FROM meta WHERE key='state_version'"
        ).fetchone()
        return int(row["value"])

    @property
    def semantic_version(self) -> str:
        row = self.conn.execute(
            "SELECT value FROM meta WHERE key='semantic_version'"
        ).fetchone()
        return str(row["value"])

    def _set_meta(self, key: str, value: str) -> None:
        self.conn.execute(
            "INSERT INTO meta(key, value) VALUES(?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, value),
        )

    def append_event(self, event: EventRecord) -> EventReceipt:
        validate_event(event)
        existing = self.conn.execute(
            "SELECT event_index, recorded_at, raw_text, source_id, valid_time "
            "FROM events WHERE event_id=?",
            (event.event_id,),
        ).fetchone()
        if existing:
            if (
                existing["raw_text"] != event.raw_text
                or existing["source_id"] != event.source_id
                or existing["valid_time"] != event.valid_time
            ):
                raise SchemaValidationError(
                    f"event_id collision with different content: {event.event_id}"
                )
            return EventReceipt(
                event_id=event.event_id,
                event_index=int(existing["event_index"]),
                recorded_at=str(existing["recorded_at"]),
                duplicate=True,
            )

        row = self.conn.execute(
            "SELECT COALESCE(MAX(event_index), 0) + 1 AS next_index FROM events"
        ).fetchone()
        event_index = int(row["next_index"])
        with self.conn:
            self.conn.execute(
                """
                INSERT INTO events(
                    event_id, event_index, valid_time, recorded_at, raw_text,
                    source_id, actor_id, observer_ids, recipient_ids,
                    semantic_version, supersedes, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event.event_id,
                    event_index,
                    event.valid_time,
                    event.recorded_at,
                    event.raw_text,
                    event.source_id,
                    event.actor_id,
                    _dumps(list(event.observer_ids)),
                    _dumps(list(event.recipient_ids)),
                    event.semantic_version,
                    event.supersedes,
                    _dumps(event.metadata),
                ),
            )
        return EventReceipt(
            event_id=event.event_id,
            event_index=event_index,
            recorded_at=event.recorded_at,
        )

    def get_event(self, event_id: str) -> EventRecord:
        row = self.conn.execute(
            "SELECT * FROM events WHERE event_id=?", (event_id,)
        ).fetchone()
        if not row:
            raise KeyError(f"unknown event_id: {event_id}")
        return self._row_to_event(row)

    def list_events(self) -> tuple[EventRecord, ...]:
        rows = self.conn.execute(
            "SELECT * FROM events ORDER BY event_index"
        ).fetchall()
        return tuple(self._row_to_event(row) for row in rows)

    def _row_to_event(self, row: sqlite3.Row) -> EventRecord:
        return EventRecord(
            event_id=row["event_id"],
            valid_time=row["valid_time"],
            recorded_at=row["recorded_at"],
            raw_text=row["raw_text"],
            source_id=row["source_id"],
            actor_id=row["actor_id"],
            observer_ids=tuple(_loads(row["observer_ids"], [])),
            recipient_ids=tuple(_loads(row["recipient_ids"], [])),
            semantic_version=row["semantic_version"],
            supersedes=row["supersedes"],
            metadata=dict(_loads(row["metadata"], {})),
        )

    def _event_accessible(self, event_id: str, viewer: str | None) -> bool:
        if viewer in (None, "__system__"):
            return True
        event = self.get_event(event_id)
        return bool(
            event.metadata.get("public")
            or event.actor_id == viewer
            or viewer in event.observer_ids
            or viewer in event.recipient_ids
        )

    def _existing_proposition_ids(self) -> set[str]:
        return {
            row["proposition_id"]
            for row in self.conn.execute("SELECT proposition_id FROM propositions")
        }

    def proposition_catalog(self, limit: int = 64) -> tuple[dict, ...]:
        """Return a bounded active proposition catalog for semantic revision linking."""
        rows = self.conn.execute(
            """
            SELECT p.proposition_id, p.canonical_text, p.source_event_ids
            FROM propositions p
            WHERE EXISTS (
                SELECT 1
                FROM assertions a
                WHERE a.proposition_id = p.proposition_id
                  AND a.status IN ('ACTIVE', 'UNRESOLVED')
            )
            ORDER BY p.rowid DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return tuple(
            {
                "proposition_id": row["proposition_id"],
                "canonical_text": row["canonical_text"],
                "source_event_ids": _loads(row["source_event_ids"], []),
            }
            for row in rows
        )

    def _existing_assertion_ids(self) -> set[str]:
        return {
            row["assertion_id"]
            for row in self.conn.execute("SELECT assertion_id FROM assertions")
        }

    def validate_patch_candidate(self, patch: SemanticPatch) -> None:
        """Validate a candidate patch without mutating committed state."""
        self._validate_patch_against_store(patch)

    def independently_valid_assertions(
        self,
        patch: SemanticPatch,
    ) -> tuple[CognitiveAssertion, ...]:
        """Return assertions that are independently safe to preserve.

        Assertions with unresolved intra-patch dependencies are intentionally
        excluded from this preservation set and must be regenerated/revalidated
        by the semantic repair step.
        """
        valid: list[CognitiveAssertion] = []
        for assertion in patch.assertions:
            probe = SemanticPatch(
                patch_id=f"{patch.patch_id}:probe:{assertion.assertion_id}",
                event_id=patch.event_id,
                semantic_version=patch.semantic_version,
                propositions=patch.propositions,
                assertions=(assertion,),
            )
            try:
                self._validate_patch_against_store(probe)
            except SchemaValidationError:
                continue
            valid.append(assertion)
        return tuple(valid)

    def _validate_patch_against_store(self, patch: SemanticPatch) -> None:
        validate_patch_structure(patch)
        self.get_event(patch.event_id)

        event_ids = {event.event_id for event in self.list_events()}
        existing_proposition_ids = self._existing_proposition_ids()
        revision_target_ids = {
            item["proposition_id"] for item in self.proposition_catalog()
        }
        proposition_ids = existing_proposition_ids | {
            p.proposition_id for p in patch.propositions
        }
        assertion_ids = self._existing_assertion_ids() | {
            a.assertion_id for a in patch.assertions
        }

        for proposition in patch.propositions:
            missing = set(proposition.source_event_ids) - event_ids
            if missing:
                raise SchemaValidationError(
                    f"proposition references missing events: {sorted(missing)}"
                )

        for assertion in patch.assertions:
            missing_events = set(assertion.evidence_event_ids) - event_ids
            if missing_events:
                raise SchemaValidationError(
                    f"assertion references missing events: {sorted(missing_events)}"
                )
            if assertion.proposition_id and assertion.proposition_id not in proposition_ids:
                raise SchemaValidationError(
                    f"assertion references missing proposition: {assertion.proposition_id}"
                )
            if (
                assertion.related_proposition_id
                and assertion.related_proposition_id not in revision_target_ids
            ):
                raise SchemaValidationError(
                    "revision target must be present in the bounded active "
                    "proposition catalog: "
                    f"{assertion.related_proposition_id}"
                )
            missing_dependencies = (
                set(assertion.depends_on_assertion_ids) - assertion_ids
            )
            if missing_dependencies:
                raise SchemaValidationError(
                    "assertion references missing dependencies: "
                    f"{sorted(missing_dependencies)}"
                )
            if assertion.assertion_type == AssertionType.INFORMATION_EXPOSURE:
                subject = assertion.subject_agent_id
                if not subject:
                    raise SchemaValidationError(
                        "INFORMATION_EXPOSURE requires subject_agent_id"
                    )
                if not assertion.evidence_event_ids:
                    raise SchemaValidationError(
                        "INFORMATION_EXPOSURE requires evidence_event_ids"
                    )
                if not any(
                    self._event_accessible(event_id, subject)
                    for event_id in assertion.evidence_event_ids
                ):
                    raise SchemaValidationError(
                        "INFORMATION_EXPOSURE has no evidence path to subject"
                    )

    def _proposition_payload(self, proposition: Proposition) -> dict:
        return asdict(proposition)

    def _assertion_payload(self, assertion: CognitiveAssertion) -> dict:
        payload = asdict(assertion)
        payload["assertion_type"] = assertion.assertion_type.value
        payload["status"] = assertion.status.value
        payload["support_level"] = (
            assertion.support_level.value if assertion.support_level else None
        )
        payload["belief_stance"] = (
            assertion.belief_stance.value if assertion.belief_stance else None
        )
        return payload

    def _patch_payload(self, patch: SemanticPatch) -> dict:
        return {
            "patch_id": patch.patch_id,
            "event_id": patch.event_id,
            "semantic_version": patch.semantic_version,
            "propositions": [
                self._proposition_payload(p) for p in patch.propositions
            ],
            "assertions": [
                self._assertion_payload(a) for a in patch.assertions
            ],
        }

    def _patch_from_payload(self, payload: dict) -> SemanticPatch:
        propositions = tuple(
            Proposition(
                proposition_id=p["proposition_id"],
                canonical_text=p["canonical_text"],
                polarity=p.get("polarity", "POSITIVE"),
                relation_metadata=dict(p.get("relation_metadata") or {}),
                valid_time_start=p.get("valid_time_start"),
                valid_time_end=p.get("valid_time_end"),
                source_event_ids=tuple(p.get("source_event_ids") or []),
            )
            for p in payload.get("propositions", [])
        )
        assertions = []
        for a in payload.get("assertions", []):
            support = a.get("support_level")
            assertions.append(
                CognitiveAssertion(
                    assertion_id=a["assertion_id"],
                    assertion_type=AssertionType(a["assertion_type"]),
                    subject_agent_id=a.get("subject_agent_id"),
                    proposition_id=a.get("proposition_id"),
                    related_proposition_id=a.get("related_proposition_id"),
                    hypothesis_text=a.get("hypothesis_text"),
                    valid_time=a["valid_time"],
                    system_record_time=a["system_record_time"],
                    evidence_event_ids=tuple(a.get("evidence_event_ids") or []),
                    depends_on_assertion_ids=tuple(
                        a.get("depends_on_assertion_ids") or []
                    ),
                    status=AssertionStatus(a.get("status", "ACTIVE")),
                    support_level=SupportLevel(support) if support else None,
                    belief_stance=(
                        BeliefStance(a["belief_stance"])
                        if a.get("belief_stance")
                        else None
                    ),
                    semantic_version=a.get(
                        "semantic_version", payload["semantic_version"]
                    ),
                )
            )
        return SemanticPatch(
            patch_id=payload["patch_id"],
            event_id=payload["event_id"],
            semantic_version=payload["semantic_version"],
            propositions=propositions,
            assertions=tuple(assertions),
        )

    def apply_patch(
        self, expected_version: int, patch: SemanticPatch
    ) -> StateReceipt:
        existing = self.conn.execute(
            "SELECT applied_state_version FROM patches WHERE patch_id=?",
            (patch.patch_id,),
        ).fetchone()
        if existing:
            version = int(existing["applied_state_version"])
            snap = self.conn.execute(
                "SELECT checksum FROM snapshots WHERE state_version=?",
                (version,),
            ).fetchone()
            return StateReceipt(
                patch_id=patch.patch_id,
                state_version=version,
                checksum=snap["checksum"] if snap else self._checksum(),
                duplicate=True,
            )

        if expected_version != self.state_version:
            raise RuntimeError(
                f"state version mismatch: expected {expected_version}, "
                f"actual {self.state_version}"
            )

        self._validate_patch_against_store(patch)

        new_version = self.state_version + 1
        payload_json = _dumps(self._patch_payload(patch))

        with self.conn:
            for proposition in patch.propositions:
                row = self.conn.execute(
                    "SELECT canonical_text FROM propositions WHERE proposition_id=?",
                    (proposition.proposition_id,),
                ).fetchone()
                if row:
                    if row["canonical_text"] != proposition.canonical_text:
                        raise SchemaValidationError(
                            "proposition_id collision with different canonical text: "
                            f"{proposition.proposition_id}"
                        )
                    continue
                self.conn.execute(
                    """
                    INSERT INTO propositions(
                        proposition_id, canonical_text, polarity,
                        relation_metadata, valid_time_start, valid_time_end,
                        source_event_ids
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        proposition.proposition_id,
                        proposition.canonical_text,
                        proposition.polarity,
                        _dumps(proposition.relation_metadata),
                        proposition.valid_time_start,
                        proposition.valid_time_end,
                        _dumps(list(proposition.source_event_ids)),
                    ),
                )

            for assertion in patch.assertions:
                self.conn.execute(
                    """
                    INSERT INTO assertions(
                        assertion_id, assertion_type, subject_agent_id,
                        proposition_id, related_proposition_id, hypothesis_text,
                        valid_time, system_record_time, evidence_event_ids,
                        depends_on_assertion_ids, status, support_level,
                        belief_stance, semantic_version
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        assertion.assertion_id,
                        assertion.assertion_type.value,
                        assertion.subject_agent_id,
                        assertion.proposition_id,
                        assertion.related_proposition_id,
                        assertion.hypothesis_text,
                        assertion.valid_time,
                        assertion.system_record_time,
                        _dumps(list(assertion.evidence_event_ids)),
                        _dumps(list(assertion.depends_on_assertion_ids)),
                        assertion.status.value,
                        (
                            assertion.support_level.value
                            if assertion.support_level
                            else None
                        ),
                        (
                            assertion.belief_stance.value
                            if assertion.belief_stance
                            else None
                        ),
                        assertion.semantic_version,
                    ),
                )
                for parent in assertion.depends_on_assertion_ids:
                    self.conn.execute(
                        """
                        INSERT OR IGNORE INTO dependencies(
                            parent_assertion_id, child_assertion_id
                        ) VALUES (?, ?)
                        """,
                        (parent, assertion.assertion_id),
                    )

            self.conn.execute(
                """
                INSERT INTO patches(
                    patch_id, event_id, semantic_version, payload_json,
                    status, applied_state_version
                ) VALUES (?, ?, ?, ?, 'ACTIVE', ?)
                """,
                (
                    patch.patch_id,
                    patch.event_id,
                    patch.semantic_version,
                    payload_json,
                    new_version,
                ),
            )
            self._set_meta("state_version", str(new_version))
            self._set_meta("semantic_version", patch.semantic_version)
            checksum = self._create_snapshot(new_version)

        return StateReceipt(
            patch_id=patch.patch_id,
            state_version=new_version,
            checksum=checksum,
        )

    def _active_assertion_rows(self) -> list[sqlite3.Row]:
        return self.conn.execute(
            """
            SELECT * FROM assertions
            WHERE status IN ('ACTIVE', 'UNRESOLVED')
            ORDER BY assertion_id
            """
        ).fetchall()

    def _checksum(self) -> str:
        assertions = [dict(row) for row in self._active_assertion_rows()]
        propositions = [
            dict(row)
            for row in self.conn.execute(
                "SELECT * FROM propositions ORDER BY proposition_id"
            ).fetchall()
        ]
        payload = _dumps(
            {"assertions": assertions, "propositions": propositions}
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def _create_snapshot(self, version: int) -> str:
        last_event = self.conn.execute(
            "SELECT event_id, event_index FROM events ORDER BY event_index DESC LIMIT 1"
        ).fetchone()
        active_ids = [
            row["assertion_id"] for row in self._active_assertion_rows()
        ]
        checksum = self._checksum()
        self.conn.execute(
            """
            INSERT OR REPLACE INTO snapshots(
                state_version, through_event_id, event_index, created_at,
                semantic_version, active_assertion_ids, checksum
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                version,
                last_event["event_id"] if last_event else None,
                int(last_event["event_index"]) if last_event else None,
                utc_now_iso(),
                self.semantic_version,
                _dumps(active_ids),
                checksum,
            ),
        )
        return checksum

    def _assertion_dict(
        self, row: sqlite3.Row | dict, proposition_texts: dict[str, str] | None = None
    ) -> dict:
        proposition_text = None
        if row["proposition_id"]:
            if isinstance(row, dict) and "_historical_proposition_text" in row:
                proposition_text = row["_historical_proposition_text"]
            elif proposition_texts is not None:
                proposition_text = proposition_texts.get(row["proposition_id"])
            else:
                proposition = self.conn.execute(
                    "SELECT canonical_text FROM propositions WHERE proposition_id=?",
                    (row["proposition_id"],),
                ).fetchone()
                if proposition:
                    proposition_text = proposition["canonical_text"]
        return {
            "assertion_id": row["assertion_id"],
            "assertion_type": row["assertion_type"],
            "subject_agent_id": row["subject_agent_id"],
            "proposition_id": row["proposition_id"],
            "proposition_text": proposition_text,
            "related_proposition_id": (
                row.get("related_proposition_id")
                if isinstance(row, dict)
                else row["related_proposition_id"]
            ),
            "hypothesis_text": row["hypothesis_text"],
            "valid_time": row["valid_time"],
            "system_record_time": row["system_record_time"],
            "evidence_event_ids": _loads(row["evidence_event_ids"], []),
            "depends_on_assertion_ids": _loads(
                row["depends_on_assertion_ids"], []
            ),
            "status": row["status"],
            "support_level": row["support_level"],
            "belief_stance": row["belief_stance"],
            "semantic_version": row["semantic_version"],
        }

    def _event_dict(self, event: EventRecord) -> dict:
        payload = asdict(event)
        payload["observer_ids"] = list(event.observer_ids)
        payload["recipient_ids"] = list(event.recipient_ids)
        return payload

    def _assertion_evidence_closure(
        self,
        assertion_id: str,
        by_id: dict[str, sqlite3.Row | dict],
        visiting: set[str] | None = None,
    ) -> set[str]:
        visiting = set() if visiting is None else set(visiting)
        if assertion_id in visiting:
            return set()
        visiting.add(assertion_id)
        row = by_id[assertion_id]
        events = set(_loads(row["evidence_event_ids"], []))
        proposition_id = row["proposition_id"]
        if proposition_id:
            if isinstance(row, dict) and "_historical_proposition_source_ids" in row:
                events.update(row["_historical_proposition_source_ids"])
            else:
                proposition = self.conn.execute(
                    "SELECT source_event_ids FROM propositions WHERE proposition_id=?",
                    (proposition_id,),
                ).fetchone()
                if proposition:
                    events.update(_loads(proposition["source_event_ids"], []))
        for parent in _loads(row["depends_on_assertion_ids"], []):
            if parent in by_id:
                events |= self._assertion_evidence_closure(
                    parent, by_id, visiting
                )
        return events

    def _historical_assertion_rows(
        self, knowledge_cutoff: str
    ) -> tuple[list[dict], dict[str, str], bool]:
        """Reconstruct the accepted semantic state before later invalidations.

        Patch payloads are immutable even when a rebuild replaces the derived
        tables. An invalidation is a separate system-time event, so current
        assertion status cannot answer an earlier knowledge-cutoff query.
        """
        invalidations: dict[str, list[tuple[int, str]]] = {}
        for row in self.conn.execute(
            "SELECT assertion_id, state_version, invalidated_at "
            "FROM assertion_invalidations ORDER BY state_version"
        ):
            invalidations.setdefault(row["assertion_id"], []).append(
                (int(row["state_version"]), row["invalidated_at"])
            )
        current_status = {
            row["assertion_id"]: row["status"]
            for row in self.conn.execute("SELECT assertion_id, status FROM assertions")
        }
        propositions: dict[str, str] = {}
        proposition_sources: dict[str, tuple[str, ...]] = {}
        assertions: dict[str, dict] = {}
        incomplete_legacy_history = False
        for patch_row in self.conn.execute(
            "SELECT payload_json, status, applied_state_version FROM patches "
            "ORDER BY applied_state_version, patch_id"
        ):
            payload = _loads(patch_row["payload_json"], {})
            for proposition in payload.get("propositions", []):
                propositions[proposition["proposition_id"]] = proposition["canonical_text"]
                proposition_sources[proposition["proposition_id"]] = tuple(
                    proposition.get("source_event_ids") or []
                )
            applied_version = int(patch_row["applied_state_version"])
            for original in payload.get("assertions", []):
                assertion_id = original["assertion_id"]
                if not _time_leq(original["system_record_time"], knowledge_cutoff):
                    continue
                events = invalidations.get(assertion_id, [])
                invalidated = any(
                    version > applied_version and _time_leq(at, knowledge_cutoff)
                    for version, at in events
                )
                # Old databases lack invalidation-time receipts. Never turn an
                # unrecorded invalid assertion into historical evidence.
                if not events and (
                    patch_row["status"] != "ACTIVE"
                    or current_status.get(assertion_id) not in ("ACTIVE", "UNRESOLVED")
                ):
                    invalidated = True
                    incomplete_legacy_history = True
                if invalidated or original["status"] not in ("ACTIVE", "UNRESOLVED"):
                    assertions.pop(assertion_id, None)
                    continue
                row = dict(original)
                row["_historical_proposition_text"] = propositions.get(
                    original.get("proposition_id")
                )
                row["_historical_proposition_source_ids"] = proposition_sources.get(
                    original.get("proposition_id"), ()
                )
                row["evidence_event_ids"] = _dumps(original.get("evidence_event_ids") or [])
                row["depends_on_assertion_ids"] = _dumps(
                    original.get("depends_on_assertion_ids") or []
                )
                assertions[assertion_id] = row
        return [assertions[key] for key in sorted(assertions)], propositions, incomplete_legacy_history

    def build_view(
        self,
        viewer: str | None,
        event_time: str | None,
        knowledge_cutoff: str | None,
        query: str,
    ) -> QueryContext:
        if knowledge_cutoff is None:
            rows = self._active_assertion_rows()
            proposition_texts = None
            incomplete_legacy_history = False
        else:
            rows, proposition_texts, incomplete_legacy_history = (
                self._historical_assertion_rows(knowledge_cutoff)
            )
        by_id = {row["assertion_id"]: row for row in rows}

        included: list[sqlite3.Row] = []
        evidence_ids: set[str] = set()
        for row in rows:
            if not _time_leq(row["valid_time"], event_time):
                continue
            if not _time_leq(row["system_record_time"], knowledge_cutoff):
                continue

            closure = self._assertion_evidence_closure(
                row["assertion_id"], by_id
            )
            if knowledge_cutoff is not None and any(
                not _time_leq(self.get_event(event_id).recorded_at, knowledge_cutoff)
                for event_id in closure
            ):
                continue
            if viewer not in (None, "__system__"):
                if not closure:
                    continue
                if not all(
                    self._event_accessible(event_id, viewer)
                    for event_id in closure
                ):
                    continue
            included.append(row)
            evidence_ids |= closure

        def related_proposition_id(row) -> str | None:
            if isinstance(row, dict):
                return row.get("related_proposition_id")
            return row["related_proposition_id"]

        def record_at_or_after(row, reference) -> bool:
            row_valid = _parse_time(row["valid_time"])
            ref_valid = _parse_time(reference["valid_time"])
            if row_valid != ref_valid:
                return row_valid > ref_valid
            return _parse_time(row["system_record_time"]) >= _parse_time(
                reference["system_record_time"]
            )

        revisions_by_new: dict[str, list[tuple[str, sqlite3.Row | dict]]] = {}
        belief_rows = [
            row
            for row in included
            if row["assertion_type"] == AssertionType.BELIEF_ESTIMATE.value
        ]
        for row in included:
            if row["assertion_type"] != AssertionType.PROPOSITION_REVISION.value:
                continue
            new_proposition_id = row["proposition_id"]
            old_proposition_id = related_proposition_id(row)
            if new_proposition_id and old_proposition_id:
                revisions_by_new.setdefault(new_proposition_id, []).append(
                    (old_proposition_id, row)
                )

        stale_belief_ids: set[str] = set()
        revision_conflicts: list[dict] = []
        seen_revision_conflicts: set[tuple[str, str, str]] = set()
        for exposure in included:
            if exposure["assertion_type"] != AssertionType.INFORMATION_EXPOSURE.value:
                continue
            subject = exposure["subject_agent_id"]
            new_proposition_id = exposure["proposition_id"]
            if not subject or not new_proposition_id:
                continue
            for old_proposition_id, revision in revisions_by_new.get(
                new_proposition_id, []
            ):
                if not record_at_or_after(exposure, revision):
                    continue
                prior = [
                    row
                    for row in belief_rows
                    if row["subject_agent_id"] == subject
                    and row["proposition_id"] == old_proposition_id
                    and (
                        _parse_time(row["valid_time"])
                        < _parse_time(exposure["valid_time"])
                        or (
                            _parse_time(row["valid_time"])
                            == _parse_time(exposure["valid_time"])
                            and _parse_time(row["system_record_time"])
                            < _parse_time(exposure["system_record_time"])
                        )
                    )
                ]
                if not prior:
                    continue
                prior_ids = {row["assertion_id"] for row in prior}
                later_stance = [
                    row
                    for row in belief_rows
                    if row["subject_agent_id"] == subject
                    and row["proposition_id"]
                    in {old_proposition_id, new_proposition_id}
                    and row["assertion_id"] not in prior_ids
                    and record_at_or_after(row, exposure)
                ]
                if later_stance:
                    continue
                stale_belief_ids.update(prior_ids)
                conflict_key = (
                    subject,
                    old_proposition_id,
                    new_proposition_id,
                )
                if conflict_key in seen_revision_conflicts:
                    continue
                seen_revision_conflicts.add(conflict_key)
                revision_conflicts.append(
                    {
                        "conflict_type": "REVISION_STANCE_UNRESOLVED",
                        "subject_agent_id": subject,
                        "prior_proposition_id": old_proposition_id,
                        "revision_proposition_id": new_proposition_id,
                        "revision_assertion_id": revision["assertion_id"],
                        "exposure_assertion_id": exposure["assertion_id"],
                        "stale_belief_assertion_ids": sorted(prior_ids),
                    }
                )

        relevant_items: list[dict] = []
        for row in included:
            item = self._assertion_dict(row, proposition_texts)
            if row["assertion_id"] in stale_belief_ids:
                item["projection_status"] = "STALE_AFTER_REVISION_EXPOSURE"
            relevant_items.append(item)
        relevant = tuple(relevant_items)

        evidence = tuple(
            self._event_dict(self.get_event(event_id))
            for event_id in sorted(evidence_ids)
        )
        unresolved_items = [
            self._assertion_dict(row, proposition_texts)
            for row in included
            if row["status"] == AssertionStatus.UNRESOLVED.value
        ]
        unresolved_items.extend(revision_conflicts)
        unresolved = tuple(unresolved_items)
        hypotheses = tuple(
            self._assertion_dict(row, proposition_texts)
            for row in included
            if row["assertion_type"]
            in {
                AssertionType.LATENT_HYPOTHESIS.value,
                AssertionType.OTHER_UNKNOWN.value,
            }
        )

        belief_keys = {
            (row["subject_agent_id"], row["proposition_id"])
            for row in included
            if row["assertion_type"] == AssertionType.BELIEF_ESTIMATE.value
            and row["assertion_id"] not in stale_belief_ids
        }
        unsupported: list[str] = []
        if incomplete_legacy_history:
            unsupported.append(
                "Historical invalidation time was not recorded for a pre-upgrade "
                "assertion; this cutoff cannot be certified as complete."
            )
        for row in included:
            if row["assertion_type"] != AssertionType.INFORMATION_EXPOSURE.value:
                continue
            key = (row["subject_agent_id"], row["proposition_id"])
            if key not in belief_keys and row["proposition_id"]:
                unsupported.append(
                    f"received({row['subject_agent_id']}, {row['proposition_id']}) "
                    "does not by itself entail belief"
                )
        for conflict in revision_conflicts:
            unsupported.append(
                "A received revision does not establish acceptance: "
                f"{conflict['subject_agent_id']} received "
                f"{conflict['revision_proposition_id']} revising "
                f"{conflict['prior_proposition_id']}; the prior belief estimate "
                "cannot certify the current stance without later stance evidence."
            )

        return QueryContext(
            viewer=viewer,
            event_time=event_time,
            knowledge_cutoff=knowledge_cutoff,
            query=query,
            relevant_assertions=relevant,
            evidence=evidence,
            unresolved_conflicts=unresolved,
            latent_hypotheses=hypotheses,
            unsupported_conclusions=tuple(unsupported),
            state_version=self.state_version,
            semantic_version=self.semantic_version,
        )

    def invalidate(
        self,
        affected_records: Iterable[str],
        reason: str,
    ) -> InvalidationReceipt:
        affected = set(affected_records)
        if not affected:
            raise ValueError("affected_records must not be empty")
        if not reason.strip():
            raise ValueError("reason must not be empty")

        direct: set[str] = set()
        invalid_patches: set[str] = set()
        invalidated_proposition_ids: set[str] = set()

        rows = self.conn.execute("SELECT * FROM assertions").fetchall()
        for row in rows:
            assertion_id = row["assertion_id"]
            if (
                assertion_id in affected
                or row["proposition_id"] in affected
                or row["related_proposition_id"] in affected
            ):
                direct.add(assertion_id)
                continue
            event_ids = set(_loads(row["evidence_event_ids"], []))
            if event_ids & affected:
                direct.add(assertion_id)

        for row in self.conn.execute(
            "SELECT patch_id, payload_json FROM patches WHERE status='ACTIVE'"
        ).fetchall():
            if row["patch_id"] in affected:
                invalid_patches.add(row["patch_id"])
                payload = _loads(row["payload_json"], {})
                direct |= {
                    a["assertion_id"]
                    for a in payload.get("assertions", [])
                    if "assertion_id" in a
                }
                invalidated_proposition_ids |= {
                    p["proposition_id"]
                    for p in payload.get("propositions", [])
                    if "proposition_id" in p
                }

        if invalidated_proposition_ids:
            for row in rows:
                if (
                    row["proposition_id"] in invalidated_proposition_ids
                    or row["related_proposition_id"] in invalidated_proposition_ids
                ):
                    direct.add(row["assertion_id"])

        invalidated = set(direct)
        queue = list(direct)
        while queue:
            parent = queue.pop()
            children = self.conn.execute(
                "SELECT child_assertion_id FROM dependencies "
                "WHERE parent_assertion_id=?",
                (parent,),
            ).fetchall()
            for child in children:
                child_id = child["child_assertion_id"]
                if child_id not in invalidated:
                    invalidated.add(child_id)
                    queue.append(child_id)

        new_version = self.state_version + 1
        invalidated_at = utc_now_iso()
        with self.conn:
            for assertion_id in invalidated:
                self.conn.execute(
                    "INSERT INTO assertion_invalidations("
                    "assertion_id, state_version, invalidated_at, reason) VALUES (?, ?, ?, ?)",
                    (assertion_id, new_version, invalidated_at, reason),
                )
                self.conn.execute(
                    "UPDATE assertions SET status='INVALID' WHERE assertion_id=?",
                    (assertion_id,),
                )
            for patch_id in invalid_patches:
                self.conn.execute(
                    "UPDATE patches SET status='INVALID' WHERE patch_id=?",
                    (patch_id,),
                )
            self._set_meta("state_version", str(new_version))
            checksum = self._create_snapshot(new_version)

        return InvalidationReceipt(
            state_version=new_version,
            invalidated_assertion_ids=tuple(sorted(invalidated)),
            invalidated_patch_ids=tuple(sorted(invalid_patches)),
            reason=reason,
            checksum=checksum,
        )

    def active_patches(self) -> tuple[SemanticPatch, ...]:
        active_ids = {
            row["assertion_id"] for row in self._active_assertion_rows()
        }
        rows = self.conn.execute(
            """
            SELECT payload_json FROM patches
            WHERE status='ACTIVE'
            ORDER BY applied_state_version, patch_id
            """
        ).fetchall()
        result = []
        for row in rows:
            patch = self._patch_from_payload(_loads(row["payload_json"], {}))
            result.append(
                SemanticPatch(
                    patch_id=patch.patch_id,
                    event_id=patch.event_id,
                    semantic_version=patch.semantic_version,
                    propositions=patch.propositions,
                    assertions=tuple(
                        assertion for assertion in patch.assertions
                        if assertion.assertion_id in active_ids
                    ),
                )
            )
        return tuple(result)

    def rebuild(
        self,
        scope: str = "all",
        checkpoint: int | None = None,
    ) -> RebuildReceipt:
        if scope != "all":
            raise NotImplementedError("minimal v0.4 rebuild currently supports scope='all'")

        temp = CognitionStore(":memory:")
        try:
            for event in self.list_events():
                temp.append_event(event)
            for patch in self.active_patches():
                temp.apply_patch(temp.state_version, patch)

            old_version = self.state_version
            new_version = old_version + 1
            with self.conn:
                self.conn.execute("DELETE FROM dependencies")
                self.conn.execute("DELETE FROM assertions")
                self.conn.execute("DELETE FROM propositions")
                self.conn.execute("DELETE FROM snapshots")

                for row in temp.conn.execute(
                    "SELECT * FROM propositions ORDER BY proposition_id"
                ).fetchall():
                    self.conn.execute(
                        """
                        INSERT INTO propositions VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        tuple(row),
                    )
                for row in temp.conn.execute(
                    "SELECT * FROM assertions ORDER BY assertion_id"
                ).fetchall():
                    self.conn.execute(
                        """
                        INSERT INTO assertions(
                            assertion_id, assertion_type, subject_agent_id,
                            proposition_id, related_proposition_id, hypothesis_text,
                            valid_time, system_record_time, evidence_event_ids,
                            depends_on_assertion_ids, status, support_level,
                            belief_stance, semantic_version
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            row["assertion_id"],
                            row["assertion_type"],
                            row["subject_agent_id"],
                            row["proposition_id"],
                            row["related_proposition_id"],
                            row["hypothesis_text"],
                            row["valid_time"],
                            row["system_record_time"],
                            row["evidence_event_ids"],
                            row["depends_on_assertion_ids"],
                            row["status"],
                            row["support_level"],
                            row["belief_stance"],
                            row["semantic_version"],
                        ),
                    )
                for row in temp.conn.execute(
                    "SELECT * FROM dependencies"
                ).fetchall():
                    self.conn.execute(
                        "INSERT INTO dependencies VALUES (?, ?)", tuple(row)
                    )

                self._set_meta("state_version", str(new_version))
                self._set_meta("semantic_version", temp.semantic_version)
                checksum = self._create_snapshot(new_version)

            return RebuildReceipt(
                state_version=new_version,
                rebuilt_assertion_count=len(temp._active_assertion_rows()),
                active_patch_count=len(temp.active_patches()),
                checksum=checksum,
                checkpoint=checkpoint,
            )
        finally:
            temp.close()

    def deterministic_checksum(self) -> str:
        return self._checksum()

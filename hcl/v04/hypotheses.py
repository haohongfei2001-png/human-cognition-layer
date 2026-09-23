"""Bounded latent-hypothesis tracking for HCL v0.4."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Protocol

from .model import utc_now_iso
from .schema import SchemaValidationError
from .store import CognitionStore


class HypothesisStatus(str, Enum):
    SUPPORTED = "SUPPORTED"
    PLAUSIBLE = "PLAUSIBLE"
    WEAKENED = "WEAKENED"
    CONTRADICTED = "CONTRADICTED"


@dataclass(frozen=True)
class HypothesisCandidate:
    label: str
    description: str
    status: HypothesisStatus
    support_event_ids: tuple[str, ...] = ()
    counterevidence_event_ids: tuple[str, ...] = ()
    unresolved_event_ids: tuple[str, ...] = ()
    rationale: str = ""


@dataclass(frozen=True)
class HypothesisTarget:
    target_id: str
    subject_agent_id: str
    target_kind: str
    question: str
    candidate_definitions: tuple[tuple[str, str], ...]


@dataclass(frozen=True)
class HypothesisState:
    target_id: str
    version: int
    candidates: tuple[HypothesisCandidate, ...]
    created_at: str
    semantic_version: str = "v04.hyp.1"


@dataclass(frozen=True)
class HypothesisUpdateReceipt:
    target_id: str
    version: int
    repaired: bool = False
    repair_reason: str | None = None
    operation: str = "UPDATE"


class HypothesisBackend(Protocol):
    def complete_json(
        self,
        messages: list[dict[str, str]],
        *,
        max_tokens: int,
        temperature: float = 0.0,
    ) -> str:
        ...


HYPOTHESIS_UPDATE_SYSTEM = """You update a bounded latent-human-state hypothesis set.

The hypotheses are candidate interpretations, not facts.

Rules:
- Keep every frozen candidate label exactly; do not add, rename, or remove labels.
- OTHER_UNKNOWN must remain available.
- Evidence references must be raw event IDs supplied in the input.
- Do not cite previous HCL hypotheses as external evidence.
- Repeated retellings are not automatically independent evidence.
- Preserve alternatives when evidence does not justify collapse.
- Use qualitative status only:
  SUPPORTED, PLAUSIBLE, WEAKENED, CONTRADICTED.
- Return the complete candidate set.

Return JSON only:
{
  "candidates": [
    {
      "label": "...",
      "status": "SUPPORTED|PLAUSIBLE|WEAKENED|CONTRADICTED",
      "support_event_ids": ["..."],
      "counterevidence_event_ids": ["..."],
      "unresolved_event_ids": ["..."],
      "rationale": "short evidence-grounded explanation"
    }
  ]
}
"""


HYPOTHESIS_REPAIR_SYSTEM = """Repair the proposed bounded hypothesis update.

Do not invent new candidate labels.
Do not drop OTHER_UNKNOWN.
Cite only raw event IDs supplied in the input.
Do not move the same event into multiple evidence roles for the same candidate.
Return the complete corrected JSON object only.
"""


class HypothesisTracker:
    def __init__(self, store: CognitionStore) -> None:
        self.store = store
        self.conn = store.conn
        self._init_schema()

    def _init_schema(self) -> None:
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS hypothesis_targets (
                target_id TEXT PRIMARY KEY,
                subject_agent_id TEXT NOT NULL,
                target_kind TEXT NOT NULL,
                question TEXT NOT NULL,
                candidate_definitions_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS hypothesis_versions (
                target_id TEXT NOT NULL,
                version INTEGER NOT NULL,
                state_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                semantic_version TEXT NOT NULL,
                operation TEXT NOT NULL,
                new_event_ids_json TEXT NOT NULL,
                rejected_json TEXT,
                repair_reason TEXT,
                PRIMARY KEY (target_id, version)
            );
            """
        )

    @staticmethod
    def _json(value: object) -> str:
        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )

    @staticmethod
    def _loads(value: str):
        return json.loads(value)

    def _normalize_definitions(
        self,
        definitions: tuple[tuple[str, str], ...],
    ) -> tuple[tuple[str, str], ...]:
        seen: set[str] = set()
        out: list[tuple[str, str]] = []
        for label, description in definitions:
            label = str(label).strip().upper()
            description = str(description).strip()
            if not label or not description:
                raise SchemaValidationError(
                    "candidate label and description must be non-empty"
                )
            if label in seen:
                raise SchemaValidationError(f"duplicate candidate label: {label}")
            seen.add(label)
            out.append((label, description))
        if "OTHER_UNKNOWN" not in seen:
            out.append(
                (
                    "OTHER_UNKNOWN",
                    "Other or currently unknown explanation not captured by named candidates.",
                )
            )
        if len([x for x in out if x[0] != "OTHER_UNKNOWN"]) > 3:
            raise SchemaValidationError(
                "minimal slice allows at most 3 named hypotheses"
            )
        return tuple(out)

    def create_target(self, target: HypothesisTarget) -> HypothesisUpdateReceipt:
        if not target.target_id.strip():
            raise SchemaValidationError("target_id must be non-empty")
        if not target.subject_agent_id.strip():
            raise SchemaValidationError("subject_agent_id must be non-empty")
        if not target.target_kind.strip() or not target.question.strip():
            raise SchemaValidationError("target_kind/question must be non-empty")

        definitions = self._normalize_definitions(target.candidate_definitions)
        existing = self.conn.execute(
            "SELECT target_id FROM hypothesis_targets WHERE target_id=?",
            (target.target_id,),
        ).fetchone()
        if existing:
            state = self.current(target.target_id)
            return HypothesisUpdateReceipt(
                target_id=target.target_id,
                version=state.version,
                operation="CREATE_DUPLICATE",
            )

        now = utc_now_iso()
        initial = HypothesisState(
            target_id=target.target_id,
            version=0,
            created_at=now,
            candidates=tuple(
                HypothesisCandidate(
                    label=label,
                    description=description,
                    status=HypothesisStatus.PLAUSIBLE,
                    rationale="Initial bounded candidate; no evidence update yet.",
                )
                for label, description in definitions
            ),
        )
        with self.conn:
            self.conn.execute(
                """
                INSERT INTO hypothesis_targets(
                    target_id, subject_agent_id, target_kind, question,
                    candidate_definitions_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    target.target_id,
                    target.subject_agent_id,
                    target.target_kind,
                    target.question,
                    self._json(list(definitions)),
                    now,
                ),
            )
            self._insert_version(
                initial,
                operation="CREATE",
                new_event_ids=(),
            )
        return HypothesisUpdateReceipt(
            target_id=target.target_id,
            version=0,
            operation="CREATE",
        )

    def _target_row(self, target_id: str):
        row = self.conn.execute(
            "SELECT * FROM hypothesis_targets WHERE target_id=?",
            (target_id,),
        ).fetchone()
        if not row:
            raise KeyError(f"unknown hypothesis target: {target_id}")
        return row

    def _definitions(self, target_id: str) -> tuple[tuple[str, str], ...]:
        row = self._target_row(target_id)
        return tuple(
            (str(label), str(description))
            for label, description in self._loads(
                row["candidate_definitions_json"]
            )
        )

    def _candidate_payload(self, candidate: HypothesisCandidate) -> dict:
        return {
            "label": candidate.label,
            "description": candidate.description,
            "status": candidate.status.value,
            "support_event_ids": list(candidate.support_event_ids),
            "counterevidence_event_ids": list(
                candidate.counterevidence_event_ids
            ),
            "unresolved_event_ids": list(candidate.unresolved_event_ids),
            "rationale": candidate.rationale,
        }

    def _state_payload(self, state: HypothesisState) -> dict:
        return {
            "target_id": state.target_id,
            "version": state.version,
            "created_at": state.created_at,
            "semantic_version": state.semantic_version,
            "candidates": [
                self._candidate_payload(c) for c in state.candidates
            ],
        }

    def _state_from_payload(self, payload: dict) -> HypothesisState:
        return HypothesisState(
            target_id=payload["target_id"],
            version=int(payload["version"]),
            created_at=payload["created_at"],
            semantic_version=payload.get("semantic_version", "v04.hyp.1"),
            candidates=tuple(
                HypothesisCandidate(
                    label=item["label"],
                    description=item["description"],
                    status=HypothesisStatus(item["status"]),
                    support_event_ids=tuple(
                        item.get("support_event_ids") or []
                    ),
                    counterevidence_event_ids=tuple(
                        item.get("counterevidence_event_ids") or []
                    ),
                    unresolved_event_ids=tuple(
                        item.get("unresolved_event_ids") or []
                    ),
                    rationale=item.get("rationale", ""),
                )
                for item in payload["candidates"]
            ),
        )

    def _insert_version(
        self,
        state: HypothesisState,
        *,
        operation: str,
        new_event_ids: tuple[str, ...],
        rejected_json: str | None = None,
        repair_reason: str | None = None,
    ) -> None:
        self.conn.execute(
            """
            INSERT INTO hypothesis_versions(
                target_id, version, state_json, created_at,
                semantic_version, operation, new_event_ids_json,
                rejected_json, repair_reason
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                state.target_id,
                state.version,
                self._json(self._state_payload(state)),
                state.created_at,
                state.semantic_version,
                operation,
                self._json(list(new_event_ids)),
                rejected_json,
                repair_reason,
            ),
        )

    def current(self, target_id: str) -> HypothesisState:
        row = self.conn.execute(
            """
            SELECT state_json FROM hypothesis_versions
            WHERE target_id=?
            ORDER BY version DESC
            LIMIT 1
            """,
            (target_id,),
        ).fetchone()
        if not row:
            raise KeyError(f"no state for target: {target_id}")
        return self._state_from_payload(self._loads(row["state_json"]))

    def history(self, target_id: str) -> tuple[HypothesisState, ...]:
        self._target_row(target_id)
        rows = self.conn.execute(
            """
            SELECT state_json FROM hypothesis_versions
            WHERE target_id=?
            ORDER BY version
            """,
            (target_id,),
        ).fetchall()
        return tuple(
            self._state_from_payload(self._loads(row["state_json"]))
            for row in rows
        )

    def _events_payload(self, event_ids: tuple[str, ...]) -> list[dict]:
        out: list[dict] = []
        for event_id in event_ids:
            event = self.store.get_event(event_id)
            out.append(
                {
                    "event_id": event.event_id,
                    "valid_time": event.valid_time,
                    "recorded_at": event.recorded_at,
                    "source_id": event.source_id,
                    "actor_id": event.actor_id,
                    "observer_ids": list(event.observer_ids),
                    "recipient_ids": list(event.recipient_ids),
                    "raw_text": event.raw_text,
                    "metadata": event.metadata,
                }
            )
        return out

    def _parse_candidate_output(
        self,
        target_id: str,
        payload: dict,
        previous: HypothesisState,
        *,
        next_version: int,
    ) -> HypothesisState:
        if not isinstance(payload, dict):
            raise SchemaValidationError("hypothesis update must be a JSON object")
        raw_candidates = payload.get("candidates")
        if not isinstance(raw_candidates, list):
            raise SchemaValidationError("candidates must be a list")

        definitions = dict(self._definitions(target_id))
        expected = set(definitions)
        returned: dict[str, dict] = {}
        existing_events = {event.event_id for event in self.store.list_events()}

        for raw in raw_candidates:
            if not isinstance(raw, dict):
                raise SchemaValidationError("candidate entries must be objects")
            label = str(raw.get("label", "")).strip().upper()
            if label not in expected:
                raise SchemaValidationError(
                    f"unregistered hypothesis label: {label!r}"
                )
            if label in returned:
                raise SchemaValidationError(
                    f"duplicate hypothesis label: {label}"
                )
            try:
                status = HypothesisStatus(raw.get("status"))
            except Exception as exc:
                raise SchemaValidationError(
                    f"invalid hypothesis status for {label}"
                ) from exc

            support = tuple(dict.fromkeys(raw.get("support_event_ids") or []))
            counter = tuple(
                dict.fromkeys(raw.get("counterevidence_event_ids") or [])
            )
            unresolved = tuple(
                dict.fromkeys(raw.get("unresolved_event_ids") or [])
            )
            used = set(support) | set(counter) | set(unresolved)
            missing = used - existing_events
            if missing:
                raise SchemaValidationError(
                    f"{label} references unknown events: {sorted(missing)}"
                )
            if (set(support) & set(counter)) or (
                set(support) & set(unresolved)
            ) or (set(counter) & set(unresolved)):
                raise SchemaValidationError(
                    f"{label} uses the same event in multiple evidence roles"
                )

            previous_candidate = next(
                c for c in previous.candidates if c.label == label
            )
            changed = (
                status != previous_candidate.status
                or support != previous_candidate.support_event_ids
                or counter != previous_candidate.counterevidence_event_ids
                or unresolved != previous_candidate.unresolved_event_ids
            )
            rationale = str(raw.get("rationale", "")).strip()
            if changed and not rationale:
                raise SchemaValidationError(
                    f"changed candidate {label} requires rationale"
                )
            if not rationale:
                rationale = previous_candidate.rationale

            returned[label] = {
                "status": status,
                "support": support,
                "counter": counter,
                "unresolved": unresolved,
                "rationale": rationale,
            }

        if set(returned) != expected:
            missing = expected - set(returned)
            extra = set(returned) - expected
            raise SchemaValidationError(
                f"candidate set mismatch missing={sorted(missing)} extra={sorted(extra)}"
            )
        if "OTHER_UNKNOWN" not in returned:
            raise SchemaValidationError("OTHER_UNKNOWN is mandatory")

        return HypothesisState(
            target_id=target_id,
            version=next_version,
            created_at=utc_now_iso(),
            candidates=tuple(
                HypothesisCandidate(
                    label=label,
                    description=definitions[label],
                    status=returned[label]["status"],
                    support_event_ids=returned[label]["support"],
                    counterevidence_event_ids=returned[label]["counter"],
                    unresolved_event_ids=returned[label]["unresolved"],
                    rationale=returned[label]["rationale"],
                )
                for label, _ in self._definitions(target_id)
            ),
        )

    def _proposal_messages(
        self,
        target_id: str,
        current: HypothesisState,
        new_event_ids: tuple[str, ...],
    ) -> list[dict[str, str]]:
        target = self._target_row(target_id)
        prior_event_ids: list[str] = []
        seen: set[str] = set()
        for candidate in current.candidates:
            for event_id in (
                list(candidate.support_event_ids)
                + list(candidate.counterevidence_event_ids)
                + list(candidate.unresolved_event_ids)
            ):
                if event_id not in seen and event_id not in new_event_ids:
                    seen.add(event_id)
                    prior_event_ids.append(event_id)
        return [
            {"role": "system", "content": HYPOTHESIS_UPDATE_SYSTEM},
            {
                "role": "user",
                "content": self._json(
                    {
                        "target": {
                            "target_id": target["target_id"],
                            "subject_agent_id": target["subject_agent_id"],
                            "target_kind": target["target_kind"],
                            "question": target["question"],
                            "candidate_definitions": list(
                                self._definitions(target_id)
                            ),
                        },
                        "current_state": self._state_payload(current),
                        "prior_evidence": self._events_payload(
                            tuple(prior_event_ids)
                        ),
                        "new_events": self._events_payload(new_event_ids),
                    }
                ),
            },
        ]

    def _propose_state(
        self,
        target_id: str,
        current: HypothesisState,
        new_event_ids: tuple[str, ...],
        backend: HypothesisBackend,
    ) -> tuple[HypothesisState, bool, str | None, str | None]:
        messages = self._proposal_messages(
            target_id,
            current,
            new_event_ids,
        )
        raw = backend.complete_json(
            messages,
            max_tokens=2048,
            temperature=0.0,
        )
        rejected_json = None
        repair_reason = None

        for attempt in range(2):
            try:
                payload = json.loads(raw)
                state = self._parse_candidate_output(
                    target_id,
                    payload,
                    current,
                    next_version=current.version + 1,
                )
                return (
                    state,
                    attempt == 1,
                    repair_reason,
                    rejected_json,
                )
            except (json.JSONDecodeError, SchemaValidationError) as exc:
                if attempt == 1:
                    raise
                rejected_json = raw
                repair_reason = str(exc)
                raw = backend.complete_json(
                    [
                        {
                            "role": "system",
                            "content": HYPOTHESIS_REPAIR_SYSTEM,
                        },
                        {
                            "role": "user",
                            "content": self._json(
                                {
                                    "validation_error": repair_reason,
                                    "rejected_output": rejected_json,
                                    "target": {
                                        "target_id": target_id,
                                        "candidate_definitions": list(
                                            self._definitions(target_id)
                                        ),
                                    },
                                    "current_state": self._state_payload(
                                        current
                                    ),
                                    "new_events": self._events_payload(
                                        new_event_ids
                                    ),
                                }
                            ),
                        },
                    ],
                    max_tokens=2048,
                    temperature=0.0,
                )
        raise AssertionError("unreachable")

    def update(
        self,
        target_id: str,
        new_event_ids: tuple[str, ...] | list[str],
        backend: HypothesisBackend,
    ) -> HypothesisUpdateReceipt:
        current = self.current(target_id)
        event_ids = tuple(new_event_ids)
        if not event_ids:
            raise SchemaValidationError("new_event_ids must not be empty")
        self._events_payload(event_ids)

        state, repaired, reason, rejected_json = self._propose_state(
            target_id,
            current,
            event_ids,
            backend,
        )
        with self.conn:
            self._insert_version(
                state,
                operation="UPDATE",
                new_event_ids=event_ids,
                rejected_json=rejected_json,
                repair_reason=reason,
            )
        return HypothesisUpdateReceipt(
            target_id=target_id,
            version=state.version,
            repaired=repaired,
            repair_reason=reason,
            operation="UPDATE",
        )

    def rebuild(
        self,
        target_id: str,
        backend: HypothesisBackend,
    ) -> HypothesisUpdateReceipt:
        target = self._target_row(target_id)
        definitions = self._definitions(target_id)
        initial = HypothesisState(
            target_id=target_id,
            version=0,
            created_at=utc_now_iso(),
            candidates=tuple(
                HypothesisCandidate(
                    label=label,
                    description=description,
                    status=HypothesisStatus.PLAUSIBLE,
                    rationale="Rebuild initial candidate.",
                )
                for label, description in definitions
            ),
        )

        rows = self.conn.execute(
            """
            SELECT new_event_ids_json FROM hypothesis_versions
            WHERE target_id=? AND operation='UPDATE'
            ORDER BY version
            """,
            (target_id,),
        ).fetchall()
        current = initial
        for row in rows:
            event_ids = tuple(self._loads(row["new_event_ids_json"]))
            current, _, _, _ = self._propose_state(
                target_id,
                current,
                event_ids,
                backend,
            )

        final = HypothesisState(
            target_id=target_id,
            version=self.current(target_id).version + 1,
            created_at=utc_now_iso(),
            candidates=current.candidates,
        )
        with self.conn:
            self._insert_version(
                final,
                operation="REBUILD",
                new_event_ids=(),
            )
        return HypothesisUpdateReceipt(
            target_id=target_id,
            version=final.version,
            operation="REBUILD",
        )

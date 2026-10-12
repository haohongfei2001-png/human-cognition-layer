"""In-memory contract fixture plus the explicit SQLite backend factory.

The host authenticates principals and provisions sessions/sources. Request text
never provisions authority. StateStore.sqlite opens the S1.2 durable backend;
the default fixture cannot establish crash recovery or persistent budgets.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from threading import RLock

from hcl.kernel.types import (
    AccessPolicy, CommitResult, Delta, FormalProblem, HCLFailure,
    InferenceResult, Principal, RULE_VERSION, Snapshot, SourceDocument, SourceHandle,
)


def denied() -> HCLFailure:
    # Missing, foreign and forbidden sources intentionally share a safe error.
    return HCLFailure("DENIED", "access", "ACCESS_DENIED", "source_handles",
                      "The session or source is not authorized.")


@dataclass
class _Session:
    owner: Principal
    members: frozenset[str]
    revision: int = 0
    access_epoch: int = 0
    sources: dict[str, SourceDocument] = field(default_factory=dict)
    inferences: dict[str, InferenceResult] = field(default_factory=dict)


class StateStore:
    """In-memory implementation; administrative methods require session owner."""
    durable = False

    @staticmethod
    def sqlite(path, *, revision=False):
        """Open the durable backend; the default constructor stays a test fixture."""
        from hcl.memory.sqlite_store import SQLiteStateStore
        return SQLiteStateStore(path, revision=revision)

    def __init__(self) -> None:
        self._sessions: dict[str, _Session] = {}
        self._lock = RLock()

    def create_session(self, session_id: str, owner: Principal,
                       members: frozenset[str] = frozenset()) -> None:
        with self._lock:
            if not session_id or session_id in self._sessions:
                raise ValueError("new nonempty session ID required")
            self._sessions[session_id] = _Session(owner, frozenset(members) | {owner.subject_id})

    def _session(self, session_id: str, principal: Principal) -> _Session:
        session = self._sessions.get(session_id)
        if (session is None or session.owner.tenant_id != principal.tenant_id
                or principal.subject_id not in session.members):
            raise denied()
        return session

    def _owner(self, session_id: str, principal: Principal) -> _Session:
        session = self._session(session_id, principal)
        if session.owner != principal:
            raise denied()
        return session

    def put_source(self, session_id: str, principal: Principal, source_id: str,
                   text: str, *, formal_problem: FormalProblem | None = None,
                   readers: frozenset[str] | None = None) -> SourceHandle:
        """Trusted host ingestion, never callable by an operator or model."""
        with self._lock:
            session = self._owner(session_id, principal)
            if not source_id or not isinstance(text, str):
                raise ValueError("source ID and source text required")
            for name, value in (("source_id", source_id), ("text", text)):
                if not isinstance(value, str):
                    raise ValueError("source ID and text must be strings")
                try:
                    value.encode("utf-8")
                except UnicodeEncodeError:
                    raise HCLFailure("INVALID_REQUEST", "ingestion", "INVALID_SOURCE_ENCODING", name,
                                     "The source must be valid Unicode text; it was not stored.") from None
            if formal_problem is not None and not isinstance(formal_problem, FormalProblem):
                raise ValueError("typed formal input required")
            previous = session.sources.get(source_id)
            handle = SourceHandle(source_id, previous.handle.version + 1 if previous else 1)
            policy = AccessPolicy(principal.tenant_id,
                                  frozenset(readers) if readers is not None else session.members)
            session.sources[source_id] = SourceDocument(handle, text, policy, formal_problem)
            if previous is not None and previous.access_policy != policy:
                session.access_epoch += 1
            session.revision += 1
            return handle

    def set_readers(self, session_id: str, principal: Principal, source_id: str,
                    readers: frozenset[str]) -> None:
        with self._lock:
            session = self._owner(session_id, principal)
            if source_id not in session.sources:
                raise denied()
            source = session.sources[source_id]
            session.sources[source_id] = replace(
                source, access_policy=AccessPolicy(principal.tenant_id, readers))
            session.access_epoch += 1
            session.revision += 1

    def snapshot(self, session_id: str, principal: Principal,
                 source_handles: tuple[SourceHandle, ...]) -> Snapshot:
        with self._lock:
            session = self._session(session_id, principal)
            views = {}
            for handle in source_handles:
                source = session.sources.get(handle.source_id)
                if source is None or not source.access_policy.permits(principal):
                    raise denied()
                if source.handle != handle:
                    raise HCLFailure("STALE_STATE", "snapshot", "STALE_SOURCE",
                                     "source_handles.version", "A source version changed.")
                if handle.source_id in views:
                    raise HCLFailure("INVALID_REQUEST", "admission", "DUPLICATE_SOURCE",
                                     "source_handles", "A source was requested more than once.")
                views[handle.source_id] = source
            return Snapshot(session_id, principal, session.revision, session.access_epoch,
                            RULE_VERSION, {key: value.handle.version for key, value in views.items()},
                            {}, views)

    def _validate(self, session: _Session, principal: Principal, read_set,
                  access_epoch: int, rule_version: str) -> None:
        if access_epoch != session.access_epoch:
            raise HCLFailure("DENIED", "access", "ACCESS_EPOCH_CHANGED", "access_epoch",
                             "Access changed; the prior snapshot cannot be delivered.")
        if rule_version != RULE_VERSION:
            raise HCLFailure("STALE_STATE", "commit", "RULE_VERSION_CHANGED", "rule_version",
                             "The rule version is no longer current.")
        for source_id, version in read_set.items():
            source = session.sources.get(source_id)
            if source is None or not source.access_policy.permits(principal):
                raise denied()
            if source.handle.version != version:
                raise HCLFailure("STALE_STATE", "commit", "READ_SET_CHANGED", "read_set",
                                 "An input read by the operation changed.")

    def validate_snapshot(self, snapshot: Snapshot) -> None:
        with self._lock:
            session = self._session(snapshot.session_id, snapshot.principal)
            self._validate(session, snapshot.principal, snapshot.source_versions,
                           snapshot.access_epoch, snapshot.rule_version)
            if (set(snapshot.immutable_views) != set(snapshot.source_versions)
                    or any(source != session.sources[source_id]
                           for source_id, source in snapshot.immutable_views.items())):
                raise HCLFailure("DENIED", "access", "SNAPSHOT_CONTENT_MISMATCH", "immutable_views",
                                 "The snapshot does not match the authorized stored source versions.")

    def commit(self, expected_revision: int, read_set, access_epoch: int,
               delta: Delta) -> CommitResult:
        with self._lock:
            session = self._session(delta.session_id, delta.principal)
            if (expected_revision != delta.base_revision or access_epoch != delta.access_epoch
                    or dict(read_set) != dict(delta.read_set)):
                raise HCLFailure("FAILED", "commit", "DELTA_CONTRACT_MISMATCH", "delta",
                                 "The operation's commit contract is inconsistent.")
            self._validate(session, delta.principal, read_set, access_epoch, delta.rule_version)
            # S1.1 deliberately fails closed. Fine-grained rebasing is S1.2.
            if session.revision != expected_revision:
                raise HCLFailure("STALE_STATE", "commit", "REVISION_CHANGED", "base_revision",
                                 "The session changed; recomputation is required.")
            ids = [result.result_id for result in delta.new_inferences]
            if len(ids) != len(set(ids)) or any(key in session.inferences for key in ids):
                raise HCLFailure("FAILED", "commit", "RESULT_ID_COLLISION", "new_inferences",
                                 "An inference identity is already present.")
            # Complete validation precedes the only mutation point.
            session.inferences.update({result.result_id: result for result in delta.new_inferences})
            if ids:
                session.revision += 1
            return CommitResult(session.revision, tuple(ids))

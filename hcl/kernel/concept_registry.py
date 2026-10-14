"""Additive, host-requested concept adoption and persistent consumer contracts.

Old requests and old candidate dialects never acquire follow-current semantics.
A stream names an explicit adoption chain, not a global truth or a new ACL.
"""
from dataclasses import dataclass
import re
from .types import Issue
from .scope import identifier

VERSION = "concept-registry-1"


@dataclass(frozen=True)
class ConceptBinding:
    choice_id: str
    stream_id: str

    def __post_init__(self):
        identifier(self.choice_id)
        identifier(self.stream_id)


@dataclass(frozen=True)
class ConceptAdoptionIssue(Issue):
    kind: str = "concept.adopt"
    stream_id: str = ""
    support_result_ids: tuple[str, ...] = ()
    version_labels: tuple[str, ...] = ()
    expected_head: str | None = None

    def __post_init__(self):
        identifier(self.stream_id)
        object.__setattr__(self, "support_result_ids", tuple(self.support_result_ids))
        object.__setattr__(self, "version_labels", tuple(self.version_labels))
        if not 1 <= len(self.support_result_ids) <= 8 or len(self.support_result_ids) != len(self.version_labels):
            raise ValueError("bounded matching independent definition supports required")
        if len(set(self.support_result_ids)) != len(self.support_result_ids):
            raise ValueError("duplicate support is not independent evidence")
        for value in (*self.support_result_ids, *self.version_labels):
            identifier(value)
        if self.expected_head is not None:
            identifier(self.expected_head)
        if self.source_id is not None:
            raise ValueError("adoption sources come from exact committed proofs")


@dataclass(frozen=True)
class ConceptFollowIssue(Issue):
    kind: str = "judgment.follow_concepts"
    base_result_id: str = ""
    bindings: tuple[ConceptBinding, ...] = ()

    def __post_init__(self):
        identifier(self.base_result_id)
        object.__setattr__(self, "bindings", tuple(self.bindings))
        if not 1 <= len(self.bindings) <= 4 or any(type(b) is not ConceptBinding for b in self.bindings):
            raise ValueError("bounded explicit concept choice bindings required")
        if len({b.choice_id for b in self.bindings}) != len(self.bindings) or self.source_id is not None:
            raise ValueError("unique choice binding with proof-bound sources required")


@dataclass(frozen=True)
class ConceptQuery:
    mode: str
    key: str
    at: int = 1000000

    def __post_init__(self):
        if self.mode not in ("RESULT", "SELECTION"):
            raise ValueError("explicit concept query mode required")
        identifier(self.key)
        if type(self.at) is not int or not 0 <= self.at <= 1000000:
            raise ValueError("finite explicit concept use time required")

    # Compatibility accessors are not added wire fields to old contracts.
    source_only = False
    history = False
    known_at = None
    source_scope = ()

    @property
    def evidence_result_ids(self):
        return (self.key,) if self.mode == "RESULT" else ()

    def wire(self):
        return dict(mode=self.mode, key=self.key, at=self.at)


@dataclass(frozen=True)
class ConceptDependency:
    query: ConceptQuery
    digest: str
    index_version: str = VERSION

    def __post_init__(self):
        if (type(self.query) is not ConceptQuery or type(self.digest) is not str
                or re.fullmatch("[0-9a-f]{64}", self.digest) is None or self.index_version != VERSION):
            raise ValueError("exact concept dependency required")

    def wire(self):
        return dict(concept_query=self.query.wire(), digest=self.digest, index_version=self.index_version)

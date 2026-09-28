"""Versioned evidence and rooted support, independent of evaluators/providers.

Support sets are alternatives (OR); members of one set are obligations (AND).
Grounding means a recorded derivation has live roots, never that it is true.
"""
from dataclasses import asdict, dataclass
from enum import Enum
from datetime import datetime
import hashlib
import json


def identity(kind, *parts):
    raw = json.dumps(parts, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
    return kind + ':' + hashlib.sha256(raw.encode()).hexdigest()


def _within_time(value, cutoff):
    if cutoff is None:
        return True
    if value is None:
        return False
    if value == cutoff:
        return True
    try:
        left = datetime.fromisoformat(value.replace('Z', '+00:00'))
        right = datetime.fromisoformat(cutoff.replace('Z', '+00:00'))
        if left.tzinfo is None or right.tzinfo is None:
            return False
        return left <= right
    except (ValueError, TypeError, AttributeError):
        # Unordered natural-language time labels are preserved, never guessed.
        return False


class ClaimKind(str, Enum):
    SOURCE_REPORT = 'SOURCE_REPORT'
    SYSTEM_INTERPRETATION = 'SYSTEM_INTERPRETATION'
    CONDITIONAL_TOOL_RESULT = 'CONDITIONAL_TOOL_RESULT'


@dataclass(frozen=True)
class Scope:
    actor: str | None = None
    observer: str | None = None
    context: str | None = None
    event: str | None = None
    event_time: str | None = None
    access_time: str | None = None
    record_time: str | None = None
    through_order: int | None = None
    source_ids: tuple[str, ...] = ()
    assumptions: tuple[str, ...] = ()

    def __post_init__(self):
        if (not isinstance(self.source_ids, tuple) or not all(isinstance(x, str) and x for x in self.source_ids)
                or len(set(self.source_ids)) != len(self.source_ids)
                or not isinstance(self.assumptions, tuple)
                or not all(isinstance(x, str) and x for x in self.assumptions)
                or (self.through_order is not None and
                    (type(self.through_order) is not int or self.through_order < 1))):
            raise ValueError('explicit bounded scope required')

    @property
    def id(self):
        return identity('scope', asdict(self))


@dataclass(frozen=True)
class SourceSpan:
    source_id: str
    version: int
    start: int
    end: int
    quote: str
    document_sha256: str
    order: int
    permitted_observers: tuple[str, ...] = ()
    event_time: str | None = None
    access_time: str | None = None
    record_time: str | None = None

    @property
    def id(self):
        return identity('span', asdict(self))

    def permits(self, scope):
        # None is the authorized analyst, not an omniscient story character.
        return (self.source_id in scope.source_ids
                and (scope.observer is None or scope.observer in self.permitted_observers)
                and (scope.through_order is None or self.order <= scope.through_order)
                and _within_time(self.event_time, scope.event_time)
                and _within_time(self.access_time, scope.access_time)
                and _within_time(self.record_time, scope.record_time))


@dataclass(frozen=True)
class Claim:
    id: str
    scope: Scope
    kind: ClaimKind
    content_json: str

    @property
    def content(self):
        return json.loads(self.content_json)


@dataclass(frozen=True)
class Interpretation:
    claim_id: str
    required_premises: tuple[str, ...] = ()
    alternatives: tuple[str, ...] = ()
    unknown_conditions: tuple[str, ...] = ()


@dataclass(frozen=True)
class Dependency:
    conclusion: str
    supports: tuple[str, ...]


class EvidenceCore:
    """Request/session-local audit graph; read projections never expand access."""
    def __init__(self, *, max_nodes=4096):
        self.max_nodes = max_nodes
        self.spans = {}
        self.claims = {}
        self.dependencies = {}
        self.interpretations = {}
        self.withdrawn = set()

    def _room(self, key):
        if key not in self.spans and key not in self.claims and len(self.spans) + len(self.claims) >= self.max_nodes:
            raise ValueError('evidence capacity exceeded')

    def add_span(self, document, *, source_id, version, start=0, end=None, order=1,
                 permitted_observers=(), event_time=None, access_time=None, record_time=None):
        end = len(document) if end is None else end
        if (not isinstance(document, str) or not document or not isinstance(source_id, str) or not source_id
                or type(version) is not int or version < 1 or type(order) is not int or order < 1
                or type(start) is not int or type(end) is not int or not 0 <= start < end <= len(document)
                or not isinstance(permitted_observers, tuple)
                or not all(isinstance(x, str) and x for x in permitted_observers)):
            raise ValueError('valid authorized source and exact span required')
        span = SourceSpan(source_id, version, start, end, document[start:end],
            hashlib.sha256(document.encode()).hexdigest(), order, permitted_observers,
            event_time, access_time, record_time)
        self._room(span.id)
        self.spans[span.id] = span
        return span.id

    def claim(self, scope, kind, content):
        if not isinstance(scope, Scope) or not isinstance(kind, ClaimKind):
            raise ValueError('typed scope and claim kind required')
        raw = json.dumps(content, ensure_ascii=False, sort_keys=True, allow_nan=False)
        key = identity('claim', scope.id, kind.value, raw)
        self._room(key)
        self.claims[key] = Claim(key, scope, kind, raw)
        self.dependencies.setdefault(key, set())
        return key

    def support(self, conclusion, *supports):
        claim = self.claims[conclusion]
        if not supports or len(set(supports)) != len(supports):
            raise ValueError('nonempty distinct supporting obligations required')
        for key in supports:
            if key in self.spans:
                if not self.spans[key].permits(claim.scope):
                    raise ValueError('source outside conclusion scope')
            elif key in self.claims:
                if self.claims[key].scope != claim.scope:
                    raise ValueError('cross-scope inference requires an explicit future projection operation')
            else:
                raise ValueError('unknown support')
        if claim.kind == ClaimKind.SOURCE_REPORT and any(key not in self.spans for key in supports):
            raise ValueError('source report cannot be rooted in a system interpretation')
        self.dependencies[conclusion].add(tuple(sorted(supports)))

    def interpret(self, claim_id, *, required_premises=(), alternatives=(), unknown_conditions=()):
        if self.claims[claim_id].kind != ClaimKind.SYSTEM_INTERPRETATION:
            raise ValueError('interpretation must remain separate from source reports')
        refs = (*required_premises, *alternatives)
        if any(k not in self.claims or self.claims[k].scope != self.claims[claim_id].scope for k in refs):
            raise ValueError('interpretation reference outside scope')
        self.interpretations[claim_id] = Interpretation(claim_id, tuple(required_premises),
            tuple(alternatives), tuple(unknown_conditions))

    def grounded(self):
        # Least fixed point: rootless cycles cannot make themselves live.
        live = set(self.spans) - self.withdrawn
        while True:
            added = {key for key, groups in self.dependencies.items()
                if key not in live and key not in self.withdrawn
                and any(set(group) <= live for group in groups)
                and set(self.interpretations.get(key, Interpretation(key)).required_premises) <= live}
            if not added:
                return frozenset(live)
            live.update(added)

    def withdraw(self, key):
        if key not in self.spans and key not in self.claims:
            raise ValueError('unknown evidence identity')
        before = self.grounded()
        self.withdrawn.add(key)
        return before - self.grounded()

    def receipt(self, scope):
        live = self.grounded()
        claims = [c for c in self.claims.values() if c.scope == scope]
        visible = {k for k, span in self.spans.items() if span.permits(scope)}
        visible.update(c.id for c in claims)
        return dict(schema='hcl-shared-evidence-v1', scope=asdict(scope),
            spans=[dict(id=k, **asdict(self.spans[k]), active=k in live)
                   for k in sorted(visible & self.spans.keys())],
            claims=[dict(id=c.id, kind=c.kind.value, content=c.content, grounded=c.id in live,
                supports=[list(s) for s in sorted(self.dependencies[c.id]) if set(s) <= visible],
                interpretation=asdict(self.interpretations[c.id]) if c.id in self.interpretations else None)
                for c in sorted(claims, key=lambda c: c.id)],
            grounding_semantics='LIVE_RECORDED_DERIVATION_NOT_TRUTH')

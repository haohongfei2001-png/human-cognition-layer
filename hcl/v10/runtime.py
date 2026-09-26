"""Exact bounded Dung argumentation, conditional on a declared complete graph.

This computes formal acceptance, never moral truth or a character's belief.
No natural-language attack extraction or priority guessing is performed.
"""

from dataclasses import asdict, dataclass
from datetime import datetime
from itertools import combinations

from hcl.v04.model import EventRecord
from hcl.v06 import HCLV06Runtime, SYSTEM_VIEWER

SCOPE = "DECLARED_COMPLETE_ARGUMENTATION_FRAMEWORK"
SEMANTICS = ("grounded", "complete", "preferred", "stable")


def _text(value, cap=240):
    if not isinstance(value, str) or not value.strip() or len(value) > cap:
        raise ValueError("bounded nonempty text required")
    return value


@dataclass(frozen=True)
class Argument:
    argument_id: str
    evidence_text: str

    def __post_init__(self):
        _text(self.argument_id)
        _text(self.evidence_text, 2000)


@dataclass(frozen=True)
class Attack:
    attacker: str
    target: str
    evidence_text: str

    def __post_init__(self):
        _text(self.attacker)
        _text(self.target)
        _text(self.evidence_text, 2000)


@dataclass(frozen=True)
class ArgumentFramework:
    framework_id: str
    source_event_id: str
    arguments: tuple[Argument, ...]
    attacks: tuple[Attack, ...]
    scope: str = SCOPE

    def __post_init__(self):
        _text(self.framework_id)
        _text(self.source_event_id)
        if self.scope != SCOPE:
            raise ValueError("complete declared graph scope required")
        if not isinstance(self.arguments, tuple) or not isinstance(self.attacks, tuple):
            raise ValueError("immutable framework tuples required")
        if not 1 <= len(self.arguments) <= 12 or len(self.attacks) > 144:
            raise ValueError("bounded graph cap exceeded")
        if not all(isinstance(a, Argument) for a in self.arguments) or not all(
            isinstance(a, Attack) for a in self.attacks
        ):
            raise ValueError("typed arguments/attacks required")
        ids = self.ids
        if len(set(ids)) != len(ids):
            raise ValueError("duplicate argument")
        edges = [(e.attacker, e.target) for e in self.attacks]
        if len(set(edges)) != len(edges) or any(
            a not in ids or b not in ids for a, b in edges
        ):
            raise ValueError("duplicate or undeclared attack endpoint")

    @property
    def ids(self):
        return tuple(a.argument_id for a in self.arguments)

    def as_dict(self):
        return asdict(self)

    def _attacked(self, chosen):
        return {e.target for e in self.attacks if e.attacker in chosen}

    def _defended(self, chosen):
        defeated = self._attacked(chosen)
        return {
            a
            for a in self.ids
            if all(e.attacker in defeated for e in self.attacks if e.target == a)
        }

    def grounded(self):
        accepted = set()
        steps = []
        while True:
            defended = self._defended(accepted)
            steps.append(
                {
                    "step": len(steps),
                    "in": sorted(accepted),
                    "defended": sorted(defended),
                }
            )
            if defended == accepted:
                break
            accepted = defended
        return self.labelling(accepted), steps

    def labelling(self, accepted):
        out = self._attacked(accepted)
        return {
            "IN": sorted(accepted),
            "OUT": sorted(out),
            "UNDEC": sorted(set(self.ids) - set(accepted) - out),
        }

    def extensions(self, semantics):
        if semantics not in SEMANTICS:
            raise ValueError("explicit supported semantics required")
        if semantics == "grounded":
            return [self.grounded()[0]]
        complete = []
        for n in range(len(self.ids) + 1):
            for group in combinations(self.ids, n):
                s = set(group)
                if not s & self._attacked(s) and self._defended(s) == s:
                    complete.append(s)
        if semantics == "preferred":
            complete = [s for s in complete if not any(s < t for t in complete)]
        elif semantics == "stable":
            complete = [s for s in complete if s | self._attacked(s) == set(self.ids)]
        return sorted((self.labelling(s) for s in complete), key=lambda x: x["IN"])

    def analyse(self, semantics="grounded", target=None):
        if target is not None and target not in self.ids:
            raise ValueError("declared target required")
        labels = self.extensions(semantics)
        grounded, steps = self.grounded()
        accepts = (
            [target in row["IN"] for row in labels] if target is not None else None
        )
        return {
            "framework_id": self.framework_id,
            "source_event_id": self.source_event_id,
            "scope": "CONDITIONAL_ON_DECLARED_COMPLETE_GRAPH",
            "semantics": semantics,
            "status": "EXTENSIONS_AVAILABLE" if labels else "NO_EXTENSION",
            "labellings": labels,
            "grounded": grounded,
            "grounded_steps": steps,
            "target": target,
            "credulous": any(accepts) if accepts else None,
            "skeptical": all(accepts) if accepts else None,
            "not_world_truth": True,
            "not_private_mental_truth": True,
            "not_moral_verdict": True,
        }


class HCLV10Runtime:
    def __init__(self, perspectives=None):
        self.perspectives = (
            perspectives if perspectives is not None else HCLV06Runtime()
        )
        self._frameworks = {}

    def ingest_event(self, event: EventRecord):
        return self.perspectives.ingest_prestructured_event(event)

    def ingest_framework(self, framework: ArgumentFramework):
        if not isinstance(framework, ArgumentFramework):
            raise ValueError("typed framework required")
        previous = self._frameworks.get(framework.framework_id)
        if previous is not None:
            if previous != framework:
                raise ValueError("framework ID collision")
            return False
        source = next(
            (
                e
                for e in self.perspectives.events
                if e.event_id == framework.source_event_id
            ),
            None,
        )
        if source is None or source.metadata.get("argumentation_scope") != SCOPE:
            raise ValueError("source must declare the complete attack graph")
        for time in (source.valid_time, source.recorded_at):
            if datetime.fromisoformat(time.replace("Z", "+00:00")).utcoffset() is None:
                raise ValueError("framework chronology requires timezone")
        if any(
            a.evidence_text not in source.raw_text
            for a in framework.arguments + framework.attacks
        ):
            raise ValueError("argument/attack lacks exact source quote")
        self._frameworks[framework.framework_id] = framework
        return True

    def answer_context(
        self,
        framework_id,
        *,
        viewer_agent_id=SYSTEM_VIEWER,
        event_time=None,
        knowledge_cutoff=None
    ):
        f = self._frameworks.get(framework_id)
        if f is None:
            return {"status": "SYSTEM_INSUFFICIENT", "frameworks": []}
        view = self.perspectives.perspective_view(
            target_agent_id=viewer_agent_id,
            event_time=event_time,
            knowledge_cutoff=knowledge_cutoff,
        )
        if f.source_event_id not in view.event_ids:
            return {"status": "SYSTEM_INSUFFICIENT", "frameworks": []}
        return {
            "status": "DECLARED_FRAMEWORK_AVAILABLE",
            "frameworks": [f.as_dict()],
            "source_view": view.as_dict(),
            "scope": "CONDITIONAL_ON_DECLARED_COMPLETE_GRAPH",
        }

    def analyse(self, framework_id, semantics="grounded", target=None, **view_args):
        context = self.answer_context(framework_id, **view_args)
        if not context["frameworks"]:
            return {
                "status": "SYSTEM_INSUFFICIENT",
                "labellings": [],
                "credulous": None,
                "skeptical": None,
                "grounded_steps": [],
            }
        return self._frameworks[framework_id].analyse(semantics, target)

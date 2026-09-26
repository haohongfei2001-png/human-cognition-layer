"""Bounded factual abduction and interventions under declared Boolean SCMs.

Implements published SCM semantics, not causal discovery from correlations.
A consequence is conditional on the supplied model, never private-mind truth.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, asdict
from datetime import datetime
from itertools import product
import re

from hcl.v04.model import EventRecord
from hcl.v06 import HCLV06Runtime, SYSTEM_VIEWER

NAME = re.compile(r"[A-Za-z][A-Za-z0-9_]{0,47}\Z")
SCOPE = "DECLARED_BOOLEAN_STRUCTURAL_MODEL"


def _name(value):
    if not isinstance(value, str) or not NAME.fullmatch(value):
        raise ValueError("bounded variable name required")
    return value


def _assignment(values, variables):
    result = dict(values)
    if any(
        k not in variables or type(v) is not int or v not in (0, 1)
        for k, v in result.items()
    ):
        raise ValueError("assignment requires known variable and integer zero/one")
    return result


def _expression(text):
    if not isinstance(text, str) or not text or len(text) > 1000:
        raise ValueError("bounded Boolean expression required")
    try:
        node = ast.parse(text, mode="eval").body
    except (SyntaxError, RecursionError) as exc:
        raise ValueError("invalid Boolean expression") from exc
    nodes = list(ast.walk(node))
    if len(nodes) > 128:
        raise ValueError("expression complexity cap exceeded")
    allowed = (
        ast.Name,
        ast.Load,
        ast.Constant,
        ast.BoolOp,
        ast.And,
        ast.Or,
        ast.UnaryOp,
        ast.Not,
        ast.BinOp,
        ast.BitXor,
    )
    for part in nodes:
        if not isinstance(part, allowed):
            raise ValueError("only names, 0/1, not, and, or, xor are permitted")
        if isinstance(part, ast.Name):
            _name(part.id)
        if isinstance(part, ast.Constant) and (
            type(part.value) is not int or part.value not in (0, 1)
        ):
            raise ValueError("only integer Boolean constants permitted")
    return node


def _evaluate(node, values):
    if isinstance(node, ast.Name):
        return values[node.id]
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.UnaryOp):
        return 1 - _evaluate(node.operand, values)
    if isinstance(node, ast.BinOp):
        return _evaluate(node.left, values) ^ _evaluate(node.right, values)
    children = [_evaluate(x, values) for x in node.values]
    return int(all(children) if isinstance(node.op, ast.And) else any(children))


@dataclass(frozen=True)
class StructuralRule:
    target: str
    expression: str
    evidence_text: str

    def __post_init__(self):
        _name(self.target)
        _expression(self.expression)
        if (
            not isinstance(self.evidence_text, str)
            or not self.evidence_text.strip()
            or len(self.evidence_text) > 2000
        ):
            raise ValueError("bounded rule source excerpt required")


@dataclass(frozen=True)
class CausalModel:
    model_id: str
    source_event_id: str
    variables: tuple[str, ...]
    exogenous: tuple[str, ...]
    rules: tuple[StructuralRule, ...]
    scope: str = SCOPE

    def __post_init__(self):
        for value in (self.model_id, self.source_event_id):
            if not isinstance(value, str) or not value.strip() or len(value) > 240:
                raise ValueError("bounded model/source ID required")
        if self.scope != SCOPE:
            raise ValueError(
                "solver requires a declared structural model, not a correlation or causal guess"
            )
        if not all(
            isinstance(v, tuple) for v in (self.variables, self.exogenous, self.rules)
        ):
            raise ValueError("immutable model tuples required")
        if not 1 <= len(self.variables) <= 24 or len(self.exogenous) > 8:
            raise ValueError("bounded model/world cap exceeded")
        for name in self.variables + self.exogenous:
            _name(name)
        if len(set(self.variables)) != len(self.variables) or len(
            set(self.exogenous)
        ) != len(self.exogenous):
            raise ValueError("duplicate variable")
        if not set(self.exogenous) <= set(self.variables):
            raise ValueError("exogenous variable not declared")
        if not all(isinstance(rule, StructuralRule) for rule in self.rules):
            raise ValueError("typed structural rules required")
        targets = [r.target for r in self.rules]
        if len(set(targets)) != len(targets) or set(targets) != set(
            self.variables
        ) - set(self.exogenous):
            raise ValueError(
                "each endogenous variable requires exactly one rule; exogenous variables have no rule"
            )
        pending = {
            r.target: {
                n.id
                for n in ast.walk(_expression(r.expression))
                if isinstance(n, ast.Name)
            }
            for r in self.rules
        }
        if any(not deps <= set(self.variables) for deps in pending.values()):
            raise ValueError("undeclared causal parent")
        available = set(self.exogenous)
        while pending:
            ready = sorted(k for k, deps in pending.items() if deps <= available)
            if not ready:
                raise ValueError("cyclic causal model")
            for key in ready:
                available.add(key)
                del pending[key]

    def as_dict(self):
        return asdict(self)

    def world(self, exogenous_values, interventions=None):
        """Evaluate equations, replacing intervened endogenous equations by constants."""
        roots = _assignment(exogenous_values, self.exogenous)
        if set(roots) != set(self.exogenous):
            raise ValueError("every exogenous value required")
        changes = _assignment(interventions or {}, self.variables)
        values = dict(roots)
        values.update(changes)
        pending = {
            r.target: _expression(r.expression)
            for r in self.rules
            if r.target not in changes
        }
        while pending:
            ready = [
                k
                for k, node in pending.items()
                if {n.id for n in ast.walk(node) if isinstance(n, ast.Name)}
                <= values.keys()
            ]
            if not ready:
                raise ValueError("unresolved model")
            for key in sorted(ready):
                values[key] = _evaluate(pending.pop(key), values)
        return {k: values[k] for k in self.variables}

    def counterfactual(self, target, *, observations=None, interventions=None):
        """Abduce factual worlds first; share their exogenous context in each alternative.

        Observations constrain the factual world, never the intervened world.
        No probability is assigned to equally enumerated possible worlds.
        """
        if target not in self.variables:
            raise ValueError("unknown target")
        observed = _assignment(observations or {}, self.variables)
        changes = _assignment(interventions or {}, self.variables)
        traces = []
        for root_bits in product((0, 1), repeat=len(self.exogenous)):
            roots = dict(zip(self.exogenous, root_bits))
            factual = self.world(roots)
            if any(factual[k] != v for k, v in observed.items()):
                continue
            alternative = self.world(roots, changes)
            traces.append(
                {"exogenous": roots, "factual": factual, "alternative": alternative}
            )
        possible = sorted({t["alternative"][target] for t in traces})
        status = (
            "INCONSISTENT_OBSERVATIONS"
            if not traces
            else "DETERMINATE" if len(possible) == 1 else "SYSTEM_INSUFFICIENT"
        )
        return {
            "model_id": self.model_id,
            "source_event_id": self.source_event_id,
            "scope": "CONDITIONAL_ON_DECLARED_MODEL",
            "status": status,
            "target": target,
            "observations": observed,
            "interventions": changes,
            "possible_values": possible,
            "value": possible[0] if len(possible) == 1 else None,
            "world_count": len(traces),
            "traces": traces,
            "not_observed_fact": True,
            "not_private_mental_truth": True,
        }


class HCLV09Runtime:
    """Model history is explicit; two conflicting models are never silently merged."""

    def __init__(self, perspectives=None):
        self.perspectives = (
            perspectives if perspectives is not None else HCLV06Runtime()
        )
        self._models = {}

    def ingest_event(self, event: EventRecord):
        return self.perspectives.ingest_prestructured_event(event)

    def ingest_model(self, model: CausalModel):
        if not isinstance(model, CausalModel):
            raise ValueError("typed causal model required")
        existing = self._models.get(model.model_id)
        if existing is not None:
            if existing != model:
                raise ValueError("causal model ID collision")
            return False
        source = next(
            (
                e
                for e in self.perspectives.events
                if e.event_id == model.source_event_id
            ),
            None,
        )
        if source is None or source.metadata.get("causal_model_scope") != SCOPE:
            raise ValueError(
                "source must explicitly declare a structural-model assumption"
            )
        for time in (source.valid_time, source.recorded_at):
            if datetime.fromisoformat(time.replace("Z", "+00:00")).utcoffset() is None:
                raise ValueError("model chronology requires timezone")
        if any(rule.evidence_text not in source.raw_text for rule in model.rules):
            raise ValueError("structural rule missing exact source quote")
        # Quote anchoring does not itself prove a rule's entailment. Preserve
        # this exact model for external semantic audit and answer receipt.
        self._models[model.model_id] = model
        return True

    def answer_context(
        self,
        model_id,
        *,
        viewer_agent_id=SYSTEM_VIEWER,
        event_time=None,
        knowledge_cutoff=None,
    ):
        model = self._models.get(model_id)
        if model is None:
            return {"status": "SYSTEM_INSUFFICIENT", "models": []}
        view = self.perspectives.perspective_view(
            target_agent_id=viewer_agent_id,
            event_time=event_time,
            knowledge_cutoff=knowledge_cutoff,
        )
        if model.source_event_id not in view.event_ids:
            return {"status": "SYSTEM_INSUFFICIENT", "models": []}
        return {
            "status": "DECLARED_MODEL_AVAILABLE",
            "models": [model.as_dict()],
            "source_view": view.as_dict(),
            "scope": "CONDITIONAL_ON_DECLARED_MODEL",
        }

    def counterfactual(
        self,
        model_id,
        target,
        *,
        viewer_agent_id=SYSTEM_VIEWER,
        event_time=None,
        knowledge_cutoff=None,
        observations=None,
        interventions=None,
    ):
        context = self.answer_context(
            model_id,
            viewer_agent_id=viewer_agent_id,
            event_time=event_time,
            knowledge_cutoff=knowledge_cutoff,
        )
        if not context["models"]:
            return {
                "status": "SYSTEM_INSUFFICIENT",
                "possible_values": [],
                "value": None,
                "traces": [],
            }
        return self._models[model_id].counterfactual(
            target, observations=observations, interventions=interventions
        )

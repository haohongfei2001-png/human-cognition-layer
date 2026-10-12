"""Finite event-product belief computation under an explicit local model.

This is a pure calculation, not an extractor or a claim about private minds.
World state, an agent's alternatives, and higher-order alternatives are distinct.
No probability is inferred from the number of remaining possible worlds.
"""

from dataclasses import dataclass
from hashlib import sha256
from itertools import product
from collections.abc import Mapping
import json

from hcl.kernel.types import freeze, thaw


@dataclass(frozen=True)
class EpistemicLimits:
    max_worlds: int = 512
    max_edges: int = 65536
    max_evaluations: int = 100000
    max_depth: int = 4
    max_events: int = 64

    def __post_init__(self):
        ceilings = (8192, 1048576, 10000000, 16, 512)
        if any(
            type(value) is not int or not 1 <= value <= cap
            for value, cap in zip(self.__dict__.values(), ceilings)
        ):
            raise ValueError("bounded epistemic limits required")


class EpistemicFrontier(Exception):
    pass


class Work:
    def __init__(self, limits):
        self.limits, self.used = limits, 0
        self.empty_views = set()

    def step(self, amount=1):
        if self.used + amount > self.limits.max_evaluations:
            raise EpistemicFrontier("EVALUATION_FRONTIER")
        self.used += amount


def _identity(value):
    if type(value) is not str or not value or len(value) > 160:
        raise ValueError("bounded identity required")
    value.encode("utf-8")


def _formula(node, atoms, agents, *, modal=True, depth=0, counter=None):
    counter = counter if counter is not None else [0]
    counter[0] += 1
    if counter[0] > 256 or depth > 32:
        raise ValueError("formula syntax bound")
    if type(node) is bool:
        return
    if not isinstance(node, Mapping):
        raise ValueError("typed formula required")
    op = node.get("op")
    if op == "atom" and set(node) == {"op", "name"} and node["name"] in atoms:
        return
    if op == "not" and set(node) == {"op", "arg"}:
        _formula(
            node["arg"], atoms, agents, modal=modal, depth=depth + 1, counter=counter
        )
        return
    if (
        op in ("and", "or")
        and set(node) == {"op", "args"}
        and isinstance(node["args"], (tuple, list))
        and 1 <= len(node["args"]) <= 32
    ):
        for arg in node["args"]:
            _formula(arg, atoms, agents, modal=modal, depth=depth + 1, counter=counter)
        return
    if (
        modal
        and op == "believes"
        and set(node) == {"op", "agent", "arg"}
        and node["agent"] in agents
    ):
        _formula(
            node["arg"], atoms, agents, modal=True, depth=depth + 1, counter=counter
        )
        return
    raise ValueError("formula dialect violation")


def _relations(relations, agents, identities):
    if not isinstance(relations, Mapping) or set(relations) != set(agents):
        raise ValueError("each declared agent requires its own relation")
    result = {}
    identities = frozenset(identities)
    edges = 0
    for agent in agents:
        rows = relations[agent]
        if not isinstance(rows, Mapping) or set(rows) != identities:
            raise ValueError("every world/event needs an explicit accessibility row")
        result[agent] = {}
        for origin, targets in rows.items():
            if (
                not isinstance(targets, (list, tuple))
                or len(set(targets)) != len(targets)
                or not set(targets) <= identities
            ):
                raise ValueError("undeclared or repeated accessibility target")
            edges += len(targets)
            if edges > 1048576:
                raise ValueError("relation construction bound")
            result[agent][origin] = tuple(sorted(targets))
    return freeze(result)


@dataclass(frozen=True)
class EpistemicModel:
    atoms: tuple[str, ...]
    agents: tuple[str, ...]
    worlds: object
    relations: object
    designated: tuple[str, ...]
    history: tuple[str, ...] = ()

    def __post_init__(self):
        if not 1 <= len(self.atoms) <= 32 or not 1 <= len(self.agents) <= 16:
            raise ValueError("finite atoms/agents required")
        for names in (self.atoms, self.agents, self.designated):
            if len(set(names)) != len(names):
                raise ValueError("repeated identity")
            for name in names:
                _identity(name)
        if (
            not isinstance(self.worlds, Mapping)
            or not self.worlds
            or len(self.worlds) > 8192
        ):
            raise ValueError("finite nonempty world model required")
        for identity, values in self.worlds.items():
            _identity(identity)
            if (
                not isinstance(values, Mapping)
                or set(values) != set(self.atoms)
                or any(type(value) is not bool for value in values.values())
            ):
                raise ValueError("every world requires exact Boolean atom values")
        if not self.designated or not set(self.designated) <= set(self.worlds):
            raise ValueError("actual model alternatives must be declared")
        if len(self.history) > 512:
            raise ValueError("event history bound")
        for event in self.history:
            _identity(event)
        object.__setattr__(self, "atoms", tuple(self.atoms))
        object.__setattr__(self, "agents", tuple(self.agents))
        object.__setattr__(self, "designated", tuple(self.designated))
        object.__setattr__(self, "history", tuple(self.history))
        object.__setattr__(self, "worlds", freeze(self.worlds))
        object.__setattr__(
            self, "relations", _relations(self.relations, self.agents, self.worlds)
        )


@dataclass(frozen=True)
class EventModel:
    event_id: str
    variants: object
    relations: object
    designated: tuple[str, ...]
    assumptions: tuple[str, ...] = ()

    def bind(self, model):
        _identity(self.event_id)
        if not isinstance(self.variants, Mapping) or not 1 <= len(self.variants) <= 32:
            raise ValueError("bounded event alternatives required")
        for identity, variant in self.variants.items():
            _identity(identity)
            if (
                not isinstance(variant, Mapping)
                or set(variant) != {"pre", "post"}
                or not isinstance(variant["post"], Mapping)
            ):
                raise ValueError(
                    "typed precondition and simultaneous postconditions required"
                )
            _formula(variant["pre"], model.atoms, model.agents, modal=False)
            if not set(variant["post"]) <= set(model.atoms):
                raise ValueError("undeclared event effect")
            for value in variant["post"].values():
                _formula(value, model.atoms, model.agents, modal=False)
        if (
            not self.designated
            or len(set(self.designated)) != len(self.designated)
            or not set(self.designated) <= set(self.variants)
        ):
            raise ValueError("declared actual event alternative required")
        for assumption in self.assumptions:
            _identity(assumption)
        return _relations(self.relations, model.agents, self.variants)

    def __post_init__(self):
        object.__setattr__(self, "variants", freeze(self.variants))
        object.__setattr__(self, "relations", freeze(self.relations))
        object.__setattr__(self, "designated", tuple(self.designated))
        object.__setattr__(self, "assumptions", tuple(self.assumptions))


def _evaluate(model, world, formula, work, depth=0):
    work.step()
    if type(formula) is bool:
        return frozenset((formula,))
    op = formula["op"]
    if op == "atom":
        return frozenset((model.worlds[world][formula["name"]],))
    if op == "not":
        return frozenset(
            not value for value in _evaluate(model, world, formula["arg"], work, depth)
        )
    if op in ("and", "or"):
        # Three-valued finite model checking, not explosive empty-model truth.
        result = frozenset((op == "and",))
        for arg in formula["args"]:
            values = _evaluate(model, world, arg, work, depth)
            result = frozenset(
                (left and right) if op == "and" else (left or right)
                for left, right in product(result, values)
            )
        return result
    if depth >= work.limits.max_depth:
        raise EpistemicFrontier("NESTING_FRONTIER")
    accessible = model.relations[formula["agent"]][world]
    if not accessible:
        work.empty_views.add((formula["agent"], world))
        return frozenset((False, True))
    values = [
        _evaluate(model, target, formula["arg"], work, depth + 1)
        for target in accessible
    ]
    if any(value == frozenset((False,)) for value in values):
        return frozenset((False,))
    if all(value == frozenset((True,)) for value in values):
        return frozenset((True,))
    return frozenset((False, True))


def _admit_model(model, limits):
    if len(model.worlds) > limits.max_worlds:
        raise EpistemicFrontier("WORLD_FRONTIER")
    if len(model.history) > limits.max_events:
        raise EpistemicFrontier("EVENT_FRONTIER")
    if (
        sum(
            len(targets)
            for rows in model.relations.values()
            for targets in rows.values()
        )
        > limits.max_edges
    ):
        raise EpistemicFrontier("RELATION_FRONTIER")


def query_belief(model, formula, limits=None):
    limits = limits or EpistemicLimits()
    _formula(formula, model.atoms, model.agents)
    work = Work(limits)
    try:
        _admit_model(model, limits)
        possibilities = set()
        witnesses = []
        for world in model.designated:
            values = _evaluate(model, world, formula, work)
            possibilities.update(values)
            witnesses.append(dict(world=world, possible_values=sorted(values)))
        return dict(
            status=(
                "DETERMINATE"
                if len(possibilities) == 1
                else ("INCONSISTENT_VIEW" if work.empty_views else "UNRESOLVED")
            ),
            inconsistent_views=tuple(sorted(work.empty_views)),
            possible_values=sorted(possibilities),
            witnesses=witnesses,
            evaluations=work.used,
            frontier=[],
            history=list(model.history),
            scope="FINITE_MODEL_PREDICTION_NOT_PRIVATE_MENTAL_TRUTH",
        )
    except EpistemicFrontier as error:
        return dict(
            status="FRONTIER_UNEXPLORED",
            possible_values=[False, True],
            witnesses=[],
            evaluations=work.used,
            frontier=[str(error)],
            history=list(model.history),
            scope="FINITE_MODEL_PREDICTION_NOT_PRIVATE_MENTAL_TRUTH",
        )


def remaining_states(model, perspective_path, limits=None):
    limits = limits or EpistemicLimits()
    if not isinstance(perspective_path, (list, tuple)) or any(
        agent not in model.agents for agent in perspective_path
    ):
        raise ValueError("declared perspective path required")
    work = Work(limits)
    try:
        _admit_model(model, limits)
        if len(perspective_path) > limits.max_depth:
            raise EpistemicFrontier("NESTING_FRONTIER")
        worlds = set(model.designated)
        work.step(len(worlds))
        for agent in perspective_path:
            reached = set()
            for world in worlds:
                targets = model.relations[agent][world]
                work.step(1 + len(targets))
                reached.update(targets)
            worlds = reached
        return dict(
            status="CONDITIONAL_POSSIBILITIES" if worlds else "INCONSISTENT_VIEW",
            worlds=tuple(sorted(worlds)),
            values=tuple(model.worlds[world] for world in sorted(worlds)),
            frontier=(),
            evaluations=work.used,
            probability_status="NO_WEIGHTS_INFERRED_FROM_STATE_COUNTS",
        )
    except EpistemicFrontier as error:
        return dict(
            status="FRONTIER_UNEXPLORED",
            worlds=(),
            values=(),
            evaluations=work.used,
            frontier=(str(error),),
        )


def minimize_model(model, work):
    """Reachability plus exact finite bisimulation; no world-count probabilities.

    Equal valuations alone are insufficient: each refinement also preserves
    every agent's set of successor classes, including empty inconsistent views.
    """
    reached = set(model.designated)
    pending = list(model.designated)
    while pending:
        world = pending.pop()
        for agent in model.agents:
            neighbors = model.relations[agent][world]
            work.step(1 + len(neighbors))
            for target in neighbors:
                if target not in reached:
                    reached.add(target)
                    pending.append(target)
    names = tuple(sorted(reached))

    def partition(signatures):
        unique = {
            value: index for index, value in enumerate(sorted(set(signatures.values())))
        }
        return {key: unique[value] for key, value in signatures.items()}

    colors = partition(
        {key: tuple(model.worlds[key][atom] for atom in model.atoms) for key in names}
    )
    while True:
        signatures = {}
        for key in names:
            successors = []
            for agent in model.agents:
                targets = model.relations[agent][key]
                work.step(1 + len(targets))
                successors.append(tuple(sorted({colors[target] for target in targets})))
            signatures[key] = (colors[key], tuple(successors))
        refined = partition(signatures)
        if len(set(refined.values())) == len(set(colors.values())):
            colors = refined
            break
        colors = refined
    groups = {}
    for key, color in colors.items():
        groups.setdefault(color, []).append(key)
    identities = {
        color: "world:"
        + sha256(
            json.dumps(sorted(members), separators=(",", ":")).encode()
        ).hexdigest()
        for color, members in groups.items()
    }
    worlds = {
        identities[color]: dict(model.worlds[members[0]])
        for color, members in groups.items()
    }
    relations = {
        agent: {
            identities[color]: tuple(
                sorted(
                    {
                        identities[colors[target]]
                        for target in model.relations[agent][members[0]]
                    }
                )
            )
            for color, members in groups.items()
        }
        for agent in model.agents
    }
    designated = tuple(sorted({identities[colors[key]] for key in model.designated}))
    return EpistemicModel(
        model.atoms, model.agents, worlds, relations, designated, model.history
    )


def update_perspectives(model, event, limits=None, *, minimize=True):
    limits = limits or EpistemicLimits()
    event_relations = event.bind(model)
    work = Work(limits)
    if len(model.history) >= limits.max_events:
        return None, dict(
            status="FRONTIER_UNEXPLORED", frontier=["EVENT_FRONTIER"], evaluations=0
        )
    try:
        _admit_model(model, limits)
        worlds, pairs = {}, {}
        for old, values in model.worlds.items():
            for variant_id, variant in event.variants.items():
                work.step()
                if _evaluate(model, old, variant["pre"], work) != frozenset((True,)):
                    continue
                if len(worlds) >= limits.max_worlds:
                    raise EpistemicFrontier("WORLD_FRONTIER")
                identity = (
                    "world:"
                    + sha256(
                        json.dumps(
                            [old, event.event_id, variant_id], separators=(",", ":")
                        ).encode()
                    ).hexdigest()
                )
                changed = dict(values)
                for atom, expression in variant["post"].items():
                    changed[atom] = next(iter(_evaluate(model, old, expression, work)))
                worlds[identity], pairs[old, variant_id] = changed, identity
        designated = tuple(
            pairs[old, variant]
            for old in model.designated
            for variant in event.designated
            if (old, variant) in pairs
        )
        if not designated:
            return None, dict(
                status="INAPPLICABLE_EVENT", frontier=[], evaluations=work.used
            )
        relations, edges = {}, 0
        for agent in model.agents:
            relations[agent] = {}
            for (old, variant), origin in pairs.items():
                targets = []
                for neighbor in model.relations[agent][old]:
                    for alternative in event_relations[agent][variant]:
                        work.step()
                        target = pairs.get((neighbor, alternative))
                        if target is not None:
                            if edges >= limits.max_edges:
                                raise EpistemicFrontier("RELATION_FRONTIER")
                            targets.append(target)
                            edges += 1
                relations[agent][origin] = tuple(targets)
        updated = EpistemicModel(
            model.atoms,
            model.agents,
            worlds,
            relations,
            designated,
            (*model.history, event.event_id),
        )
        product_worlds = len(updated.worlds)
        if minimize:
            updated = minimize_model(updated, work)
        return updated, dict(
            status="APPLIED",
            product_world_count=product_worlds,
            retained_world_count=len(updated.worlds),
            frontier=[],
            evaluations=work.used,
            world_count=len(worlds),
            edge_count=edges,
            assumptions=event.assumptions,
            scope="DECLARED_EVENT_OBSERVATION_MODEL_ONLY",
        )
    except EpistemicFrontier as error:
        return None, dict(
            status="FRONTIER_UNEXPLORED", frontier=[str(error)], evaluations=work.used
        )

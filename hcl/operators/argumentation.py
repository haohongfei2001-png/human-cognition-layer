"""Finite structured arguments, scoped attacks, preference defeat and acceptance.

Rooted support is not argument acceptance. This solver constructs proof trees
first and runs Dung's grounded characteristic fixed point on their defeat graph.
It supplies no premise truth, universal moral rule or semantic reconstruction.
"""

from dataclasses import dataclass, replace, asdict
from hashlib import sha256
from itertools import product, combinations

from hcl.memory.codec import canonical


@dataclass(frozen=True, order=True)
class Literal:
    atom: str
    negative: bool = False
    scope: str = "declared"
    kind: str = "CLAIM"

    def __post_init__(self):
        if (
            any(
                type(value) is not str or not value or len(value) > 160
                for value in (self.atom, self.scope)
            )
            or type(self.negative) is not bool
            or self.kind not in ("CLAIM", "RULE_APPLICABLE")
        ):
            raise ValueError("bounded scoped literal required")

    def contrary(self, other):
        return (self.atom, self.scope, self.kind) == (
            other.atom,
            other.scope,
            other.kind,
        ) and self.negative != other.negative


@dataclass(frozen=True)
class Premise:
    premise_id: str
    conclusion: Literal
    ordinary: bool = True
    assumptions: frozenset[str] = frozenset()

    def __post_init__(self):
        object.__setattr__(self, "assumptions", frozenset(self.assumptions))


@dataclass(frozen=True)
class Rule:
    rule_id: str
    premises: tuple[Literal, ...]
    conclusion: Literal
    strict: bool = False
    assumptions: frozenset[str] = frozenset()

    def __post_init__(self):
        object.__setattr__(self, "premises", tuple(self.premises))
        object.__setattr__(self, "assumptions", frozenset(self.assumptions))


@dataclass(frozen=True)
class Theory:
    premises: tuple[Premise, ...]
    rules: tuple[Rule, ...]
    priorities: tuple[tuple[str, str], ...] = ()
    active_assumptions: frozenset[str] = frozenset()

    def __post_init__(self):
        if len(self.premises) > 128 or len(self.rules) > 128:
            raise ValueError("bounded theory required")
        identities = []
        for premise in self.premises:
            if (
                type(premise) is not Premise
                or type(premise.conclusion) is not Literal
                or type(premise.ordinary) is not bool
            ):
                raise ValueError("typed premise required")
            identities.append(premise.premise_id)
        for rule in self.rules:
            if (
                type(rule) is not Rule
                or type(rule.conclusion) is not Literal
                or type(rule.strict) is not bool
                or not 1 <= len(rule.premises) <= 8
            ):
                raise ValueError("typed nonempty rule required")
            if any(
                type(p) is not Literal or p.scope != rule.conclusion.scope
                for p in rule.premises
            ):
                raise ValueError(
                    "cross-scope rule requires an upstream explicit bridge"
                )
            identities.append(rule.rule_id)
        if len(set(identities)) != len(identities) or any(
            type(key) is not str or not key or len(key) > 160 for key in identities
        ):
            raise ValueError("unique theory identities required")
        if any(
            type(a) is not str or not a or len(a) > 160 for a in self.active_assumptions
        ):
            raise ValueError("bounded active assumption identities required")
        for row in (*self.premises, *self.rules):
            if any(
                type(a) is not str or not a or len(a) > 160 for a in row.assumptions
            ):
                raise ValueError("bounded assumption identity required")
        if any(
            len(pair) != 2 or not set(pair) <= set(identities) or pair[0] == pair[1]
            for pair in self.priorities
        ):
            raise ValueError("declared strict priority required")
        closure = {key: set() for key in identities}
        for better, worse in self.priorities:
            closure[better].add(worse)
        for pivot in identities:
            for origin in identities:
                if pivot in closure[origin]:
                    closure[origin].update(closure[pivot])
        if any(key in targets for key, targets in closure.items()):
            raise ValueError("cyclic priority is unresolved, not a total order")
        object.__setattr__(self, "premises", tuple(self.premises))
        object.__setattr__(self, "rules", tuple(self.rules))
        object.__setattr__(
            self, "priorities", tuple(tuple(pair) for pair in self.priorities)
        )
        object.__setattr__(
            self, "active_assumptions", frozenset(self.active_assumptions)
        )


@dataclass(frozen=True)
class Argument:
    argument_id: str
    conclusion: Literal
    top: str
    top_kind: str
    children: tuple[str, ...]
    subarguments: frozenset[str]
    ancestry_literals: frozenset[Literal]
    premises: frozenset[str]
    rules: frozenset[str]
    bases: frozenset[str]
    assumptions: frozenset[str]


class Frontier(Exception):
    pass


class Work:
    def __init__(self, maximum):
        if type(maximum) is not int or not 1 <= maximum <= 10000000:
            raise ValueError("bounded work required")
        self.maximum, self.used = maximum, 0

    def take(self, amount=1):
        if self.used + amount > self.maximum:
            raise Frontier("ARGUMENT_WORK_BOUND")
        self.used += amount


def _graph(arguments, defeats, maximum):
    names = tuple(sorted(arguments))
    edges = tuple(tuple(pair) for pair in defeats)
    if (
        len(names) > maximum
        or len(names) != len(set(names))
        or any(type(name) is not str or not name or len(name) > 160 for name in names)
        or any(len(pair) != 2 or not set(pair) <= set(names) for pair in edges)
    ):
        raise ValueError("bounded declared defeat graph required")
    return names, tuple(sorted(set(edges)))


def grounded(arguments, defeats, *, max_work=100000):
    """Least fixed point of defense, not intersection of preferred extensions."""
    names, defeats = _graph(arguments, defeats, 4096)
    incoming = {key: set() for key in names}
    outgoing = {key: set() for key in names}
    for attacker, target in defeats:
        incoming[target].add(attacker)
        outgoing[attacker].add(target)
    work = Work(max_work)
    accepted = set()
    iterations = []
    try:
        while True:
            attacked = set()
            for key in accepted:
                work.take(len(outgoing[key]))
                attacked.update(outgoing[key])
            defended = set()
            for key in names:
                work.take(1 + len(incoming[key]))
                if incoming[key] <= attacked:
                    defended.add(key)
            iterations.append(tuple(sorted(defended)))
            if defended == accepted:
                break
            if not accepted <= defended:
                raise AssertionError("characteristic iteration lost monotonicity")
            accepted = defended
        rejected = (
            set().union(*(outgoing[key] for key in accepted)) if accepted else set()
        )
        return dict(
            status="COMPLETE",
            grounded=tuple(sorted(accepted)),
            labels={
                key: "IN" if key in accepted else "OUT" if key in rejected else "UNDEC"
                for key in names
            },
            iterations=tuple(iterations),
            work=work.used,
            frontier=(),
        )
    except Frontier as error:
        return dict(
            status="FRONTIER_UNEXPLORED",
            grounded=(),
            labels={},
            iterations=tuple(iterations),
            work=work.used,
            frontier=(str(error),),
        )


def preferred_extensions(arguments, defeats, *, max_work=100000):
    names, defeats = _graph(arguments, defeats, 24)
    work = Work(max_work)
    admissible_count = 0
    maximal = []
    try:
        for mask in range(1 << len(names)):
            work.take()
            selected = frozenset(
                name for i, name in enumerate(names) if mask & (1 << i)
            )
            conflict = False
            attacked = set()
            attackers = set()
            for attacker, target in defeats:
                work.take()
                if attacker in selected:
                    attacked.add(target)
                if target in selected:
                    attackers.add(attacker)
                if attacker in selected and target in selected:
                    conflict = True
                    break
            if not conflict and attackers <= attacked:
                admissible_count += 1
                dominated = False
                retained = []
                for group in maximal:
                    work.take(1 + len(group) + len(selected))
                    if selected <= group:
                        dominated = True
                    if not group < selected:
                        retained.append(group)
                if not dominated:
                    if len(retained) >= 256:
                        raise Frontier("PREFERRED_WITNESS_STORAGE_BOUND")
                    retained.append(selected)
                maximal = retained
        preferred = tuple(tuple(sorted(group)) for group in maximal)
        return dict(
            status="COMPLETE",
            preferred=tuple(sorted(preferred)),
            admissible_witnesses=(),
            checked_admissible=admissible_count,
            work=work.used,
            frontier=(),
        )
    except Frontier as error:
        # Incomplete subset enumeration cannot certify maximality or skeptical
        # acceptance. Keep explicitly admissible witnesses, not fake extensions.
        return dict(
            status="FRONTIER_UNEXPLORED",
            preferred=(),
            admissible_witnesses=tuple(tuple(sorted(group)) for group in maximal),
            checked_admissible=admissible_count,
            work=work.used,
            frontier=(str(error),),
        )


def construct_arguments(theory, *, max_arguments=256, max_work=100000):
    if (
        type(theory) is not Theory
        or type(max_arguments) is not int
        or not 1 <= max_arguments <= 4096
    ):
        raise ValueError("typed bounded argument construction required")
    work = Work(max_work)
    arguments = {}
    by_literal = {}
    signatures = set()
    cycles = set()

    def add(conclusion, top, kind, children, premises, rules, bases, assumptions):
        work.take()
        if len(arguments) >= max_arguments:
            raise Frontier("ARGUMENT_COUNT_BOUND")
        identity = (
            "argument:"
            + sha256(
                canonical(
                    [
                        asdict(conclusion),
                        top,
                        kind,
                        list(children),
                        sorted(premises),
                        sorted(rules),
                        sorted(bases),
                        sorted(assumptions),
                    ]
                ).encode()
            ).hexdigest()
        )
        subs = {identity}
        ancestry = {conclusion}
        for child in children:
            subs.update(arguments[child].subarguments)
            ancestry.update(arguments[child].ancestry_literals)
        argument = Argument(
            identity,
            conclusion,
            top,
            kind,
            tuple(children),
            frozenset(subs),
            frozenset(ancestry),
            frozenset(premises),
            frozenset(rules),
            frozenset(bases),
            frozenset(assumptions),
        )
        arguments[identity] = argument
        by_literal.setdefault(conclusion, []).append(identity)

    try:
        for premise in theory.premises:
            if premise.assumptions <= theory.active_assumptions:
                add(
                    premise.conclusion,
                    premise.premise_id,
                    "ORDINARY_PREMISE" if premise.ordinary else "STRICT_PREMISE",
                    (),
                    (premise.premise_id,),
                    (),
                    (premise.premise_id,) if premise.ordinary else (),
                    premise.assumptions,
                )
        while True:
            before = len(arguments)
            for rule in theory.rules:
                work.take()
                if not rule.assumptions <= theory.active_assumptions or any(
                    p not in by_literal for p in rule.premises
                ):
                    continue
                choices = tuple(tuple(by_literal[p]) for p in rule.premises)
                for children in product(*choices):
                    work.take()
                    signature = (rule.rule_id, children)
                    if signature in signatures:
                        continue
                    signatures.add(signature)
                    supports = [arguments[key] for key in children]
                    if any(
                        rule.rule_id in child.rules
                        or rule.conclusion in child.ancestry_literals
                        for child in supports
                    ):
                        cycles.add(rule.rule_id)
                        continue

                    def union(field):
                        return set().union(
                            *(getattr(child, field) for child in supports)
                        )

                    add(
                        rule.conclusion,
                        rule.rule_id,
                        "STRICT_RULE" if rule.strict else "DEFEASIBLE_RULE",
                        children,
                        union("premises"),
                        union("rules") | {rule.rule_id},
                        union("bases") if rule.strict else {rule.rule_id},
                        union("assumptions") | set(rule.assumptions),
                    )
            if len(arguments) == before:
                break
        return arguments, dict(
            status="COMPLETE_ACYCLIC_ARGUMENTS",
            work=work.used,
            frontier=(),
            excluded_circular_rules=tuple(sorted(cycles)),
        )
    except Frontier as error:
        return arguments, dict(
            status="FRONTIER_UNEXPLORED",
            work=work.used,
            frontier=(str(error),),
            excluded_circular_rules=tuple(sorted(cycles)),
        )


ACCEPTANCE_SCOPE = (
    "FINITE_ACYCLIC_SCOPED_ARGUMENTS_WITH_EXPLICIT_PRIORITIES_NOT_PREMISE_TRUTH"
)


def evaluate_arguments(theory, *, max_arguments=256, max_work=100000):
    arguments, construction = construct_arguments(
        theory, max_arguments=max_arguments, max_work=max_work
    )
    if construction["frontier"]:
        return dict(
            status="FRONTIER_UNEXPLORED",
            arguments=arguments,
            attacks=(),
            defeats=(),
            labels={},
            grounded=(),
            iterations=(),
            excluded_circular_rules=construction["excluded_circular_rules"],
            acceptance_scope=ACCEPTANCE_SCOPE,
            frontier=construction["frontier"],
            work=construction["work"],
        )
    remaining = max_work - construction["work"]
    if remaining < 1:
        return dict(
            status="FRONTIER_UNEXPLORED",
            arguments=arguments,
            attacks=(),
            defeats=(),
            labels={},
            grounded=(),
            iterations=(),
            excluded_circular_rules=construction["excluded_circular_rules"],
            acceptance_scope=ACCEPTANCE_SCOPE,
            frontier=("ARGUMENT_WORK_BOUND",),
            work=construction["work"],
        )
    work = Work(remaining)
    priority = {
        key: set()
        for key in (
            *[p.premise_id for p in theory.premises],
            *[r.rule_id for r in theory.rules],
        )
    }
    for better, worse in theory.priorities:
        priority[better].add(worse)
    for pivot in priority:
        for origin in priority:
            if pivot in priority[origin]:
                priority[origin].update(priority[pivot])

    def preferred(target, attacker):
        return bool(target.bases and attacker.bases) and all(
            a in priority[t] for t in target.bases for a in attacker.bases
        )

    attacks = []
    defeats = set()
    try:
        for attacker in arguments.values():
            for target in arguments.values():
                for sub_id in sorted(target.subarguments):
                    work.take()
                    sub = arguments[sub_id]
                    kind = None
                    if attacker.conclusion.contrary(sub.conclusion):
                        if sub.top_kind == "ORDINARY_PREMISE":
                            kind = "UNDERMINING"
                        elif sub.top_kind == "DEFEASIBLE_RULE":
                            kind = "REBUTTAL"
                    if (
                        sub.top_kind == "DEFEASIBLE_RULE"
                        and attacker.conclusion.kind == "RULE_APPLICABLE"
                        and attacker.conclusion.negative
                        and attacker.conclusion.atom == sub.top
                        and attacker.conclusion.scope == sub.conclusion.scope
                    ):
                        kind = "UNDERCUTTING"
                    if kind:
                        blocked = kind != "UNDERCUTTING" and preferred(sub, attacker)
                        attacks.append(
                            dict(
                                attacker=attacker.argument_id,
                                target=target.argument_id,
                                subargument=sub_id,
                                kind=kind,
                                blocked_by_priority=blocked,
                            )
                        )
                        if not blocked:
                            defeats.add((attacker.argument_id, target.argument_id))
        if remaining - work.used < 1:
            raise Frontier("ARGUMENT_WORK_BOUND")
        strict = tuple(
            argument for argument in arguments.values() if not argument.bases
        )
        strict_conflicts = []
        for i, first in enumerate(strict):
            for second in strict[i + 1 :]:
                work.take()
                if first.conclusion.contrary(second.conclusion):
                    strict_conflicts.append((first.argument_id, second.argument_id))
        if remaining - work.used < 1:
            raise Frontier("ARGUMENT_WORK_BOUND")
        graph = grounded(arguments, defeats, max_work=remaining - work.used)
        return dict(
            status=graph["status"],
            theory_consistency=(
                "INCONSISTENT_STRICT_CORE"
                if strict_conflicts
                else "NO_STRICT_CONFLICT_FOUND"
            ),
            strict_conflicts=tuple(strict_conflicts),
            arguments=arguments,
            attacks=tuple(attacks),
            defeats=tuple(sorted(defeats)),
            labels=graph["labels"],
            grounded=graph["grounded"],
            frontier=graph["frontier"],
            iterations=graph["iterations"],
            work=construction["work"] + work.used + graph["work"],
            excluded_circular_rules=construction["excluded_circular_rules"],
            acceptance_scope=ACCEPTANCE_SCOPE,
        )
    except Frontier as error:
        return dict(
            status="FRONTIER_UNEXPLORED",
            arguments=arguments,
            attacks=tuple(attacks),
            defeats=tuple(sorted(defeats)),
            labels={},
            grounded=(),
            iterations=(),
            excluded_circular_rules=construction["excluded_circular_rules"],
            acceptance_scope=ACCEPTANCE_SCOPE,
            frontier=(str(error),),
            work=construction["work"] + work.used,
        )


def claim_acceptance(result, literal):
    accepted = {
        argument.conclusion
        for key, argument in result["arguments"].items()
        if result["labels"].get(key) == "IN"
    }
    return (literal in accepted, any(literal.contrary(value) for value in accepted))


def critical_retractions(theory, target, candidates, *, max_work=100000):
    """Verify a minimum-cardinality change within a declared finite edit set.

    Each hypothetical removes candidate theory items, never source text. Every
    smaller subset is actually recomputed before the first successful witness.
    A solver/search frontier cannot stand in for a negative sensitivity result.
    """
    candidates = tuple(sorted(candidates))
    all_ids = {p.premise_id for p in theory.premises} | {
        r.rule_id for r in theory.rules
    }
    if (
        type(target) is not Literal
        or len(candidates) > 12
        or len(set(candidates)) != len(candidates)
        or not set(candidates) <= all_ids
    ):
        raise ValueError("bounded declared sensitivity edits required")
    original = evaluate_arguments(theory, max_work=max_work)
    used = original["work"]
    if original["frontier"]:
        return dict(
            status="FRONTIER_UNEXPLORED", edits=(), minimum_cardinality=None, work=used
        )
    before = claim_acceptance(original, target)
    checked = 0
    for cardinality in range(1, len(candidates) + 1):
        for selected in combinations(candidates, cardinality):
            if used >= max_work:
                return dict(
                    status="FRONTIER_UNEXPLORED",
                    edits=(),
                    minimum_cardinality=None,
                    work=used,
                )
            removed = set(selected)
            changed = replace(
                theory,
                premises=tuple(
                    p for p in theory.premises if p.premise_id not in removed
                ),
                rules=tuple(r for r in theory.rules if r.rule_id not in removed),
                priorities=tuple(
                    pair for pair in theory.priorities if not set(pair) & removed
                ),
            )
            result = evaluate_arguments(changed, max_work=max_work - used)
            used += result["work"]
            if result["frontier"]:
                return dict(
                    status="FRONTIER_UNEXPLORED",
                    edits=(),
                    minimum_cardinality=None,
                    work=used,
                )
            after = claim_acceptance(result, target)
            checked += 1
            if after != before:
                return dict(
                    status="MINIMUM_CARDINALITY_WITNESS",
                    edits=selected,
                    minimum_cardinality=cardinality,
                    before=before,
                    after=after,
                    checked_subsets=checked,
                    work=used,
                    scope="ONLY_THE_DECLARED_RETRACTION_CANDIDATE_SET",
                )
    return dict(
        status="NO_CHANGE_IN_DECLARED_EDIT_SET",
        edits=(),
        minimum_cardinality=None,
        checked_subsets=checked,
        work=used,
    )

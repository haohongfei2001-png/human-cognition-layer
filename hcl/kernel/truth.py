"""Rooted assumption-labelled support, with bounded incremental fixed points.

This computes support in an explicitly supplied graph. It does not establish
source truth, causal influence or argument acceptance. Scope/Bridge obligations
are checked by the scoped program compiler before this pure graph is evaluated.
"""

from collections import deque
from dataclasses import dataclass, replace
from hashlib import sha256
from itertools import product
import json
from types import MappingProxyType

from hcl.kernel.scope import identifier


@dataclass(frozen=True)
class TruthProfile:
    max_claims: int = 256
    max_roots: int = 256
    max_rules: int = 512
    max_assumptions: int = 256
    max_supports_per_claim: int = 64
    max_work: int = 100000

    def __post_init__(self):
        for name, maximum in (
            ("max_claims", 2048),
            ("max_roots", 4096),
            ("max_rules", 4096),
            ("max_assumptions", 1024),
            ("max_supports_per_claim", 1024),
            ("max_work", 1000000),
        ):
            value = getattr(self, name)
            if type(value) is not int or not 1 <= value <= maximum:
                raise ValueError("bounded truth profile required")


@dataclass(frozen=True)
class Support:
    assumptions: frozenset[str]
    roots: frozenset[str]

    def __post_init__(self):
        object.__setattr__(self, "assumptions", frozenset(self.assumptions))
        object.__setattr__(self, "roots", frozenset(self.roots))

    def key(self):
        return tuple(sorted(self.assumptions)), tuple(sorted(self.roots))


@dataclass(frozen=True)
class EvidenceRoot:
    root_id: str
    claim_id: str
    assumptions: frozenset[str] = frozenset()
    active: bool = True
    provenance_roots: frozenset[str] = frozenset()

    def __post_init__(self):
        object.__setattr__(self, "assumptions", frozenset(self.assumptions))
        object.__setattr__(self, "provenance_roots", frozenset(self.provenance_roots))


@dataclass(frozen=True)
class DerivationRule:
    rule_id: str
    premises: tuple[str, ...]
    conclusion: str
    assumptions: frozenset[str] = frozenset()
    enabled: bool = True

    def __post_init__(self):
        object.__setattr__(self, "premises", tuple(self.premises))
        object.__setattr__(self, "assumptions", frozenset(self.assumptions))


@dataclass(frozen=True)
class TruthProgram:
    claims: tuple[str, ...]
    roots: tuple[EvidenceRoot, ...]
    rules: tuple[DerivationRule, ...]
    active_assumptions: frozenset[str]
    nogoods: tuple[frozenset[str], ...] = ()

    def __post_init__(self):
        for name in ("claims", "roots", "rules"):
            object.__setattr__(self, name, tuple(getattr(self, name)))
        object.__setattr__(self, "active_assumptions", frozenset(self.active_assumptions))
        object.__setattr__(self, "nogoods", tuple(frozenset(s) for s in self.nogoods))


@dataclass(frozen=True)
class TruthState:
    supports: object
    frontier: frozenset[str]
    work: int
    recomputed_claims: frozenset[str]
    profile: TruthProfile

    def __post_init__(self):
        object.__setattr__(
            self,
            "supports",
            MappingProxyType(
                {key: tuple(sorted(value, key=lambda s: s.key())) for key, value in self.supports.items()}
            ),
        )

    def environments(self, claim):
        values = {support.assumptions for support in self.supports[claim]}
        return tuple(
            sorted(
                (env for env in values if not any(other < env for other in values)),
                key=lambda env: tuple(sorted(env)),
            )
        )

    def semantic_hash(self, claim):
        value = [support.key() for support in self.supports[claim]]
        return sha256(json.dumps([value, claim in self.frontier], sort_keys=True).encode()).hexdigest()

    def support_bits(self, positive_claim, negative_claim):
        return {
            "positive_support": bool(self.supports[positive_claim]),
            "negative_support": bool(self.supports[negative_claim]),
            "frontier_unexplored": bool({positive_claim, negative_claim} & self.frontier),
            "epistemic_status": "CONDITIONAL_SUPPORT_NOT_TRUTH_OR_ARGUMENT_ACCEPTANCE",
        }


@dataclass(frozen=True)
class RevisionResult:
    state: TruthState
    changed_claims: tuple[str, ...]
    retained_claims: tuple[str, ...]


class TruthKernel:
    def __init__(self, profile=None):
        self.profile = profile or TruthProfile()
        if type(self.profile) is not TruthProfile:
            raise ValueError("typed truth profile required")

    def validate(self, program):
        if type(program) is not TruthProgram:
            raise ValueError("typed truth program required")
        claims = set(program.claims)
        if (
            len(claims) != len(program.claims)
            or not claims
            or len(claims) > self.profile.max_claims
            or len(program.roots) > self.profile.max_roots
            or len(program.rules) > self.profile.max_rules
            or len(program.nogoods) > self.profile.max_assumptions
        ):
            raise ValueError("truth program identity or size bound")
        assumptions = set(program.active_assumptions)
        root_ids, rule_ids = set(), set()
        for key in claims:
            identifier(key)
        for root in program.roots:
            if (
                type(root) is not EvidenceRoot
                or root.root_id in root_ids
                or root.claim_id not in claims
                or type(root.active) is not bool
            ):
                raise ValueError("invalid evidence root")
            identifier(root.root_id)
            root_ids.add(root.root_id)
            assumptions.update(root.assumptions)
        direct_roots = {root.root_id for root in program.roots if not root.provenance_roots}
        if any(not root.provenance_roots <= direct_roots for root in program.roots):
            raise ValueError("derived seed requires original evidence roots, not a self-supporting cycle")
        for rule in program.rules:
            if (
                type(rule) is not DerivationRule
                or rule.rule_id in rule_ids
                or rule.conclusion not in claims
                or not rule.premises
                or len(rule.premises) != len(set(rule.premises))
                or not set(rule.premises) <= claims
                or type(rule.enabled) is not bool
            ):
                raise ValueError("rootless axioms or invalid derivation rule")
            identifier(rule.rule_id)
            rule_ids.add(rule.rule_id)
            assumptions.update(rule.assumptions)
        for nogood in program.nogoods:
            if not nogood:
                raise ValueError("explicit nonempty nogood required")
            assumptions.update(nogood)
        if len(assumptions) > self.profile.max_assumptions:
            raise ValueError("assumption bound exceeded")
        for key in assumptions:
            identifier(key)

    @staticmethod
    def _dependents(programs, seeds):
        reverse = {}
        for program in programs:
            for rule in program.rules:
                for premise in rule.premises:
                    reverse.setdefault(premise, set()).add(rule.conclusion)
        reached, queue = set(seeds), deque(sorted(seeds))
        while queue:
            for conclusion in sorted(reverse.get(queue.popleft(), ())):
                if conclusion not in reached:
                    reached.add(conclusion)
                    queue.append(conclusion)
        return reached

    def run(self, program):
        self.validate(program)
        return self._close(program, set(program.claims), {}, set())

    def revise(self, previous_program, previous_state, program):
        self.validate(previous_program)
        self.validate(program)
        if type(previous_state) is not TruthState or set(previous_state.supports) != set(
            previous_program.claims
        ):
            raise ValueError("previous state/program mismatch")
        # Prior state is a retained result of this kernel, not arbitrary model
        # input. The durable loader additionally binds its content identity.
        seeds = (set(previous_program.claims) ^ set(program.claims)) | set(previous_state.frontier)
        changed_assumptions = previous_program.active_assumptions ^ program.active_assumptions
        for kind, key in (("roots", "root_id"), ("rules", "rule_id")):
            old = {getattr(row, key): row for row in getattr(previous_program, kind)}
            new = {getattr(row, key): row for row in getattr(program, kind)}
            for identity in set(old) | set(new):
                before, after = old.get(identity), new.get(identity)
                if before != after or any(
                    row and row.assumptions & changed_assumptions for row in (before, after)
                ):
                    for row in (before, after):
                        if row:
                            seeds.add(row.claim_id if kind == "roots" else row.conclusion)
        if (
            previous_program.nogoods != program.nogoods
            or replace(previous_state.profile, max_work=self.profile.max_work) != self.profile
        ):
            seeds.update(program.claims)
        old_roots = {row.root_id: row for row in previous_program.roots}
        new_roots = {row.root_id: row for row in program.roots}
        changed_root_ids = {
            key
            for key in set(old_roots) | set(new_roots)
            if old_roots.get(key) != new_roots.get(key)
            or any(
                row and row.assumptions & changed_assumptions
                for row in (old_roots.get(key), new_roots.get(key))
            )
        }
        for root in (*previous_program.roots, *program.roots):
            if root.provenance_roots & changed_root_ids:
                seeds.add(root.claim_id)
        dirty = self._dependents((previous_program, program), seeds) & set(program.claims)
        retained = {claim: previous_state.supports[claim] for claim in program.claims if claim not in dirty}
        state = self._close(program, dirty, retained, set(previous_state.frontier) - dirty)
        all_claims = set(previous_program.claims) | set(program.claims)
        changed = tuple(
            sorted(
                claim
                for claim in all_claims
                if claim not in previous_state.supports
                or claim not in state.supports
                or previous_state.semantic_hash(claim) != state.semantic_hash(claim)
            )
        )
        return RevisionResult(state, changed, tuple(sorted(all_claims - set(changed))))

    def _close(self, program, targets, seed, inherited_frontier):
        labels = {claim: set(seed.get(claim, ())) for claim in program.claims}
        work, frontier = 0, set(inherited_frontier)
        exhausted = False

        def insert(claim, support):
            nonlocal work, exhausted
            if work >= self.profile.max_work:
                exhausted = True
                frontier.update(targets)
                return False
            work += 1
            if not support.roots or not support.assumptions <= program.active_assumptions:
                return False
            if any(nogood <= support.assumptions for nogood in program.nogoods):
                return False
            current = labels[claim]
            if any(
                prior.assumptions <= support.assumptions and prior.roots <= support.roots for prior in current
            ):
                return False
            dominated = {
                prior
                for prior in current
                if support.assumptions <= prior.assumptions and support.roots <= prior.roots
            }
            if len(current - dominated) >= self.profile.max_supports_per_claim:
                frontier.add(claim)
                return False
            current.difference_update(dominated)
            current.add(support)
            return True

        originals = {root.root_id: root for root in program.roots if not root.provenance_roots}
        live_originals = {
            key
            for key, root in originals.items()
            if root.active
            and root.assumptions <= program.active_assumptions
            and not any(nogood <= root.assumptions for nogood in program.nogoods)
        }
        for root in sorted(program.roots, key=lambda x: x.root_id):
            if root.active and root.claim_id in targets and root.provenance_roots <= live_originals:
                insert(
                    root.claim_id,
                    Support(
                        root.assumptions
                        | frozenset().union(*(originals[key].assumptions for key in root.provenance_roots)),
                        root.provenance_roots or frozenset({root.root_id}),
                    ),
                )
        changed = True
        while changed and not exhausted:
            changed = False
            for rule in sorted(program.rules, key=lambda x: x.rule_id):
                if (
                    not rule.enabled
                    or rule.conclusion not in targets
                    or not rule.assumptions <= program.active_assumptions
                ):
                    continue
                inputs = [tuple(sorted(labels[claim], key=lambda s: s.key())) for claim in rule.premises]
                for combination in product(*inputs):
                    assumptions = rule.assumptions | frozenset().union(*(x.assumptions for x in combination))
                    roots = frozenset().union(*(x.roots for x in combination))
                    changed = insert(rule.conclusion, Support(assumptions, roots)) or changed
                    if exhausted:
                        break
                if exhausted:
                    break
        frontier = self._dependents((program,), frontier) & set(program.claims)
        return TruthState(labels, frozenset(frontier), work, frozenset(targets), self.profile)

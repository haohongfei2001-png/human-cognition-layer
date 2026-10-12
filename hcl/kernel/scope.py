"""Shared exact dependency checks; narrative claims never confer access."""

from collections.abc import Mapping

from hcl.kernel.types import HCLFailure, Principal, RULE_VERSION


def failure(status, code, field, message, stage="commit"):
    return HCLFailure(status, stage, code, field, message)


def identifier(value):
    if type(value) is not str or not value.strip():
        raise ValueError("nonempty identifier required")
    value.encode("utf-8")
    return value


def principal_identity(principal):
    if type(principal) is not Principal:
        raise ValueError("typed principal required")
    identifier(principal.tenant_id)
    identifier(principal.subject_id)


def version_map(read_set):
    if not isinstance(read_set, Mapping) or any(
        type(key) is not str or not key or type(version) is not int or version < 1
        for key, version in read_set.items()
    ):
        raise failure(
            "INVALID_REQUEST", "INVALID_READ_SET", "read_set", "Exact positive source versions are required."
        )
    return dict(read_set)


def check_commit_contract(expected_revision, read_set, access_epoch, delta):
    version_map(read_set)
    if (
        type(expected_revision) is not int
        or expected_revision < 0
        or type(access_epoch) is not int
        or access_epoch < 0
        or type(delta.base_revision) is not int
        or type(delta.access_epoch) is not int
        or expected_revision != delta.base_revision
        or access_epoch != delta.access_epoch
        or dict(read_set) != version_map(delta.read_set)
    ):
        raise failure("FAILED", "DELTA_CONTRACT_MISMATCH", "delta", "The commit contract is inconsistent.")
    if delta.rule_version != RULE_VERSION:
        raise failure(
            "STALE_STATE", "RULE_VERSION_CHANGED", "rule_version", "The rule version is no longer current."
        )


# Cognitive scope does not contain or grant host AccessPolicy permissions.
from dataclasses import dataclass
from itertools import product


@dataclass(frozen=True)
class Perspective:
    perspective_id: str
    agent_id: str | None
    nested_path: tuple[str, ...]
    at_point: str
    observation_model: str
    belief_model: str
    source_evidence: tuple[str, ...]

    def __post_init__(self):
        object.__setattr__(self, "nested_path", tuple(self.nested_path))
        object.__setattr__(self, "source_evidence", tuple(self.source_evidence))
        for value in (
            self.perspective_id,
            self.at_point,
            self.observation_model,
            self.belief_model,
            *self.nested_path,
            *self.source_evidence,
        ):
            identifier(value)
        if self.agent_id is not None:
            identifier(self.agent_id)
        if len(self.nested_path) > 16:
            raise ValueError("bounded nested perspective required")


@dataclass(frozen=True)
class CognitiveScope:
    scope_id: str
    frame_id: str
    perspective_id: str
    at_point: str

    def __post_init__(self):
        for value in (self.scope_id, self.frame_id, self.perspective_id, self.at_point):
            identifier(value)


@dataclass(frozen=True)
class Bridge:
    bridge_id: str
    source_scope: str
    target_scope: str
    viewpoint_map: tuple[str, str]
    entity_mapping: tuple[tuple[str, str], ...]
    temporal_mapping: tuple[tuple[str, str], ...]
    required_assumptions: frozenset[str]
    evidence_roots: frozenset[str]

    def __post_init__(self):
        for name in ("viewpoint_map", "entity_mapping", "temporal_mapping"):
            value = getattr(self, name)
            object.__setattr__(
                self, name, tuple(tuple(pair) for pair in value) if name != "viewpoint_map" else tuple(value)
            )
        object.__setattr__(self, "required_assumptions", frozenset(self.required_assumptions))
        object.__setattr__(self, "evidence_roots", frozenset(self.evidence_roots))
        for value in (
            self.bridge_id,
            self.source_scope,
            self.target_scope,
            *self.viewpoint_map,
            *self.required_assumptions,
            *self.evidence_roots,
        ):
            identifier(value)
        if (
            len(self.viewpoint_map) != 2
            or self.source_scope == self.target_scope
            or not self.required_assumptions
            or not self.evidence_roots
            or len(self.entity_mapping) > 64
            or len(self.temporal_mapping) > 64
        ):
            raise ValueError("explicit conditional evidenced bridge required")
        for pair in (*self.entity_mapping, *self.temporal_mapping):
            if len(pair) != 2:
                raise ValueError("pairwise bridge mapping required")
            identifier(pair[0])
            identifier(pair[1])
        if len({left for left, _ in self.entity_mapping}) != len(self.entity_mapping):
            raise ValueError("bridge cannot silently choose conflicting entity targets")


@dataclass(frozen=True)
class BridgeResult:
    status: str
    supports: tuple
    obligations: tuple[str, ...]


def evaluate_bridge(
    bridge,
    premise_support,
    *,
    source_scope,
    target_scope,
    source_perspective,
    target_perspective,
    identity_graph,
    temporal_network,
    records_by_root,
    active_assumptions,
    live_roots,
    max_environments=64,
    nonmaterial_roots=frozenset(),
):
    """Discharge actual mapping/access obligations before conditional projection.

    The caller has already applied system ACL to every root and record. Receipt
    only licenses an information-access projection; it does not compute belief,
    understanding, or the truth of an embedded/private proposition.
    """
    from hcl.kernel.truth import Support
    from hcl.kernel.temporal import record_eligibility

    if (
        type(bridge) is not Bridge
        or type(premise_support) is not Support
        or type(source_scope) is not CognitiveScope
        or type(target_scope) is not CognitiveScope
        or type(source_perspective) is not Perspective
        or type(target_perspective) is not Perspective
        or type(max_environments) is not int
        or not 1 <= max_environments <= 1024
    ):
        raise ValueError("typed bounded bridge evaluation required")
    if (
        bridge.source_scope != source_scope.scope_id
        or bridge.target_scope != target_scope.scope_id
        or source_scope.perspective_id != source_perspective.perspective_id
        or target_scope.perspective_id != target_perspective.perspective_id
        or bridge.viewpoint_map != (source_perspective.perspective_id, target_perspective.perspective_id)
        or source_scope.at_point != source_perspective.at_point
        or target_scope.at_point != target_perspective.at_point
    ):
        raise ValueError("bridge scope/viewpoint identities do not match")
    active_assumptions, live_roots = frozenset(active_assumptions), frozenset(live_roots)
    required = premise_support.assumptions | bridge.required_assumptions
    roots = premise_support.roots | bridge.evidence_roots
    if not required <= active_assumptions or not roots <= live_roots:
        return BridgeResult("WITHDRAWN_OBLIGATION", (), ("ASSUMPTION_OR_EVIDENCE_NOT_LIVE",))
    issues, alternatives = set(), []
    for left, right in bridge.entity_mapping:
        paths = identity_graph.paths(left, right)
        if paths.frontier_unexplored:
            issues.add("IDENTITY_FRONTIER_UNEXPLORED")
        if not paths.supports:
            issues.add("IDENTITY_ALIGNMENT_UNRESOLVED")
        alternatives.append(paths.supports)
    constraints = {edge.constraint_id: edge for edge in temporal_network.constraints}
    for left, right in bridge.temporal_mapping:
        checked = temporal_network.check(left, right)
        if checked["status"] != "ENTAILED":
            issues.add("TEMPORAL_MAPPING_" + checked["status"])
        else:
            if not temporal_network.verify_witness(left, right, checked["witness"]):
                raise ValueError("temporal bridge witness did not verify")
            for identity in checked["witness"]:
                required |= constraints[identity].assumptions
                roots |= frozenset(constraints[identity].evidence_roots)
    if (
        source_scope.at_point != target_scope.at_point
        and (source_scope.at_point, target_scope.at_point) not in bridge.temporal_mapping
    ):
        issues.add("MISSING_TIME_MAPPING")
    if source_perspective.nested_path != target_perspective.nested_path:
        issues.add("NESTED_VIEWPOINT_PROJECTION_UNRESOLVED")
    if target_perspective.agent_id is not None:
        # Access may be recorded under a different source-local identity. A
        # same-as proof transports that agent reference; equal names never do.
        # Internal program lineage remains in support/ACL dependencies, but is
        # not a narrative report with an expressible receipt. Pure metadata is
        # insufficient to project an unsupported default to a character.
        material = premise_support.roots - frozenset(nonmaterial_roots)
        if not material:
            issues.add("NO_MATERIAL_SOURCE_EVIDENCE")
        for root in material:
            record = records_by_root.get(root)
            options = []
            access_failures = set()
            if record is not None:
                for local_agent in sorted(record.agent_access_end):
                    if local_agent == target_perspective.agent_id:
                        identities = (Support(frozenset(), frozenset()),)
                    elif (
                        local_agent in identity_graph.entities
                        and target_perspective.agent_id in identity_graph.entities
                    ):
                        paths = identity_graph.paths(local_agent, target_perspective.agent_id)
                        identities = paths.supports
                        if paths.frontier_unexplored:
                            issues.add("ACCESS_IDENTITY_FRONTIER_UNEXPLORED")
                    else:
                        identities = ()
                    if not identities:
                        continue
                    eligibility = record_eligibility(
                        record, temporal_network, at_point=target_scope.at_point, agent_id=local_agent
                    )
                    if eligibility["status"] != "ELIGIBLE":
                        access_failures.add("AGENT_ACCESS_" + eligibility["status"])
                        continue
                    proof_assumptions = frozenset()
                    proof_roots = frozenset()
                    for obligation in eligibility["obligations"]:
                        for identity in obligation["witness"]:
                            proof_assumptions |= constraints[identity].assumptions
                            proof_roots |= frozenset(constraints[identity].evidence_roots)
                    for path in identities:
                        options.append(
                            Support(proof_assumptions | path.assumptions, proof_roots | path.roots)
                        )
            if not options:
                issues.update(access_failures)
                issues.add("AGENT_ACCESS_NOT_ESTABLISHED")
            alternatives.append(tuple(options))
    if not required <= active_assumptions or not roots <= live_roots:
        issues.add("MAPPING_PROOF_NOT_LIVE")
    if any("FRONTIER_UNEXPLORED" not in issue for issue in issues):
        return BridgeResult("UNRESOLVED", (), tuple(sorted(issues)))
    supports = []
    combinations = product(*alternatives) if alternatives else ((),)
    for number, combination in enumerate(combinations):
        if number >= max_environments * 16:
            return BridgeResult(
                "FRONTIER_UNEXPLORED", tuple(supports), ("BRIDGE_COMBINATION_WORK_UNEXPLORED",)
            )
        assumptions = required | frozenset().union(*(item.assumptions for item in combination))
        evidence = roots | frozenset().union(*(item.roots for item in combination))
        if not assumptions <= active_assumptions or not evidence <= live_roots:
            continue
        if any(nogood <= assumptions for nogood in identity_graph.nogoods):
            continue
        supports.append(Support(assumptions, evidence))
        if len(supports) >= max_environments:
            # The exact limit does not prove an extra branch exists; conservatively
            # expose an unexpanded frontier rather than overstate completeness.
            return BridgeResult("FRONTIER_UNEXPLORED", tuple(supports), ("BRIDGE_ENVIRONMENTS_UNEXPLORED",))
    return BridgeResult(
        (
            ("FRONTIER_UNEXPLORED" if issues else "CONDITIONAL_INFORMATION_PROJECTION")
            if supports
            else "UNRESOLVED"
        ),
        tuple(supports),
        tuple(sorted(issues)) if supports else ("NO_COMPATIBLE_MAPPING_ENVIRONMENT",),
    )

"""Actual rooted revision over authorized, source-bound finite candidate IR."""

from dataclasses import asdict, replace
from hashlib import sha256

from hcl.kernel.dependencies import QueryDelta
from hcl.kernel.identity import IdentityGraph, IdentityHypothesis, SourceLocalEntity
from hcl.kernel.scope import Bridge, CognitiveScope, Perspective, evaluate_bridge
from hcl.kernel.temporal import (
    TemporalConstraint,
    TemporalForest,
    TemporalRecord,
    TimePoint,
    record_eligibility,
)
from hcl.kernel.truth import (
    EvidenceRoot,
    DerivationRule,
    Support,
    TruthKernel,
    TruthProfile,
    TruthProgram,
    TruthState,
)
from hcl.kernel.types import HCLFailure, InferenceResult, OpResult, RULE_VERSION, thaw
from hcl.memory.codec import canonical
from hcl.semantics.revision import KINDS, LIMITS, PROGRAM_SCHEMA, programs_from_view, qualified

VERSION = "s2.2-rooted-temporal-revision-1"
RESULT_KIND = "CONDITIONAL_REVISION"


def program_wire(program):
    return {
        "claims": list(program.claims),
        "roots": [
            {
                "root_id": r.root_id,
                "claim_id": r.claim_id,
                "assumptions": sorted(r.assumptions),
                "active": r.active,
                "provenance_roots": sorted(r.provenance_roots),
            }
            for r in program.roots
        ],
        "rules": [
            {
                "rule_id": r.rule_id,
                "premises": list(r.premises),
                "conclusion": r.conclusion,
                "assumptions": sorted(r.assumptions),
                "enabled": r.enabled,
            }
            for r in program.rules
        ],
        "active_assumptions": sorted(program.active_assumptions),
        "nogoods": [sorted(value) for value in program.nogoods],
    }


def state_wire(state):
    return {
        "supports": {
            key: [{"assumptions": sorted(item.assumptions), "roots": sorted(item.roots)} for item in values]
            for key, values in state.supports.items()
        },
        "frontier": sorted(state.frontier),
        "work": state.work,
        "recomputed_claims": sorted(state.recomputed_claims),
        "profile": asdict(state.profile),
    }


def restore(program, state):
    p = TruthProgram(
        tuple(program["claims"]),
        tuple(EvidenceRoot(**dict(row)) for row in program["roots"]),
        tuple(DerivationRule(**dict(row)) for row in program["rules"]),
        frozenset(program["active_assumptions"]),
        tuple(program["nogoods"]),
    )
    s = TruthState(
        {
            key: tuple(Support(frozenset(item["assumptions"]), frozenset(item["roots"])) for item in values)
            for key, values in state["supports"].items()
        },
        frozenset(state["frontier"]),
        state["work"],
        frozenset(state["recomputed_claims"]),
        TruthProfile(**dict(state["profile"])),
    )
    return p, s


def reachable(rules, start):
    adjacency = {}
    for premises, conclusion in rules:
        for premise in premises:
            adjacency.setdefault(premise, set()).add(conclusion)
    reached = {start}
    queue = [start]
    while queue:
        for value in adjacency.get(queue.pop(), ()):
            if value not in reached:
                reached.add(value)
                queue.append(value)
    return reached


class RevisionOperator:
    def run(self, snapshot, issue, allowance, query, previous=None):
        try:
            return self._run(snapshot, issue, allowance, query, previous)
        except (ValueError, TypeError, KeyError, IndexError, RecursionError):
            raise HCLFailure(
                "INVALID_REQUEST",
                "revision",
                "INVALID_SCOPED_REVISION_PROGRAM",
                "program",
                "The scoped revision program is inconsistent or outside its bounded contract.",
            ) from None

    def _run(self, snapshot, issue, allowance, query, previous):
        view = snapshot.query_views["0"]
        programs = programs_from_view(view)
        if len(programs) > 16 or allowance.max_local_evaluations < 1:
            raise HCLFailure(
                "BUDGET_EXHAUSTED",
                "revision",
                "REVISION_EXECUTION_BOUND",
                "budget",
                "The bounded revision execution has no remaining allowance.",
            )
        registry = {kind: {} for kind in KINDS}
        owners = {}
        meta = {}
        program_hashes = {}
        issues = set()
        for program in programs:
            if program["schema"] != PROGRAM_SCHEMA:
                raise ValueError("program version")
            source = program["source_id"]
            version = program["source_version"]
            program_hashes[source] = sha256(canonical(thaw(program)).encode()).hexdigest()
            meta[source] = (
                "program:"
                + qualified(source, "__presence__")
                + "@"
                + str(version)
                + ":"
                + program_hashes[source]
            )
            for kind in KINDS:
                for row in program[kind]:
                    if row["id"] in owners:
                        raise ValueError("duplicate program identity")
                    owners[row["id"]] = (source, version)
                    registry[kind][row["id"]] = row
        if any(len(registry[kind]) > limit for kind, limit in LIMITS.items()):
            raise HCLFailure(
                "BUDGET_EXHAUSTED",
                "revision",
                "REVISION_PROGRAM_BOUND",
                "program",
                "The combined revision program exceeds its bounded profile.",
            )
        claims = registry["claims"]
        positive, negative = query["positive"], query["negative"]
        if positive not in claims or negative not in claims:
            raise ValueError("missing query claim")
        a, b = claims[positive], claims[negative]
        if (a["predicate"], a["arguments"], a["scope"], a["negated"]) != (
            b["predicate"],
            b["arguments"],
            b["scope"],
            False,
        ) or b["negated"] is not True:
            raise ValueError("query must name opposite polarities of one scoped atom")
        active = frozenset(registry["assumptions"]) | frozenset(registry["identities"])
        nogoods = tuple(frozenset(row) for program in programs for row in program["nogoods"])
        for frame in registry["frames"].values():
            seen = set()
            current = frame["id"]
            while current is not None:
                if current in seen or current not in registry["frames"]:
                    raise ValueError("frame cycle or missing frame")
                seen.add(current)
                current = registry["frames"][current]["parent"]
        perspectives = {
            key: Perspective(
                key,
                row["agent"],
                tuple(row["nested"]),
                row["at"],
                row["observation_model"],
                row["belief_model"],
                (meta[owners[key][0]],),
            )
            for key, row in registry["perspectives"].items()
        }
        scopes = {
            key: CognitiveScope(key, row["frame"], row["perspective"], row["at"])
            for key, row in registry["scopes"].items()
        }
        for key, row in scopes.items():
            if (
                row.frame_id not in registry["frames"]
                or row.perspective_id not in perspectives
                or perspectives[row.perspective_id].at_point != row.at_point
            ):
                raise ValueError("scope/perspective mismatch")
        points = {
            key: TimePoint(key, row["axis"], row["scope"], row["agent"])
            for key, row in registry["points"].items()
        }
        for claim in claims.values():
            if claim["scope"] not in scopes or any(
                entity not in registry["entities"] for entity in claim["arguments"]
            ):
                raise ValueError("claim scope/entity")
        source_times = {row["source_id"]: row["recorded_at"] for row in view["source_history"]}
        root_ids = {
            key: key + "@" + str(owners[key][1]) + ":" + program_hashes[owners[key][0]]
            for key in registry["roots"]
        }
        all_claims = set(claims) | set(meta.values()) | {"report:" + key for key in root_ids.values()}
        base_roots = [EvidenceRoot(value, value) for value in meta.values()]
        records = {}
        raw_assumptions = {}
        for key, row in registry["roots"].items():
            root = root_ids[key]
            raw_assumptions[root] = frozenset(row["assumptions"])
            base_roots.append(EvidenceRoot(root, "report:" + root, frozenset(row["assumptions"])))
            records[root] = TemporalRecord(
                key, owners[key][1], source_times[owners[key][0]], row["event_end"], dict(row["access"]), {}
            )
        live_roots = {
            root.root_id
            for root in base_roots
            if root.assumptions <= active and not any(n <= root.assumptions for n in nogoods)
        }

        def evidence(row):
            if not set(row["evidence_roots"]) <= set(root_ids):
                return None
            return frozenset(root_ids[key] for key in row["evidence_roots"])

        def root_environment(roots):
            return frozenset().union(*(raw_assumptions.get(root, frozenset()) for root in roots))

        verified = {}
        constraints = []
        for key, row in registry["clock_bridges"].items():
            roots = evidence(row)
            environment = frozenset(row["assumptions"]) | root_environment(roots or ())
            if (
                roots is not None
                and roots <= live_roots
                and environment <= active
                and not any(n <= environment for n in nogoods)
            ):
                verified[key] = row
            else:
                issues.add("CLOCK_BRIDGE_OBLIGATION_UNRESOLVED")
        for key, row in registry["constraints"].items():
            roots = evidence(row)
            if roots is None or row["left"] not in points or row["right"] not in points:
                issues.add("TEMPORAL_REFERENCE_WITHDRAWN")
                continue
            assumptions = frozenset(row["assumptions"])
            if row["clock_bridge"] is not None:
                bridge = verified.get(row["clock_bridge"])
                if bridge is None:
                    issues.add("CLOCK_BRIDGE_OBLIGATION_UNRESOLVED")
                    continue
                left, right = points[row["left"]], points[row["right"]]
                if (left.axis, right.axis, left.scope_id, right.scope_id) != (
                    bridge["left_axis"],
                    bridge["right_axis"],
                    bridge["source_scope"],
                    bridge["target_scope"],
                ):
                    raise ValueError("temporal bridge axes/scopes mismatch")
                assumptions |= frozenset(bridge["assumptions"])
                roots |= evidence(bridge)
            if not roots <= live_roots:
                issues.add("TEMPORAL_EVIDENCE_WITHDRAWN")
                continue
            assumptions |= root_environment(roots)
            constraints.append(
                TemporalConstraint(
                    key,
                    row["left"],
                    row["right"],
                    row["numerator"],
                    row["denominator"],
                    row["strict"],
                    assumptions,
                    tuple(sorted(roots)),
                    row["clock_bridge"],
                )
            )
        temporal = TemporalForest(
            tuple(points.values()),
            tuple(constraints),
            active_assumptions=active,
            verified_bridges=frozenset(verified),
            nogoods=nogoods,
        )
        by_constraint = {row.constraint_id: row for row in constraints}
        facts = []
        root_status = {}
        root_frontier = set()
        for key, row in registry["roots"].items():
            claim = claims[row["claim"]]
            scope = scopes[claim["scope"]]
            perspective = perspectives[scope.perspective_id]
            root = root_ids[key]
            eligibility = record_eligibility(
                records[root], temporal, at_point=scope.at_point, agent_id=perspective.agent_id
            )
            root_status[key] = eligibility
            if eligibility["status"] != "ELIGIBLE":
                if eligibility["status"] == "UNRESOLVED":
                    issues.add("ROOT_TEMPORAL_UNRESOLVED")
                    root_frontier.add(row["claim"])
                continue
            assumptions = frozenset(row["assumptions"])
            proof = frozenset({root})
            for obligation in eligibility["obligations"]:
                for identity in obligation["witness"]:
                    assumptions |= by_constraint[identity].assumptions
                    proof |= frozenset(by_constraint[identity].evidence_roots)
            assumptions |= root_environment(proof)
            if any(nogood <= assumptions for nogood in nogoods):
                issues.add("ROOT_ENVIRONMENT_CONFLICT")
                root_frontier.add(row["claim"])
                root_status[key] = dict(
                    eligibility, status="UNRESOLVED", environment_status="ROOT_ENVIRONMENT_CONFLICT"
                )
                continue
            facts.append(EvidenceRoot("fact:" + root, row["claim"], assumptions, True, proof))
        entities = tuple(
            SourceLocalEntity(key, owners[key][0], owners[key][1], row["label"], tuple(row["segment_ids"]))
            for key, row in registry["entities"].items()
        )
        identities = []
        for key, row in registry["identities"].items():
            roots = evidence(row)
            if (
                roots is None
                or row["left"] not in registry["entities"]
                or row["right"] not in registry["entities"]
            ):
                issues.add("IDENTITY_OBLIGATION_WITHDRAWN")
                continue
            identities.append(
                IdentityHypothesis(
                    key,
                    row["left"],
                    row["right"],
                    roots,
                    frozenset(row["assumptions"]) | root_environment(roots),
                    roots <= live_roots,
                )
            )
        identity_graph = IdentityGraph(entities, identities, active_assumptions=active, nogoods=nogoods)
        rules = []
        for key, row in registry["rules"].items():
            if row["conclusion"] not in claims or not set(row["premises"]) <= set(claims):
                issues.add("RULE_REFERENCE_WITHDRAWN")
                continue
            scope = claims[row["conclusion"]]["scope"]
            if any(claims[premise]["scope"] != scope for premise in row["premises"]):
                raise ValueError("cross-scope rule requires a Bridge")
            rules.append(
                DerivationRule(
                    key,
                    tuple(row["premises"]) + (meta[owners[key][0]],),
                    row["conclusion"],
                    frozenset(row["assumptions"]),
                )
            )
        total_work = 0
        runs = 0
        frontier = set(root_frontier)
        proofs = []
        extra_roots = {}
        last_program = None
        profile = TruthProfile(
            max_claims=2048,
            max_roots=4096,
            max_rules=4096,
            max_assumptions=1024,
            max_supports_per_claim=64,
            max_work=min(100000, max(1, allowance.max_local_evaluations * 3000)),
        )

        def make_program():
            return TruthProgram(
                tuple(sorted(all_claims)),
                tuple(base_roots + facts + list(extra_roots.values())),
                tuple(rules),
                active,
                nogoods,
            )

        flow = [(rule.premises, rule.conclusion) for rule in rules]
        flow += [((row["source_claim"],), row["target_claim"]) for row in registry["bridges"].values()]

        def mark_uncertainty(state):
            dirty = set().union(*(reachable(flow, key) for key in frontier)) if frontier else set()
            return replace(state, frontier=state.frontier | frozenset(dirty & set(state.supports)))

        def calculate():
            nonlocal runs, total_work, last_program
            if runs >= allowance.max_local_evaluations or total_work >= profile.max_work:
                return None
            kernel = TruthKernel(replace(profile, max_work=max(1, profile.max_work - total_work)))
            last_program = make_program()
            state = kernel.run(last_program)
            runs += 1
            total_work += state.work
            return mark_uncertainty(state)

        state = calculate()

        # Bridges execute proof obligations on actual rooted source supports.
        # Iteration permits finite chains, never rootless mutual projection.
        def resolve_bridges(state):
            while True:
                added = False
                for key, row in registry["bridges"].items():
                    if row["source_claim"] not in claims or row["target_claim"] not in claims:
                        issues.add("BRIDGE_REFERENCE_WITHDRAWN")
                        continue
                    source, target = claims[row["source_claim"]], claims[row["target_claim"]]
                    expected_pairs = set(zip(source["arguments"], target["arguments"]))
                    if (
                        source["predicate"] != target["predicate"]
                        or source["negated"] != target["negated"]
                        or len(source["arguments"]) != len(target["arguments"])
                        or set(tuple(pair) for pair in row["entity_mapping"]) != expected_pairs
                    ):
                        raise ValueError("bridge must preserve predicate/polarity and map every entity")
                    roots = evidence(row)
                    if roots is None:
                        issues.add("BRIDGE_EVIDENCE_WITHDRAWN")
                        continue
                    source_scope, target_scope = scopes[source["scope"]], scopes[target["scope"]]
                    bridge = Bridge(
                        key,
                        source_scope.scope_id,
                        target_scope.scope_id,
                        (source_scope.perspective_id, target_scope.perspective_id),
                        tuple(row["entity_mapping"]),
                        tuple(row["temporal_mapping"]),
                        frozenset(row["assumptions"]) | root_environment(roots),
                        roots,
                    )
                    for support in state.supports[row["source_claim"]]:
                        result = evaluate_bridge(
                            bridge,
                            support,
                            source_scope=source_scope,
                            target_scope=target_scope,
                            source_perspective=perspectives[source_scope.perspective_id],
                            target_perspective=perspectives[target_scope.perspective_id],
                            identity_graph=identity_graph,
                            temporal_network=temporal,
                            records_by_root=records,
                            active_assumptions=active,
                            live_roots=live_roots,
                            nonmaterial_roots=frozenset(meta.values()),
                        )
                        proofs.append(
                            {
                                "bridge_id": key,
                                "status": result.status,
                                "obligations": list(result.obligations),
                            }
                        )
                        if result.status != "CONDITIONAL_INFORMATION_PROJECTION":
                            issues.update(result.obligations)
                            frontier.add(row["target_claim"])
                        for derived in result.supports:
                            identity = (
                                "bridge:"
                                + sha256(
                                    canonical(
                                        [key, sorted(derived.assumptions), sorted(derived.roots)]
                                    ).encode()
                                ).hexdigest()
                            )
                            if identity not in extra_roots:
                                if len(base_roots) + len(facts) + len(extra_roots) >= profile.max_roots:
                                    issues.add("BRIDGE_ROOT_BOUND_UNEXPLORED")
                                    frontier.add(row["target_claim"])
                                    continue
                                extra_roots[identity] = EvidenceRoot(
                                    identity, row["target_claim"], derived.assumptions, True, derived.roots
                                )
                                added = True
                if not added:
                    break
                next_state = calculate()
                if next_state is None:
                    issues.add("REVISION_WORK_UNEXPLORED")
                    frontier.update(claims)
                    break
                state = next_state
            return mark_uncertainty(state)

        state = resolve_bridges(state)
        # Negative defaults watch actual supported candidate records, not just
        # whether a string/row exists. Cyclic negative dependencies stay unresolved.
        defaults = registry["defaults"]
        watch = {}
        watch_receipts = {}
        for key, row in defaults.items():
            matching = [
                (dependency, snapshot.query_views[str(number)])
                for number, dependency in enumerate(snapshot.query_dependencies)
                if dict(dependency.query.filters) == dict(row["query"])
                and dependency.query.history
                and dependency.query.known_at == getattr(issue, "known_at", None)
                and not dependency.query.source_only
            ]
            if not matching:
                raise ValueError("missing actual absence query dependency")
            dependency, projection = matching[0]
            watch_receipts[key] = {
                "query_dependency": dependency.wire(),
                "pending": thaw(projection["pending"]),
                "scope": "CONDITIONAL_SUPPORTED_RECORD_ABSENCE_NOT_WORLD_ABSENCE",
            }
            watch[key] = {
                claim_id
                for claim_id, claim in claims.items()
                if claim["index"] is not None
                and all(claim["index"].get(field) == value for field, value in row["query"].items())
            }
        depends = {
            key: {other for other, rule in defaults.items() if reachable(flow, rule["claim"]) & watch[key]}
            for key in defaults
        }
        waiting = set(defaults)
        default_status = {}
        while waiting:
            ready = sorted(key for key in waiting if not depends[key] & waiting)
            if not ready:
                for key in waiting:
                    default_status[key] = "NONSTRATIFIED_DEFAULT_UNRESOLVED"
                    frontier.add(defaults[key]["claim"])
                issues.add("NONSTRATIFIED_DEFAULT_UNRESOLVED")
                break
            for key in ready:
                waiting.remove(key)
                row = defaults[key]
                if view["pending"] or watch_receipts[key]["pending"] or watch[key] & state.frontier:
                    default_status[key] = "COVERAGE_OR_SEARCH_UNRESOLVED"
                    issues.add(default_status[key])
                    frontier.add(row["claim"])
                    continue
                matching_supports = [support for claim in watch[key] for support in state.supports[claim]]
                if matching_supports:
                    if any(
                        nogood <= (support.assumptions | frozenset(row["assumptions"]))
                        for support in matching_supports
                        for nogood in nogoods
                    ):
                        # A receipt in an incompatible environment cannot settle
                        # every default branch. Full branch enumeration is not
                        # implemented; preserve the explicit unresolved frontier.
                        default_status[key] = "DEFAULT_ENVIRONMENT_BRANCHING_UNEXPLORED"
                        issues.add(default_status[key])
                        frontier.add(row["claim"])
                    else:
                        default_status[key] = "REBUTTED_BY_SUPPORTED_RECORD"
                    continue
                if len(base_roots) + len(facts) + len(extra_roots) >= profile.max_roots:
                    default_status[key] = "DEFAULT_ROOT_BOUND_UNEXPLORED"
                    issues.add(default_status[key])
                    frontier.add(row["claim"])
                    continue
                if any(nogood <= frozenset(row["assumptions"]) for nogood in nogoods):
                    default_status[key] = "DEFAULT_ENVIRONMENT_CONFLICT"
                    issues.add(default_status[key])
                    frontier.add(row["claim"])
                    continue
                default_status[key] = "CONDITIONAL_INDEXED_ABSENCE"
                absence = "absence:" + key
                active = active | {absence}
                proof = frozenset({meta[owners[key][0]]})
                extra_roots[absence] = EvidenceRoot(
                    absence, row["claim"], frozenset(row["assumptions"]) | {absence}, True, proof
                )
                next_state = calculate()
                if next_state is None:
                    default_status[key] = "DEFAULT_WORK_UNEXPLORED"
                    issues.add("REVISION_WORK_UNEXPLORED")
                    frontier.add(row["claim"])
                    state = mark_uncertainty(state)
                    continue
                state = resolve_bridges(next_state)
        final_program = last_program
        # A pending unexecuted proposal cannot masquerade as a completed kernel
        # state. Keep the last computed graph and expose the unexpanded frontier.
        state = mark_uncertainty(state)
        changed = tuple(sorted(claims))
        retained = ()
        recomputed = tuple(sorted(state.recomputed_claims & set(claims)))
        if (
            previous is not None
            and not frontier
            and total_work < profile.max_work
            and runs < allowance.max_local_evaluations
        ):
            previous_program, previous_state = restore(
                previous.values["kernel_program"], previous.values["kernel_state"]
            )
            kernel = TruthKernel(replace(profile, max_work=max(1, profile.max_work - total_work)))
            revision = kernel.revise(previous_program, previous_state, final_program)
            runs += 1
            total_work += revision.state.work
            state = revision.state
            changed = tuple(
                key
                for key in revision.changed_claims
                if key in claims or key in previous.values["claim_metadata"]
            )
            retained = tuple(key for key in revision.retained_claims if key in claims)
            recomputed = tuple(sorted(state.recomputed_claims & set(claims)))
        bits = state.support_bits(positive, negative)
        metadata = {
            key: {
                "predicate": row["predicate"],
                "arguments": [registry["entities"][value]["label"] for value in row["arguments"]],
                "negated": row["negated"],
                "scope_id": row["scope"],
                "frame_kind": registry["frames"][scopes[row["scope"]].frame_id]["kind"],
                "perspective_id": scopes[row["scope"]].perspective_id,
                "agent_id": perspectives[scopes[row["scope"]].perspective_id].agent_id,
                "at_point": scopes[row["scope"]].at_point,
            }
            for key, row in claims.items()
        }
        semantic_hashes = {
            key: sha256(
                canonical(
                    [
                        state.semantic_hash(key),
                        thaw(claims[key]),
                        asdict(scopes[claims[key]["scope"]]),
                        asdict(perspectives[scopes[claims[key]["scope"]].perspective_id]),
                    ]
                ).encode()
            ).hexdigest()
            for key in claims
        }
        if previous is not None:
            old_hashes = previous.values["semantic_hashes"]
            changed = tuple(
                sorted(
                    key
                    for key in set(old_hashes) | set(semantic_hashes)
                    if old_hashes.get(key) != semantic_hashes.get(key)
                )
            )
            retained = tuple(sorted(set(semantic_hashes) - set(changed)))
        values = {
            "operator_version": VERSION,
            "principal": {"tenant": snapshot.principal.tenant_id, "subject": snapshot.principal.subject_id},
            "query": dict(query),
            "known_at": getattr(issue, "known_at", None),
            "source_bindings": thaw(view["source_history"]),
            "support_bits": bits,
            "claim_metadata": metadata,
            "changed_claims": changed,
            "retained_claims": retained,
            "recomputed_claims": recomputed,
            "semantic_hashes": semantic_hashes,
            "root_temporal_results": root_status,
            "bridge_proofs": proofs,
            "default_results": default_status,
            "absence_watches": watch_receipts,
            "kernel_program": program_wire(final_program),
            "kernel_state": state_wire(state),
            "semantic_certified": False,
            "candidate_completeness": "NOT_ESTABLISHED",
            "coverage_pending": thaw(view["pending"]),
        }
        digest = sha256(
            canonical([VERSION, snapshot.session_id, snapshot.revision, issue.issue_id, values]).encode()
        ).hexdigest()
        result = InferenceResult(
            "revision-result:" + digest,
            RESULT_KIND,
            values,
            tuple(
                canonical(sorted(env)) for claim in (positive, negative) for env in state.environments(claim)
            ),
            tuple(
                sorted(
                    root
                    for claim in (positive, negative)
                    for support in state.supports[claim]
                    for root in support.roots
                )
            ),
            (negative,) if bits["negative_support"] else (),
            RULE_VERSION,
            "CONDITIONAL_REVISION_NOT_WORLD_OR_PRIVATE_TRUTH",
        )
        delta = QueryDelta(
            snapshot.session_id,
            snapshot.principal,
            snapshot.revision,
            snapshot.access_epoch,
            RULE_VERSION,
            {},
            (result,),
            snapshot.query_dependencies,
        )
        return OpResult(
            "revision:" + digest,
            VERSION,
            {},
            (),
            (result.result_id,),
            tuple(sorted(issues)),
            {
                "local_evaluations": runs,
                "truth_work": total_work,
                "temporal_relaxations": temporal.work,
                "identity_path_work": identity_graph.total_work,
            },
            (),
            delta,
        )

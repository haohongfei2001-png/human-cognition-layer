"""Bounded same-host concept adoption over an immutable v2 judgment proof.

This is an explicit new envelope, never a rewritten v2 candidate. Source/ACL and
registry authorization belong to the caller. The pure verifier replays every
inherited certificate; certificate validity alone grants no authority to read,
adopt, commit, or deliver anything.
"""
from copy import deepcopy
from dataclasses import replace
from types import SimpleNamespace

from hcl.kernel.execution import ExecutionBudget, PROTOCOL
from hcl.kernel.types import Delta, HCLFailure, InferenceResult, Issue, OpResult, Principal, thaw
from hcl.memory import codec
from hcl.operators.concept_induction import validate_term
from hcl.operators.concept_judgment import (
    KIND as BASE_KIND, VERSION as BASE_VERSION, classification_semantics,
    decision_projection, decision_semantics, verify_concept_judgment,
)
from hcl.operators.concept_versions import compute_versions
from hcl.operators.judgment import JudgmentWork
from hcl.operators.judgment_model import JudgmentModelOperator
from hcl.semantics.concept_version_compiler import digest, host_context, semantic_definition
from hcl.semantics.judgment_concept_compiler import (
    concept_judgment_qualifications, verify_concept_program,
)

SCHEMA = "hcl-persistent-concept-judgment-1"
VERSION = "s4-persistent-concept-judgment-1"
KIND = "CONDITIONAL_PERSISTENT_CONCEPT_JUDGMENT"
COVERAGE = "CONDITIONAL_SAME_HOST_PERSISTED_CONCEPT_JUDGMENT"
SELECTION_FIELDS = {"choice_id", "stream_id", "adoption_id", "definition_version", "proof", "version_label"}
MAX_WORK = 10000000


def _canonical(value):
    return codec.canonical(thaw(value))


def _snapshot(host, sources, rule):
    return SimpleNamespace(session_id=host["session_id"], principal=Principal(**host["principal"]),
        revision=0, access_epoch=0, rule_version=rule, source_versions=sources)


def _bound(limit):
    if type(limit) is not int or not 0 <= limit <= MAX_WORK:
        raise ValueError("bounded persistent certificate required")
    return replace(ExecutionBudget(), max_local_evaluations=limit)


def _needs(reason):
    raise HCLFailure("NEEDS_RECOMPILE", "persistent_concept", "PERSISTENT_CONCEPT_NEEDS_RECOMPILE", reason,
        "The adopted concept cannot safely replace this judgment's bound reading; recompile the affected model.")


def _decode_proof(encoded):
    result = codec.decode(thaw(encoded))
    if type(result) is not InferenceResult or result.kind != BASE_KIND:
        raise ValueError("an original v2 concept judgment proof is required")
    return result


def _local_environments(result, data):
    environments = set()
    local = data.get("local_model")
    if local is not None:
        assumptions, residuals = concept_judgment_qualifications(data["program"])
        expected = dict(model_id="judgment-proposal:" + data["program"]["candidate_identity"],
            version=PROTOCOL, dialect="judgment-model-2", domain_assumptions=list(assumptions),
            fit_residuals=[], unmodeled_observations=list(residuals))
        if local != expected:
            raise ValueError("original local-model qualifications changed")
        environments.update("local-model:" + local["model_id"] + ":assumption:" + str(i)
                            for i in range(len(local["domain_assumptions"])))
    elif not (type(result.result_id) is str and result.result_id.startswith("concept-judgment:")
              and len(result.result_id) == len("concept-judgment:") + 64):
        raise ValueError("original concept result identity changed")
    return environments


def verify_concept_inference(result, *, replay=True):
    """Check all v2 metadata; optional full pure replay, never source authority.

    local_model commit IDs additionally bind historical access epochs/query
    tokens, unavailable inside the v2 certificate. Those IDs must be matched to
    the original accepted store object by the caller, as with shipped v2.
    """
    if type(result) is not InferenceResult or result.kind != BASE_KIND:
        raise ValueError("original concept inference required")
    data = thaw(result.values)
    if data["operator_version"] != BASE_VERSION:
        raise ValueError("unsupported original concept operator")
    _bound(data["execution_allowance"])
    environments = _local_environments(result, data)
    if replay:
        operation = verify_concept_judgment(data)
        expected = operation.candidate_delta.new_inferences[0]
        if "local_model" not in data and result.result_id != expected.result_id:
            raise ValueError("original concept result identity changed")
        environments.update(expected.assumption_environments)
        local = data.get("local_model")
        local_conditions = () if local is None else tuple(
            "local-model:" + local["model_id"] + ":assumption:" + str(i)
            for i in range(len(local["domain_assumptions"])))
        if tuple(result.assumption_environments) != (*expected.assumption_environments, *local_conditions):
            raise ValueError("original concept condition order or multiplicity changed")
    else:
        snapshot = _snapshot(data["program"]["host_context"], data["source_versions"], data["rule_version"])
        verify_concept_program(data["program"], snapshot, _bound(data["execution_allowance"]))
        environments.update(data["concepts"]["assumption_environments"])
        for branch in data["branches"]:
            for model in branch["actual_judgment"]["models"]:
                for record in (model["cognition"]["actual"], model["actual_interaction"], model["actual_argument"]):
                    if record is not None:
                        environments.update(record["assumption_environments"])
                for decision in model["decisions"]:
                    for framework in decision["frameworks"]:
                        environments.update(framework["active_assumptions"])
        operation = None
    if (set(result.assumption_environments) != environments
            or len(result.assumption_environments) != len(environments)
            or tuple(result.premise_ids) != tuple(sorted(data["source_versions"]))
            or tuple(result.counterevidence_ids) != tuple(data["concepts"]["counterevidence_ids"])
            or result.rule_version != data["rule_version"]
            or result.coverage != "CONDITIONAL_CONCEPT_SENSITIVE_JUDGMENT"
            or result.diagnostics):
        raise ValueError("original concept inference metadata changed")
    return operation


def _merge_sources(target, sources):
    for key, version in sources.items():
        if type(key) is not str or type(version) is not int or version < 0:
            raise ValueError("invalid inherited source version")
        if key in target and target[key] != version:
            _needs("conflicting_source_versions")
        target[key] = version


def _language(version):
    language = {}
    sorts = set()
    for criterion in version["criteria"]:
        for kind in ("positive", "negative", "boundary"):
            for example in criterion[kind]:
                sorts.add(example["term"]["sort"])
                for symbol, signature in validate_term(example["term"]).items():
                    if symbol in language and language[symbol] != signature:
                        _needs("incompatible_signature")
                    language[symbol] = signature
    return language, sorts


def _compatible(program, choice, adopted):
    versions = {v["id"]: v for v in program["versions"]}
    family = tuple(adopted[k] for k in ("concept_key", "scope", "frame_kind"))
    language, sorts = _language(adopted)
    for label in choice["versions"]:
        old = versions[label]
        if tuple(old[k] for k in ("concept_key", "scope", "frame_kind")) != family:
            _needs("different_concept_family_or_frame")
        old_language, old_sorts = _language(old)
        if sorts != old_sorts or any(s in old_language and old_language[s] != t for s, t in language.items()):
            _needs("incompatible_signature")
    cases = {c["id"]: c for c in program["cases"]}
    for use in program["uses"]:
        if use["selector"] != dict(kind="CHOICE", id=choice["id"]):
            continue
        if use["commitment"] is not None:
            _needs("original_commitment_must_remain_pinned")
        if adopted["effective_at"] > use["at"]:
            _needs("future_concept_version")
        case = cases[use["case_id"]]["term"]
        if case is not None and (case["sort"] not in sorts or any(
                s in language and language[s] != t for s, t in validate_term(case).items())):
            _needs("incompatible_case_signature")


def _prepare(base, selections, *, replay=False):
    data = thaw(base.values)
    verify_concept_inference(base, replay=replay)
    program = deepcopy(data["program"]["concepts"])
    sources = dict(data["source_versions"])
    choices = {c["id"]: c for c in program["choices"]}
    original_versions = {v["id"]: v for v in program["versions"]}
    seen, replacements, proof_environments, counters = set(), {}, set(), set()
    if len(selections) > 4:
        raise ValueError("bounded explicit concept selections required")
    normalized = []
    for raw in selections:
        selection = thaw(raw)
        if set(selection) != SELECTION_FIELDS or any(type(selection[k]) is not str or not selection[k]
                or len(selection[k]) > 256 for k in SELECTION_FIELDS - {"proof"}):
            raise ValueError("invalid explicit adoption selection")
        key = selection["choice_id"]
        if key in seen or key not in choices:
            raise ValueError("unique existing CHOICE selector required")
        seen.add(key)
        proof = _decode_proof(selection["proof"])
        verify_concept_inference(proof, replay=replay)
        adopted = thaw(proof.values)
        if (adopted["program"]["host_context"] != data["program"]["host_context"]
                or adopted["rule_version"] != data["rule_version"]):
            _needs("different_host_or_rule")
        matching = [v for v in adopted["concepts"]["definitions"]
                    if v["id"] == selection["version_label"] and v["definition_version"] == selection["definition_version"]]
        if len(matching) != 1 or not adopted["concepts"]["complete"]:
            _needs("uncomputed_adopted_definition")
        definition = matching[0]
        version = deepcopy(next(v for v in adopted["program"]["concepts"]["versions"] if v["id"] == selection["version_label"]))
        family = "concept:" + digest([program["namespace"], version["scope"], version["concept_key"]])
        if (definition["concept_id"] != family or definition["definition_version"] !=
                "concept-definition:" + digest([family, semantic_definition(version)])):
            raise ValueError("adopted definition identity differs from raw evidence")
        _compatible(program, choices[key], version)
        label = "adopted:" + digest([key, selection["stream_id"], selection["adoption_id"],
            selection["definition_version"], proof.result_id])[:56]
        nonce = 0
        while label in {v["id"] for v in program["versions"]}:
            nonce += 1
            label = "adopted:" + digest([selection, nonce])[:56]
        equivalents = [old for old in choices[key]["versions"]
                      if semantic_definition(original_versions[old]) == semantic_definition(version)]
        replacements[key] = (label, equivalents)
        version["id"] = label
        program["versions"].append(version)
        choices[key]["versions"] = [label]
        _merge_sources(sources, adopted["source_versions"])
        for segment_id, binding in adopted["program"]["concepts"]["source_bindings"].items():
            if segment_id in program["source_bindings"] and program["source_bindings"][segment_id] != binding:
                _needs("conflicting_source_binding")
            program["source_bindings"][segment_id] = binding
        proof_environments.update(proof.assumption_environments)
        counters.update(proof.counterevidence_ids)
        normalized.append(selection)
    for constraint in program["constraints"]:
        pairs = constraint["allowed_pairs"]
        for position, side in enumerate(("left", "right")):
            key = constraint[side]
            if key not in replacements:
                continue
            label, equivalents = replacements[key]
            # Constraints declare pairs of particular meanings. A genuinely new
            # meaning provides no evidence for any previously allowed pair.
            if len(equivalents) != 1:
                _needs("constraint_requires_explicit_recompilation")
            pairs = [list(pair) for pair in pairs if pair[position] == equivalents[0]]
            for pair in pairs:
                pair[position] = label
        if not pairs:
            _needs("incompatible_joint_constraint")
        constraint["allowed_pairs"] = pairs
    program["source_versions"] = sources
    return program, tuple(normalized), sources, proof_environments, counters


def _fixed_models(base):
    data = thaw(base.values)
    if not data["complete"] or not data["branches"]:
        _needs("incomplete_original_judgment")
    branch = data["branches"][0]
    if not branch["complete"]:
        _needs("incomplete_original_fixed_inputs")
    if branch["actual_judgment"]["program"] != data["program"]["base_program"]:
        raise ValueError("fixed input program changed")
    return {i: model for i, model in enumerate(branch["actual_judgment"]["models"])}


def _projection(values):
    branches = values["branches"]
    semantics = sorted({_canonical(dict(
        classifications={k: classification_semantics(v) for k, v in b["classifications"].items()},
        decisions={k: decision_semantics(v) for k, v in b["decision_projection"].items()})) for b in branches})
    return dict(semantics=dict(complete=values["complete"], branches=semantics,
                              robust_recommended=values["robust_recommended"]),
        trace=digest(_canonical([values["concepts"], branches])))


def _solve(snapshot, issue, allowance, base, selections):
    program, selections, sources, proof_environments, counters = _prepare(base, selections)
    original = thaw(base.values)
    if host_context(snapshot) != original["program"]["host_context"] or snapshot.rule_version != original["rule_version"]:
        _needs("different_host_or_rule")
    if any(snapshot.source_versions.get(k) != v for k, v in sources.items()):
        _needs("missing_original_or_adopted_source")
    original_snapshot = _snapshot(original["program"]["host_context"], original["source_versions"], original["rule_version"])
    fixed = _fixed_models(base)
    work = JudgmentWork(_bound(allowance.max_local_evaluations).max_local_evaluations)
    concepts = compute_versions(program, work.limit)
    work.spend(concepts["local_evaluations"])
    branches, issues = [], list(concepts["frontier"])
    environments = set(base.assumption_environments) | proof_environments | set(concepts["assumption_environments"])
    counters.update(base.counterevidence_ids)
    counters.update(concepts["counterevidence_ids"])
    try:
        for branch in concepts["branches"]:
            if not branch["complete"]:
                continue
            work.spend()
            operation = JudgmentModelOperator()._run(original_snapshot, issue,
                replace(allowance, max_local_evaluations=work.limit - work.used), original["program"]["base_program"],
                concept_context=dict(bindings=original["program"]["concept_bindings"],
                    classifications=branch["classifications"], shared_upstream={}, fixed_models=fixed,
                    fixed_program=original["program"]["base_program"], fixed_sources=original["source_versions"],
                    fixed_rule=original["rule_version"]))
            work.spend(operation.resource_usage["local_evaluations"])
            inference = operation.candidate_delta.new_inferences[0]
            actual = thaw(inference.values)
            complete = not any(m["frontier"] or not m["decisions"] or m["actual_argument"] is None
                or any(a["frontier"] for a in m["actual_argument"]["values"]["models"])
                or any(d["status"] != "COMPUTED" for d in m["decisions"]) for m in actual["models"])
            branches.append(dict(branch_id=branch["branch_id"], selections=branch["selections"],
                classifications=branch["classifications"], actual_judgment=actual, result_id=inference.result_id,
                complete=complete, decision_projection=decision_projection(actual)))
            environments.update(inference.assumption_environments)
            issues.extend(operation.issues)
    except OverflowError:
        issues.append("PERSISTENT_CONCEPT_WORK_FRONTIER")
    complete = bool(branches) and concepts["complete"] and len(branches) == len(concepts["branches"]) and all(b["complete"] for b in branches)
    robust = {}
    try:
        if complete:
            keys = set(branches[0]["decision_projection"])
            if any(set(b["decision_projection"]) != keys for b in branches):
                raise ValueError("persistent decision identities changed")
            for key in sorted(keys):
                work.spend(len(branches))
                robust[key] = sorted(set.intersection(*(set(b["decision_projection"][key]["recommended"]) for b in branches)))
    except OverflowError:
        complete, robust = False, {}
        issues.append("PERSISTENT_CONCEPT_WORK_FRONTIER")
    if not complete:
        issues.append("PERSISTENT_CONCEPT_INCOMPLETE_VERSION_FRONTIER")
    if program["unmodeled_segments"]:
        issues.append("UNMODELED_CONCEPT_SOURCE")
    values = dict(schema=SCHEMA, operator_version=VERSION, issue_id=issue.issue_id,
        rule_version=snapshot.rule_version, source_versions=dict(snapshot.source_versions),
        base_result=codec.encode(base), selections=list(selections), concepts=concepts, branches=branches,
        robust_recommended=robust, complete=complete, issues=sorted(set(issues)),
        local_evaluations=work.used, execution_allowance=work.limit,
        reused_fixed_models=len(fixed) * len(branches), semantic_certified=False,
        scope="CONDITIONAL_SAME_PRINCIPAL_SESSION_ADOPTION_NOT_GLOBAL_PROPAGATION_OR_MORAL_TRUTH")
    return values, environments, counters


def _previous_recipe(previous, base):
    if type(previous) is not InferenceResult or previous.kind != KIND:
        raise ValueError("previous persistent inference required")
    data = thaw(previous.values)
    # Previous is already an accepted result at the runtime boundary. Recheck
    # its immutable base and metadata; delivery independently replays its recipe.
    _check_persistent_metadata(previous)
    if data["base_result"] != codec.encode(base):
        _needs("different_original_base")
    sources = dict(base.values["source_versions"])
    for selection in data["selections"]:
        _merge_sources(sources, _decode_proof(selection["proof"]).values["source_versions"])
    return dict(schema="hcl-persistent-prior-projection-1", issue_id=data["issue_id"],
        execution_allowance=data["execution_allowance"], selections=data["selections"],
        source_versions=sources, projection=_projection(data))


def _operation(snapshot, issue, allowance, base, selections, previous=None):
    values, environments, counters = _solve(snapshot, issue, allowance, base, selections)
    projection = _projection(values)
    prior = _projection(thaw(base.values)) if previous is None else previous["projection"]
    if previous is not None:
        values["previous_result"] = codec.encode(previous)
        for selection in previous["selections"]:
            proof = _decode_proof(selection["proof"])
            if any(snapshot.source_versions.get(k) != v for k, v in proof.values["source_versions"].items()):
                _needs("missing_prior_comparison_source")
            environments.update(proof.assumption_environments)
            counters.update(proof.counterevidence_ids)
    values.update(comparison_basis="ORIGINAL_BASE_BUNDLE" if previous is None else "PRIOR_PERSISTENT_PROJECTION",
                  semantics_changed=projection["semantics"] != prior["semantics"],
                  trace_changed=projection["trace"] != prior["trace"])
    inference = InferenceResult("persistent-concept:" + digest([issue.issue_id, _canonical(values)]), KIND, values,
        tuple(sorted(environments)), tuple(sorted(snapshot.source_versions)), tuple(sorted(counters)),
        snapshot.rule_version, COVERAGE)
    return OpResult("judgment.persistent_concepts", VERSION, snapshot.source_versions, ("append_inference",),
        (inference.result_id,), tuple(values["issues"]), dict(local_evaluations=values["local_evaluations"]), (),
        Delta(snapshot.session_id, snapshot.principal, snapshot.revision, snapshot.access_epoch,
              snapshot.rule_version, snapshot.source_versions, (inference,)))


def compute_persistent(snapshot, issue, allowance, base_result: InferenceResult, selections: tuple[dict],
                       *, previous_result: InferenceResult | None = None) -> OpResult:
    """Solve newly selected meanings using caller-source-validated immutable proofs.

    No provider, source reads, store changes, or authority decisions occur here.
    Full replay is separate from newly charged branch-local computation.
    """
    try:
        previous = None if previous_result is None else _previous_recipe(previous_result, base_result)
        return _operation(snapshot, issue, allowance, base_result, selections, previous)
    except HCLFailure:
        raise
    except (ValueError, TypeError, KeyError, IndexError, RecursionError, StopIteration, OverflowError):
        raise HCLFailure("INVALID_REQUEST", "persistent_concept", "INVALID_PERSISTENT_CONCEPT_JUDGMENT", "certificate",
            "The persistent concept judgment violates its immutable proof and selection contract.") from None


def verify_persistent(values):
    """Replay all evidence, one bounded prior projection, and the actual new solve."""
    data = thaw(values)
    if data["schema"] != SCHEMA or data["operator_version"] != VERSION:
        raise ValueError("unsupported persistent concept certificate")
    base = _decode_proof(data["base_result"])
    _prepare(base, data["selections"], replay=True)
    host = base.values["program"]["host_context"]
    snapshot = _snapshot(thaw(host), data["source_versions"], data["rule_version"])
    previous = None
    if "previous_result" in data:
        previous = codec.decode(data["previous_result"])
        if type(previous) is not dict or set(previous) != {"schema", "issue_id", "execution_allowance", "selections", "source_versions", "projection"}:
            raise ValueError("bounded prior projection required")
        if previous["schema"] != "hcl-persistent-prior-projection-1":
            raise ValueError("unsupported prior projection")
        _prepare(base, previous["selections"], replay=True)
        prior_snapshot = _snapshot(thaw(host), previous["source_versions"], data["rule_version"])
        actual, _, _ = _solve(prior_snapshot, Issue(previous["issue_id"], "judgment.evaluate"),
            _bound(previous["execution_allowance"]), base, previous["selections"])
        if _canonical(_projection(actual)) != _canonical(previous["projection"]):
            raise ValueError("prior semantic/trace projection changed")
    expected = _operation(snapshot, Issue(data["issue_id"], "judgment.evaluate"),
        _bound(data["execution_allowance"]), base, data["selections"], previous)
    if _canonical(expected.candidate_delta.new_inferences[0].values) != _canonical(data):
        raise ValueError("persistent concept result differs from replay")
    return expected


def _valid_result_identity(result_id, data):
    if result_id == "persistent-concept:" + digest([data["issue_id"], _canonical(data)]):
        return True
    # The engine may wrap the pure identity with authenticated query/ACL commit
    # context. Its opaque suffix must be checked against the accepted store
    # record at that boundary; the pure certificate cannot reconstruct it.
    parts = result_id.split(":") if type(result_id) is str else []
    return len(parts) == 3 and parts[0] == "concept-successor" and all(
        len(p) == 64 and all(c in "0123456789abcdef" for c in p) for p in parts[1:])


def _check_persistent_metadata(result, expected=None):
    data = thaw(result.values)
    if (result.kind != KIND or data["schema"] != SCHEMA or data["operator_version"] != VERSION
            or not _valid_result_identity(result.result_id, data)
            or tuple(result.premise_ids) != tuple(sorted(data["source_versions"]))
            or result.rule_version != data["rule_version"] or result.coverage != COVERAGE or result.diagnostics):
        raise ValueError("persistent inference metadata changed")
    if expected is not None and (tuple(result.assumption_environments) != tuple(expected.assumption_environments)
            or tuple(result.counterevidence_ids) != tuple(expected.counterevidence_ids)):
        raise ValueError("persistent inference conditions changed")


def verify_persistent_inference(result):
    if type(result) is not InferenceResult:
        raise ValueError("persistent inference required")
    expected = verify_persistent(result.values)
    _check_persistent_metadata(result, expected.candidate_delta.new_inferences[0])
    return expected

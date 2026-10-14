"""Actual finite M12 definitions, new-case classification and joint version uses.

Semantic identity is independent of evidence identity. This result grants no
access; current source/ACL/host checks remain at the ordinary runtime boundary.
"""
from itertools import product
from hcl.kernel.types import thaw
from hcl.memory import codec
from hcl.operators.concept_induction import generalize_examples, match_independent_case
from hcl.operators.judgment import JudgmentWork
from hcl.semantics.concept_version_compiler import digest, semantic_definition

VERSION = "finite-concept-versions-1"


def classify_case(definition, case, work):
    """Four-valued directional classification; matching is not membership."""
    positive, negative, uncertain, traces = [], [], [], []
    if set(case["assumptions"]) - set(case["active_assumptions"]):
        return dict(status="CASE_ASSUMPTION_RETRACTED", possible_values=[False, True],
                    support=[], exclusion=[], uncertain=["CASE_ASSUMPTION_RETRACTED"], criteria=[])
    for criterion in definition["criteria"]:
        work.spend()
        actual = criterion["actual"]
        if actual is None or actual["frontier"] or criterion["withdrawn"]:
            uncertain.append(criterion["id"])
            traces.append(dict(criterion_id=criterion["id"], match="UNCOMPUTED", direction=criterion["direction"]))
            continue
        if "patterns" in actual:
            from hcl.operators.concept_repairs import match_disjunction
            check = match_disjunction(actual["patterns"], case["term"], work.spend)
        else:
            check = match_independent_case(actual["pattern"], case["term"], work.spend)
        direction = criterion["direction"]
        trace = dict(criterion_id=criterion["id"], direction=direction, actual=check,
                     challenged_by=criterion["counterexamples"], boundary=criterion["boundary"])
        traces.append(trace)
        if check["status"] == "UNKNOWN":
            uncertain.append(criterion["id"])
            continue
        matched = check["status"] == "MATCH"
        if direction in ("SUFFICIENT", "BICONDITIONAL") and matched:
            positive.append(criterion["id"])
        if direction in ("NECESSARY", "BICONDITIONAL") and not matched:
            negative.append(criterion["id"])
        if criterion["counterexamples"]:
            uncertain.append("CHALLENGED:" + criterion["id"])
        if any(row["term"] == case["term"] for row in criterion["boundary"]):
            uncertain.append("BOUNDARY:" + criterion["id"])
    if definition["withdrawn"]:
        uncertain.append("VERSION_ASSUMPTION_RETRACTED")
    status = ("CONFLICTING" if positive and negative else "UNRESOLVED" if uncertain else
              "MEMBER" if positive else "EXCLUDED" if negative else "UNDETERMINED")
    values = [True] if status == "MEMBER" else [False] if status == "EXCLUDED" else [False, True]
    return dict(status=status, possible_values=values, support=positive, exclusion=negative,
                uncertain=uncertain, criteria=traces)


def compute_versions(program, max_work):
    program = thaw(program)
    if program["namespace"] != digest(program["host_context"]):
        raise ValueError("concept host namespace changed")
    work = JudgmentWork(max_work)
    definitions, branches, frontier, conditions, counters = [], [], [], set(), set()
    versions = {v["id"]: v for v in program["versions"]}
    cases = {c["id"]: c for c in program["cases"]}
    conditions.update("concept-case:" + c["id"] + ":" + a for c in cases.values() for a in c["active_assumptions"])
    try:
        for version in versions.values():
            work.spend()
            family = "concept:" + digest([program["namespace"], version["scope"], version["concept_key"]])
            semantics = semantic_definition(version)
            definition = dict(id=version["id"], concept_id=family,
                definition_version="concept-definition:" + digest([family, semantics]),
                semantic_definition=semantics, criteria=[],
                withdrawn=sorted(set(version["assumptions"]) - set(version["active_assumptions"])),
                evidence_fingerprint=digest([version, program["source_versions"], program["source_bindings"]]))
            definitions.append(definition)
            conditions.update("concept-version:" + family + ":" + a for a in version["active_assumptions"])
            active = set(version["active_assumptions"])
            for criterion in version["criteria"]:
                work.spend()
                selected = {k: sorted((r for r in criterion[k] if set(r["assumptions"]) <= active),
                                     key=lambda r: (codec.canonical(r["term"]), r["id"]))
                            for k in ("positive", "negative", "boundary")}
                withdrawn = (not set(criterion["assumptions"]) <= active or
                             any(len(selected[k]) != len(criterion[k]) for k in selected))
                actual = None
                if version.get("definition_language") == "OR_OF_POSITIVE_PARTITION_LGGS_1":
                    from hcl.operators.concept_repairs import evaluate_partition
                    if not withdrawn:
                        actual = evaluate_partition(criterion, min(1000000, work.limit-work.used))
                        work.spend(actual["work"])
                        frontier.extend(actual["frontier"])
                elif selected["positive"] and not set(criterion["assumptions"]) - active:
                    actual = generalize_examples(*([dict(id=r["id"], term=r["term"]) for r in selected[k]]
                                                   for k in ("positive", "negative")),
                                                 max_work=min(1000000, work.limit - work.used))
                    work.spend(actual["work"])
                    if actual["frontier"]:
                        frontier.extend(actual["frontier"])
                challenged = ([] if actual is None or criterion["direction"] not in ("SUFFICIENT", "BICONDITIONAL")
                              else list(actual["counterexample_ids"]))
                counters.update("concept-example:" + version["id"] + ":" + criterion["id"] + ":" + k for k in challenged)
                boundary = []
                for row in selected["boundary"]:
                    if actual is not None and "patterns" in actual:
                        from hcl.operators.concept_repairs import match_disjunction
                        check = match_disjunction(actual["patterns"], row["term"], work.spend)
                    else:
                        check = match_independent_case(None if actual is None else actual["pattern"], row["term"], work.spend)
                    boundary.append(dict(id=row["id"], term=row["term"], actual=check, segment_ids=row["segment_ids"]))
                definition["criteria"].append(dict(id=criterion["id"], direction=criterion["direction"],
                    actual=actual, counterexamples=challenged, boundary=boundary, withdrawn=withdrawn))
        if frontier:
            raise OverflowError()
        definitions_by_id = {d["id"]: d for d in definitions}
        choices = {c["id"]: c["versions"] for c in program["choices"]}
        for combination in product(*choices.values()):
            work.spend()
            selection = dict(zip(choices, combination))
            if any([selection[c["left"]], selection[c["right"]]] not in c["allowed_pairs"] for c in program["constraints"]):
                continue
            branch = dict(branch_id="concept-branch:" + digest(selection), selections=selection, classifications={}, complete=False)
            branches.append(branch)
            for use in program["uses"]:
                work.spend()
                selector = use["selector"]
                key = selector["id"] if selector["kind"] == "PINNED" else selection[selector["id"]]
                definition = definitions_by_id[key]
                case = cases[use["case_id"]]
                actual = classify_case(definition, case, work)
                branch["classifications"][use["id"]] = dict(use_id=use["id"], case_id=case["id"],
                    concept_id=definition["concept_id"], definition_version=definition["definition_version"],
                    version_label=key, at=use["at"], frame_kind=use["frame_kind"], scope=use["scope"],
                    commitment=use["commitment"], selector=selector, actual=actual,
                    assumption_environments=sorted(set(versions[key]["active_assumptions"]) | set(case["active_assumptions"])),
                    evidence_segment_ids=sorted(set(use["segment_ids"]) | set(case["segment_ids"]) | set(versions[key]["segment_ids"])))
            branch["complete"] = True
    except OverflowError:
        frontier.append("CONCEPT_VERSION_WORK_FRONTIER")
    if not branches and not frontier:
        frontier.append("NO_COMPATIBLE_DECLARED_VERSION_BRANCH")
    return dict(schema=VERSION, definitions=definitions, branches=branches,
        complete=not frontier and all(b["complete"] for b in branches), frontier=sorted(set(frontier)),
        local_evaluations=work.used, assumption_environments=sorted(conditions), counterevidence_ids=sorted(counters),
        source_versions=program["source_versions"], evidence_fingerprint=digest(program),
        scope="CONDITIONAL_TYPED_CRITERIA_NOT_OPEN_WORLD_MEMBERSHIP", semantic_certified=False)

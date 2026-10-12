"""Source-qualified structural mappings, distinct from concept truth or beauty."""

from hashlib import sha256
from hcl.kernel.types import Delta, InferenceResult, OpResult, freeze, thaw
from hcl.memory import codec
from hcl.operators.structure_mapping import structural_mappings

KIND = "CONDITIONAL_STRUCTURAL_MAPPINGS"
VERSION = "structural-concepts-1"


def _active(model, side):
    original = model[side]
    active = set(model["active_assumptions"])
    kept = {
        row["id"]: row for row in original["facts"] if set(row["assumptions"]) <= active
    }
    while True:
        next_rows = {
            key: row
            for key, row in kept.items()
            if all(
                arg["kind"] != "FACT" or arg["id"] in kept for arg in row["arguments"]
            )
        }
        if len(next_rows) == len(kept):
            break
        kept = next_rows
    return dict(
        entities=[
            {k: v for k, v in row.items() if k != "segment_ids"}
            for row in original["entities"]
        ],
        predicates=[
            {k: v for k, v in row.items() if k != "segment_ids"}
            for row in original["predicates"]
        ],
        facts=[
            {k: v for k, v in row.items() if k not in ("assumptions", "segment_ids")}
            for row in kept.values()
        ],
    ), tuple(sorted(row["id"] for row in original["facts"] if row["id"] not in kept))


def compute_concepts(program, max_work):
    program = thaw(program)
    if (
        type(max_work) is not int
        or max_work < 0
        or type(program["source_versions"]) is not dict
        or any(type(v) is not int or v < 1 for v in program["source_versions"].values())
        or program["input_identity"]
        != sha256(
            codec.dumps(
                dict(
                    schema=program["schema"],
                    models=program["models"],
                    inductions=program["inductions"],
                )
            )
        ).hexdigest()
    ):
        raise ValueError("structural input binding or allowance changed")
    used, outputs, issues, environments, counterevidence = 0, [], set(), set(), set()
    for model in program["models"]:
        base, inactive_base = _active(model, "base")
        target, inactive_target = _active(model, "target")
        active = set(model["active_assumptions"])
        compatibilities = [
            r for r in model["compatibilities"] if set(r["assumptions"]) <= active
        ]
        computed = structural_mappings(
            base,
            target,
            [[r["base"], r["target"]] for r in compatibilities],
            max_work=min(max_work - used, 1000000),
            max_mappings=model["max_mappings"],
        )
        used += computed["work"]
        issues.update(computed["frontier"])
        if (
            inactive_base
            or inactive_target
            or len(compatibilities) != len(model["compatibilities"])
        ):
            issues.add("STRUCTURAL_ASSUMPTION_OR_DEPENDENCY_WITHDRAWN")
        if model["unmodeled_segments"]:
            issues.add("UNMODELED_STRUCTURAL_SOURCE")
        condition = lambda a: "structural:" + model["id"] + ":assumption:" + a
        registries = {
            side: {
                name: {r["id"]: r for r in model[side][name]}
                for name in ("entities", "predicates", "facts")
            }
            for side in ("base", "target")
        }
        pair_rows = {(r["base"], r["target"]): r for r in compatibilities}

        def evidence(side, facts):
            conditions, segments, pending, seen = set(), set(), list(facts), set()
            registry = registries[side]
            while pending:
                key = pending.pop()
                if key in seen:
                    continue
                seen.add(key)
                row = registry["facts"][key]
                conditions.update(condition(a) for a in row["assumptions"])
                segments.update(row["segment_ids"])
                segments.update(registry["predicates"][row["predicate"]]["segment_ids"])
                for arg in row["arguments"]:
                    if arg["kind"] == "FACT":
                        pending.append(arg["id"])
                    else:
                        segments.update(registry["entities"][arg["id"]]["segment_ids"])
            return conditions, segments

        for mapping in computed["mappings"]:
            assumptions, spans = set(), set()
            for side, facts in (
                ("base", mapping["facts"]),
                ("target", mapping["facts"].values()),
            ):
                a, s = evidence(side, facts)
                assumptions.update(a)
                spans.update(s)
            for pair in mapping["predicates"].items():
                row = pair_rows[pair]
                assumptions.update(condition(a) for a in row["assumptions"])
                spans.update(row["segment_ids"])
            mapping["assumption_environments"] = tuple(sorted(assumptions))
            mapping["evidence_segment_ids"] = tuple(sorted(spans))
            environments.update(assumptions)
            metric_conditions = {
                name: set()
                for name in (
                    "higher_order_links",
                    "supported_relations",
                    "explicit_counterexamples",
                    "attribute_mismatches",
                )
            }
            metric_spans = {name: set() for name in metric_conditions}
            for prediction in mapping["predictions"]:
                a, s = evidence("base", [prediction["base_fact"]])
                required, provenance = assumptions | a, spans | s
                # A partial mapping can support additional projected facts that
                # are not members of mapping['facts']. Charge each metric's
                # actual contributors, keeping positive and negative premises
                # separate even when the target contains both polarities.
                for metric, count in prediction["metric_contributions"].items():
                    if not count:
                        continue
                    target_key = (
                        "counterexample_target_fact"
                        if metric == "explicit_counterexamples"
                        else "supporting_target_fact"
                    )
                    ma, ms = evidence("target", [prediction[target_key]])
                    metric_conditions[metric].update(required | ma)
                    metric_spans[metric].update(provenance | ms)
                actuals = [
                    prediction[key]
                    for key in ("supporting_target_fact", "counterexample_target_fact")
                    if prediction[key] is not None
                ]
                a, s = evidence("target", actuals)
                required.update(a)
                provenance.update(s)
                prediction["assumption_environments"] = tuple(sorted(required))
                prediction["evidence_segment_ids"] = tuple(sorted(provenance))
                environments.update(required)
                if prediction["counterexample_target_fact"]:
                    counterevidence.add(
                        "structural:"
                        + model["id"]
                        + ":target:"
                        + prediction["counterexample_target_fact"]
                    )
            for check in mapping["attribute_checks"]:
                a, s = evidence("base", [check["base_fact"]])
                required, provenance = assumptions | a, spans | s
                options = [
                    r
                    for r in compatibilities
                    if r["base"]
                    == registries["base"]["facts"][check["base_fact"]]["predicate"]
                    and r["target"] == check["target_predicate"]
                ]
                if len(options) == 1:
                    required.update(condition(a) for a in options[0]["assumptions"])
                    provenance.update(options[0]["segment_ids"])
                if check.get("counterexample_target_fact"):
                    ma, ms = evidence("target", [check["counterexample_target_fact"]])
                    metric_conditions["attribute_mismatches"].update(required | ma)
                    metric_spans["attribute_mismatches"].update(provenance | ms)
                actuals = [
                    check.get(key)
                    for key in ("supporting_target_fact", "counterexample_target_fact")
                    if check.get(key) is not None
                ]
                a, s = evidence("target", actuals)
                required.update(a)
                provenance.update(s)
                check["assumption_environments"] = tuple(sorted(required))
                check["evidence_segment_ids"] = tuple(sorted(provenance))
                environments.update(required)
                if check.get("counterexample_target_fact"):
                    counterevidence.add(
                        "structural:"
                        + model["id"]
                        + ":target:"
                        + check["counterexample_target_fact"]
                    )
            mapping["metric_conditions"] = {
                name: tuple(sorted(values))
                for name, values in metric_conditions.items()
            }
            mapping["metric_evidence_segment_ids"] = {
                name: tuple(sorted(values)) for name, values in metric_spans.items()
            }
            mapping["ordering_assumption_environments"] = tuple(
                sorted(assumptions.union(*metric_conditions.values()))
            )

        outputs.append(
            dict(
                id=model["id"],
                actual=computed,
                inactive_base_facts=inactive_base,
                inactive_target_facts=inactive_target,
                unmodeled_segments=model["unmodeled_segments"],
            )
        )
    from hcl.operators.concept_induction import generalize_examples

    inductions = []
    for proposal in program["inductions"]:
        active = set(proposal["active_assumptions"])
        selected = {
            label: [row for row in proposal[label] if set(row["assumptions"]) <= active]
            for label in ("positive", "negative")
        }
        inactive = tuple(
            sorted(
                row["id"]
                for label in selected
                for row in proposal[label]
                if row not in selected[label]
            )
        )
        condition = lambda a: "concept:" + proposal["id"] + ":assumption:" + a
        conditions = {
            condition(a) for row in selected["positive"] for a in row["assumptions"]
        }
        evidence = {s for row in selected["positive"] for s in row["segment_ids"]}
        if selected["positive"]:
            computed = generalize_examples(
                *(
                    [
                        {k: v for k, v in row.items() if k in ("id", "term")}
                        for row in selected[label]
                    ]
                    for label in ("positive", "negative")
                ),
                max_work=min(max_work - used, 1000000)
            )
            used += computed["work"]
            issues.update(computed["frontier"])
            rows = {row["id"]: row for label in selected for row in selected[label]}
            for evaluation in computed["examples"]:
                row = rows[evaluation["id"]]
                evaluation["assumption_environments"] = tuple(
                    sorted(conditions | {condition(a) for a in row["assumptions"]})
                )
                evaluation["evidence_segment_ids"] = tuple(
                    sorted(evidence | set(row["segment_ids"]))
                )
                environments.update(evaluation["assumption_environments"])
            for key in computed["counterexample_ids"]:
                counterevidence.add("concept:" + proposal["id"] + ":example:" + key)
            if computed["counterexample_ids"]:
                issues.add("CONCEPT_GENERALIZATION_HAS_COUNTEREXAMPLES")
        else:
            computed = None
            issues.add("INDUCTION_NO_ACTIVE_POSITIVES")
        if inactive:
            issues.add("CONCEPT_EXAMPLE_ASSUMPTION_WITHDRAWN")
        if proposal["unmodeled_segments"]:
            issues.add("UNMODELED_CONCEPT_SOURCE")
        family = (
            "concept:"
            + sha256(
                codec.dumps(
                    [
                        program["concept_namespace"],
                        proposal["concept_key"],
                        proposal["purpose"],
                    ]
                )
            ).hexdigest()
        )
        definition = dict(
            concept_id=family,
            purpose=proposal["purpose"],
            pattern=None if computed is None else computed["pattern"],
            assumption_environments=tuple(sorted(conditions)),
            evidence_segment_ids=tuple(sorted(evidence)),
            source_versions=program["source_versions"],
            proposal=proposal,
        )
        inductions.append(
            dict(
                id=proposal["id"],
                concept_key=proposal["concept_key"],
                concept_id=family,
                version_id="concept-version:"
                + sha256(codec.dumps(definition)).hexdigest(),
                purpose=proposal["purpose"],
                actual=computed,
                inactive_examples=inactive,
                assumption_environments=tuple(sorted(conditions)),
                evidence_segment_ids=tuple(sorted(evidence)),
                unmodeled_segments=proposal["unmodeled_segments"],
            )
        )
        environments.update(conditions)
    return dict(
        schema=VERSION,
        models=outputs,
        inductions=inductions,
        local_evaluations=used,
        issues=tuple(sorted(issues)),
        assumption_environments=tuple(sorted(environments)),
        counterevidence_ids=tuple(sorted(counterevidence)),
        source_versions=program["source_versions"],
        source_bindings=program["source_bindings"],
        semantic_certified=False,
        candidate_completeness="NOT_ESTABLISHED",
        scope="FINITE_SOURCE_BOUND_STRUCTURAL_MAPPING_NOT_TARGET_OR_AESTHETIC_TRUTH",
    )


def concept_result_id(issue_id, values):
    return (
        "structural-result:"
        + sha256(codec.dumps([issue_id, freeze(values)])).hexdigest()
    )


class ConceptOperator:
    def run(self, snapshot, issue, allowance, program):
        values = compute_concepts(program, allowance.max_local_evaluations)
        values["inputs"] = dict(
            program=thaw(program), max_work=allowance.max_local_evaluations
        )
        result = InferenceResult(
            concept_result_id(issue.issue_id, values),
            KIND,
            values,
            tuple(values["assumption_environments"]),
            tuple(snapshot.source_versions),
            tuple(values["counterevidence_ids"]),
            snapshot.rule_version,
            "CONDITIONAL_STRUCTURAL_MODEL",
        )
        delta = Delta(
            snapshot.session_id,
            snapshot.principal,
            snapshot.revision,
            snapshot.access_epoch,
            snapshot.rule_version,
            snapshot.source_versions,
            (result,),
        )
        return OpResult(
            operation_id="concepts.structural_mapping",
            version=VERSION,
            read_set=snapshot.source_versions,
            effects=("append_inference",),
            result_refs=(result.result_id,),
            issues=tuple(values["issues"]),
            resource_usage=dict(local_evaluations=values["local_evaluations"]),
            diagnostics=(),
            candidate_delta=delta,
        )


def verify_concepts(values):
    expected = compute_concepts(
        values["inputs"]["program"], values["inputs"]["max_work"]
    )
    if any(
        codec.dumps(freeze(values[key])) != codec.dumps(freeze(value))
        for key, value in expected.items()
    ):
        raise ValueError("structural mapping differs from its actual bound computation")
    return expected

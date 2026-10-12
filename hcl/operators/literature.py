"""Bounded story/discourse computation and literal form contrasts.

Source-bound proposals remain conditional. This layer does not supply a gold
literary interpretation, reader emotion score, or author-intent oracle.
"""

from dataclasses import asdict, replace
from hashlib import sha256

from hcl.kernel.temporal import (
    TimePoint,
    TemporalConstraint,
    TemporalForest,
    TemporalProfile,
)
from hcl.kernel.types import Delta, InferenceResult, Issue, OpResult, freeze, thaw
from hcl.memory import codec
from hcl.operators.narrative_form import measure_form

VERSION = "narrative-computation-1"
KIND = "CONDITIONAL_NARRATIVE_MODEL"
MAX_FORM_WORK = 100000
PROFILE = TemporalProfile(
    max_points=128, max_constraints=4096, max_relaxations=100000, max_proof_edges=512
)
OPEN_MECHANISMS = (
    "THEME_MECHANISM_COMPARISON_UNCOMPUTED",
    "STRUCTURAL_MAPPING_UNCOMPUTED",
    "CHARACTER_MECHANISM_COMPOSITION_UNCOMPUTED",
    "AESTHETIC_EFFECT_NOT_CERTIFIED",
)


def identity(fragment, kind, value):
    return "narrative:" + sha256(codec.dumps([fragment, kind, value])).hexdigest()


def compute_narrative(program, originals, max_batches):
    """Actual finite computations; each bounded scan/clock closure uses one batch."""
    if type(max_batches) is not int or max_batches < 0:
        raise ValueError("nonnegative narrative batch allowance required")
    program = thaw(program)
    fragments = program["fragments"]
    if type(program["source_versions"]) is not dict or any(
        type(v) is not int or v < 1 for v in program["source_versions"].values()
    ):
        raise ValueError("narrative source version contract changed")
    digest = program.pop("candidate_identity")
    if sha256(codec.dumps(program)).hexdigest() != digest or set(originals) != set(
        program["source_versions"]
    ):
        raise ValueError("narrative original binding mismatch")
    program["candidate_identity"] = digest
    ends = {key: 0 for key in originals}
    hashes = {key: sha256(text.encode()).hexdigest() for key, text in originals.items()}
    for fragment in fragments:
        for segment in fragment["source_segments"]:
            text = originals[segment["source_id"]]
            if (
                segment["version"] != program["source_versions"][segment["source_id"]]
                or segment["start"] != ends[segment["source_id"]]
                or not segment["start"] < segment["end"] <= len(text)
                or segment["source_sha256"] != hashes[segment["source_id"]]
            ):
                raise ValueError("narrative original coverage mismatch")
            ends[segment["source_id"]] = segment["end"]
    if ends != {key: len(text) for key, text in originals.items()}:
        raise ValueError("narrative source omitted")
    used = 0
    issues = list(OPEN_MECHANISMS)
    if program["comparisons"]:
        issues.remove("THEME_MECHANISM_COMPARISON_UNCOMPUTED")
        issues.append("THEME_INTERPRETATIONS_REMAIN_CONDITIONAL")

    if program["characters"]:
        issues.remove("CHARACTER_MECHANISM_COMPOSITION_UNCOMPUTED")
        issues.append("CHARACTER_INTERPRETATIONS_REMAIN_CONDITIONAL")

    if program["analogies"]:
        issues.remove("STRUCTURAL_MAPPING_UNCOMPUTED")
        issues.append("STRUCTURAL_READINGS_REMAIN_CONDITIONAL")

    def batch():
        nonlocal used
        if used >= max_batches:
            issues.append("NARRATIVE_BATCH_FRONTIER")
            return False
        used += 1
        return True

    def key(ref):
        return (ref["fragment"], ref["id"])

    def ident(ref, kind):
        return identity(ref["fragment"], kind, ref["id"])

    frames = {(f["fragment"], r["id"]): r for f in fragments for r in f["frames"]}
    events = {(f["fragment"], r["id"]): r for f in fragments for r in f["events"]}
    active = {
        identity(f["fragment"], "assumption", a)
        for f in fragments
        for a in f["active_assumptions"]
    }

    def environment(fragment, values):
        return tuple(sorted(identity(fragment, "assumption", a) for a in values))

    def frame_resolved(ref):
        seen = set()
        here = key(ref)
        while here in frames and here not in seen:
            seen.add(here)
            parent = frames[here]["parent"]
            if parent is None:
                return True
            here = key(parent)
        return False

    inactive = []
    points = []
    point_conditions = {}
    for event_key, event in events.items():
        required = set(environment(event_key[0], event["assumptions"]))
        if not frame_resolved(event["frame"]) or not required <= active:
            inactive.append(identity(event_key[0], "event", event_key[1]))
            continue
        point_conditions[identity(event_key[0], "event", event_key[1])] = required
        points.append(
            TimePoint(
                identity(event_key[0], "event", event_key[1]),
                "EVENT",
                ident(event["frame"], "frame"),
            )
        )
    points_by_id = {p.point_id: p for p in points}
    edges = []
    unusable = []
    for f in fragments:
        for row in f["orders"]:
            left, right = ident(row["left"], "event"), ident(row["right"], "event")
            if (
                left not in points_by_id
                or right not in points_by_id
                or points_by_id[left].scope_id != points_by_id[right].scope_id
            ):
                unusable.append(
                    dict(
                        fragment=f["fragment"],
                        id=row["id"],
                        reason="EVENT_OR_FRAME_UNRESOLVED",
                    )
                )
                continue
            assumptions = set(environment(f["fragment"], row["assumptions"]))
            for ref in (row["left"], row["right"]):
                assumptions.update(
                    environment(ref["fragment"], events[key(ref)]["assumptions"])
                )
            edges.append(
                TemporalConstraint(
                    identity(f["fragment"], "order", row["id"]),
                    left,
                    right,
                    strict=row["strict"],
                    assumptions=frozenset(assumptions),
                    evidence_roots=tuple(row["segment_ids"]),
                )
            )
    story = None
    if points and batch():
        story = TemporalForest(
            points, edges, active_assumptions=active, profile=PROFILE
        )

    def compare(forest, left, right):
        if forest is None:
            return dict(relation="FRONTIER_UNEXPLORED", checks={}, assumptions=())
        if left not in forest.points or right not in forest.points:
            return dict(relation="UNRESOLVED", checks={}, assumptions=())
        checks = {
            name: forest.check(a, b, strict=strict)
            for name, a, b, strict in (
                ("before", left, right, True),
                ("after", right, left, True),
                ("not_after", left, right, False),
                ("not_before", right, left, False),
            )
        }
        by_id = {edge.constraint_id: edge for edge in forest.constraints}
        conditions = point_conditions[left] | point_conditions[right]
        for name, a, b, strict in (
            ("before", left, right, True),
            ("after", right, left, True),
            ("not_after", left, right, False),
            ("not_before", right, left, False),
        ):
            result = checks[name]
            if result["status"] == "ENTAILED" and not forest.verify_witness(
                a, b, result["witness"], strict=strict
            ):
                raise ValueError("invalid temporal certificate")
            if result["status"] == "REFUTED" and not forest.verify_witness(
                b, a, result["witness"], strict=not strict
            ):
                raise ValueError("invalid negated temporal certificate")
            conditions.update(
                a for edge in result["witness"] for a in by_id[edge].assumptions
            )
        statuses = {row["status"] for row in checks.values()}
        if statuses & {
            "TEMPORAL_CONFLICT",
            "FRONTIER_UNEXPLORED",
            "HYPOTHESIS_BRANCHING_UNEXPLORED",
        }:
            relation = next(
                name
                for name in (
                    "TEMPORAL_CONFLICT",
                    "FRONTIER_UNEXPLORED",
                    "HYPOTHESIS_BRANCHING_UNEXPLORED",
                )
                if name in statuses
            )
        elif checks["before"]["status"] == "ENTAILED":
            relation = "BEFORE"
        elif checks["after"]["status"] == "ENTAILED":
            relation = "AFTER"
        elif (
            checks["not_after"]["status"]
            == checks["not_before"]["status"]
            == "ENTAILED"
        ):
            relation = "SAME_EVENT" if left == right else "SAME_TIME_IDENTITY_UNPROVED"
        else:
            relation = "UNRESOLVED"
        return dict(
            relation=relation, checks=checks, assumptions=tuple(sorted(conditions))
        )

    queries = []
    for f in fragments:
        for row in f["queries"]:
            left, right = ident(row["left"], "event"), ident(row["right"], "event")
            result = compare(story, left, right)
            # No budget is not the same thing as a missing, withdrawn event.
            if left not in points_by_id or right not in points_by_id:
                result = dict(
                    relation="EVENT_OR_FRAME_UNRESOLVED", checks={}, assumptions=()
                )
            queries.append(
                dict(
                    fragment=f["fragment"],
                    query_id=row["id"],
                    left=row["left"],
                    right=row["right"],
                    segment_ids=row["segment_ids"],
                    **result
                )
            )
            if result["relation"] not in (
                "BEFORE",
                "AFTER",
                "SAME_EVENT",
                "SAME_TIME_IDENTITY_UNPROVED",
            ):
                issues.append("STORY_" + result["relation"])
    # Each mention is a separate presentation occurrence. Host byte order never
    # creates a story edge and source-name order never creates chapter order.
    mentions = []
    for f in fragments:
        segments = {s["segment_id"]: s for s in f["source_segments"]}
        for row in f["mentions"]:
            segment = segments[row["anchor"]["segment_id"]]
            mentions.append(
                dict(
                    fragment=f["fragment"],
                    mention_id=row["id"],
                    event=row["event"],
                    frame=row["frame"],
                    source_id=segment["source_id"],
                    version=segment["version"],
                    anchor=row["anchor"],
                    attribution_resolved=key(row["event"]) in events
                    and frame_resolved(row["frame"]),
                )
            )
    discourse = []
    if mentions and batch():
        ordered = sorted(
            mentions,
            key=lambda row: (
                row["source_id"],
                row["anchor"]["start"],
                row["anchor"]["end"],
                row["fragment"],
                row["mention_id"],
            ),
        )
        for left, right in zip(ordered, ordered[1:]):
            relation = (
                "SOURCE_ORDER_UNRESOLVED"
                if left["source_id"] != right["source_id"]
                else (
                    "BEFORE"
                    if left["anchor"]["end"] <= right["anchor"]["start"]
                    else "OVERLAPPING_MENTIONS"
                )
            )
            discourse.append(
                dict(
                    left=[left["fragment"], left["mention_id"]],
                    right=[right["fragment"], right["mention_id"]],
                    relation=relation,
                    axis="NARRATIVE_ORDER",
                    basis="EXACT_ORIGINAL_OFFSETS",
                )
            )
    elif mentions:
        issues.append("DISCOURSE_FRONTIER")
    motif_map = {
        identity(f["fragment"], "motif", row["id"]): row["literal"]
        for f in fragments
        for row in f["motifs"]
    }
    passages = [
        dict(id=source_id, text=text) for source_id, text in sorted(originals.items())
    ]
    form = measure_form(passages, motif_map, MAX_FORM_WORK if batch() else 0)
    issues.extend(form["frontier"])
    variants = []
    for f in fragments:
        segments = {s["segment_id"]: s for s in f["source_segments"]}
        for row in f["variants"]:
            if row["kind"] == "REORDER":
                from hcl.operators.narrative_variants import (
                    reorder_text,
                    reorder_discourse,
                    MAX_REORDER_WORK,
                )

                source_id = segments[row["parts"][0]["segment_id"]]["source_id"]
                text = originals[source_id]
                changed, offsets = reorder_text(text, row["parts"], row["order"])
                value = measure_form(
                    [dict(id=source_id, text=changed)],
                    motif_map,
                    MAX_FORM_WORK if batch() else 0,
                )
                contrast = reorder_discourse(
                    mentions, source_id, offsets, MAX_REORDER_WORK if batch() else 0
                )
                variants.append(
                    dict(
                        fragment=f["fragment"],
                        id=row["id"],
                        hypothetical=True,
                        kind="REORDER",
                        source_id=source_id,
                        original_parts=row["parts"],
                        offset_map=offsets,
                        original_sha256=sha256(text.encode()).hexdigest(),
                        variant_sha256=sha256(changed.encode()).hexdigest(),
                        form=value,
                        discourse_contrast=contrast,
                        scope="GENERATED_VARIANT_NOT_SOURCE_EVIDENCE",
                        semantic_effect="NOT_ESTABLISHED",
                    )
                )
                issues.extend(value["frontier"])
                issues.extend(contrast["frontier"])
                if contrast["unresolved_mentions"]:
                    issues.append("REORDER_MENTION_BOUNDARY_UNRESOLVED")
                continue
            anchor = row["anchor"]
            source_id = segments[anchor["segment_id"]]["source_id"]
            text = originals[source_id]
            changed = (
                text[: anchor["start"]] + row["replacement"] + text[anchor["end"] :]
            )
            value = measure_form(
                [dict(id=source_id, text=changed)],
                motif_map,
                MAX_FORM_WORK if batch() else 0,
            )
            variants.append(
                dict(
                    fragment=f["fragment"],
                    id=row["id"],
                    hypothetical=True,
                    kind=row["kind"],
                    source_id=source_id,
                    original_anchor=anchor,
                    replacement=row["replacement"],
                    original_sha256=sha256(text.encode()).hexdigest(),
                    variant_sha256=sha256(changed.encode()).hexdigest(),
                    form=value,
                    scope="GENERATED_VARIANT_NOT_SOURCE_EVIDENCE",
                    semantic_effect="NOT_ESTABLISHED",
                )
            )
            issues.extend(value["frontier"])
    if inactive:
        issues.append("EVENT_ASSUMPTION_OR_FRAME_UNRESOLVED")
    if unusable:
        issues.append("CROSS_FRAME_OR_EVENT_ORDER_UNRESOLVED")
    if program["unresolved_references"]:
        issues.append("CROSS_FRAGMENT_REFERENCE_UNRESOLVED")
    unmodeled = tuple(sorted({s for f in fragments for s in f["unmodeled_segments"]}))
    if unmodeled:
        issues.append("NARRATIVE_UNMODELED_SOURCE")
    coverage = dict(
        read_fragments=len(fragments),
        read_regions=tuple(
            {k: s[k] for k in ("source_id", "version", "start", "end", "segment_id")}
            for f in fragments
            for s in f["source_segments"]
        ),
        supplied_scope_read=True,
        unmodeled_segments=unmodeled,
        unresolved_references=program["unresolved_references"],
        semantic_completeness="NOT_ESTABLISHED",
        external_chapters="OUTSIDE_EXPLICIT_SOURCE_SCOPE",
    )
    return dict(
        schema=VERSION,
        batch_evaluations=used,
        story_queries=queries,
        story_constraints=[
            dict(asdict(e), assumptions=sorted(e.assumptions)) for e in edges
        ],
        inactive_events=inactive,
        unusable_orders=unusable,
        frames=[
            dict(fragment=f["fragment"], **row)
            for f in fragments
            for row in f["frames"]
        ],
        mentions=mentions,
        discourse_edges=discourse,
        form=form,
        variants=variants,
        coverage=coverage,
        assumption_environments=tuple(sorted(active)),
        issues=tuple(sorted(set(issues))),
        semantic_certified=False,
        candidate_completeness="NOT_ESTABLISHED",
        scope="CONDITIONAL_SOURCE_BOUND_NARRATIVE_NOT_AUTHOR_INTENT_OR_AESTHETIC_VERDICT",
    )


class LiteratureOperator:
    def run(self, snapshot, issue, allowance, program):
        originals = {
            key: source.text for key, source in snapshot.immutable_views.items()
        }
        computed = compute_narrative(
            program, originals, allowance.max_local_evaluations
        )
        from hcl.operators.discovery_model import DiscoveryModelOperator
        from hcl.semantics.segments import SourceSegment

        segments = tuple(
            SourceSegment(
                **row, text=originals[row["source_id"]][row["start"] : row["end"]]
            )
            for fragment in program["fragments"]
            for row in fragment["source_segments"]
        )
        by_id = {s.segment_id: s for s in segments}
        comparisons = []
        used = computed["batch_evaluations"]
        comparison_issues = set()
        for comparison in program["comparisons"]:
            scopes = {
                key: tuple(by_id[s] for s in ids)
                for key, ids in comparison["context_scope_ids"].items()
            }
            operation = DiscoveryModelOperator().run(
                snapshot,
                Issue(
                    "narrative-comparison:"
                    + sha256(
                        codec.dumps([issue.issue_id, comparison["id"]])
                    ).hexdigest()
                ),
                replace(
                    allowance,
                    max_local_evaluations=allowance.max_local_evaluations - used,
                ),
                comparison["program"],
                segments,
                context_scopes=scopes,
            )
            actual = operation.candidate_delta.new_inferences[0]
            used += operation.resource_usage["local_evaluations"]
            comparison_issues.update(operation.issues)
            comparisons.append(
                dict(
                    id=comparison["id"],
                    input_identity=sha256(codec.dumps(thaw(comparison))).hexdigest(),
                    result_id=actual.result_id,
                    kind=actual.kind,
                    values=thaw(actual.values),
                    assumption_environments=actual.assumption_environments,
                    source_versions=dict(operation.read_set),
                    issues=operation.issues,
                    resource_usage=dict(operation.resource_usage),
                )
            )
        from hcl.operators.concepts import ConceptOperator

        analogies = []
        for analogy in program["analogies"]:
            operation = ConceptOperator().run(
                snapshot,
                Issue(analogy["id"]),
                replace(
                    allowance,
                    max_local_evaluations=allowance.max_local_evaluations - used,
                ),
                analogy["program"],
            )
            actual = operation.candidate_delta.new_inferences[0]
            used += operation.resource_usage["local_evaluations"]
            comparison_issues.update(operation.issues)
            analogies.append(
                dict(
                    id=analogy["id"],
                    fragment=analogy["fragment"],
                    local_id=analogy["local_id"],
                    input_identity=sha256(codec.dumps(thaw(analogy))).hexdigest(),
                    result_id=actual.result_id,
                    kind=actual.kind,
                    values=thaw(actual.values),
                    assumption_environments=actual.assumption_environments,
                    counterevidence_ids=actual.counterevidence_ids,
                    source_versions=dict(operation.read_set),
                    issues=operation.issues,
                    resource_usage=dict(operation.resource_usage),
                )
            )
        from hcl.operators.narrative_characters import execute_characters

        characters, character_work = execute_characters(
            snapshot,
            replace(
                allowance, max_local_evaluations=allowance.max_local_evaluations - used
            ),
            program,
        )
        used += character_work
        comparison_issues.update(
            issue for record in characters for issue in record["issues"]
        )
        values = dict(
            computed,
            comparisons=comparisons,
            analogies=analogies,
            characters=characters,
            rule_version=snapshot.rule_version,
            comparison_issues=tuple(sorted(comparison_issues)),
            local_evaluations=used,
            inputs=dict(
                issue_id=issue.issue_id,
                program=thaw(program),
                originals=originals,
                max_batches=allowance.max_local_evaluations,
            ),
            source_versions=dict(snapshot.source_versions),
        )
        result = InferenceResult(
            "narrative-result:"
            + sha256(codec.dumps([issue.issue_id, values])).hexdigest(),
            KIND,
            values,
            tuple(
                sorted(
                    set(computed["assumption_environments"])
                    | {
                        a
                        for c in (*comparisons, *analogies, *characters)
                        for a in c["assumption_environments"]
                    }
                )
            ),
            tuple(snapshot.source_versions),
            tuple(
                sorted(
                    {
                        e
                        for a in (*analogies, *characters)
                        for e in a["counterevidence_ids"]
                    }
                )
            ),
            snapshot.rule_version,
            "CONDITIONAL_NARRATIVE",
        )
        return OpResult(
            "literature.execute",
            VERSION,
            snapshot.source_versions,
            ("append_inference",),
            (result.result_id,),
            tuple(sorted(set(computed["issues"]) | comparison_issues)),
            {"local_evaluations": used},
            (),
            Delta(
                snapshot.session_id,
                snapshot.principal,
                snapshot.revision,
                snapshot.access_epoch,
                snapshot.rule_version,
                snapshot.source_versions,
                (result,),
            ),
        )


def verify_narrative(values):
    inputs = values["inputs"]
    if type(inputs["issue_id"]) is not str or not inputs["issue_id"]:
        raise ValueError("narrative issue identity missing")
    if codec.dumps(freeze(values["source_versions"])) != codec.dumps(
        freeze(inputs["program"]["source_versions"])
    ):
        raise ValueError("narrative source version certificate changed")
    if values["rule_version"] != inputs["program"]["rule_version"]:
        raise ValueError("narrative rule certificate changed")
    expected = compute_narrative(
        inputs["program"], inputs["originals"], inputs["max_batches"]
    )
    if any(
        codec.dumps(freeze(values[key])) != codec.dumps(freeze(value))
        for key, value in expected.items()
    ):
        raise ValueError("narrative computation mismatch")
    from hcl.operators.discovery_model import verify_discovery, delivery_values
    from hcl.operators.abduction import (
        context_identity,
        program_hash,
        identity as discovery_identity,
    )

    comparisons = {row["id"]: row for row in inputs["program"]["comparisons"]}
    actual = values["comparisons"]
    if len(actual) != len(comparisons) or len({r["id"] for r in actual}) != len(actual):
        raise ValueError("narrative comparison coverage mismatch")
    used = expected["batch_evaluations"]
    issues = set()
    for record in actual:
        source = comparisons[record["id"]]
        program = source["program"]
        value = record["values"]
        if record["input_identity"] != sha256(codec.dumps(thaw(source))).hexdigest():
            raise ValueError("narrative comparison input changed")
        comparison_issue = (
            "narrative-comparison:"
            + sha256(codec.dumps([inputs["issue_id"], source["id"]])).hexdigest()
        )
        expected_result_id = "discovery-result:" + discovery_identity(
            [comparison_issue, dict(values["source_versions"]), thaw(value)]
        )
        if record["result_id"] != expected_result_id:
            raise ValueError("narrative comparison result identity changed")
        if (
            record["kind"] != "CONDITIONAL_MECHANISM_DISCOVERY"
            or codec.dumps(freeze(record["source_versions"]))
            != codec.dumps(freeze(values["source_versions"]))
            or codec.dumps(freeze(value["source_versions"]))
            != codec.dumps(freeze(values["source_versions"]))
        ):
            raise ValueError("narrative comparison source changed")
        expected_contexts = {
            c["id"]: context_identity(thaw(c)) for c in program["contexts"]
        }
        expected_probes = {
            p["id"]: dict(
                context_hash=context_identity(thaw(p["context"])),
                query_id=p["query_id"],
            )
            for p in program["probes"]
        }
        for key, wanted in (
            ("context_bindings", expected_contexts),
            ("probe_bindings", expected_probes),
            ("observations", program["observations"]),
            ("grammar", program["grammar"]),
            ("search", program["search"]),
            ("source_bindings", program["source_bindings"]),
        ):
            if codec.dumps(freeze(value[key])) != codec.dumps(freeze(wanted)):
                raise ValueError("narrative comparison contract changed")
        if not set(value["initial_program_hashes"]) <= {
            program_hash(thaw(p)) for p in program["programs"]
        }:
            raise ValueError("narrative comparison seeds changed")
        verify_discovery(value)
        cost = record["resource_usage"]["local_evaluations"]
        if type(cost) is not int or cost != value["local_evaluations"] or cost < 0:
            raise ValueError("narrative comparison work mismatch")
        used += cost
        issues.update(record["issues"])
        wanted_issues = set(value["frontier"]) | set(
            delivery_values(value)["domain_issues"]
        )
        if value["unmodeled_segments"]:
            wanted_issues.add("UNMODELED_DISCOVERY_SOURCE")
        if any(c["profile"]["unmodeled"] for c in value["prediction_matrix"].values()):
            wanted_issues.add("UNCOMPUTED_OR_UNMODELED_PREDICTION")
        if tuple(sorted(wanted_issues)) != tuple(record["issues"]):
            raise ValueError("narrative comparison limitations missing")
        conditions = {
            a
            for column in value["prediction_matrix"].values()
            for result in column["actual_results"]
            for a in result["assumption_environments"]
        }
        conditions.update(
            a
            for probe in value["distinguishing_observations"]
            for evaluation in probe["evaluations"].values()
            for result in evaluation["actual_results"]
            for a in result["assumption_environments"]
        )
        if tuple(sorted(conditions)) != tuple(record["assumption_environments"]):
            raise ValueError("narrative comparison conditions missing")
    from hcl.operators.concepts import verify_concepts, concept_result_id

    analogies = {row["id"]: row for row in inputs["program"]["analogies"]}
    if len(values["analogies"]) != len(analogies) or len(
        {r["id"] for r in values["analogies"]}
    ) != len(analogies):
        raise ValueError("narrative analogy coverage changed")
    for record in values["analogies"]:
        source = analogies[record["id"]]
        value = record["values"]
        if (
            record["kind"] != "CONDITIONAL_STRUCTURAL_MAPPINGS"
            or type(record["fragment"]) is not int
            or record["fragment"] != source["fragment"]
            or record["local_id"] != source["local_id"]
            or record["result_id"] != concept_result_id(source["id"], value)
            or codec.dumps(freeze(record["source_versions"]))
            != codec.dumps(freeze(values["source_versions"]))
            or record["input_identity"] != sha256(codec.dumps(thaw(source))).hexdigest()
            or codec.dumps(freeze(value["inputs"]["program"]))
            != codec.dumps(freeze(source["program"]))
            or value["inputs"]["max_work"] != inputs["max_batches"] - used
        ):
            raise ValueError("narrative analogy input or allowance changed")
        expected_analogy = verify_concepts(value)
        if (
            tuple(record["issues"]) != tuple(expected_analogy["issues"])
            or tuple(record["assumption_environments"])
            != tuple(expected_analogy["assumption_environments"])
            or tuple(record["counterevidence_ids"])
            != tuple(expected_analogy["counterevidence_ids"])
            or codec.dumps(freeze(record["resource_usage"]))
            != codec.dumps(freeze(dict(local_evaluations=value["local_evaluations"])))
        ):
            raise ValueError("narrative analogy evidence or limitations changed")
        used += value["local_evaluations"]
        issues.update(record["issues"])
    from hcl.operators.narrative_characters import verify_characters

    used += verify_characters(
        values["characters"], inputs["program"], inputs["max_batches"] - used
    )
    issues.update(
        issue for record in values["characters"] for issue in record["issues"]
    )
    if (
        type(values["local_evaluations"]) is not int
        or used != values["local_evaluations"]
        or used > inputs["max_batches"]
        or tuple(sorted(issues)) != tuple(values["comparison_issues"])
    ):
        raise ValueError("narrative comparison allowance mismatch")
    return expected

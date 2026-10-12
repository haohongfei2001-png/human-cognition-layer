"""Actual conditional mappings/anti-unification and a narrative consumer.

The offline port proposes explicit experimental structures. It supplies no
correspondence, verdict, pattern, score or evidence of model comprehension.
"""

import argparse
from dataclasses import replace
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import tempfile
import hcl
from hcl import HCL, ExecutionBudget, ExecutionIssue
from hcl.kernel.types import Issue, Principal, TaskRequest, thaw
from hcl.memory.store import StateStore
from hcl.models.gateway import ModelGateway, OfflineModelPort
from hcl.semantics.segments import segment_snapshot

BASE = "The canal feeds the mill. The mill feeds the town. The canal feeds the town. Repeating a role is represented by the declared pairs (canal,canal) and (mill,mill)."
TARGET = "The spring feeds the field. The field feeds the orchard. The spring does not feed the orchard. The mixed pair (spring,field) is a negative example; a repeated pair may also be challenged."


def propose(snapshot, question, mode="refuted"):
    anchors = {
        name: [
            s.segment_id
            for s in segment_snapshot(snapshot, question)
            if s.kind == "SOURCE" and s.source_id == name
        ]
        for name in ("base", "target")
    }

    def domain(names, side):
        refs = anchors[side]
        entities = [dict(id=name, type="role", segment_ids=refs) for name in names]
        predicates = [
            dict(
                id="feeds",
                kind="RELATION",
                arguments=["ENTITY:role", "ENTITY:role"],
                segment_ids=refs,
            )
        ]
        facts = [
            dict(
                id="link-" + str(i),
                predicate="feeds",
                arguments=[
                    dict(kind="ENTITY", id=names[a]),
                    dict(kind="ENTITY", id=names[b]),
                ],
                negated=side == "target" and i == 2 and mode != "supported",
                assumptions=[],
                segment_ids=refs,
            )
            for i, (a, b) in enumerate(((0, 1), (1, 2), (0, 2)))
        ]
        return dict(entities=entities, predicates=predicates, facts=facts)

    model = dict(
        id="flow",
        assumptions=["declared-relational-reading"],
        active_assumptions=(
            [] if mode == "withdrawn" else ["declared-relational-reading"]
        ),
        base=domain(("canal", "mill", "town"), "base"),
        target=domain(("spring", "field", "orchard"), "target"),
        compatibilities=[
            dict(
                base="feeds",
                target="feeds",
                assumptions=["declared-relational-reading"],
                segment_ids=anchors["base"] + anchors["target"],
            )
        ],
        max_mappings=16,
        unmodeled_segments=[],
    )

    def term(symbol, args=()):
        return dict(kind="TERM", sort="Role", symbol=symbol, arguments=list(args))

    def example(name, a, b, side):
        return dict(
            id=name,
            term=term("pair", (term(a), term(b))),
            assumptions=["example-reading"],
            segment_ids=anchors[side],
        )

    induction = dict(
        id="repetition",
        concept_key="role-repetition",
        purpose="Compare declared repeated and mixed roles.",
        assumptions=["example-reading"],
        active_assumptions=["example-reading"],
        positive=[
            example("canal", "canal", "canal", "base"),
            example("mill", "mill", "mill", "base"),
        ],
        negative=[example("mixed", "spring", "field", "target")],
        unmodeled_segments=[],
    )
    if mode == "induction-counterexample":
        induction["negative"].append(
            example("boundary", "orchard", "orchard", "target")
        )
    return dict(
        schema="hcl-structural-candidates-1", models=[model], inductions=[induction]
    )


def witness():
    owner = Principal("synthetic-witness", "owner")
    rows = []
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "state.sqlite"
        store = StateStore.sqlite(path, revision=True)
        store.create_session("s", owner, {"bob"})
        handles = (
            store.put_source("s", owner, "base", BASE),
            store.put_source("s", owner, "target", TARGET),
        )
        try:
            for mode in (
                "refuted",
                "supported",
                "withdrawn",
                "induction-counterexample",
                "budget",
                "narrative",
            ):
                request = TaskRequest(
                    mode,
                    "Compare these declared interpretations and preserve counterexamples.",
                    handles,
                    "s",
                    owner,
                    budget=ExecutionBudget(
                        max_mock_calls=1,
                        max_feedback=0,
                        max_local_evaluations=2 if mode == "budget" else 100000,
                        max_request_bytes=1048576,
                        max_context_tokens=1048576,
                        max_output_bytes=1048576,
                        max_total_output_bytes=8000000,
                        max_visible_output_tokens=1048576,
                    ),
                    issue=ExecutionIssue(
                        "root",
                        goals=(
                            Issue(
                                mode,
                                (
                                    "literature.analyze"
                                    if mode == "narrative"
                                    else "analogy.compare"
                                ),
                            ),
                        ),
                    ),
                )
                snapshot = store.snapshot("s", owner, handles)
                candidate = propose(snapshot, request.question, mode)
                if mode == "narrative":
                    candidate = dict(
                        schema="hcl-literature-fragment-1",
                        assumptions=[],
                        active_assumptions=[],
                        frames=[],
                        events=[],
                        mentions=[],
                        orders=[],
                        queries=[],
                        motifs=[],
                        variants=[],
                        comparisons=[],
                        analogies=[dict(id="structural-reading", task=candidate)],
                        unmodeled_segments=[],
                    )
                port = OfflineModelPort(json.dumps(candidate))
                result = HCL(
                    store, principal=owner, gateway=ModelGateway(store, port)
                ).run_sync(request)
                assert result.status == (
                    "COMPLETED" if mode in ("refuted", "supported") else "PARTIAL"
                ), (mode, result.status, result.diagnostics)
                actual = next(
                    r
                    for r in store.inferences("s", owner)
                    if r.result_id in result.execution_receipt["result_ids"]
                )
                values = (
                    actual.values["analogies"][0]["values"]
                    if mode == "narrative"
                    else actual.values
                )
                mappings = values["models"][0]["actual"]["mappings"]
                if mode in ("refuted", "supported", "narrative"):
                    mapping = next(
                        r
                        for r in mappings
                        if dict(r["entities"])
                        == dict(canal="spring", mill="field", town="orchard")
                    )
                    prediction = next(
                        p for p in mapping["predictions"] if p["base_fact"] == "link-2"
                    )
                    assert prediction["status"] == (
                        "TARGET_SUPPORTED" if mode == "supported" else "TARGET_REFUTED"
                    )
                    assert (
                        prediction["assumption_environments"]
                        and prediction["evidence_segment_ids"]
                    )
                if mode == "induction-counterexample":
                    assert values["inductions"][0]["actual"]["counterexample_ids"] == (
                        "boundary",
                    )
                if mode == "withdrawn":
                    assert not mappings
                replay_port = OfflineModelPort("NO_NEW_SEND")
                replay = HCL(
                    store, principal=owner, gateway=ModelGateway(store, replay_port)
                ).run_sync(request)
                assert replay.answer == result.answer and replay_port.attempts == 0
                rows.append(
                    dict(
                        case=mode,
                        status=result.status,
                        usage=thaw(result.usage),
                        actual=thaw(values),
                        answer=result.answer,
                        claim_fields=[
                            field.field
                            for claim in result.claim_records
                            for field in claim.used_result_fields
                        ],
                        unresolved=thaw(result.unresolved_issues),
                        offline_attempts=port.attempts,
                        replay_new_attempts=0,
                    )
                )
            store.set_readers("s", owner, "target", {"bob"})
            blocked = HCL(store, principal=owner).run_sync(request)
            assert (
                blocked.status == "DENIED"
                and not blocked.answer
                and not blocked.claim_records
            )
            rows.append(
                dict(
                    case="cached-narrative-current-acl",
                    status=blocked.status,
                    answer_absent=True,
                )
            )
        finally:
            store.close()
    root = Path(hcl.__file__).resolve().parents[1]
    return dict(
        schema="hcl-unified-structural-concepts-witness-1",
        checked_commit=subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=root, text=True
        ).strip(),
        runtime_hashes={
            str(p.relative_to(root)): sha256(p.read_bytes()).hexdigest()
            for p in sorted((root / "hcl").rglob("*.py"))
        },
        rows=rows,
        provider_calls=0,
        provider_spend_usd=0,
        sealed_content_reads=0,
        evidence_scope="BOUNDED_SOURCE_QUALIFIED_RELATIONAL_MAPPING_TERM_INDUCTION_AND_NARRATIVE_CONSUMPTION",
        not_established=[
            "OPEN_EXTRACTION_ACCURACY",
            "OPEN_METAPHOR_OR_IRONY_COMPREHENSION",
            "UNRESTRICTED_INDUCTION",
            "FULL_CONCEPT_REVISION_PROPAGATION",
            "FULL_M11",
            "FULL_M12",
            "FULL_T13",
            "FULL_T14",
            "FULL_T15",
            "FULL_T16",
            "FULL_T27",
            "FULL_S4",
            "LIVE_EFFECT",
        ],
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    args.output.write_text(
        json.dumps(witness(), ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    )

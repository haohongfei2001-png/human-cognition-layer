"""Actual grounded/preferred/sensitivity witness under injected source readings."""

import argparse
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import tempfile

from hcl import HCL, ExecutionBudget, ExecutionIssue
from hcl.kernel.types import Principal, TaskRequest, Issue, thaw
from hcl.memory.store import StateStore
from hcl.models.gateway import ModelGateway, OfflineModelPort
from hcl.semantics.segments import segment_snapshot


def propose(snapshot, question, mode):
    segments = segment_snapshot(snapshot, question)
    source = [s.segment_id for s in segments if s.kind == "SOURCE"]
    query = [s.segment_id for s in segments if s.kind == "QUESTION"]
    literals = [
        dict(id=key, atom=atom, negative=negative, kind=kind, segment_ids=source)
        for key, atom, negative, kind in [
            ("witness", "witness", False, "CLAIM"),
            ("event", "event", False, "CLAIM"),
            ("not-event", "event", True, "CLAIM"),
            ("meeting", "meeting", False, "CLAIM"),
            ("undercut", "inference", True, "RULE_APPLICABLE"),
        ]
    ]
    premises = [
        dict(
            id=key,
            literal=literal,
            ordinary=ordinary,
            assumptions=[],
            segment_ids=source,
        )
        for key, literal, ordinary in [
            ("report", "witness", False),
            ("denial", "not-event", True),
            ("meeting-report", "meeting", False),
        ]
    ]
    if mode == "undercut":
        premises.append(
            dict(
                id="undercutter",
                literal="undercut",
                ordinary=False,
                assumptions=[],
                segment_ids=source,
            )
        )
    model = dict(
        id="dialogue",
        source_id="story",
        frame_kind="SOURCE_DISCOURSE",
        assumptions=["source-reconstruction"],
        active_assumptions=["source-reconstruction"]
        + ([] if mode == "withdrawn" else ["witness-default"]),
        unmodeled_segments=[],
        literals=literals,
        premises=premises,
        rules=[
            dict(
                id="inference",
                premises=["witness"],
                conclusion="event",
                strict=False,
                assumptions=["witness-default"],
                segment_ids=source,
            )
        ],
        priorities=(
            []
            if mode == "equal"
            else [
                dict(
                    better="denial" if mode == "reversed" else "inference",
                    worse="inference" if mode == "reversed" else "denial",
                    segment_ids=source,
                )
            ]
        ),
        queries=[
            dict(
                id="event",
                literal="event",
                preferred=True,
                critical_candidates=["report", "inference", "denial"],
                segment_ids=query,
            ),
            dict(
                id="meeting",
                literal="meeting",
                preferred=False,
                critical_candidates=[],
                segment_ids=query,
            ),
        ],
    )
    return dict(schema="hcl-argument-candidates-1", models=[model])


def witness():
    owner = Principal("synthetic", "owner")
    rows = []
    with tempfile.TemporaryDirectory() as directory:
        for mode in ("supported", "reversed", "equal", "undercut", "withdrawn"):
            store = StateStore.sqlite(
                Path(directory) / (mode + ".sqlite"), revision=True
            )
            try:
                store.create_session("witness", owner)
                source = "A cites a witness and argues that reliable testimony normally supports the event. B denies the event. Both agreed to meet on Tuesday."
                if mode == "undercut":
                    source += (
                        " New evidence says this inference rule is inapplicable here."
                    )
                handle = store.put_source("witness", owner, "story", source)
                request = TaskRequest(
                    mode,
                    "Which reconstructed argument is accepted, and which premise changes matter?",
                    (handle,),
                    "witness",
                    owner,
                    budget=ExecutionBudget(
                        max_mock_calls=2,
                        max_output_bytes=65536,
                        max_visible_output_tokens=65536,
                        max_total_output_bytes=524288,
                    ),
                    issue=ExecutionIssue(
                        "root", goals=(Issue("debate", "argument.evaluate"),)
                    ),
                )
                candidate = propose(
                    store.snapshot("witness", owner, (handle,)), request.question, mode
                )
                port = OfflineModelPort(json.dumps(candidate))
                result = HCL(
                    store, principal=owner, gateway=ModelGateway(store, port)
                ).run_sync(request)
                assert result.status == "COMPLETED", result.diagnostics
                inference = next(
                    r
                    for r in store.inferences("witness", owner)
                    if r.result_id in result.execution_receipt["result_ids"]
                )
                assert port.attempts == 1
                rows.append(
                    dict(
                        case=mode,
                        source=source,
                        status=result.status,
                        answer=result.answer,
                        usage=thaw(result.usage),
                        actual_result=dict(
                            result_id=inference.result_id, values=thaw(inference.values)
                        ),
                        fixture_attempts=port.attempts,
                        consumed=[
                            dict(
                                result_id=f.result_id,
                                field=f.field,
                                path=list(getattr(f, "path", ())),
                                selection=list(getattr(f, "selection", ())),
                                value=thaw(f.value),
                            )
                            for c in result.claim_records
                            for f in c.used_result_fields
                        ],
                    )
                )
            finally:
                store.close()
    result = {row["case"]: row["actual_result"]["values"]["models"][0] for row in rows}
    assert result["supported"]["queries"][0]["positive_accepted"] is True
    assert result["supported"]["queries"][0]["critical"]["minimum_cardinality"] == 1
    for name in ("reversed", "undercut", "withdrawn"):
        assert result[name]["queries"][0]["positive_accepted"] is False
        assert result[name]["queries"][0]["opposed_accepted"] is True
    assert result["equal"]["queries"][0]["positive_accepted"] is False
    assert result["equal"]["queries"][0]["opposed_accepted"] is False
    assert len(result["equal"]["queries"][0]["preferred"]["preferred"]) == 2
    assert all(row["queries"][1]["positive_accepted"] for row in result.values())
    root = Path(__file__).resolve().parents[1]
    return dict(
        schema="hcl-unified-s4-argument-witness-1",
        checked_commit=subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=root, text=True
        ).strip(),
        runtime_hashes={
            str(p.relative_to(root)): sha256(p.read_bytes()).hexdigest()
            for p in sorted((root / "hcl").rglob("*.py"))
        },
        rows=rows,
        provider_calls=0,
        provider_spend_usd="0",
        sealed_content_reads=0,
        evidence_scope="ACTUAL_FINITE_STRUCTURED_ARGUMENT_ACCEPTANCE_UNDER_INJECTED_RECONSTRUCTIONS",
        not_established=[
            "open reconstruction or premise truth",
            "complete M13 reflective equilibrium and concept feedback",
            "M10/M11/M12/M14",
            "full S3/S4 or acceptance families",
            "live functionality",
            "effectiveness",
        ],
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.write_text(json.dumps(witness(), ensure_ascii=False, indent=2) + "\n")

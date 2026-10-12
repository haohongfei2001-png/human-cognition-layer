"""Actual unknown commitment facts must not manufacture a relationship posterior."""

import argparse
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import tempfile
from hcl import HCL, ExecutionBudget, ExecutionIssue
from hcl.kernel.types import Issue, Principal, TaskRequest, thaw
from hcl.memory.store import StateStore
from hcl.models.gateway import ModelGateway, OfflineModelPort
from scripts.witness_unified_relationship import (
    propose as base_proposal,
    SOURCE as BASE_SOURCE,
)

SOURCE = (
    BASE_SOURCE
    + " Additional conditional variants explicitly leave completion or earlier activation unknown; absence of proof is not a negative observation."
)


def propose(snapshot, question, mode):
    candidate = base_proposal(snapshot, question, "relationship")
    m = candidate["models"][0]
    mental = m["mental"]
    refs = mental["variables"][0]["segment_ids"]
    mental["variables"].append(
        dict(
            id="done",
            initial=(
                False
                if mode in ("not-fulfilled", "latched-unknown")
                else True if mode == "fulfilled" else None
            ),
            observed_by=["a", "b"],
            segment_ids=refs,
        )
    )
    terms = m["interaction"]["commitments"][0]
    terms.update(condition=True, outcome=dict(op="atom", name="done"), deadline=5)
    relation = m["relationships"][0]
    relation["updates"] = relation["updates"][:1]
    relation["updates"][0]["commitment_status"] = "ACTIVE"
    if mode == "latched-unknown":
        mental["variables"].append(
            dict(
                id="activation", initial=None, observed_by=["a", "b"], segment_ids=refs
            )
        )
        terms["condition"] = dict(op="atom", name="activation")
        next(e for e in mental["events"] if e["id"] == "change-1")["effects"][
            "activation"
        ] = False
    return candidate


def witness():
    rows = []
    owner = Principal("synthetic", "reader")
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "state.sqlite"
        store = StateStore.sqlite(path, revision=True)
        store.create_session("s", owner)
        handle = store.put_source("s", owner, "records", SOURCE)
        original = store.snapshot("s", owner, (handle,))
        try:
            for mode in (
                "not-fulfilled",
                "fulfilled",
                "unknown",
                "latched-unknown",
                "budget",
            ):
                request = TaskRequest(
                    mode,
                    "Which relationship updates are justified by the actual qualified commitment history?",
                    (handle,),
                    "s",
                    owner,
                    budget=ExecutionBudget(
                        max_mock_calls=1,
                        max_feedback=0,
                        max_local_evaluations=1 if mode == "budget" else 16000,
                        max_request_bytes=1048576,
                        max_context_tokens=1048576,
                        max_output_bytes=4194304,
                        max_total_output_bytes=16777216,
                        max_visible_output_tokens=1048576,
                    ),
                    issue=ExecutionIssue(
                        "root", goals=(Issue(mode, "relationship.evaluate"),)
                    ),
                )
                candidate = propose(
                    store.snapshot("s", owner, (handle,)), request.question, mode
                )
                port = OfflineModelPort(json.dumps(candidate))
                result = HCL(
                    store, principal=owner, gateway=ModelGateway(store, port)
                ).run_sync(request)
                assert result.status == (
                    "COMPLETED" if mode in ("not-fulfilled", "fulfilled") else "PARTIAL"
                ), (mode, result.diagnostics)
                actual = next(
                    r
                    for r in store.inferences("s", owner)
                    if r.result_id in result.execution_receipt["result_ids"]
                )
                if mode != "budget":
                    relation = actual.values["models"][0]["relationships"][0]
                    factor = relation["history"][0]
                    if mode == "not-fulfilled":
                        assert (
                            factor["qualification"]
                            == "ESTABLISHED_IN_CONDITIONAL_MODEL"
                            and factor["weights"]["supportive"] == "1/4"
                        )
                    elif mode == "fulfilled":
                        assert (
                            factor["qualification"] == "INAPPLICABLE"
                            and factor["weights"]["supportive"] == "1/2"
                        )
                    else:
                        proof = factor["commitment_qualification"]
                        assert (
                            factor["qualification"] == "UNRESOLVED"
                            and factor["weights"]["supportive"] == "1/2"
                        )
                        assert (
                            proof["possible_values"] == (False, True)
                            and proof["state_completion_complete"]
                        )
                        assert "bookkeeping prefix" in result.answer
                assert (
                    port.attempts == 1
                    and actual.values["local_evaluations"]
                    <= request.budget.max_local_evaluations
                )
                assert (
                    store.snapshot("s", owner, (handle,)).immutable_views
                    == original.immutable_views
                )
                selected = [
                    f
                    for c in result.claim_records
                    for f in c.used_result_fields
                    if f.result_id == actual.result_id and f.field == "models"
                ]
                assert selected and selected[0].value == actual.values["models"]
                store.close()
                store = StateStore.sqlite(path, revision=True)
                port = OfflineModelPort("NO_RESEND")
                replay = HCL(
                    store, principal=owner, gateway=ModelGateway(store, port)
                ).run_sync(request)
                assert port.attempts == 0 and (
                    replay.answer,
                    replay.claim_records,
                    replay.usage,
                ) == (result.answer, result.claim_records, result.usage)
                rows.append(
                    dict(
                        case=mode,
                        status=result.status,
                        actual=thaw(actual.values),
                        answer=result.answer,
                        usage=thaw(result.usage),
                        offline_attempts=1,
                        replay_attempts=0,
                        complete_models_consumed=True,
                    )
                )
            store.set_readers("s", owner, "records", {"other"})
            denied = HCL(store, principal=owner).run_sync(request)
            assert (
                denied.status == "DENIED"
                and not denied.answer
                and not denied.claim_records
            )
            rows.append(
                dict(
                    case="revoked-replay",
                    status=denied.status,
                    usage=thaw(denied.usage),
                )
            )
        finally:
            store.close()
    root = Path(__file__).resolve().parents[1]
    return dict(
        schema="hcl-unified-relationship-qualification-witness-1",
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
        evidence_scope="ACTUAL_M07_PREFIX_QUALIFICATION_BEFORE_M09_LIKELIHOOD",
        not_established=[
            "JOINT_TRAJECTORY_IDENTIFICATION",
            "OPEN_SEMANTIC_EXTRACTION",
            "CALIBRATED_TRUST",
            "FULL_M09",
            "FULL_S3",
            "LIVE_EFFECT",
        ],
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    Path(args.output).write_text(
        json.dumps(witness(), ensure_ascii=False, indent=2) + "\n"
    )

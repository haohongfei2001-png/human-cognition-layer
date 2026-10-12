"""Actual conditional revision, temporal access, absence invalidation and replay.

Offline candidates below propose source-bound meanings, never computed labels.
The runtime code imports neither this script nor any test/sample catalog.
"""

import argparse
from dataclasses import replace
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import tempfile

from hcl import HCL, RevisionIssue
from hcl.kernel.types import BudgetSlice, Principal, TaskRequest, thaw
from hcl.memory.store import StateStore
from hcl.models.gateway import ModelGateway, OfflineModelPort
from hcl.semantics.revision import KINDS, qualified
from hcl.semantics.segments import segment_snapshot


def ref(source, identity):
    return [source, identity]


def propose(store, request, handle, *, default=False, late_receipt=False, access=None):
    """A synthetic extraction fixture; time/identity claims remain assumptions."""
    source = handle.source_id
    snapshot = store.revision_snapshot(request.session_id, request.principal, (handle,))
    anchors = [row.segment_id for row in segment_snapshot(snapshot, request.question) if row.kind == "SOURCE"]
    proposal = {kind: [] for kind in KINDS}
    proposal.update(source_id=source, nogoods=[], unparsed_segments=[])

    def add(category, identity, **fields):
        row = dict(id=identity, segment_ids=anchors, **fields)
        proposal[category].append(row)
        return row

    add("frames", "frame", kind="SOURCE_DISCOURSE", parent=None)
    add("entities", "person", label="张三")
    add("entities", "message", label="通知 m")
    add(
        "perspectives",
        "view",
        agent=None if access is None else ref(source, "person"),
        nested=[],
        at=ref(source, "now"),
        observation_model="explicit-report",
        belief_model="NOT_COMPUTED",
    )
    add("scopes", "scope", frame=ref(source, "frame"), perspective=ref(source, "view"), at=ref(source, "now"))
    add("points", "now", axis="EVENT", scope=ref(source, "scope"), agent=None)
    filters = dict(kind="receipt", agent_id=ref(source, "person"), message_id=ref(source, "message"))
    for identity, predicate, negative in (
        ("receipt", "receipt", False),
        ("q", "no-indexed-receipt" if default else "attends", False),
        ("not-q", "no-indexed-receipt" if default else "attends", True),
    ):
        add(
            "claims",
            identity,
            predicate=predicate,
            arguments=[ref(source, "person"), ref(source, "message")],
            negated=negative,
            scope=ref(source, "scope"),
            index=filters if identity == "receipt" else None,
        )
    if default:
        add("assumptions", "closed-index-scope")
        add(
            "defaults",
            "absence",
            claim=ref(source, "q"),
            query=filters,
            assumptions=[ref(source, "closed-index-scope")],
        )
        add(
            "rules",
            "rebut",
            premises=[ref(source, "receipt")],
            conclusion=ref(source, "not-q"),
            assumptions=[],
        )
    else:
        report = add(
            "roots",
            "report",
            claim=ref(source, "receipt"),
            assumptions=[],
            event_end=ref(source, "now"),
            access=[],
            origin="DIRECT_REPORT",
        )
        add(
            "rules",
            "conditional",
            premises=[ref(source, "receipt")],
            conclusion=ref(source, "q"),
            assumptions=[],
        )
        if access is not None:
            add(
                "points",
                "receive",
                axis="AGENT_ACCESS",
                scope=ref(source, "scope"),
                agent=ref(source, "person"),
            )
            report["access"] = [dict(agent=ref(source, "person"), point=ref(source, "receive"))]
            add("assumptions", "clock")
            add(
                "clock_bridges",
                "map",
                left_axis="EVENT" if access == "late" else "AGENT_ACCESS",
                right_axis="AGENT_ACCESS" if access == "late" else "EVENT",
                source_scope=ref(source, "scope"),
                target_scope=ref(source, "scope"),
                assumptions=[ref(source, "clock")],
                evidence_roots=[ref(source, "report")],
            )
            add(
                "constraints",
                "receipt-order",
                left=ref(source, "now" if access == "late" else "receive"),
                right=ref(source, "receive" if access == "late" else "now"),
                numerator=0,
                denominator=1,
                strict=True,
                assumptions=[],
                evidence_roots=[ref(source, "report")],
                clock_bridge=ref(source, "map"),
            )
    if late_receipt:
        for identity in ("same", "clock", "projection"):
            add("assumptions", identity)
        for name in ("person", "message"):
            add(
                "identities",
                "same-" + name,
                left=ref(source, name),
                right=ref("initial", name),
                assumptions=[ref(source, "same")],
                evidence_roots=[ref(source, "report")],
            )
        add(
            "clock_bridges",
            "time-map",
            left_axis="EVENT",
            right_axis="EVENT",
            source_scope=ref(source, "scope"),
            target_scope=ref("initial", "scope"),
            assumptions=[ref(source, "clock")],
            evidence_roots=[ref(source, "report")],
        )
        add(
            "constraints",
            "earlier",
            left=ref(source, "now"),
            right=ref("initial", "now"),
            numerator=0,
            denominator=1,
            strict=True,
            assumptions=[],
            evidence_roots=[ref(source, "report")],
            clock_bridge=ref(source, "time-map"),
        )
        add(
            "bridges",
            "receipt-projection",
            source_claim=ref(source, "receipt"),
            target_claim=ref("initial", "receipt"),
            entity_mapping=[[ref(source, name), ref("initial", name)] for name in ("person", "message")],
            temporal_mapping=[[ref(source, "now"), ref("initial", "now")]],
            assumptions=[ref(source, "projection")],
            evidence_roots=[ref(source, "report")],
        )
    return proposal


def witness():
    rows = []
    principal = Principal("synthetic", "owner")
    budget = BudgetSlice(
        max_mock_calls=1, max_request_bytes=262144, max_output_bytes=262144, max_local_evaluations=33
    )
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "revision.sqlite"
        store = StateStore.sqlite(path, revision=True)
        store.create_session("witness", principal)
        initial = store.put_source(
            "witness", principal, "initial", "当前限定资料没有收到通知的记录；在这个假设下暂作缺证结论。"
        )
        request = TaskRequest(
            "initial",
            "当前资料支持什么？",
            (initial,),
            "witness",
            principal,
            budget=budget,
            issue=RevisionIssue("revision"),
        )

        def execute(request, *sources, query_source="initial"):
            proposal = dict(
                schema="hcl-revision-candidates-1",
                sources=list(sources),
                query=dict(positive=ref(query_source, "q"), negative=ref(query_source, "not-q")),
            )
            port = OfflineModelPort(json.dumps(proposal, ensure_ascii=False))
            result = HCL(store, principal=principal, gateway=ModelGateway(store, port)).run_sync(request)
            if result.status in ("COMPLETED", "PARTIAL"):
                values = next(iter(result.execution_receipt["inference_values"].values()))
                used = {field.field: field.value for field in result.claim_records[0].used_result_fields}
                assert used["support_bits"] == values["support_bits"] and not values["semantic_certified"]
                rows.append(
                    dict(
                        request_id=request.request_id,
                        status=result.status,
                        answer=result.answer,
                        actual_values=thaw(values),
                        consumed=thaw(used),
                        usage=thaw(result.usage),
                        source_inputs=[
                            dict(source_id=h.source_id, version=h.version) for h in request.source_handles
                        ],
                    )
                )
            assert result.usage["provider_calls"] == 0
            return result, port

        first, _ = execute(request, propose(store, request, initial, default=True))
        assert first.status == "COMPLETED" and rows[-1]["actual_values"]["support_bits"]["positive_support"]
        cutoff = first.state_revision
        late = store.put_source(
            "witness",
            principal,
            "late",
            "新证据报告同一人物此前收到同一通知，人物和时间对应均作为显式候选假设。",
        )
        stale, port = execute(request)
        assert stale.status == "STALE_STATE" and not stale.answer and port.attempts == 0
        pending, _ = execute(replace(request, request_id="pending", source_handles=()))
        assert (
            pending.status == "PARTIAL" and not rows[-1]["actual_values"]["support_bits"]["positive_support"]
        )
        update, _ = execute(
            replace(request, request_id="new-receipt", source_handles=(late,)),
            propose(store, request, late, late_receipt=True),
        )
        computed = rows[-1]["actual_values"]
        assert (
            not computed["support_bits"]["positive_support"] and computed["support_bits"]["negative_support"]
        )
        assert "REBUTTED_BY_SUPPORTED_RECORD" in computed["default_results"].values()
        assert computed["absence_watches"] and any(
            row["status"] == "CONDITIONAL_INFORMATION_PROJECTION" for row in computed["bridge_proofs"]
        )
        assert update.usage["identity_path_work"] > 0 and update.usage["temporal_relaxations"] > 0
        historical = replace(
            request,
            request_id="historical",
            source_handles=(),
            issue=RevisionIssue("revision", known_at=cutoff),
        )
        old, _ = execute(historical)
        assert (
            rows[-1]["actual_values"]["support_bits"]["positive_support"]
            and not rows[-1]["actual_values"]["support_bits"]["negative_support"]
        )
        store.close()
        store = StateStore.sqlite(path)
        replay, port = execute(historical)
        assert replay.answer == old.answer and replay.execution_receipt["replayed"] and port.attempts == 0
        store.close()
        # Separate person-clock session keeps unrelated contradiction/default data
        # out of this direct late-access/correction contrast.
        path = Path(directory) / "temporal.sqlite"
        store = StateStore.sqlite(path, revision=True)
        store.create_session("witness", principal)
        handle = store.put_source("witness", principal, "person", "张三在所问时点之后才收到通知。")
        person_request = replace(request, request_id="late-access", source_handles=(handle,))
        late_result, _ = execute(
            person_request, propose(store, person_request, handle, access="late"), query_source="person"
        )
        assert not rows[-1]["actual_values"]["support_bits"]["positive_support"]
        old_cut = late_result.state_revision
        handle = store.put_source(
            "witness", principal, "person", "新证据明确人物其实在所问时点之前收到通知。"
        )
        person_request = replace(person_request, request_id="corrected-access", source_handles=(handle,))
        corrected, _ = execute(
            person_request, propose(store, person_request, handle, access="early"), query_source="person"
        )
        assert rows[-1]["actual_values"]["support_bits"]["positive_support"]
        original_view = replace(
            person_request,
            request_id="old-person-view",
            source_handles=(),
            issue=RevisionIssue("revision", known_at=old_cut),
        )
        execute(original_view, query_source="person")
        assert not rows[-1]["actual_values"]["support_bits"]["positive_support"]
        store.close()
    root = Path(__file__).resolve().parents[1]
    return dict(
        schema="hcl-unified-s22-witness-1",
        checked_commit=subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip(),
        runtime_hashes={
            str(path.relative_to(root)): sha256(path.read_bytes()).hexdigest()
            for path in sorted((root / "hcl").rglob("*.py"))
        },
        provider_calls=0,
        provider_spend_usd="0",
        sealed_content_reads=0,
        rows=rows,
        evidence_scope="ACTUAL_BOUNDED_REVISION_UNDER_INJECTED_CANDIDATE_MEANINGS",
        not_established=[
            "open semantic extraction",
            "independent source alignment",
            "candidate completeness",
            "private belief truth",
            "full S1/S2 and T02/T03/T21/T22",
            "S3-S7 effectiveness",
        ],
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    Path(args.output).write_text(json.dumps(witness(), ensure_ascii=False, indent=2) + "\n")

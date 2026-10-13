"""Executed story/discourse and generated-order contrasts, not reading quality."""

import argparse
from dataclasses import replace
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import tempfile

from hcl import HCL, ExecutionBudget, ExecutionIssue
from hcl.kernel.types import Issue, Principal, TaskRequest, thaw
from hcl.memory.store import StateStore
from hcl.models.gateway import ModelGateway, OfflineModelPort
from hcl.runtime.context import ContextCompiler

TEXT = "She arrived. Three days earlier, she left. The door, the door!"


def proposal(snapshot, request, *, reversed_order):
    chunks = ContextCompiler().chunks(
        snapshot,
        request.question,
        "literature_compile",
        request.budget,
        OfflineModelPort().describe(),
    )
    assert len(chunks) == 1
    segments = chunks[0].segments
    refs = [s.segment_id for s in segments]
    frame = dict(fragment=0, id="narrator")

    def anchor(start, end):
        segment = next(s for s in segments if s.start <= start < end <= s.end)
        return dict(
            segment_id=segment.segment_id, start=start, end=end, quote=TEXT[start:end]
        )

    mentions = []
    for event, word in (("arrival", "arrived"), ("departure", "left")):
        start = TEXT.index(word)
        mentions.append(
            dict(
                id=event,
                event=dict(fragment=0, id=event),
                frame=frame,
                anchor=anchor(start, start + len(word)),
            )
        )
    parts = [anchor(s.start, s.end) for s in segments]
    order = list(range(len(parts)))
    if reversed_order:
        order[0], order[1] = order[1], order[0]
    return dict(
        schema="hcl-literature-fragment-1",
        assumptions=["event-reading"],
        active_assumptions=["event-reading"],
        frames=[
            dict(
                id="narrator",
                parent=None,
                kind="NARRATION",
                narrator="proposed voice",
                focalizer=None,
                segment_ids=refs,
            )
        ],
        events=[
            dict(
                id=name,
                frame=frame,
                description=name,
                assumptions=["event-reading"],
                segment_ids=refs,
            )
            for name in ("arrival", "departure")
        ],
        mentions=mentions,
        orders=[
            dict(
                id="earlier",
                left=dict(fragment=0, id="departure"),
                right=dict(fragment=0, id="arrival"),
                strict=True,
                assumptions=[],
                segment_ids=refs,
            )
        ],
        queries=[
            dict(
                id="chronology",
                left=dict(fragment=0, id="departure"),
                right=dict(fragment=0, id="arrival"),
                segment_ids=refs,
            )
        ],
        motifs=[dict(id="repeated-door", literal="door", segment_ids=refs)],
        variants=[
            dict(
                id="ordered-contrast",
                kind="REORDER",
                parts=parts,
                order=order,
                segment_ids=refs,
            )
        ],
        comparisons=[],
        analogies=[],
        unmodeled_segments=[],
    )


def witness():
    rows = []
    owner = Principal("synthetic-witness", "owner")
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "state.sqlite"
        store = StateStore.sqlite(path, revision=True)
        store.create_session("s", owner, {"other"})
        handle = store.put_source("s", owner, "book", TEXT)
        original = store.snapshot("s", owner, (handle,))
        budget = ExecutionBudget(
            max_mock_calls=1,
            max_feedback=0,
            max_output_bytes=1048576,
            max_total_output_bytes=8000000,
            max_visible_output_tokens=1048576,
            max_context_tokens=1048576,
            max_request_bytes=1048576,
            max_local_evaluations=10,
        )
        try:
            for mode in ("identity-order", "reordered-presentation", "work-frontier"):
                request = TaskRequest(
                    mode,
                    "Compare original and hypothetical presentation.",
                    (handle,),
                    "s",
                    owner,
                    budget=(
                        replace(budget, max_local_evaluations=1)
                        if mode == "work-frontier"
                        else budget
                    ),
                    issue=ExecutionIssue(
                        "root", goals=(Issue(mode, "literature.analyze"),)
                    ),
                )
                candidate = proposal(
                    original, request, reversed_order=mode != "identity-order"
                )
                port = OfflineModelPort(json.dumps(candidate))
                result = HCL(
                    store, principal=owner, gateway=ModelGateway(store, port)
                ).run_sync(request)
                assert result.status == "PARTIAL", (mode, result.diagnostics)
                actual = next(
                    r
                    for r in store.inferences("s", owner)
                    if r.result_id in result.execution_receipt["result_ids"]
                )
                variant = actual.values["variants"][0]
                contrast = variant["discourse_contrast"]
                if mode == "work-frontier":
                    assert contrast["frontier"] and not contrast["changed_pairs"]
                else:
                    assert actual.values["story_queries"][0]["relation"] == "BEFORE"
                    assert len(contrast["changed_pairs"]) == (
                        1 if mode == "reordered-presentation" else 0
                    )
                    assert (
                        contrast["status"] == "COMPLETE_DECLARED_OCCURRENCE_COMPARISON"
                    )
                    assert actual.values["story_queries"][0]["assumptions"]
                assert (
                    store.snapshot("s", owner, (handle,)).immutable_views
                    == original.immutable_views
                )
                store.close()
                store = StateStore.sqlite(path)
                replay_port = OfflineModelPort("NO_RESEND")
                replay = HCL(
                    store, principal=owner, gateway=ModelGateway(store, replay_port)
                ).run_sync(request)
                assert replay.answer == result.answer and replay_port.attempts == 0
                rows.append(
                    dict(
                        case=mode,
                        status=result.status,
                        actual=thaw(actual.values),
                        answer=result.answer,
                        usage=thaw(result.usage),
                        offline_attempts=port.attempts,
                        replay_new_attempts=0,
                    )
                )
            store.set_readers("s", owner, "book", {"other"})
            denied = HCL(store, principal=owner).run_sync(request)
            assert (
                denied.status == "DENIED"
                and not denied.answer
                and not denied.claim_records
            )
            rows.append(
                dict(
                    case="revoked-cached-variant",
                    status=denied.status,
                    usage=thaw(denied.usage),
                )
            )
        finally:
            store.close()
    return dict(
        schema="hcl-unified-narrative-witness-1",
        checked_commit=subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True
        ).strip(),
        runtime_hashes={
            str(p): sha256(p.read_bytes()).hexdigest()
            for p in sorted(Path("hcl").rglob("*.py"))
        },
        provider_calls=0,
        provider_spend_usd=0,
        sealed_content_reads=0,
        rows=rows,
        evidence_scope="EXACT_HYPOTHETICAL_REORDER_AND_DECLARED_OCCURRENCE_CONTRAST",
        not_established=[
            "OPEN_EXTRACTION_ACCURACY",
            "SEMANTIC_EFFECT_OF_REWRITING",
            "READER_EMOTION_OR_AESTHETIC_TRUTH",
            "FULL_M11",
            "FULL_T13",
            "FULL_T14",
            "FULL_T27",
            "FULL_S4",
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

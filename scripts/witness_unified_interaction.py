"""Actual finite M03/M05/M07 composition under injected source interpretations."""

from hashlib import sha256
import argparse
import json
import math
from pathlib import Path
import subprocess
import tempfile

from hcl import HCL, ExecutionBudget, ExecutionIssue
from hcl.kernel.types import Principal, TaskRequest, Issue, thaw
from hcl.memory.store import StateStore
from hcl.models.gateway import OfflineModelPort, ModelGateway
from hcl.semantics.segments import segment_snapshot

SOURCE = (
    "A knows the passage is dangerous. B initially has no observation. "
    "A can say safe, dangerous, or a less informative true description; "
    "B chooses whether to cross or wait. In a separate proposed commitment, "
    "A offers to perform a task if its condition holds, B accepts the original "
    "terms, and the record separately specifies performance and receipt of acknowledgments."
)


def propose(snapshot, question, mode):
    segments = segment_snapshot(snapshot, question)
    refs = [s.segment_id for s in segments if s.kind == "SOURCE"]
    questions = [s.segment_id for s in segments if s.kind == "QUESTION"]
    states = ["r", "b", "success", "harm", "waited"]
    same = {s: s for s in states}
    graph = dict(
        states=states,
        terminal=["success", "harm", "waited"],
        horizon=1,
        utilities=dict(r="0", b="0", success="3", harm="-3", waited="0"),
        actions=[
            dict(
                id=key,
                cost="0",
                enabled=["r", "b"],
                feasible=["r", "b"],
                transitions=dict(same, **target),
                observations={s: "same" for s in states},
            )
            for key, target in [
                ("cross", dict(r="success", b="harm")),
                ("wait", dict(r="waited", b="waited")),
            ]
        ],
    )
    atom = lambda name: dict(op="atom", name=name)
    mental = dict(
        id="scene",
        source_id="records",
        frame_kind="INTERPRETATION",
        assumptions=["proposed-scene"],
        active_assumptions=["proposed-scene"],
        unmodeled_segments=[],
        agents=[
            dict(id=a, label=a, source_id="records", segment_ids=refs)
            for a in ("a", "b")
        ],
        variables=[dict(id="safe", initial=False, observed_by=["a"], segment_ids=refs)],
        events=[],
        queries=[
            dict(
                id="belief-" + a,
                at=1,
                formula=dict(op="believes", agent=a, arg=atom("safe")),
                segment_ids=questions,
            )
            for a in ("a", "b")
        ],
        plans=[
            dict(
                id="listener",
                actor="b",
                at=1,
                graph=graph,
                bindings=[
                    dict(state="r", when=atom("safe")),
                    dict(state="b", when=dict(op="not", arg=atom("safe"))),
                ],
                weights={"r": "1/2", "b": "1/2"},
                policy=None,
                segment_ids=refs,
            )
        ],
        causal=[],
    )
    game = dict(
        id="signal",
        at=1,
        speaker="a",
        listener="b",
        plan_id="listener",
        messages=[
            dict(id=key, meaning=meaning, cost=cost, segment_ids=refs)
            for key, meaning, cost in [
                ("R", ["r"], "1"),
                ("B", ["b"], "0"),
                ("V", ["r", "b"], "0"),
            ]
        ],
        prior={s: "1/2" if s in ("r", "b") else "0" for s in states},
        speaker_prior=None,
        beta="1",
        listener_beta="1",
        depth=1,
        goal="ACTION",
        utilities={
            s: {a["id"]: "2" if a["id"] == "cross" else "0" for a in graph["actions"]}
            for s in states
        },
        sincere=True,
        segment_ids=refs,
    )
    row = dict(
        mental=mental,
        utterances=[],
        acts=[],
        commitments=[],
        games=[game],
        through=6,
        max_ack_depth=4,
    )
    if mode in ("listener_private", "listener_late"):
        at = 1 if mode == "listener_private" else 2
        mental["events"].append(
            dict(
                id="listener-observation",
                at=at,
                kind="change",
                effects={"safe": False},
                seen_by=["b"],
                received_by=[],
                understood_by=[],
                trusted_by=[],
                assumptions=[],
                segment_ids=refs,
            )
        )
        if at == 1:
            mental["plans"][0]["weights"] = {"b": "1"}
    if mode == "prior_missing":
        game["prior"] = None

    def message(identity, at, delivery, speaker, recipient):
        event = identity + "-delivery"
        mental["events"].append(
            dict(
                id=event,
                at=delivery,
                kind="message",
                effects={},
                seen_by=[],
                received_by=[recipient],
                understood_by=[recipient],
                trusted_by=[],
                assumptions=[],
                segment_ids=refs,
            )
        )
        row["utterances"].append(
            dict(
                id=identity,
                at=at,
                speaker=speaker,
                audience=[recipient],
                version="v1",
                literal={},
                segment_ids=refs,
                deliveries=[
                    dict(
                        event_id=event,
                        segment_ids=refs,
                        readings=[
                            dict(
                                actor=recipient,
                                contents=[{}],
                                versions=["v1"],
                                segment_ids=refs,
                            )
                        ],
                    )
                ],
            )
        )

    def act(identity, at, actor, audience, kind, parent):
        row["acts"].append(
            dict(
                id=identity,
                at=at,
                actor=actor,
                audience=[audience],
                kind=kind,
                refers_to=parent,
                version="v1",
                segment_ids=refs,
            )
        )

    if mode in ("commit_breach", "commit_fulfilled", "acknowledgments"):
        row["games"] = []
        message("offer", 1, 1, "a", "b")
        if mode == "acknowledgments":
            message("interpret", 2, 3, "b", "a")
            act("interpret", 2, "b", "a", "INTERPRET", "offer")
            message("confirm", 4, 5, "a", "b")
            act("confirm", 4, "a", "b", "ACK", "interpret")
        else:
            mental["variables"].extend(
                dict(id=k, initial=v, observed_by=["a", "b"], segment_ids=refs)
                for k, v in [("condition", True), ("done", False)]
            )
            message("accept", 2, 2, "b", "a")
            act("accept", 2, "b", "a", "ACCEPT", "offer")
            row["commitments"] = [
                dict(
                    id="promise",
                    offer_id="offer",
                    speaker="a",
                    recipient="b",
                    version="v1",
                    condition=atom("condition"),
                    outcome=atom("done"),
                    deadline=5,
                    requires_acceptance=True,
                    acceptance="RECEIVED_BY_OFFEROR",
                    activation="LATCHED",
                    withdrawal="RECEIVED_RELEASE",
                    segment_ids=refs,
                )
            ]
            if mode == "commit_fulfilled":
                mental["events"].append(
                    dict(
                        id="performance",
                        at=4,
                        kind="change",
                        effects={"done": True},
                        seen_by=["a", "b"],
                        received_by=[],
                        understood_by=[],
                        trusted_by=[],
                        assumptions=[],
                        segment_ids=refs,
                    )
                )
    return dict(schema="hcl-interaction-candidates-1", models=[row])


def witness():
    rows = []
    computations = {}
    with tempfile.TemporaryDirectory() as directory:
        store = StateStore.sqlite(Path(directory) / "state.sqlite", revision=True)
        owner = Principal("synthetic", "reader")
        store.create_session("s", owner)
        handle = store.put_source("s", owner, "records", SOURCE)
        try:
            for mode in (
                "strategic",
                "listener_private",
                "listener_late",
                "prior_missing",
                "commit_breach",
                "commit_fulfilled",
                "acknowledgments",
            ):
                request = TaskRequest(
                    mode,
                    "What follows conditionally from these proposed interaction mechanisms?",
                    (handle,),
                    "s",
                    owner,
                    budget=ExecutionBudget(
                        max_mock_calls=1,
                        max_local_evaluations=4096,
                        max_request_bytes=1048576,
                        max_output_bytes=1048576,
                        max_context_tokens=1048576,
                        max_total_output_bytes=16777216,
                        max_visible_output_tokens=1048576,
                    ),
                    issue=ExecutionIssue(
                        "root", goals=(Issue(mode, "interaction.evaluate"),)
                    ),
                )
                candidate = propose(
                    store.snapshot("s", owner, (handle,)), request.question, mode
                )
                port = OfflineModelPort(json.dumps(candidate))
                client = HCL(store, principal=owner, gateway=ModelGateway(store, port))
                result = client.run_sync(request)
                assert result.status == (
                    "PARTIAL" if mode == "prior_missing" else "COMPLETED"
                ), (mode, result.diagnostics)
                actual = next(
                    r
                    for r in store.inferences("s", owner)
                    if r.result_id in result.execution_receipt["result_ids"]
                )
                model = actual.values["models"][0]
                if mode in ("strategic", "listener_private", "listener_late"):
                    computed = thaw(model["games"][0]["computation"])
                    computations[mode] = computed
                    expected = 1 / (1 + math.exp(-0.5))
                    prediction = computed["expected_listener"]["predictions"]["V"]
                    assert abs(prediction["posterior"]["r"] - expected) < 1e-12
                    assert (
                        abs(
                            prediction["actions"]["q"]["cross"] - 3 * (2 * expected - 1)
                        )
                        < 1e-12
                    )
                    assert computed["speaker"]["best_messages"] == ["V"]
                elif mode == "prior_missing":
                    assert not model["games"][0]["computation"]["actual_listener"][
                        "predictions"
                    ]
                elif mode.startswith("commit_"):
                    assert model["commitments"][0]["status"] == (
                        "BREACHED" if mode == "commit_breach" else "FULFILLED"
                    )
                else:
                    chain = model["acknowledgments"]["chains"][-1]
                    assert (
                        chain["depth"] == 2
                        and chain["complete"] is True
                        and chain["common_knowledge"] == "NOT_ESTABLISHED"
                    )
                replay = client.run_sync(request)
                assert (replay.answer, replay.claim_records) == (
                    result.answer,
                    result.claim_records,
                )
                assert port.attempts == 1
                rows.append(
                    dict(
                        case=mode,
                        status=result.status,
                        answer=result.answer,
                        actual_result=thaw(actual.values),
                        usage=thaw(result.usage),
                        consumed=[
                            dict(
                                result_id=f.result_id,
                                field=f.field,
                                path=getattr(f, "path", ()),
                                value=thaw(f.value),
                            )
                            for c in result.claim_records
                            for f in c.used_result_fields
                        ],
                    )
                )
            assert (
                computations["strategic"]["speaker"]
                == computations["listener_private"]["speaker"]
            )
            assert (
                computations["strategic"]["expected_listener"]
                == computations["listener_private"]["expected_listener"]
            )
            assert (
                computations["strategic"]["actual_listener"]
                != computations["listener_private"]["actual_listener"]
            )
            assert computations["strategic"] == computations["listener_late"]
            store.set_readers("s", owner, "records", {"other"})
            denied = client.run_sync(request)
            assert (
                denied.status == "DENIED"
                and not denied.answer
                and not denied.claim_records
            )
        finally:
            store.close()
    root = Path(__file__).resolve().parents[1]
    return dict(
        schema="hcl-unified-interaction-witness-1",
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
        evidence_scope="FINITE_DECLARED_M03_M05_M07_COMPOSITION_WITH_INJECTED_SOURCE_INTERPRETATIONS",
        not_established=[
            "OPEN_EXTRACTION",
            "HUMAN_CALIBRATION",
            "PRIVATE_INTENT",
            "FULL_M07",
            "INSTITUTIONAL_GROUP_AUTHORITY",
            "FULL_S3",
            "RESEARCH_ACCEPTANCE",
        ],
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    Path(args.output).write_text(
        json.dumps(witness(), ensure_ascii=False, indent=2) + "\n"
    )

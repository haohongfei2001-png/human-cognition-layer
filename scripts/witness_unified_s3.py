"""Actual finite S3 domain calculations; fixture models are test conditions only."""

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
from hcl.semantics.segments import segment_snapshot


def propose(snapshot, question, *, observed=False, received=None):
    segments = segment_snapshot(snapshot, question)
    source = [s.segment_id for s in segments if s.kind == "SOURCE"]
    query = [s.segment_id for s in segments if s.kind == "QUESTION"]
    atom = dict(op="atom", name="open")
    states = ["open", "closed", "detour", "arrived", "blocked"]
    identity = {s: s for s in states}

    def action(name, cost, enabled, feasible, transitions):
        return dict(
            id=name,
            cost=cost,
            enabled=enabled,
            feasible=feasible,
            transitions=dict(identity, **transitions),
            observations=identity,
        )

    graph = dict(
        states=states,
        terminal=["arrived", "blocked"],
        utilities={s: 6 if s == "arrived" else 0 for s in states},
        horizon=2,
        actions=[
            action(
                "direct",
                1,
                ["open", "closed"],
                ["open"],
                {"open": "arrived", "closed": "blocked"},
            ),
            action(
                "detour-start",
                1,
                ["open", "closed"],
                ["open", "closed"],
                {"open": "detour", "closed": "detour"},
            ),
            action("detour-finish", 2, ["detour"], ["detour"], {"detour": "arrived"}),
        ],
    )

    def plan(at):
        return dict(
            id="route-" + str(at),
            actor="nora",
            at=at,
            graph=graph,
            bindings=[
                dict(state="open", when=atom),
                dict(state="closed", when=dict(op="not", arg=atom)),
            ],
            weights=None,
            policy=None,
            segment_ids=source,
        )

    def belief(agent, at):
        return dict(
            id=agent + "-" + str(at),
            at=at,
            formula=dict(op="believes", agent=agent, arg=atom),
            segment_ids=query,
        )

    events = [
        dict(
            id="closure",
            at=1,
            kind="change",
            effects={"open": False},
            seen_by=["nora", "omar"] if observed else ["omar"],
            received_by=[],
            understood_by=[],
            trusted_by=[],
            assumptions=["observation-channel"],
            segment_ids=source,
        )
    ]
    if received is not None:
        events.append(
            dict(
                id="notice",
                at=2,
                kind="message",
                effects={"open": False},
                seen_by=[],
                received_by=["nora"] if received else [],
                understood_by=["nora"] if received else [],
                trusted_by=["nora"] if received else [],
                assumptions=["notice-trust"],
                segment_ids=source,
            )
        )
    models = [
        dict(
            id="route",
            source_id="story",
            frame_kind="SOURCE_DISCOURSE",
            assumptions=[
                "candidate-observation-structure",
                "persistence-unless-update",
            ],
            active_assumptions=[
                "candidate-observation-structure",
                "persistence-unless-update",
                "observation-channel",
                *(["notice-trust"] if received is not None else []),
            ],
            unmodeled_segments=[],
            agents=[
                dict(id=name, label=name.title(), source_id="story", segment_ids=source)
                for name in ("nora", "omar")
            ],
            variables=[
                dict(
                    id="open",
                    initial=True,
                    observed_by=["nora", "omar"],
                    segment_ids=source,
                )
            ],
            events=events,
            queries=[belief("nora", 1), belief("omar", 1)],
            plans=[plan(1)],
            causal=[],
        )
    ]
    if received is not None:
        models[0]["queries"] += [belief("nora", 2), belief("omar", 2)]
        models[0]["plans"].append(plan(2))
    return dict(schema="hcl-mental-scene-candidates-1", models=models)


def witness():
    rows = []
    owner = Principal("synthetic", "owner")
    with tempfile.TemporaryDirectory() as directory:
        for name, observed, received in [
            ("unseen", False, None),
            ("seen", True, None),
            ("received", False, True),
            ("analyst-only", False, False),
            ("withdrawn", False, None),
            ("causal", False, None),
        ]:
            store = StateStore.sqlite(
                Path(directory) / (name + ".sqlite"), revision=True
            )
            try:
                store.create_session("witness", owner)
                source = (
                    "Nora and Omar see an open corridor. "
                    + (
                        "Nora stays while Omar closes it. "
                        if observed
                        else "Nora leaves; Omar closes it. "
                    )
                    + "Nora wants to reach the hall. The direct route costs one unit. A two-part detour costs one then two units. Arrival is worth six units."
                )
                if received is not None:
                    source += (
                        " Nora later receives, understands and trusts a closure notice."
                        if received
                        else " The analyst later obtains a closure record, without Nora receiving it."
                    )
                if name == "causal":
                    source += " The upstream switch drives X. Y lights only when X and the upstream switch differ."
                handle = store.put_source("witness", owner, "story", source)
                request = TaskRequest(
                    name,
                    "How do their information and Nora’s route prediction differ at each time?",
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
                        "root", goals=(Issue("mental", "mental.simulate"),)
                    ),
                )
                snapshot = store.snapshot("witness", owner, (handle,))
                candidate = propose(
                    snapshot, request.question, observed=observed, received=received
                )
                if name == "withdrawn":
                    candidate["models"][0]["active_assumptions"].remove(
                        "persistence-unless-update"
                    )
                if name == "causal":
                    anchors = [
                        s.segment_id
                        for s in segment_snapshot(snapshot, request.question)
                        if s.kind == "SOURCE"
                    ]
                    structure = dict(
                        id="switch",
                        source_event_id="switch-event",
                        variables=["U", "X", "Y"],
                        exogenous=["U"],
                        rules=[
                            dict(
                                target="X",
                                expression="U",
                                evidence_text="The upstream switch drives X.",
                            ),
                            dict(
                                target="Y",
                                expression="X ^ U",
                                evidence_text="Y lights only when X and the upstream switch differ.",
                            ),
                        ],
                    )
                    candidate["models"][0]["causal"] = [
                        dict(
                            id=key,
                            model=structure,
                            target="Y",
                            observations=o,
                            interventions=i,
                            segment_ids=anchors,
                        )
                        for key, o, i in [
                            ("observe", {"X": 0}, {}),
                            ("do", {}, {"X": 0}),
                            ("abduct-do", {"X": 1}, {"X": 0}),
                            ("withdraw", {}, {}),
                        ]
                    ]
                port = OfflineModelPort(json.dumps(candidate, ensure_ascii=False))
                result = HCL(
                    store, principal=owner, gateway=ModelGateway(store, port)
                ).run_sync(request)
                assert result.status == (
                    "PARTIAL" if name == "withdrawn" else "COMPLETED"
                ), result.diagnostics
                selected = [
                    r
                    for r in store.inferences("witness", owner)
                    if r.result_id in result.execution_receipt["result_ids"]
                ]
                assert len(selected) == 1 and port.attempts == 1
                actual = thaw(selected[0].values)
                rows.append(
                    dict(
                        case=name,
                        source=source,
                        status=result.status,
                        answer=result.answer,
                        usage=thaw(result.usage),
                        actual_result=dict(
                            result_id=selected[0].result_id, values=actual
                        ),
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
                        fixture_attempts=port.attempts,
                    )
                )
            finally:
                store.close()
    by_name = {row["case"]: row["actual_result"]["values"]["models"][0] for row in rows}
    assert by_name["unseen"]["plans"][0]["q"] == {"direct": "5", "detour-start": "3"}
    assert by_name["seen"]["plans"][0]["q"] == {"direct": "-1", "detour-start": "3"}
    assert by_name["received"]["plans"][0]["best_actions"] == ["direct"]
    assert by_name["received"]["plans"][1]["best_actions"] == ["detour-start"]
    assert by_name["analyst-only"]["plans"][1]["best_actions"] == ["direct"]
    assert not by_name["withdrawn"]["plans"]
    assert [r["possible_values"] for r in by_name["causal"]["causal"]] == [
        [0],
        [0, 1],
        [1],
        [0],
    ]
    root = Path(__file__).resolve().parents[1]
    return dict(
        schema="hcl-unified-s3-finite-mechanisms-witness-1",
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
        evidence_scope="BOUNDED_ACTUAL_M03_M05_M06_COMPUTATION_UNDER_SOURCE_ANCHORED_INJECTED_MODELS",
        not_established=[
            "open model extraction or semantic alignment",
            "complete M03/M05/M06",
            "M04/M07/M08/M09",
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

"""Bounded M04 witness: actual residual edits and prospective discrimination."""

import argparse
from copy import deepcopy
from dataclasses import replace
from hashlib import sha256
from itertools import product
import json
from pathlib import Path
import subprocess
import tempfile

from hcl import HCL, ExecutionBudget, ExecutionIssue
from hcl.kernel.types import Principal, TaskRequest, Issue, thaw
from hcl.memory.store import StateStore
from hcl.models.gateway import ModelGateway, OfflineModelPort
from hcl.semantics.segments import segment_snapshot


def propose(snapshot, question):
    segments = segment_snapshot(snapshot, question)
    anchors = [s.segment_id for s in segments if s.kind == "SOURCE"]
    questions = [s.segment_id for s in segments if s.kind == "QUESTION"]
    states = ["open", "closed", "detour", "success", "failure"]
    same = {s: s for s in states}
    graph = dict(
        states=states,
        terminal=["success", "failure"],
        utilities={s: "6" if s == "success" else "0" for s in states},
        horizon=2,
        actions=[
            dict(
                id="direct",
                cost="1",
                enabled=["open", "closed"],
                feasible=["open"],
                transitions=dict(same, open="success", closed="failure"),
                observations=same,
            ),
            dict(
                id="detour-start",
                cost="1",
                enabled=["open", "closed"],
                feasible=["open", "closed"],
                transitions=dict(same, open="detour", closed="detour"),
                observations=same,
            ),
            dict(
                id="finish",
                cost="2",
                enabled=["detour"],
                feasible=["detour"],
                transitions=dict(same, detour="success"),
                observations=same,
            ),
        ],
    )
    model = dict(
        id="route",
        source_id="records",
        frame_kind="INTERPRETATION",
        assumptions=["candidate-mechanism"],
        active_assumptions=["candidate-mechanism"],
        unmodeled_segments=[],
        agents=[dict(id="a", label="A", source_id="records", segment_ids=anchors)],
        variables=[
            dict(id="open", initial=True, observed_by=["a"], segment_ids=anchors)
        ],
        events=[
            dict(
                id="change",
                at=1,
                kind="change",
                effects={"open": False},
                seen_by=[],
                received_by=[],
                understood_by=[],
                trusted_by=[],
                assumptions=[],
                segment_ids=anchors,
            )
        ],
        queries=[],
        plans=[
            dict(
                id="route",
                actor="a",
                at=1,
                graph=graph,
                bindings=[
                    dict(state="open", when={"op": "atom", "name": "open"}),
                    dict(
                        state="closed",
                        when={"op": "not", "arg": {"op": "atom", "name": "open"}},
                    ),
                ],
                weights=None,
                policy=None,
                segment_ids=anchors,
            )
        ],
        causal=[],
    )
    contexts, observations = [], []
    for i, (opened, received, seen) in enumerate(product((False, True), repeat=3)):
        template = dict(
            schema="hcl-mental-scene-candidates-1", models=[deepcopy(model)]
        )
        template["models"][0]["events"][0]["effects"]["open"] = opened
        features = dict(received=received, seen=seen)
        contexts.append(
            dict(
                id=f"context-{i}",
                adapter="mental-scene-1",
                template=template,
                features=features,
                feature_segments={k: [anchors[i]] for k in features},
                segment_ids=[anchors[i]],
            )
        )
        observations.append(
            dict(
                id=f"observation-{i}",
                context_id=f"context-{i}",
                query_id="choice",
                values=[
                    "detour-start" if not opened and (received or seen) else "direct"
                ],
                factor_id=f"event-{i}",
                provenance_group=f"record-{i}",
                derived_from=[],
                segment_ids=[anchors[i]],
            )
        )
    program = dict(
        id="received-only",
        adapter="mental-scene-1",
        latent={"reward": "6"},
        observe=[
            dict(
                event_id="change",
                actor="a",
                channel="seen_by",
                when={"feature": "received"},
            )
        ],
        transition=[
            dict(
                target=dict(kind="utility", plan_id="route", state="success"),
                value={"latent": "reward"},
            )
        ],
        constraint=[],
        predict=[dict(id="choice", field="plan.best_actions", record_id="route")],
    )
    return dict(
        schema="hcl-discovery-candidates-1",
        contexts=contexts,
        observations=observations,
        programs=[program],
        probes=[],
        grammar=dict(
            observation_features=["received", "seen"],
            latent_domains={"reward": ["4", "6", "8"]},
            max_expression_size=40,
        ),
        search=dict(max_rounds=1, beam=12, new_per_round=4, max_candidates=64),
        unmodeled_segments=[],
    )


def witness():
    owner = Principal("synthetic", "owner")
    rows = []
    with tempfile.TemporaryDirectory() as directory:
        store = StateStore.sqlite(Path(directory) / "state.sqlite", revision=True)
        try:
            store.create_session("s", owner)
            source = "".join(
                f'Record {i}: passage open={o}, notified={r}, directly observed={s}; recorded action={"detour" if not o and (r or s) else "direct"}.\n'
                for i, (o, r, s) in enumerate(product((False, True), repeat=3))
            )
            handle = store.put_source("s", owner, "records", source)
            request = TaskRequest(
                "discover",
                "Which observation mechanism explains these choices, and what would distinguish goals?",
                (handle,),
                "s",
                owner,
                budget=ExecutionBudget(
                    max_mock_calls=2,
                    max_local_evaluations=512,
                    max_request_bytes=1048576,
                    max_output_bytes=1048576,
                    max_visible_output_tokens=1048576,
                    max_context_tokens=1048576,
                    max_total_output_bytes=16777216,
                ),
                issue=ExecutionIssue(
                    "root", goals=(Issue("discover", "hypothesis.discover"),)
                ),
            )
            candidate = propose(store.snapshot("s", owner, (handle,)), request.question)
            for mode in ("channel-edit", "future-probe"):
                current = deepcopy(candidate)
                if mode == "future-probe":
                    current["contexts"] = [current["contexts"][2]]
                    current["observations"] = [current["observations"][2]]
                    current["search"]["max_rounds"] = 0
                    current["programs"][0]["latent"]["reward"] = "4"
                    other = deepcopy(current["programs"][0])
                    other["id"] = "reward-8"
                    other["latent"]["reward"] = "8"
                    other["constraint"] = [{"const": True}]
                    current["programs"].append(other)
                    probe = deepcopy(current["contexts"][0])
                    probe["id"] = "cost-7"
                    next(
                        a
                        for a in probe["template"]["models"][0]["plans"][0]["graph"][
                            "actions"
                        ]
                        if a["id"] == "finish"
                    )["cost"] = "6"
                    current["probes"] = [
                        dict(
                            id="cost-7",
                            context=probe,
                            query_id="choice",
                            segment_ids=probe["segment_ids"],
                        )
                    ]
                    current["unmodeled_segments"] = [
                        s.segment_id
                        for s in segment_snapshot(
                            store.snapshot("s", owner, (handle,)), request.question
                        )
                        if s.kind == "SOURCE"
                    ]
                port = OfflineModelPort(json.dumps(current))
                task = replace(
                    request,
                    request_id=mode,
                    issue=ExecutionIssue(
                        "root", goals=(Issue(mode, "hypothesis.discover"),)
                    ),
                )
                result = HCL(
                    store, principal=owner, gateway=ModelGateway(store, port)
                ).run_sync(task)
                assert result.status == "PARTIAL", result.diagnostics
                actual = next(
                    r
                    for r in store.inferences("s", owner)
                    if r.result_id in result.execution_receipt["result_ids"]
                )
                values = thaw(actual.values)
                if mode == "channel-edit":
                    assert any(
                        len(c["profile"]["explained"]) == 8
                        for c in values["prediction_matrix"].values()
                    )
                    assert values["edit_history"] and any(
                        e["operation"] == "extend_channel"
                        for e in values["edit_history"]
                    )
                else:
                    assert (
                        values["distinguishing_observations"][0]["separated_pairs"] == 1
                    )
                    assert (
                        len(values["prediction_classes"][0]["members"]) == 2
                        and len(values["pareto_programs"]) == 1
                    )
                assert port.attempts == 1
                rows.append(
                    dict(
                        case=mode,
                        status=result.status,
                        answer=result.answer,
                        actual_result=values,
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
        finally:
            store.close()
    root = Path(__file__).resolve().parents[1]
    return dict(
        schema="hcl-unified-discovery-witness-1",
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
        evidence_scope="BOUNDED_DECLARED_MECHANISM_DISCOVERY_UNDER_INJECTED_SOURCE_INTERPRETATION",
        not_established=[
            "OPEN_EXTRACTION",
            "COMPLETE_HYPOTHESIS_GRAMMAR",
            "CALIBRATED_POSTERIOR",
            "FULL_M04",
            "FULL_S3",
            "FULL_S4",
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

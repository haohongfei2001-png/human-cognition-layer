"""Source-bound conditional longitudinal mechanisms with real shared computations.

The proposal is an explicit experimental model, not extracted truth. No answer,
fit, trust score, change point or downstream Q is provided by this port.
"""

from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import argparse
import json
import subprocess
import tempfile
from hcl import HCL, ExecutionBudget, ExecutionIssue
from hcl.kernel.types import Principal, TaskRequest, Issue, thaw
from hcl.memory.store import StateStore
from hcl.models.gateway import OfflineModelPort, ModelGateway
from scripts.witness_unified_affect import propose as affect_candidate

SOURCE = (
    "Across home and work B waits when a passage is closed and crosses when it opens. "
    "B observes closure at 1, opening at 2, closure at 3, and opening at 4. "
    "Safety and duty have opposing consequences. A later reported choice may contradict this pattern. "
    "A offers passage support; a condition arises at 1 without fulfillment, and the route opens at 2. "
    "Ability, goodwill and reliability are distinct directed hypotheses, not interchangeable personality labels. "
    "An apology or receipt alone need not prove acceptance or restored trust. "
    "Role obligations may conflict; self-description and another person's attribution are separate evidence channels. "
    "The following priorities, likelihoods, independence model, transition graph and source mappings are declared "
    "experimental hypotheses, not measured psychology or verified natural-language extraction."
)


def propose(snapshot, question, mode="stable"):
    base = affect_candidate(snapshot, question, "mixed")["models"][0]
    mental = base["mental"]
    original = base["episodes"][0]
    template = mental["plans"][0]
    refs = original["segment_ids"]
    episodes = []
    plans = []
    events = []
    for at in range(1, 6):
        episode = deepcopy(original)
        episode.update(
            id="episode-" + str(at),
            episode_id="event-" + str(at),
            before=at - 1,
            at=at,
            plan_id="plan-" + str(at),
            previous_weights=None,
            current_weights=None,
            forecast_action=None,
        )
        episodes.append(episode)
        plan = deepcopy(template)
        plan.update(id=episode["plan_id"], at=at, weights=None)
        plans.append(plan)
        if at < 5:
            event = deepcopy(mental["events"][0])
            event.update(
                id="change-" + str(at),
                at=at,
                effects={"safe": at % 2 == 0},
                seen_by=["b"],
            )
            events.append(event)
    mental.update(events=events, plans=plans)
    observations = [
        dict(
            id="choice-" + str(at),
            context_id="home" if at % 2 else "work",
            episode_id="episode-" + str(at),
            action="wait" if at % 2 else "cross",
            segment_ids=refs,
        )
        for at in range(1, 5)
    ]
    mechanisms = [
        dict(
            id="safety",
            label="constant safety priority with changing information",
            priorities={"safety": "1", "duty": "0"},
            coping_id=None,
            goal_multipliers={"safety": "1", "duty": "1"},
            respect_roles=False,
            relationship_effects=[],
            segment_ids=refs,
        ),
        dict(
            id="duty",
            label="constant duty priority",
            priorities={"safety": "0", "duty": "1"},
            coping_id=None,
            goal_multipliers={"safety": "1", "duty": "1"},
            respect_roles=False,
            relationship_effects=[],
            segment_ids=refs,
        ),
        dict(
            id="coping",
            label="appraisal-conditioned attention",
            priorities=None,
            coping_id="safety-focus",
            goal_multipliers={"safety": "1", "duty": "1"},
            respect_roles=False,
            relationship_effects=[],
            segment_ids=refs,
        ),
    ]
    candidate = dict(
        schema="hcl-relationship-candidates-1",
        models=[
            dict(
                mental=mental,
                interaction=dict(
                    utterances=[],
                    acts=[],
                    commitments=[],
                    games=[],
                    through=5,
                    max_ack_depth=2,
                ),
                affect=dict(episodes=episodes, channels=base["channels"]),
                relationships=[],
                roles=[],
                identities=[
                    dict(
                        id="self",
                        at=1,
                        actor="b",
                        speaker="b",
                        kind="SELF_IDENTIFICATION",
                        content="I consider duty important.",
                        segment_ids=refs,
                    ),
                    dict(
                        id="attributed",
                        at=2,
                        actor="b",
                        speaker="a",
                        kind="OTHER_ATTRIBUTION",
                        content="A calls B cautious.",
                        segment_ids=refs,
                    ),
                ],
                observations=observations,
                forecasts=[
                    dict(
                        id="next",
                        context_id="next-work",
                        episode_id="episode-5",
                        segment_ids=refs,
                    )
                ],
                mechanisms=mechanisms,
                search=dict(max_segments=3, max_candidates=256),
            )
        ],
    )
    model = candidate["models"][0]
    refs = model["observations"][0]["segment_ids"]
    if mode in ("relationship", "null_prior", "unreceived", "contradicted"):
        add_relationships(candidate)
        if mode == "null_prior":
            model["relationships"][0]["prior"] = None
        elif mode == "unreceived":
            model["mental"]["events"][1]["seen_by"] = ["a"]
        elif mode == "contradicted":
            model["relationships"][0]["updates"][0]["likelihoods"] = {
                "supportive": "0",
                "limited": "0",
            }
    if mode == "counterevidence":
        model["observations"][-1]["action"] = "wait"
    if mode in ("role_conflict", "reconciled"):
        model["roles"] = [
            dict(
                id=identity,
                actor="b",
                from_time=3,
                through_time=3,
                condition=True,
                episode_actions={"episode-3": actions},
                segment_ids=refs,
            )
            for identity, actions in (
                ("friend", ["cross", "wait"] if mode == "reconciled" else ["cross"]),
                ("worker", ["wait"]),
            )
        ]
        responsive = deepcopy(model["mechanisms"][0])
        responsive.update(id="role-sensitive", respect_roles=True)
        model["mechanisms"].append(responsive)
    if mode == "coping_attention":
        for episode in model["affect"]["episodes"]:
            episode["coping"][0].update(action_ids=["wait"], horizon=2)
    if mode == "withdrawn":
        model["mental"]["assumptions"].append("unconfirmed-closure")
        model["mental"]["events"][0]["assumptions"] = ["unconfirmed-closure"]
    return candidate


def add_relationships(candidate):
    model = candidate["models"][0]
    mental = model["mental"]
    refs = model["observations"][0]["segment_ids"]
    offer = dict(
        id="offer-event",
        at=0,
        kind="message",
        effects={"safe": True},
        seen_by=[],
        received_by=["b"],
        understood_by=["b"],
        trusted_by=["b"],
        assumptions=[],
        segment_ids=refs,
    )
    mental["events"].insert(0, offer)
    model["interaction"]["utterances"] = [
        dict(
            id="offer",
            at=0,
            speaker="a",
            audience=["b"],
            version="v1",
            literal={"safe": True},
            deliveries=[
                dict(
                    event_id="offer-event",
                    readings=[
                        dict(
                            actor="b",
                            contents=[{"safe": True}],
                            versions=["v1"],
                            segment_ids=refs,
                        )
                    ],
                    segment_ids=refs,
                )
            ],
            segment_ids=refs,
        )
    ]
    model["interaction"]["commitments"] = [
        dict(
            id="terms",
            offer_id="offer",
            speaker="a",
            recipient="b",
            version="v1",
            condition={"op": "not", "arg": {"op": "atom", "name": "safe"}},
            outcome={"op": "atom", "name": "safe"},
            deadline=1,
            requires_acceptance=False,
            acceptance="QUALIFIED_ACT",
            activation="LATCHED",
            withdrawal="NO_RELEASE",
            segment_ids=refs,
        )
    ]

    def relation(identity, observer, target, dimension):
        return dict(
            id=identity,
            observer=observer,
            target=target,
            domain="route-support",
            dimension=dimension,
            hypotheses=[
                dict(
                    id="supportive",
                    label="supportive conditional model",
                    segment_ids=refs,
                ),
                dict(
                    id="limited",
                    label="limited conditional model",
                    segment_ids=refs,
                ),
            ],
            prior={"supportive": "1/2", "limited": "1/2"},
            factorization="CONDITIONAL_INDEPENDENCE_MODEL",
            updates=[],
            segment_ids=refs,
        )

    reliability = relation("reliability", "b", "a", "RELIABILITY")
    reliability["updates"] = [
        dict(
            id="breach",
            at=1,
            event_id="change-1",
            condition={"op": "not", "arg": {"op": "atom", "name": "safe"}},
            commitment_id="terms",
            commitment_status="BREACHED",
            likelihoods={"supportive": "1/4", "limited": "3/4"},
            segment_ids=refs,
        ),
        dict(
            id="repair",
            at=2,
            event_id="change-2",
            condition={"op": "atom", "name": "safe"},
            commitment_id="terms",
            commitment_status="BREACHED_THEN_FULFILLED",
            likelihoods={"supportive": "3/4", "limited": "1/4"},
            segment_ids=refs,
        ),
    ]
    model["relationships"] = [
        reliability,
        relation("ability", "b", "a", "ABILITY"),
        relation("goodwill", "b", "a", "GOODWILL"),
        relation("reverse", "a", "b", "RELIABILITY"),
    ]
    responsive = deepcopy(model["mechanisms"][0])
    responsive.update(
        id="responsive",
        label="relationship-responsive conditional priorities",
        priorities={"safety": "1/2", "duty": "1/2"},
        relationship_effects=[
            dict(
                relationship_id="reliability",
                multipliers={
                    "supportive": {"safety": "1", "duty": "3"},
                    "limited": {"safety": "3", "duty": "1"},
                },
                segment_ids=refs,
            )
        ],
    )
    model["mechanisms"].append(responsive)
    return candidate


def witness():
    rows = []
    computed = {}
    with tempfile.TemporaryDirectory() as temp:
        store = StateStore.sqlite(Path(temp) / "state.sqlite", revision=True)
        owner = Principal("witness", "owner")
        store.create_session("s", owner)
        handle = store.put_source("s", owner, "records", SOURCE)
        try:
            for mode in (
                "stable",
                "counterevidence",
                "relationship",
                "null_prior",
                "unreceived",
                "contradicted",
                "role_conflict",
                "reconciled",
                "coping_attention",
                "withdrawn",
                "budget",
            ):
                request = TaskRequest(
                    "relationship-" + mode,
                    "Which conditional mechanisms fit across contexts and what follows next?",
                    (handle,),
                    "s",
                    owner,
                    budget=ExecutionBudget(
                        max_mock_calls=1,
                        max_local_evaluations=1 if mode == "budget" else 16000,
                        max_request_bytes=1048576,
                        max_output_bytes=4194304,
                        max_total_output_bytes=16777216,
                        max_context_tokens=1048576,
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
                client = HCL(store, principal=owner, gateway=ModelGateway(store, port))
                result = client.run_sync(request)
                assert result.status == (
                    "PARTIAL"
                    if mode in ("contradicted", "withdrawn", "budget")
                    else "COMPLETED"
                ), (mode, result.status, result.diagnostics)
                actual = next(
                    r
                    for r in store.inferences("s", owner)
                    if r.result_id in result.execution_receipt["result_ids"]
                )
                model = actual.values["models"][0]
                computed[mode] = model
                assert (
                    model["cognition"]["actual"]
                    == model["actual_interaction"]["values"]["models"][0][
                        "actual_mental"
                    ]
                    == model["actual_affect"]["values"]["models"][0]["actual_mental"]
                )
                if mode == "relationship":
                    history = model["relationships"][0]["history"]
                    assert history[0]["commitment"]["status"] == "BREACHED"
                    assert history[0]["weights"] == {
                        "supportive": "1/4",
                        "limited": "3/4",
                    }
                    assert (
                        history[1]["commitment"]["status"] == "BREACHED_THEN_FULFILLED"
                    )
                    assert history[1]["weights"] == {
                        "supportive": "1/2",
                        "limited": "1/2",
                    }
                    assert all(not r["history"] for r in model["relationships"][1:])
                if mode == "null_prior":
                    assert model["relationships"][0]["weights"] is None
                if mode == "unreceived":
                    assert (
                        model["relationships"][0]["history"][0]["qualification"]
                        == "INAPPLICABLE"
                    )
                if mode == "contradicted":
                    assert "RELATIONSHIP_MODEL_CONTRADICTED" in result.answer
                if mode in ("role_conflict", "reconciled"):
                    role = next(r for r in model["roles"] if r["at"] == 3)
                    assert role["branches"][0]["feasible_reconciliation_actions"] == (
                        ("wait",) if mode == "reconciled" else ()
                    )
                if mode == "stable":
                    safety = next(
                        m["mechanism_id"]
                        for m in model["mechanisms"]
                        if m["input"]["id"] == "safety"
                    )
                    assert [
                        r["values"] for r in model["prediction_matrix"][safety]
                    ] == [("wait",), ("cross",), ("wait",), ("cross",)]
                    stable = next(
                        t
                        for t in model["longitudinal"]["trajectories"]
                        if t["path"] == (safety,) * 4
                    )
                    assert (
                        not stable["change_points"]
                        and len(stable["profile"]["explained"]) == 4
                    )
                replay = client.run_sync(request)
                assert (replay.answer, replay.claim_records) == (
                    result.answer,
                    result.claim_records,
                ) and port.attempts == 1
                assert (
                    result.usage["local_evaluations"]
                    <= request.budget.max_local_evaluations
                )
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
                computed["stable"]["cognition"]
                == computed["counterevidence"]["cognition"]
                or computed["stable"]["cognition"]["actual"]["values"]["models"]
                == computed["counterevidence"]["cognition"]["actual"]["values"][
                    "models"
                ]
            )
            assert any(
                t["change_points"]
                for t in computed["counterevidence"]["preferred_forecasts"]
            )
            assert any(
                p["values"] == ("wait",)
                for t in computed["counterevidence"]["preferred_forecasts"]
                for p in t["predictions"]
            )
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
        schema="hcl-unified-relationship-witness-1",
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
        evidence_scope="FINITE_DECLARED_SHARED_M03_M05_M07_M08_M09_LONGITUDINAL_COMPOSITION",
        not_established=[
            "OPEN_EXTRACTION",
            "SEMANTIC_ALIGNMENT",
            "CANDIDATE_COMPLETENESS",
            "INDEPENDENT_CONTEXT_CERTIFICATION",
            "LIKELIHOOD_CALIBRATION",
            "PRIVATE_TRUST_IDENTITY_VALUES",
            "GENERAL_INTERVAL_PRIORS",
            "FULL_M09",
            "FULL_S3",
            "LIVE_EFFECT",
        ],
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.write_text(
        json.dumps(witness(), ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    )

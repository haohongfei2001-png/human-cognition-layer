"""Actual goal appraisal/action consequences under injected source hypotheses."""

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
from scripts.witness_unified_interaction import propose as mental_candidate

SOURCE = (
    "A and B initially know the passage is safe; at time 1 only B observes closure. "
    "B expected crossing to succeed. Under the proposed transition model crossing an open passage succeeds, "
    "crossing a closed passage causes harm, and waiting ends this local episode. "
    "For safety the declared consequences are open 3, closed -3, success 5, harm -5, waiting -1. "
    "The conflicting duty goal has opposite consequences. One coping hypothesis initially gives each goal half weight, "
    "then triples safety attention if safety deteriorates. Another prioritizes duty and considers only crossing. "
    "B reports sadness while an observer reports a smile. Neither channel determines a unique feeling. "
    "Alternative later hypotheses specify a trusted reopening report, an undelivered report, or revised goal consequences. "
    "These interpretations and semantic mappings are explicit experimental inputs, not verified natural-language extraction."
)


def propose(snapshot, question, mode):
    mental = mental_candidate(snapshot, question, "strategic")["models"][0]["mental"]
    refs = mental["variables"][0]["segment_ids"]
    mental["variables"][0].update(initial=True, observed_by=["a", "b"])
    mental["events"] = [
        dict(
            id="closure",
            at=1,
            kind="change",
            effects={"safe": False},
            seen_by=["b"],
            received_by=[],
            understood_by=[],
            trusted_by=[],
            assumptions=[],
            segment_ids=refs,
        )
    ]
    plan = mental["plans"][0]
    plan["weights"] = {"b": "1"}
    safety = dict(r="3", b="-3", success="5", harm="-5", waited="-1")
    goals = [
        dict(id="safety", label="safety concern", utilities=safety, segment_ids=refs),
        dict(
            id="duty",
            label="conflicting duty",
            utilities={s: str(-int(v)) for s, v in safety.items()},
            segment_ids=refs,
        ),
    ]
    condition = dict(goal_id="safety", dimension="change_direction", value="NEGATIVE")
    mappings = [
        dict(
            id="loss",
            label="distress candidate",
            conditions=[condition],
            requires_previous=[],
            segment_ids=refs,
        ),
        dict(
            id="gain",
            label="satisfaction candidate",
            conditions=[
                dict(goal_id="duty", dimension="change_direction", value="POSITIVE")
            ],
            requires_previous=[],
            segment_ids=refs,
        ),
    ]
    coping = [
        dict(
            id="safety-focus",
            kind="PROBLEM_FOCUSED",
            priorities=dict(safety="1/2", duty="1/2"),
            horizon=1,
            action_ids=["cross", "wait"],
            observation_overrides={},
            segment_ids=refs,
            adjustments=[
                dict(
                    id="attention-change",
                    conditions=[condition],
                    multipliers=dict(safety="3", duty="1"),
                    segment_ids=refs,
                )
            ],
        ),
        dict(
            id="duty-focus",
            kind="AVOIDANCE",
            priorities=dict(safety="1/4", duty="3/4"),
            horizon=1,
            action_ids=["cross"],
            observation_overrides={},
            adjustments=[],
            segment_ids=refs,
        ),
    ]
    episode = dict(
        id="closure-v1",
        episode_id="closure",
        actor="b",
        before=0,
        at=1,
        plan_id=plan["id"],
        previous_weights={"r": "1"},
        current_weights={"b": "1"},
        forecast_action="cross",
        goals=goals,
        mappings=mappings,
        coping=coping,
        previous_id=None,
        revision_kind="INITIAL",
        segment_ids=refs,
    )
    channels = [
        dict(
            id="self-report",
            actor="b",
            speaker="b",
            at=1,
            kind="SELF_REPORT",
            content="sadness report",
            segment_ids=refs,
        ),
        dict(
            id="expression",
            actor="b",
            speaker="observer",
            at=1,
            kind="EXPRESSION",
            content="smile observed",
            segment_ids=refs,
        ),
    ]
    model = dict(mental=mental, episodes=[episode], channels=channels)
    if mode in ("informed", "undelivered", "goal_revision", "analyst"):
        target = "b" if mode in ("informed", "analyst") else "a"
        mental["active_assumptions"].append("later-report")
        mental["events"].append(
            dict(
                id="reopening-report",
                at=2,
                kind="message",
                effects={"safe": True},
                seen_by=[],
                received_by=[target],
                understood_by=[target],
                trusted_by=[target],
                assumptions=["later-report"],
                segment_ids=refs,
            )
        )
        updated = deepcopy(episode)
        updated.update(
            id="closure-v2",
            at=2,
            plan_id="later-plan",
            previous_id=episode["id"],
            revision_kind=(
                "GOAL_REVISION"
                if mode == "goal_revision"
                else (
                    "ANALYST_REINTERPRETATION"
                    if mode == "analyst"
                    else "NEW_INFORMATION"
                )
            ),
            current_weights={"r": "1"} if target == "b" else {"b": "1"},
        )
        if mode == "goal_revision":
            updated["goals"][0]["utilities"] = {
                s: str(-int(v)) for s, v in safety.items()
            }
        later = deepcopy(plan)
        later.update(id="later-plan", at=2, weights=updated["current_weights"])
        mental["plans"].append(later)
        model["episodes"].append(updated)
    if mode == "unknown":
        mental["variables"][0]["observed_by"] = []
        mental["events"] = []
        plan["weights"] = None
        episode["previous_weights"] = episode["current_weights"] = None
    if mode == "zero_priority":
        coping[0]["adjustments"][0]["multipliers"] = dict(safety="0", duty="0")
    if mode == "disconnected":
        coping[0]["adjustments"] = []
    return dict(schema="hcl-affect-candidates-1", models=[model])


def witness():
    rows = []
    calculations = {}
    with tempfile.TemporaryDirectory() as directory:
        store = StateStore.sqlite(Path(directory) / "state.sqlite", revision=True)
        owner = Principal("synthetic", "reader")
        store.create_session("s", owner)
        handle = store.put_source("s", owner, "records", SOURCE)
        try:
            for mode in (
                "mixed",
                "informed",
                "undelivered",
                "goal_revision",
                "analyst",
                "unknown",
                "zero_priority",
                "disconnected",
                "budget",
            ):
                request = TaskRequest(
                    mode,
                    "What follows conditionally from the proposed appraisal and coping mechanisms?",
                    (handle,),
                    "s",
                    owner,
                    budget=ExecutionBudget(
                        max_mock_calls=1,
                        max_local_evaluations=1 if mode == "budget" else 4096,
                        max_request_bytes=1048576,
                        max_output_bytes=1048576,
                        max_context_tokens=1048576,
                        max_total_output_bytes=16777216,
                        max_visible_output_tokens=1048576,
                    ),
                    issue=ExecutionIssue(
                        "root", goals=(Issue(mode, "affect.evaluate"),)
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
                    if mode in ("unknown", "zero_priority", "budget")
                    else "COMPLETED"
                ), (mode, result.diagnostics)
                actual = next(
                    r
                    for r in store.inferences("s", owner)
                    if r.result_id in result.execution_receipt["result_ids"]
                )
                episodes = actual.values["models"][0]["episodes"]
                calculations[mode] = episodes
                if mode not in ("budget", "unknown"):
                    first = episodes[0]["derived"]
                    assert (
                        first["profiles"][0]["appraisal"]["state_change"]["lower"]
                        == "-6"
                    )
                    assert (
                        first["profiles"][1]["appraisal"]["state_change"]["lower"]
                        == "6"
                    )
                    assert (
                        first["profiles"][0]["appraisal"]["expectation_gap"]["lower"]
                        == "-8"
                    )
                    if mode not in ("zero_priority", "disconnected"):
                        coping = first["coping"][0]["branches"][0]
                        assert coping["input"]["priorities"] == {
                            "safety": "3/4",
                            "duty": "1/4",
                        }
                        assert coping["computation"]["q"] == {
                            "cross": "-5/2",
                            "wait": "-1/2",
                        }
                        assert coping["computation"]["best_actions"] == ("wait",)
                if len(episodes) > 1:
                    assert episodes[1]["derived"]["profiles"][0]["appraisal"][
                        "current_value"
                    ]["lower"] == ("-3" if mode == "undelivered" else "3")
                    assert "later-report" not in episodes[0]["assumption_environments"]
                    assert "later-report" in episodes[1]["assumption_environments"]
                if mode == "unknown":
                    assert "COPING_PROBABILITY_UNSPECIFIED" in result.answer
                if mode == "zero_priority":
                    assert "COPING_ZERO_PRIORITY_UNDEFINED" in result.answer
                if mode == "analyst":
                    assert "NOT_ESTABLISHED_ANALYST_ALTERNATIVE" in result.answer
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
                calculations["mixed"][0]["derived"]["coping"][0]["branches"][0][
                    "computation"
                ]["q"]
                != calculations["disconnected"][0]["derived"]["coping"][0]["branches"][
                    0
                ]["computation"]["q"]
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
        schema="hcl-unified-affect-witness-1",
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
        evidence_scope="FINITE_DECLARED_M03_M05_M08_COMPOSITION_WITH_INJECTED_INTERPRETATIONS",
        not_established=[
            "OPEN_EXTRACTION",
            "SEMANTIC_ALIGNMENT",
            "CANDIDATE_COMPLETENESS",
            "ATTRIBUTION_NORM_IDENTITY_APPRAISAL",
            "HUMAN_CALIBRATION",
            "PRIVATE_EMOTION",
            "FULL_M08",
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

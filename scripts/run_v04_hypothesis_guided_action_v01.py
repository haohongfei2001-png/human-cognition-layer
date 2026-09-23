"""Frozen internal C/D/E comparison for hypothesis-guided action v0.1."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from hcl.v04.hypotheses import HypothesisTracker
from hcl.v04.model import EventRecord
from hcl.v04.probe_policy import ActionOption, HypothesisGuidedPolicy, ProbeOption
from hcl.v04.store import CognitionStore
from scripts.run_v04_latent_hypothesis_capability_v01 import (
    event_from_mapping,
    event_payload,
    hidden_rank,
    make_backend,
    signature,
    target_from_mapping,
)


DIRECT_PROBE_SYSTEM = """Choose one allowed probe using the visible event history.
The latent candidate definitions are possibilities, not known truth.
Prefer a probe that separates plausible candidates and avoids redundant questions.
Return JSON only: {"probe_id": "<allowed id>", "rationale": "short reason"}.
"""

DIRECT_ACTION_SYSTEM = """Choose one allowed action using the full visible
history, including the probe response. Do not assume the hidden state.
Return JSON only: {"action_id": "<allowed id>", "rationale": "short reason"}.
"""

REPAIR_SYSTEM = """Repair the prior output to valid JSON with an allowed exact
option ID and a non-empty rationale. Return JSON only. Do not change the task.
"""


def validate_fixtures(fixtures: list[dict]) -> None:
    assert fixtures, "at least one frozen scenario is required"
    scenario_ids = set()
    for scenario in fixtures:
        sid = scenario["id"]
        assert sid not in scenario_ids, f"duplicate scenario: {sid}"
        scenario_ids.add(sid)
        candidate_ids = {row[0] for row in scenario["target"]["candidates"]}
        probes = {row[0] for row in scenario["probes"]}
        actions = {row[0] for row in scenario["actions"]}
        assert len(candidate_ids) == len(scenario["target"]["candidates"]) == 3
        assert len(probes) == len(scenario["probes"]) == 3
        assert len(actions) == len(scenario["actions"]) == 3
        assert scenario["hidden_target"] in candidate_ids
        assert set(scenario["high_information_probes"]) <= probes
        assert set(scenario["probe_responses"]) == candidate_ids
        assert set(scenario["correct_actions"]) == candidate_ids
        assert all(set(responses) == probes for responses in scenario["probe_responses"].values())
        assert set(scenario["correct_actions"].values()) <= actions
        event_ids = [event["event_id"] for event in scenario["initial_events"]]
        assert len(event_ids) == len(set(event_ids)) and event_ids


def visible_target(target) -> dict:
    return {
        "target_id": target.target_id,
        "subject_agent_id": target.subject_agent_id,
        "target_kind": target.target_kind,
        "question": target.question,
        "candidate_definitions": list(target.candidate_definitions) + [
            ("OTHER_UNKNOWN", "Other or currently unknown explanation.")
        ],
    }


def options(rows: list[list[str]]) -> list[dict]:
    return [{"id": row[0], "description": row[1]} for row in rows]


def direct_choice(backend, *, system: str, target, events, choices, key: str) -> tuple[str, bool]:
    allowed = {row[0] for row in choices}
    task = {
        "target": visible_target(target),
        "event_history": [event_payload(event) for event in events],
        "allowed_options": options(choices),
    }
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": json.dumps(task, sort_keys=True)},
    ]
    raw = backend.complete_json(messages, max_tokens=384, temperature=0.0)
    for attempt in range(2):
        try:
            answer = json.loads(raw)
            choice = answer[key]
            rationale = answer["rationale"]
            if isinstance(choice, str) and choice in allowed and isinstance(rationale, str) and rationale.strip():
                return choice, bool(attempt)
        except (json.JSONDecodeError, KeyError, TypeError):
            pass
        if attempt == 0:
            raw = backend.complete_json(
                [
                    {"role": "system", "content": REPAIR_SYSTEM},
                    {"role": "user", "content": json.dumps({
                        "task": task,
                        "invalid_output": raw,
                        "required_key": key,
                        "allowed_ids": sorted(allowed),
                    }, sort_keys=True)},
                ],
                max_tokens=384,
                temperature=0.0,
            )
    raise ValueError(f"invalid direct {key} output after bounded repair")


def response_event(scenario: dict, probe_id: str) -> EventRecord:
    hidden = scenario["hidden_target"]
    probe_description = dict(scenario["probes"])[probe_id]
    response = scenario["probe_responses"][hidden][probe_id]
    last_event_time = max(
        datetime.fromisoformat(event["valid_time"])
        for event in scenario["initial_events"]
    )
    observed_time = last_event_time + timedelta(minutes=1)
    return EventRecord(
        event_id=f"{scenario['id']}:probe-response",
        valid_time=observed_time.isoformat(),
        recorded_at=(observed_time + timedelta(seconds=1)).isoformat(),
        raw_text=f"Probe: {probe_description}\nObserved response: {response}",
        source_id=scenario["target"]["subject_agent_id"],
        actor_id=scenario["target"]["subject_agent_id"],
        observer_ids=("experimenter",),
        recipient_ids=(),
        semantic_version="v04.1",
        metadata={"selected_probe_id": probe_id},
    )


def initial_history(scenario: dict) -> list[EventRecord]:
    return [event_from_mapping(event) for event in scenario["initial_events"]]


def reconstruct(target, events: list[EventRecord], backend):
    store = CognitionStore()
    tracker = HypothesisTracker(store)
    tracker.create_target(target)
    for event in events:
        store.append_event(event)
    receipt = tracker.update(target.target_id, [event.event_id for event in events], backend)
    return store, tracker, receipt


def run_structured(scenario: dict, backend, *, persistent: bool) -> dict:
    target = target_from_mapping(scenario["target"])
    history = initial_history(scenario)
    policy = HypothesisGuidedPolicy()
    probe_options = tuple(ProbeOption(*row) for row in scenario["probes"])
    action_options = tuple(ActionOption(*row) for row in scenario["actions"])
    store, tracker, initial_receipt = reconstruct(target, history, backend)
    repairs = int(initial_receipt.repaired)
    try:
        initial_state = tracker.current(target.target_id)
        probe = policy.choose_probe(
            target, initial_state, [event_payload(event) for event in history],
            probe_options, backend,
        )
        repairs += int(probe.repaired)
        observed = response_event(scenario, probe.probe_id)
        if persistent:
            store.append_event(observed)
            update_receipt = tracker.update(target.target_id, [observed.event_id], backend)
            repairs += int(update_receipt.repaired)
            final_state = tracker.current(target.target_id)
            action = policy.choose_action(
                target, final_state,
                [event_payload(event) for event in history + [observed]],
                action_options, backend,
            )
        else:
            store.close()
            store = None
            rebuilt, rebuilt_tracker, update_receipt = reconstruct(
                target, history + [observed], backend,
            )
            store = rebuilt
            repairs += int(update_receipt.repaired)
            final_state = rebuilt_tracker.current(target.target_id)
            action = policy.choose_action(
                target, final_state,
                [event_payload(event) for event in history + [observed]],
                action_options, backend,
            )
        repairs += int(action.repaired)
        return {
            "scenario": scenario["id"],
            "probe_id": probe.probe_id,
            "high_information_probe": probe.probe_id in scenario["high_information_probes"],
            "action_id": action.action_id,
            "gold_action_id": scenario["correct_actions"][scenario["hidden_target"]],
            "correct": action.action_id == scenario["correct_actions"][scenario["hidden_target"]],
            "hidden_diagnostic": hidden_rank(final_state, scenario["hidden_target"]),
            "state_signature": signature(final_state),
            "repairs": repairs,
        }
    finally:
        if store is not None:
            store.close()


def run_direct(scenario: dict, backend) -> dict:
    target = target_from_mapping(scenario["target"])
    history = initial_history(scenario)
    probe_id, probe_repaired = direct_choice(
        backend, system=DIRECT_PROBE_SYSTEM, target=target, events=history,
        choices=scenario["probes"], key="probe_id",
    )
    observed = response_event(scenario, probe_id)
    action_id, action_repaired = direct_choice(
        backend, system=DIRECT_ACTION_SYSTEM, target=target,
        events=history + [observed], choices=scenario["actions"], key="action_id",
    )
    return {
        "scenario": scenario["id"],
        "probe_id": probe_id,
        "high_information_probe": probe_id in scenario["high_information_probes"],
        "action_id": action_id,
        "gold_action_id": scenario["correct_actions"][scenario["hidden_target"]],
        "correct": action_id == scenario["correct_actions"][scenario["hidden_target"]],
        "repairs": int(probe_repaired) + int(action_repaired),
    }


def summary(rows: list[dict], backend) -> dict:
    count = len(rows)
    return {
        "correct": sum(row["correct"] for row in rows),
        "total": count,
        "high_information_probes": sum(row["high_information_probe"] for row in rows),
        "repairs": sum(row["repairs"] for row in rows),
        "hidden_top_or_tied": sum(
            row.get("hidden_diagnostic", {}).get("hidden_top_or_tied", False)
            for row in rows
        ) if rows and "hidden_diagnostic" in rows[0] else None,
        "backend": backend.metrics(),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixtures", default="eval/v04/hypothesis_guided_action_v01.json")
    parser.add_argument("--model", default="deepseek-flash")
    parser.add_argument("--base-url", default=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"))
    parser.add_argument("--out", default="artifacts/hcl-v04-guided-action-v01/result.json")
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()
    fixture_bytes = Path(args.fixtures).read_bytes()
    fixtures = json.loads(fixture_bytes)
    validate_fixtures(fixtures)
    fixture_sha256 = hashlib.sha256(fixture_bytes).hexdigest()
    if args.validate_only:
        print(json.dumps({"scenarios": len(fixtures), "fixture_sha256": fixture_sha256}))
        return

    api_key = os.environ["DEEPSEEK_API_KEY"]
    backends = {
        arm: make_backend(api_key, args.base_url, args.model)
        for arm in ("C", "D", "E")
    }
    rows = {"C": [], "D": [], "E": []}
    for scenario in fixtures:
        rows["C"].append(run_structured(scenario, backends["C"], persistent=False))
        rows["D"].append(run_structured(scenario, backends["D"], persistent=True))
        rows["E"].append(run_direct(scenario, backends["E"]))
    output = {
        "format": "hcl-v04-hypothesis-guided-action-capability-v01",
        "model": args.model,
        "seed": 42,
        "fixture_sha256": fixture_sha256,
        "scenario_count": len(fixtures),
        "arms": {arm: summary(rows[arm], backends[arm]) for arm in rows},
        "c_d_state_comparison": {
            "same_probe": sum(
                c["probe_id"] == d["probe_id"]
                for c, d in zip(rows["C"], rows["D"])
            ),
            "equal_when_same_probe": sum(
                c["probe_id"] == d["probe_id"]
                and c["state_signature"] == d["state_signature"]
                for c, d in zip(rows["C"], rows["D"])
            ),
        },
        "rows": rows,
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(output, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({"arms": output["arms"], "artifact": str(out)}, sort_keys=True))


if __name__ == "__main__":
    main()

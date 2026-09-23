"""Frozen internal C/D/E/F comparison for evidence-scoped revision v0.1."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

FROZEN_FIXTURE_SHA256 = "7f08cbe1f5dd8207f505f37a9354440c28450d2462f7b0177cf184b10a4aa6ab"
DEFAULT_FIXTURES = "eval/v04/evidence_scoped_revision_v01.json"


def validate_frozen(fixtures: list[dict], digest: str) -> None:
    if digest != FROZEN_FIXTURE_SHA256:
        raise ValueError("frozen evidence-scoped fixture hash changed")
    if len(fixtures) != 6 or len({item["id"] for item in fixtures}) != 6:
        raise ValueError("expected six distinct frozen scenarios")
    if not any(not event.get("metadata", {}).get("target_ids") for scene in fixtures for event in scene["initial_events"]):
        raise ValueError("conservative unscoped evidence case is required")
    for scene in fixtures:
        if len(scene["initial_events"]) != 4:
            raise ValueError("each scene requires four initial events")
        ids = [event["event_id"] for event in scene["initial_events"]]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate event ID")
        candidates = {item[0] for item in scene["target"]["candidates"]}
        probes = {item[0] for item in scene["probes"]}
        actions = {item[0] for item in scene["actions"]}
        if len(candidates) != 3 or len(probes) != 3 or len(actions) != 3:
            raise ValueError("three candidates, probes and actions are required")
        if set(scene["probe_responses"]) != candidates or set(scene["correct_actions"]) != candidates:
            raise ValueError("hidden candidate mapping mismatch")
        if scene["hidden_target"] not in candidates:
            raise ValueError("unregistered hidden candidate")
        if not set(scene["high_information_probes"]) <= probes:
            raise ValueError("unregistered high-information probe")
        if not set(scene["correct_actions"].values()) <= actions:
            raise ValueError("unregistered correct action")
        for candidate in candidates:
            if set(scene["probe_responses"][candidate]) != probes:
                raise ValueError("incomplete probe response matrix")


def run_eager(scene: dict, backend) -> dict:
    from hcl.v04.hypotheses import HypothesisTracker
    from hcl.v04.probe_policy import ActionOption, HypothesisGuidedPolicy, ProbeOption
    from hcl.v04.store import CognitionStore
    from scripts.run_v04_hypothesis_guided_action_v01 import (
        event_payload, hidden_rank, initial_history, response_event, signature,
    )
    from scripts.run_v04_latent_hypothesis_capability_v01 import target_from_mapping

    target = target_from_mapping(scene["target"])
    events = initial_history(scene)
    store = CognitionStore()
    tracker = HypothesisTracker(store)
    tracker.create_target(target)
    policy = HypothesisGuidedPolicy()
    repairs = 0
    try:
        for event in events:
            store.append_event(event)
            repairs += int(tracker.update(target.target_id, (event.event_id,), backend).repaired)
        probe = policy.choose_probe(
            target, tracker.current(target.target_id),
            [event_payload(event) for event in events],
            tuple(ProbeOption(*item) for item in scene["probes"]), backend,
        )
        repairs += int(probe.repaired)
        observed = response_event(scene, probe.probe_id)
        store.append_event(observed)
        repairs += int(tracker.update(target.target_id, (observed.event_id,), backend).repaired)
        final = tracker.current(target.target_id)
        action = policy.choose_action(
            target, final, [event_payload(event) for event in events + [observed]],
            tuple(ActionOption(*item) for item in scene["actions"]), backend,
        )
        repairs += int(action.repaired)
        return {
            "scenario": scene["id"], "probe_id": probe.probe_id,
            "high_information_probe": probe.probe_id in scene["high_information_probes"],
            "action_id": action.action_id,
            "gold_action_id": scene["correct_actions"][scene["hidden_target"]],
            "correct": action.action_id == scene["correct_actions"][scene["hidden_target"]],
            "hidden_diagnostic": hidden_rank(final, scene["hidden_target"]),
            "state_signature": signature(final), "repairs": repairs,
        }
    finally:
        store.close()


def run_scoped(scene: dict, backend) -> dict:
    from hcl.v04.evidence_scoped_revision import EvidenceScopedRevision
    from hcl.v04.hypotheses import HypothesisTarget
    from hcl.v04.probe_policy import ActionOption, HypothesisGuidedPolicy, ProbeOption
    from hcl.v04.store import CognitionStore
    from scripts.run_v04_hypothesis_guided_action_v01 import (
        event_payload, hidden_rank, initial_history, response_event, signature,
    )
    from scripts.run_v04_latent_hypothesis_capability_v01 import target_from_mapping

    target = target_from_mapping(scene["target"])
    store = CognitionStore()
    revision = EvidenceScopedRevision(store)
    revision.register_target(target)
    side = scene["id"] + "-other"
    revision.register_target(HypothesisTarget(
        target_id=side, subject_agent_id="other", target_kind="CONTROL",
        question="Unqueried distractor target", candidate_definitions=target.candidate_definitions,
    ))
    policy = HypothesisGuidedPolicy()
    repairs = 0
    try:
        for event in initial_history(scene):
            scope = event.metadata.get("target_ids")
            revision.record(event, target_ids=tuple(scope) if scope else None)
        first = revision.refresh(target.target_id, backend)
        repairs += int(first.receipt.repaired) if first.receipt else 0
        probe = policy.choose_probe(
            target, first.state,
            [event_payload(event) for event in revision.evidence_for_target(target.target_id)],
            tuple(ProbeOption(*item) for item in scene["probes"]), backend,
        )
        repairs += int(probe.repaired)
        observed = response_event(scene, probe.probe_id)
        revision.record(observed, target_ids=(target.target_id,))
        second = revision.refresh(target.target_id, backend)
        repairs += int(second.receipt.repaired) if second.receipt else 0
        action = policy.choose_action(
            target, second.state,
            [event_payload(event) for event in revision.evidence_for_target(target.target_id)],
            tuple(ActionOption(*item) for item in scene["actions"]), backend,
        )
        repairs += int(action.repaired)
        return {
            "scenario": scene["id"], "probe_id": probe.probe_id,
            "high_information_probe": probe.probe_id in scene["high_information_probes"],
            "action_id": action.action_id,
            "gold_action_id": scene["correct_actions"][scene["hidden_target"]],
            "correct": action.action_id == scene["correct_actions"][scene["hidden_target"]],
            "hidden_diagnostic": hidden_rank(second.state, scene["hidden_target"]),
            "state_signature": signature(second.state), "repairs": repairs,
            "skipped_unrelated": first.skipped_unrelated,
        }
    finally:
        store.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixtures", default=DEFAULT_FIXTURES)
    parser.add_argument("--model", default="deepseek-flash")
    parser.add_argument("--base-url", default=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"))
    parser.add_argument("--out", default="artifacts/hcl-v04-evidence-scoped-v01/result.json")
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()
    data = Path(args.fixtures).read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    fixtures = json.loads(data)
    validate_frozen(fixtures, digest)
    if args.validate_only:
        print(json.dumps({"scenarios": len(fixtures), "fixture_sha256": digest}))
        return

    from scripts.run_v04_hypothesis_guided_action_v01 import (
        run_direct, run_structured, summary,
    )
    from scripts.run_v04_latent_hypothesis_capability_v01 import make_backend

    api_key = os.environ["DEEPSEEK_API_KEY"]
    backends = {arm: make_backend(api_key, args.base_url, args.model) for arm in "CDEF"}
    rows: dict[str, list[dict]] = {arm: [] for arm in "CDEF"}
    for scene in fixtures:
        rows["C"].append(run_structured(scene, backends["C"], persistent=False))
        rows["D"].append(run_eager(scene, backends["D"]))
        rows["E"].append(run_direct(scene, backends["E"]))
        rows["F"].append(run_scoped(scene, backends["F"]))
    output = {
        "format": "hcl-v04-evidence-scoped-revision-v01", "model": args.model,
        "fixture_sha256": digest, "scenario_count": len(fixtures),
        "arms": {arm: summary(rows[arm], backends[arm]) for arm in rows},
        "rows": rows,
        "claim_boundary": "internal synthetic diagnostic only; no external efficacy claim",
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(output, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({"arms": output["arms"], "artifact": str(out)}, sort_keys=True))


if __name__ == "__main__":
    main()

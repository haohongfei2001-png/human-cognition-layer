"""Frozen C/D/E internal diagnostic for perspective-safe correction actions."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from hcl.v04 import CognitionStore, EventRecord, HypothesisTarget, HypothesisTracker
from hcl.v04.probe_policy import ActionOption, HypothesisGuidedPolicy
from scripts.validate_v04_perspective_safe_action_v01 import FIXTURE, preflight, visible_case


DIRECT_ACTION_SYSTEM = """Choose one allowed action for the named recipient using only
the visible event history. A system-observed correction is not automatically
received by the recipient. Receipt is not acceptance; a later revision needs
its own evidence. A disputed source claim is not established world truth.
Return JSON only: {"action_id":"<allowed id>","rationale":"short evidence-grounded reason"}.
"""

REPAIR_SYSTEM = """Repair the previous output to valid JSON with exactly one
allowed action_id and a nonempty rationale. Do not change the task or add facts.
"""


class RecordingBackend:
    def __init__(self, backend):
        self.backend = backend
        self.calls: list[dict] = []
        self.input_chars = 0
        self.output_chars = 0

    def complete_json(self, messages, *, max_tokens, temperature=0.0):
        if len(self.calls) >= 96:
            raise RuntimeError("frozen provider-call ceiling exceeded")
        self.input_chars += sum(len(str(message.get("content", ""))) for message in messages)
        output = self.backend.complete_json(messages, max_tokens=max_tokens, temperature=temperature)
        self.output_chars += len(output)
        self.calls.append({"messages": messages, "output": output})
        return output

    def metrics(self):
        return {"calls": len(self.calls), "input_chars": self.input_chars, "output_chars": self.output_chars}


def target_from_case(case: dict) -> HypothesisTarget:
    raw = case["hypothesis_target"]
    return HypothesisTarget(
        target_id=raw["target_id"], subject_agent_id=raw["subject_agent_id"],
        target_kind=raw["target_kind"], question=raw["question"],
        candidate_definitions=tuple((row[0], row[1]) for row in raw["candidates"]),
    )


def event_from_fixture(raw: dict) -> EventRecord:
    return EventRecord(
        event_id=raw["event_id"], valid_time=raw["valid_time"], recorded_at=raw["recorded_at"],
        raw_text=raw["raw_text"], source_id=raw["source_id"], actor_id=raw["actor_id"],
        observer_ids=tuple(raw["observer_ids"]), recipient_ids=tuple(raw["recipient_ids"]),
        metadata=dict(raw["metadata"]),
    )


def state_evidence(state) -> list[dict]:
    return [{
        "label": candidate.label, "status": candidate.status.value,
        "support_event_ids": list(candidate.support_event_ids),
        "counterevidence_event_ids": list(candidate.counterevidence_event_ids),
        "unresolved_event_ids": list(candidate.unresolved_event_ids),
        "rationale": candidate.rationale,
    } for candidate in state.candidates]


def run_structured(case: dict, backend: RecordingBackend, *, persistent: bool) -> dict:
    events = [event_from_fixture(raw) for raw in case["events"]]
    target = target_from_case(case)
    store = CognitionStore()
    repairs = 0
    try:
        tracker = HypothesisTracker(store)
        tracker.create_target(target)
        if persistent:
            for event in events:
                store.append_event(event)
                receipt = tracker.update(target.target_id, [event.event_id], backend)
                repairs += int(receipt.repaired)
        else:
            for event in events:
                store.append_event(event)
            receipt = tracker.update(target.target_id, [event.event_id for event in events], backend)
            repairs += int(receipt.repaired)
        state = tracker.current(target.target_id)
        action = HypothesisGuidedPolicy().choose_action(
            target, state, case["events"],
            tuple(ActionOption(*row) for row in case["allowed_actions"]), backend,
        )
        repairs += int(action.repaired)
        return {
            "case_id": case["id"], "action_id": action.action_id,
            "correct": action.action_id == case["expected_action"],
            "rationale": action.rationale, "state": state_evidence(state),
            "repairs": repairs,
        }
    finally:
        store.close()


def run_direct(case: dict, backend: RecordingBackend) -> dict:
    task = visible_case(case)
    allowed = {row[0] for row in case["allowed_actions"]}
    raw = backend.complete_json([
        {"role": "system", "content": DIRECT_ACTION_SYSTEM},
        {"role": "user", "content": json.dumps(task, ensure_ascii=False, sort_keys=True)},
    ], max_tokens=384, temperature=0.0)
    for attempt in range(2):
        try:
            value = json.loads(raw)
            action_id = value["action_id"]
            rationale = value["rationale"]
            if isinstance(action_id, str) and action_id in allowed and isinstance(rationale, str) and rationale.strip():
                return {
                    "case_id": case["id"], "action_id": action_id,
                    "correct": action_id == case["expected_action"],
                    "rationale": rationale, "repairs": attempt,
                }
        except (json.JSONDecodeError, KeyError, TypeError):
            pass
        if attempt == 0:
            raw = backend.complete_json([
                {"role": "system", "content": REPAIR_SYSTEM},
                {"role": "user", "content": json.dumps({
                    "task": task, "invalid_output": raw, "allowed_action_ids": sorted(allowed),
                }, ensure_ascii=False, sort_keys=True)},
            ], max_tokens=384, temperature=0.0)
    raise ValueError(f"{case['id']}: invalid direct action after bounded repair")


def run_comparison(backend_factory) -> dict:
    freeze = preflight()
    cases = json.loads(FIXTURE.read_text())["cases"]
    backends = {arm: RecordingBackend(backend_factory()) for arm in ("C", "D", "E")}
    rows = {arm: [] for arm in backends}
    for case in cases:
        rows["C"].append(run_structured(case, backends["C"], persistent=False))
        rows["D"].append(run_structured(case, backends["D"], persistent=True))
        rows["E"].append(run_direct(case, backends["E"]))
    total_calls = sum(len(backend.calls) for backend in backends.values())
    if total_calls > 96:
        raise RuntimeError("frozen total provider-call ceiling exceeded")
    return {
        "format": "hcl-v04-perspective-safe-action-v01", "model": "deepseek-flash", "seed": 42,
        **freeze,
        "arms": {arm: {
            "correct": sum(row["correct"] for row in rows[arm]), "total": len(rows[arm]),
            "repairs": sum(row["repairs"] for row in rows[arm]), "backend": backends[arm].metrics(),
        } for arm in backends},
        "rows": rows,
        "raw_synthetic_audit": {arm: backends[arm].calls for arm in backends},
        "semantic_audit_status": "PENDING_MANUAL_REVIEW",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--out", default="artifacts/hcl-v04-perspective-safe-action-v01/result.json")
    args = parser.parse_args()
    if args.validate_only:
        print(json.dumps(preflight(), sort_keys=True))
        return
    api_key = os.environ["DEEPSEEK_API_KEY"]
    from hcl.v04.backends import DEEPSEEK_FLASH_CAPABILITIES, OpenAICompatibleBackend

    output = run_comparison(lambda: OpenAICompatibleBackend(
        api_key=api_key, base_url="https://api.deepseek.com", model="deepseek-flash",
        seed=42, capabilities=DEEPSEEK_FLASH_CAPABILITIES,
    ))
    path = Path(args.out)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(output, ensure_ascii=False, indent=2, sort_keys=True))
    print(json.dumps({"arms": output["arms"], "artifact": str(path)}, sort_keys=True))


if __name__ == "__main__":
    main()

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/run_state_generation_reliability_audit_v01.py"
SPEC = importlib.util.spec_from_file_location("sgr_audit", SCRIPT)
assert SPEC and SPEC.loader
mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)


VALID_STATE = json.dumps({
    "mode": "SIMPLE",
    "explicit_facts": ["synthetic"],
    "agents": {},
    "hypotheses": [],
    "missing_bridges": [],
    "uncertainty": {"level": "low", "reason": "direct"},
    "decision_relevant_summary": "synthetic",
})


class FakeInner:
    def __init__(self, outputs):
        self.outputs = list(outputs)

    def complete(self, messages, *, max_tokens, temperature=0.0):
        item = self.outputs.pop(0)
        if isinstance(item, BaseException):
            raise item
        return item


class StateGenerationReliabilityAuditTests(unittest.TestCase):
    def test_observer_records_hash_not_response_text(self):
        backend = mod.ObservingBackend(FakeInner([VALID_STATE]))
        returned = backend.complete([], max_tokens=8192)
        self.assertEqual(returned, VALID_STATE)
        self.assertEqual(len(backend.attempts), 1)
        obs = backend.attempts[0]
        self.assertTrue(obs["json_object_parseable"])
        self.assertIn("response_sha256", obs)
        self.assertNotIn("response", obs)
        self.assertNotIn("response_text", obs)

    def test_build_state_exhaustion_is_classifiable_without_persisting_text(self):
        observer = mod.ObservingBackend(FakeInner(["not json", "still not json", "no object"]))
        loop = mod.HCLAnswerLoop(observer)
        with self.assertRaisesRegex(RuntimeError, "no valid JSON after 3 attempts"):
            loop.build_state("synthetic input")
        self.assertEqual(len(observer.attempts), 3)
        self.assertTrue(all(not x["json_object_parseable"] for x in observer.attempts))

    def test_backend_exception_records_type_only(self):
        observer = mod.ObservingBackend(FakeInner([ValueError("secret exception text")]))
        with self.assertRaises(ValueError):
            observer.complete([], max_tokens=8192)
        self.assertEqual(observer.attempts, [{"attempt": 1, "backend_exception_type": "ValueError"}])

    def test_predeclared_interpretation_thresholds(self):
        base = {
            "length_band": "short",
            "complexity": "simple",
            "success": True,
            "failure_class": None,
            "id": "ok",
        }
        rows = [dict(base)]
        for i in range(2):
            rows.append({
                **base,
                "id": f"json-{i}",
                "success": False,
                "failure_class": "state_json_exhaustion",
            })
        summary = mod.summarize(rows)
        self.assertEqual(
            summary["predeclared_interpretation"],
            "STATE_JSON_RELIABILITY_DEFECT_ESTABLISHED",
        )

    def test_artifact_boundary_rejects_raw_content_keys(self):
        mod.assert_content_free_artifacts({"ok": True}, [{"id": "x", "attempts": []}])
        with self.assertRaises(RuntimeError):
            mod.assert_content_free_artifacts({"ok": True}, [{"id": "x", "response_text": "raw"}])


if __name__ == "__main__":
    unittest.main()

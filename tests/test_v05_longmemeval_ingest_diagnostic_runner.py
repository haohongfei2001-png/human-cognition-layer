"""Provider-free guards for LongMemEval ingest diagnostic runner."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from scripts.run_v05_longmemeval_ingest_diagnostic_v01 import SELECTION


class LongMemEvalIngestDiagnosticRunnerTests(unittest.TestCase):
    def test_frozen_diagnostic_selection_is_disjoint_from_efficacy(self):
        diag = json.loads(Path(SELECTION).read_text(encoding="utf-8"))
        sealed = json.loads(
            Path("eval/longmemeval/knowledge_update_selection_v01.json").read_text(
                encoding="utf-8"
            )
        )
        diag_ids = {x["question_id"] for x in diag["selected"]}
        sealed_ids = {x["question_id"] for x in sealed["selected"]}
        self.assertEqual(len(diag_ids), 2)
        self.assertFalse(diag_ids & sealed_ids)

    def test_diagnostic_manifest_is_text_redacted(self):
        diag = json.loads(Path(SELECTION).read_text(encoding="utf-8"))
        payload = json.dumps(diag, sort_keys=True)
        for forbidden in (
            '"question"',
            '"answer"',
            '"history"',
            '"has_answer"',
            '"answer_session_ids"',
        ):
            self.assertNotIn(forbidden, payload)


if __name__ == "__main__":
    unittest.main()

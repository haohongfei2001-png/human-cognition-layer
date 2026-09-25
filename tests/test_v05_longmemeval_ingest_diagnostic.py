"""Provider-free guards for external ingest-diagnostic selection."""

from __future__ import annotations

import unittest

from scripts.select_longmemeval_ingest_diagnostic_v01 import (
    DIAG_SALT,
    DIAG_SIZE,
    rank,
)


class LongMemEvalIngestDiagnosticSelectionTests(unittest.TestCase):
    def test_diagnostic_is_small_and_independently_salted(self):
        self.assertEqual(DIAG_SIZE, 2)
        self.assertEqual(
            DIAG_SALT,
            "HCL-LONGMEMEVAL-KU-INGEST-DIAG-V01-20260925",
        )

    def test_rank_is_deterministic(self):
        self.assertEqual(rank("q1"), rank("q1"))
        self.assertNotEqual(rank("q1"), rank("q2"))


if __name__ == "__main__":
    unittest.main()

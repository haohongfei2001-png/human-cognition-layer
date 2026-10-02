import unittest
from scripts.witness_ordinary_answer_boundary import witness

class AnswerBoundaryWitnessTests(unittest.TestCase):
    def test_existing_treatment_and_truth_boundary_stay_distinct(self):
        result = witness()
        rows = {r['case']:r for r in result['cases']}
        self.assertEqual(result['provider_calls'],0)
        self.assertFalse(result['model_failure_observed'])
        self.assertFalse(rows['unsupported_trait']['checked_treatment_present'])
        for case in ('reported_reason','reported_receipt','availability_only'):
            self.assertTrue(rows[case]['checked_treatment_present'])
        for row in rows.values():
            self.assertEqual(row['extraction_calls'],0)
            self.assertEqual(row['quote_audit_status'],'ORIGINAL_ANCHORS_LOCATED_SEMANTICS_UNASSESSED')
            self.assertFalse(row['semantic_certification'])
            self.assertTrue(row['raw_delivered_unchanged'])

if __name__ == '__main__':unittest.main()

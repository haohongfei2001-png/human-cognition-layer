"""A deferred source candidate cannot be relabeled as final or paid-ready."""
import json
from pathlib import Path
import unittest
from scripts.development_confirmation_firewall import require_final_development_disjoint


class MoralStoriesScreenTests(unittest.TestCase):
    def test_deferred_receipt_has_no_live_authority_or_answer_claim(self):
        value = json.loads(Path('reports/HCL_MORAL_STORIES_SOURCE_SCREEN.json').read_text())
        self.assertEqual(value['disposition'], 'DEFERRED_AFTER_SOURCE_FIRST_REVIEW')
        self.assertFalse(value['admitted_for_paid_execution'])
        self.assertFalse(value['native_input_mapping_frozen'])
        self.assertFalse(value['scorer_frozen'])
        self.assertEqual(value['authorized_calls'], 0)
        self.assertEqual(value['authorized_spend_usd'], 0)
        self.assertEqual(value['provider_calls'], 0)
        self.assertEqual(value['model_answers'], [])
        self.assertEqual(len(value['cases']), 6)
        self.assertTrue(all(not c['grade_rewritten'] and not c['model_output_seen'] for c in value['cases']))

    def test_publisher_aliases_and_renamed_selected_hashes_remain_consumed(self):
        value = json.loads(Path('reports/HCL_MORAL_STORIES_SOURCE_SCREEN.json').read_text())
        candidates = [{'dataset_id': value['dataset_id']}, {'writing_system_id': value['writing_system_id']}]
        candidates += [{'source_url': url} for url in ('https://huggingface.co/datasets/demelin/moral_stories/resolve/new/file', 'https://github.com/demelin/moral_stories/blob/new/file')]
        candidates += [{'source_sha256': c[field], 'dataset_id': 'renamed'}
                       for c in value['cases'] for field in ('source_sha256', 'native_row_sha256')]
        candidates.append({'source_sha256': value['distribution_sha256'], 'dataset_id': 'renamed'})
        for candidate in candidates:
            with self.subTest(candidate=candidate), self.assertRaises(ValueError):
                require_final_development_disjoint(candidate)


if __name__ == '__main__':
    unittest.main()

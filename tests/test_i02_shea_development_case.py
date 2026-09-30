"""Pinned external development case preparation and fail-closed boundaries."""
import hashlib
import json
import unittest
from unittest.mock import patch
from pathlib import Path

from scripts.i02_shea_development_case import build_development_case
from scripts.serious_eval_contract import runtime_digest


def fixture(*, license_text='CC BY 4.0', quote_block='', questions=5):
    sections = ''.join(
        f'<section id="{name}"><h2>{name}</h2><p>{"Source-local argument. " * 40}</p>'
        f'{quote_block}</section>'
        for name in ('the-lovelace-objection', 'turings-reply'))
    items = ''.join(f'<li>Explain the source-bounded difference in account {i} using evidence.</li>'
                    for i in range(questions))
    return (f'<main>{sections}<section id="discussion-questions"><ol>{items}</ol></section>'
            f'</main><footer>{license_text}</footer>').encode()


class SheaDevelopmentCaseTests(unittest.TestCase):
    def build(self, source):
        with patch('scripts.i02_shea_development_case.PINNED_HTML_SHA256',
                   hashlib.sha256(source).hexdigest()):
            return build_development_case(source)

    def test_positive_native_question_and_same_source_for_comparison(self):
        row = self.build(fixture())
        self.assertEqual(row['native_question_ordinal'], 3)
        self.assertEqual(row['native_question_count'], 5)
        self.assertEqual(row['status'], 'DEVELOPMENT_EXPOSED_NOT_CONFIRMATION')
        self.assertIn('account 2', row['question'])
        self.assertEqual(row['source_sha256'], hashlib.sha256(row['source_text'].encode()).hexdigest())

    def test_rejects_drift_licenses_and_third_party_blocks(self):
        with self.assertRaisesRegex(ValueError, 'pinned publisher HTML changed'):
            build_development_case(fixture())
        for source in (fixture(license_text='all rights reserved'),
                       fixture(quote_block='<blockquote>Other author text</blockquote>'),
                       fixture(questions=4)):
            with self.assertRaisesRegex(ValueError, 'native license, section or question structure'):
                self.build(source)

    def test_question_and_source_revision_change_hashes(self):
        original = self.build(fixture())
        changed = self.build(fixture().replace(b'Source-local argument.',
                                                b'Source-local alternative.', 1))
        self.assertNotEqual(original['source_sha256'], changed['source_sha256'])
        self.assertEqual(original['question_sha256'], changed['question_sha256'])

    def test_real_development_receipt_has_no_confirmation_or_provider_promotion(self):
        row = json.loads(Path('reports/HCL_I02_SHEA_CONCEPT_DEVELOPMENT_ENTRY.json').read_text())
        historical = json.loads(Path('reports/HCL_I02_RUNTIME_AMENDMENT_V5.json').read_text())
        self.assertEqual(row['runtime_sha256'], historical['amended_hcl_runtime_sha256'])
        self.assertEqual(row['after_method'], 'reader_source_argument_comparison_v1')
        self.assertTrue(row['source_complete_in_final_input'])
        self.assertFalse(row['specialized_cognition_treatment'])
        self.assertFalse(row['provider_input_allowed'])
        self.assertFalse(row['confirmation_qualified'])
        self.assertEqual(row['provider_calls'], 0)
        self.assertNotIn('source_text', row)
        self.assertNotIn('question', row)


if __name__ == '__main__':
    unittest.main()

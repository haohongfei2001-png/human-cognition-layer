"""Publisher metadata can be screened without outputting protected answers."""
import hashlib
import json
import unittest
from pathlib import Path

from scripts.i02_quality_bounded_screen import ARTICLE_URL, build_report


def fixture():
    base = {'article_id': '99919', 'url': ARTICLE_URL,
        'source': 'misc-longshort', 'article': 'An authored argument.'}
    other = dict(base, writer_id='1022', questions=[])
    selected = dict(base, writer_id='1020', questions=[{
        'question': 'What does the author argue?',
        'options': ['private gold option'], 'gold_label': 1,
        'validation': [
            {'untimed_eval2_context': 1, 'untimed_eval1_answerability': 1},
            {'untimed_eval2_context': 2, 'untimed_eval1_answerability': 1},
            {'untimed_eval2_context': 3, 'untimed_eval1_answerability': 2}]}])
    return (json.dumps(selected) + '\n' + json.dumps(other) + '\n').encode()


class QuALITYBoundedScreenTests(unittest.TestCase):
    def test_pinned_screen_receipt_remains_unqualified(self):
        receipt = json.loads(Path('reports/HCL_I02_QUALITY_BOUNDED_SCREEN.json').read_text())
        self.assertEqual(receipt['selected_writer_question_count'], 9)
        self.assertEqual(receipt['human_majority_at_least_third_context_count'], 0)
        self.assertFalse(receipt['native_gold_and_options_opened'])
        self.assertFalse(receipt['model_input_allowed'])
        self.assertFalse(receipt['confirmation_qualified'])

    def test_positive_screen_reports_narrow_metadata_only(self):
        raw = fixture()
        report = build_report(raw, expected_sha256=hashlib.sha256(raw).hexdigest())
        self.assertEqual(report['selected_writer_question_count'], 1)
        self.assertEqual(report['human_majority_at_least_third_context_count'], 0)
        self.assertEqual(report['human_majority_answerable_count'], 1)
        self.assertFalse(report['confirmation_qualified'])
        self.assertFalse(report['model_input_allowed'])
        self.assertTrue(report['implementer_article_body_opened_separately'])
        self.assertTrue(report['implementer_selected_question_texts_opened_separately'])
        self.assertFalse(report['native_gold_and_options_opened'])
        self.assertNotIn('private gold option', json.dumps(report))
        self.assertNotIn('What does the author argue?', json.dumps(report))

    def test_file_pin_and_metadata_changes_fail_closed(self):
        raw = fixture()
        with self.assertRaisesRegex(ValueError, 'hash mismatch'):
            build_report(raw)
        altered = raw.replace(b'misc-longshort', b'unknown-source')
        with self.assertRaisesRegex(ValueError, 'metadata changed'):
            build_report(altered, expected_sha256=hashlib.sha256(altered).hexdigest())

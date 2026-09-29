"""Publisher section tags can disqualify a task claim without case text."""

import csv
import io
import json
import unittest
from unittest.mock import patch

from scripts.i02_fairytale_question_metadata import EXPECTED_COLUMNS
from scripts.i02_fairytale_section_span import audit_section_span


def fixture(sections=('1,2', '2,3', '3,4', '4,5', '5,6', '6,8')):
    stream = io.StringIO()
    writer = csv.writer(stream)
    writer.writerow(EXPECTED_COLUMNS)
    for index, section in enumerate(sections):
        writer.writerow((index, 'summary', section,
                         'action' if index == 0 else 'causal relationship', '',
                         'PRIVATE QUESTION', 'implicit', 'PRIVATE ANSWER',
                         '', '', 'implicit', '', '', ''))
    return stream.getvalue().encode()


def audit_fixture(raw):
    with patch('scripts.i02_fairytale_section_span.PACKAGE') as path, patch(
            'scripts.i02_fairytale_section_span.audit_question_tags') as tag_check:
        path.read_text.return_value = json.dumps({'selected_sections_metadata': 43})
        tag_check.return_value = {
            'publisher_question_sha256': 'pinned-hash',
            'publisher_question_git_blob': 'pinned-blob',
            'local_or_summary_counts': {'summary': 6},
        }
        return audit_section_span(raw)


class FairytaleSectionSpanTests(unittest.TestCase):
    def test_short_summary_references_do_not_qualify_long_character_task(self):
        receipt = audit_fixture(fixture())
        self.assertEqual(receipt['summary_section_span_counts'], {1: 5, 2: 1})
        self.assertEqual(receipt['maximum_summary_section_span'], 2)
        self.assertEqual(receipt['summary_character_or_feeling_tagged_count'], 0)
        self.assertFalse(receipt['confirmation_qualified'])
        self.assertNotIn('PRIVATE QUESTION', str(receipt))
        self.assertNotIn('PRIVATE ANSWER', str(receipt))

    def test_invalid_section_reference_fails_closed(self):
        with self.assertRaisesRegex(ValueError, 'invalid source sections'):
            audit_fixture(fixture(('1,2', '2,3', '3,4', '4,5', '5,6', '6,44')))
        with self.assertRaisesRegex(ValueError, 'reference structure differs'):
            audit_fixture(fixture(('1,2', '2,3', '3,4', '4,5', '5,6', 'unknown')))


if __name__ == '__main__':
    unittest.main()

"""Pinned category audit cannot leak held-out answer content or qualify a case."""

import csv
import hashlib
import io
import json
import unittest
from unittest.mock import patch

from scripts.i02_fairytale_question_metadata import (
    EXPECTED_COLUMNS, audit_question_tags,
)


def fixture():
    stream = io.StringIO()
    writer = csv.writer(stream)
    writer.writerow(EXPECTED_COLUMNS)
    for index, (scope, category) in enumerate((
            ('local', 'character'), ('summary', 'causal relationship'))):
        writer.writerow((index, scope, '1', category, '',
                         'PRIVATE QUESTION', 'implicit', 'PRIVATE ANSWER',
                         '', '', 'implicit', '', '', ''))
    return stream.getvalue().encode()


def audit_fixture(raw):
    blob = hashlib.sha1(f'blob {len(raw)}\0'.encode() + raw).hexdigest()
    package = {'selected_question_count_metadata': 2,
               'selected_questions_git_blob': blob}
    with patch('scripts.i02_fairytale_question_metadata.PACKAGE') as path, patch(
            'scripts.i02_fairytale_question_metadata.validate_metadata_only'), patch(
            'scripts.i02_fairytale_question_metadata.QUESTION_SHA256',
            hashlib.sha256(raw).hexdigest()), patch(
            'scripts.i02_fairytale_question_metadata.QUESTION_GIT_BLOB', blob):
        path.read_text.return_value = json.dumps(package)
        return audit_question_tags(raw)


class FairytaleQuestionMetadataTests(unittest.TestCase):
    def test_metadata_only_receipt_has_no_question_or_answer(self):
        result = audit_fixture(fixture())
        self.assertEqual(result['summary_character_or_feeling_tagged_count'], 0)
        self.assertEqual(result['task_family_fit'], 'UNPROVEN_BY_METADATA')
        self.assertFalse(result['confirmation_qualified'])
        self.assertFalse(result['model_input_allowed'])
        self.assertNotIn('PRIVATE QUESTION', str(result))
        self.assertNotIn('PRIVATE ANSWER', str(result))

    def test_different_bytes_fail_before_parsing(self):
        with self.assertRaisesRegex(ValueError, 'question bytes differ'):
            audit_question_tags(b'question,answer\nPRIVATE,PRIVATE\n')

    def test_unknown_category_cannot_be_echoed_as_receipt_metadata(self):
        raw = fixture().replace(b'causal relationship', b'PRIVATE QUESTION')
        with self.assertRaisesRegex(ValueError, 'unknown question category tag'):
            audit_fixture(raw)


if __name__ == '__main__':
    unittest.main()

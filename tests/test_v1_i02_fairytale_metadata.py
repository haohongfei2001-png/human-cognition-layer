"""A real publisher metadata selection is not a licensed/valid case result."""

import json
import unittest
from pathlib import Path

from scripts.i02_fairytale_metadata import METADATA, PACKAGE, validate_metadata_only


class FairytaleMetadataTests(unittest.TestCase):
    def test_real_metadata_pins_one_candidate_without_opening_case(self):
        result = validate_metadata_only()
        self.assertEqual(result['selected']['filename'], 'bamboo-cutter-moon-child')
        self.assertEqual(result['selected']['words'], '5731')
        self.assertFalse(result['qualified'])
        self.assertFalse(result['questions_opened'])
        self.assertEqual(result['provider_calls'], 0)

    def test_metadata_drift_or_candidate_reselection_fails(self):
        raw = METADATA.read_bytes()
        with self.assertRaisesRegex(ValueError, 'metadata bytes differ'):
            validate_metadata_only(raw=raw + b'changed')
        package = json.loads(PACKAGE.read_text())
        package['selected_story_filename'] = 'some-other-story'
        with self.assertRaisesRegex(ValueError, 'not metadata selection'):
            validate_metadata_only(package=package)

    def test_metadata_cannot_silently_become_confirmation_or_model_input(self):
        package = json.loads(PACKAGE.read_text())
        package['confirmation_qualified'] = True
        with self.assertRaisesRegex(ValueError, 'cannot promote'):
            validate_metadata_only(package=package)
        package['confirmation_qualified'] = False
        package['source_text_opened'] = True
        with self.assertRaisesRegex(ValueError, 'cannot promote'):
            validate_metadata_only(package=package)
        package['source_text_opened'] = False
        package['rights_status'] = 'VERIFIED_FOR_THIS_EVALUATION'
        with self.assertRaisesRegex(ValueError, 'not yet qualified'):
            validate_metadata_only(package=package)


if __name__ == '__main__':
    unittest.main()

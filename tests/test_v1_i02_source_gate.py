"""Metadata-only screening cannot accidentally activate restricted source text."""
import copy
import json
import unittest
from pathlib import Path

from scripts.serious_eval_source_gate import (SAFE_STATUS,
    require_qualified, validate_registry)


SCREEN = json.loads(Path('reports/HCL_I02_SOURCE_SCREEN.json').read_text())


class SourceGateTests(unittest.TestCase):
    def test_current_screen_is_provider_free_and_qualifies_nothing(self):
        self.assertTrue(validate_registry(SCREEN))
        self.assertEqual(SCREEN['qualified_sources'], 0)
        self.assertEqual(SCREEN['provider_calls'], 0)
        for row in SCREEN['sources']:
            self.assertNotEqual(row['status'], SAFE_STATUS)
            self.assertFalse(row.get('confirmation_content_opened', False))
            with self.assertRaisesRegex(ValueError, 'not qualified'):
                require_qualified(SCREEN, row['source_id'])

    def test_relabeling_restricted_source_does_not_enable_ingestion(self):
        screen = copy.deepcopy(SCREEN)
        row = screen['sources'][0]
        row['status'] = SAFE_STATUS
        with self.assertRaisesRegex(ValueError, 'AI use rights'):
            require_qualified(screen, row['source_id'])

    def test_license_alone_does_not_qualify_an_unexamined_item(self):
        screen = copy.deepcopy(SCREEN)
        row = screen['sources'][2]
        row.update(status=SAFE_STATUS, explicit_ai_use_prohibition=False,
            license_verified_for_use=True)
        with self.assertRaisesRegex(ValueError, 'item-level'):
            require_qualified(screen, row['source_id'])
        row.update(item_level_source_validity='PASS_SOURCE_FIRST',
            historical_exposure='DISJOINT_CONFIRMED')
        with self.assertRaisesRegex(ValueError, 'digest'):
            require_qualified(screen, row['source_id'])

    def test_fully_qualified_source_requires_all_receipts(self):
        screen = copy.deepcopy(SCREEN)
        row = screen['sources'][2]
        row.update(status=SAFE_STATUS, explicit_ai_use_prohibition=False,
            license_verified_for_use=True, item_level_source_validity='PASS_SOURCE_FIRST',
            historical_exposure='DISJOINT_CONFIRMED', source_sha256='a' * 64)
        self.assertEqual(require_qualified(screen, row['source_id']), row)


if __name__ == '__main__':
    unittest.main()

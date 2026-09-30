import json
from pathlib import Path
import unittest
from unittest.mock import patch
from scripts.i02_source_qualification_v14 import (
    require_kranak_disjoint, require_qualified_confirmation_source_v14)
from scripts.i02_source_qualification_v13 import require_clifford_disjoint
from scripts.i02_source_qualification_v12 import require_gregory_disjoint


class ExposureBoundary(unittest.TestCase):
    def test_author_and_writing_system_survive_renamed_source(self):
        for row in ({'author_id':'joseph-kranak','source_sha256':'new'},
                    {'writing_system_id':'rebus-introduction-to-philosophy-ethics-2019'}):
            with self.assertRaises(ValueError):
                require_kranak_disjoint(row)

    def test_url_survives_changed_declared_ids_query_fragment_and_slash(self):
        for field in ('canonical_url','publisher_url','source_url'):
            with self.assertRaises(ValueError):
                require_kranak_disjoint({field:'https://press.rebus.community/intro-to-phil-ethics/chapter/kantian-deontology/?edition=x#section', 'author_id':'renamed'})
        self.assertTrue(require_kranak_disjoint({'publisher_url':'https://unrelated.example/intro-to-phil-ethics/chapter/kantian-deontology/'}))

    def test_negative_gate_cannot_grant_independent_qualification(self):
        with patch('scripts.i02_source_qualification_v14.require_qualified_confirmation_source_v13', side_effect=ValueError('rights/semantic review missing')) as parent:
            with self.assertRaisesRegex(ValueError,'review missing'):
                require_qualified_confirmation_source_v14({}, {}, {}, '/tmp/repo', 'revision')
            parent.assert_called_once()
        with patch('scripts.i02_source_qualification_v14.require_qualified_confirmation_source_v13') as parent:
            with self.assertRaises(ValueError):
                require_qualified_confirmation_source_v14({}, {'author_id':'joseph-kranak'}, {}, '/tmp/repo','revision')
            parent.assert_not_called()

    def test_receipt_has_no_invented_pin_or_model_qualification(self):
        receipt=json.loads(Path('reports/HCL_I02_REBUS_KRANAK_EXPOSURE.json').read_text())
        self.assertEqual(receipt['raw_retrieval']['result'],'HTTP_403_NO_RETRY_NO_BYPASS')
        self.assertIsNone(receipt['raw_retrieval']['body_sha256'])
        self.assertFalse(receipt['model_input_allowed'])
        self.assertEqual(receipt['confirmation_items_qualified'],0)
        self.assertEqual(receipt['provider_calls'],0)
        self.assertEqual(receipt['longmemeval'],'SEALED_NOT_ACCESSED')

    def test_historical_clifford_gregory_exclusions_remain(self):
        for check,row in ((require_clifford_disjoint, {'author_id':'william-kingdon-clifford'}),
                          (require_gregory_disjoint, {'author_id':'lady-gregory'})):
            with self.assertRaises(ValueError):
                check(row)


if __name__ == '__main__':
    unittest.main()

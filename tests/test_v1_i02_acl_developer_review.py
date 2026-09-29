"""Keep the real ACL development review reproducible without re-calling a model."""
import copy
import json
import unittest
from pathlib import Path

from scripts.i02_blind_review_packet import digest, reconcile_reviews


ROOT = Path('reports/HCL_I02_ACL_CPG_V8_DEVELOPER_REVIEW')


def read(path):
    return json.loads(Path(path).read_text())


class ACLDeveloperReviewTests(unittest.TestCase):
    def test_review_is_bound_to_raw_receipt_and_source_first_manifest(self):
        packet = read(ROOT / 'packet.json')
        allocation = read(ROOT / 'allocation.json')
        reviews = read(ROOT / 'reviews.json')
        manifest = read('reports/HCL_I02_ACL_ETHICS_SOURCE_FIRST_OBLIGATIONS.json')
        raw = read('reports/HCL_I02_ACL_ETHICS_CPG_V8_RUN_36611355531/raw_receipt.json')
        expected = read(ROOT / 'reconciliation.json')
        self.assertEqual(packet['raw_receipt_sha256'], digest(raw))
        self.assertEqual(packet['source_first_manifest_sha256'], digest(manifest))
        self.assertEqual(reconcile_reviews(packet, allocation, manifest, reviews), expected)
        self.assertEqual({phase: score['earned'] for phase, score in
                          expected['scores_by_phase'].items()},
                         {'C': 6, 'P': 7, 'G_final': 8})
        for review in reviews:
            self.assertNotIn('arm', review)
            self.assertNotIn('winner', review)

    def test_review_mutation_fails_closed(self):
        packet = read(ROOT / 'packet.json')
        allocation = read(ROOT / 'allocation.json')
        reviews = read(ROOT / 'reviews.json')
        manifest = read('reports/HCL_I02_ACL_ETHICS_SOURCE_FIRST_OBLIGATIONS.json')
        changed = copy.deepcopy(reviews)
        changed[0]['judgments'][0]['output_excerpt'] = 'not an actual output excerpt'
        with self.assertRaisesRegex(ValueError, 'exact output text'):
            reconcile_reviews(packet, allocation, manifest, changed)


if __name__ == '__main__':
    unittest.main()

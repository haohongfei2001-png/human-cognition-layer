"""I02 reviewer isolation and exact-receipt reconciliation checks."""

from copy import deepcopy
import json
from pathlib import Path
import random
import unittest

from scripts.i02_blind_review_packet import (
    build_packet, digest, reconcile_reviews)


BASE = Path('reports/HCL_I02_ACL_ETHICS_CPG_V8_RUN_36611355531')
MANIFEST = Path('reports/HCL_I02_ACL_ETHICS_SOURCE_FIRST_OBLIGATIONS.json')


def inputs():
    return json.loads(MANIFEST.read_text()), json.loads(
        (BASE / 'raw_receipt.json').read_text())


def unassessed_reviews(packet):
    return [dict(schema='hcl-i02-blind-review-v1',
        case_id=packet['case_id'], opaque_output_id=row['opaque_output_id'],
        judgments=[dict(id=item['id'], judgment='UNRESOLVED',
            rationale='No independent blinded semantic judgment was made.',
            output_excerpt='') for item in packet['obligations']])
        for row in packet['outputs']]


class BlindReviewPacketTest(unittest.TestCase):
    def test_real_receipt_becomes_arm_blind_source_first_packet(self):
        manifest, receipt = inputs()
        packet, key = build_packet(manifest, receipt,
            ['C', 'P', 'G_final'], random.Random(19))
        self.assertEqual(len(packet['outputs']), 3)
        self.assertEqual(set(key['opaque_to_phase'].values()),
            {'C', 'P', 'G_final'})
        public = json.dumps(packet)
        for private in ('actual_model_id', 'reasoning_content', 'usage',
                'rated_peak_cost_usd', 'request_raw', 'response_raw',
                'G_final', 'G_map', '"phase"'):
            self.assertNotIn(private, public)
        self.assertEqual(packet['source_first_manifest_sha256'], digest(manifest))
        scored = reconcile_reviews(packet, key, manifest,
            unassessed_reviews(packet))
        self.assertEqual(set(scored['scores_by_phase']), {'C', 'P', 'G_final'})
        self.assertTrue(all(row['earned'] == 0 for row in
            scored['scores_by_phase'].values()))

    def test_tampered_source_and_citation_fail_before_packet(self):
        manifest, receipt = inputs()
        manifest['sources'][0]['text'] += ' invented'
        with self.assertRaises(ValueError):
            build_packet(manifest, receipt, ['C'], random.Random(1))
        manifest, receipt = inputs()
        answer = json.loads(receipt['attempts'][0]['response_raw']
            ['choices'][0]['message']['content'])
        answer['source_citations'][0]['quote'] = 'invented quote'
        receipt['attempts'][0]['response_raw']['choices'][0]['message']['content'] = json.dumps(answer)
        with self.assertRaises(ValueError):
            build_packet(manifest, receipt, ['C'], random.Random(1))

    def test_map_not_answer_and_incomplete_run_fail(self):
        manifest, receipt = inputs()
        with self.assertRaises(ValueError):
            build_packet(manifest, receipt, ['G_map'], random.Random(1))
        receipt['status'] = 'FAILED_NO_RETRY'
        with self.assertRaises(ValueError):
            build_packet(manifest, receipt, ['C'], random.Random(1))

    def test_reconciliation_requires_frozen_complete_reviews(self):
        manifest, receipt = inputs()
        packet, key = build_packet(manifest, receipt, ['C', 'P'], random.Random(7))
        reviews = unassessed_reviews(packet)
        with self.assertRaises(ValueError):
            reconcile_reviews(packet, key, manifest, reviews[:1])
        altered = deepcopy(packet)
        altered['outputs'][0]['answer']['answer'] += ' post-output drift'
        with self.assertRaises(ValueError):
            reconcile_reviews(altered, key, manifest, reviews)
        altered = deepcopy(packet)
        altered['obligations'][0]['audit_question'] = 'Changed after output'
        changed_key = deepcopy(key)
        changed_key['packet_sha256'] = digest(altered)
        with self.assertRaises(ValueError):
            reconcile_reviews(altered, changed_key, manifest, reviews)
        reviews[0]['arm'] = 'C'
        with self.assertRaises(ValueError):
            reconcile_reviews(packet, key, manifest, reviews)


if __name__ == '__main__':
    unittest.main()

"""The active blind handoff cannot reveal arms from obligation-only reviews."""

from copy import deepcopy
import json
import random
import unittest

from scripts.i02_blind_review_v2 import build_packet_v2, reconcile_reviews_v2
from scripts.i02_blind_review_packet import digest
from tests.test_v1_i02_blind_review_packet import inputs, unassessed_reviews


def reviews_for(packet):
    rows = unassessed_reviews(packet)
    for row in rows:
        row['schema'] = 'hcl-i02-blind-review-v2'
        row['coverage_attestation'] = True
        row['residual_claims'] = []
    return rows


class BlindReviewV2Tests(unittest.TestCase):
    def test_actual_receipt_stays_blind_and_requires_second_review(self):
        manifest, receipt = inputs()
        packet, key = build_packet_v2(manifest, receipt,
            ['C', 'P', 'G_final'], random.Random(19))
        public = json.dumps(packet)
        for secret in ('actual_model_id', 'reasoning_content', 'usage',
                'request_raw', 'response_raw', 'G_final', 'G_map', '"phase"'):
            self.assertNotIn(secret, public)
        self.assertEqual(set(key['opaque_to_phase'].values()), {'C', 'P', 'G_final'})
        v1_only = unassessed_reviews(packet)
        with self.assertRaises(ValueError):
            reconcile_reviews_v2(packet, key, manifest, v1_only)
        assessed = reviews_for(packet)
        result = reconcile_reviews_v2(packet, key, manifest, assessed)
        self.assertEqual(set(result['scores_by_phase']), {'C', 'P', 'G_final'})
        self.assertTrue(all(value['source_first_score']['earned'] == 0
            for value in result['scores_by_phase'].values()))
        self.assertTrue(all(not value['full_answer_semantics_qualified']
            for value in result['scores_by_phase'].values()))

    def test_unsupported_private_claim_blocks_reveal_eligibility(self):
        manifest, receipt = inputs()
        packet, key = build_packet_v2(manifest, receipt, ['C'], random.Random(3))
        answer = packet['outputs'][0]['answer']
        answer['answer'] += ' The author secretly intended to exploit workers.'
        key['packet_sha256'] = digest(packet)
        assessed = reviews_for(packet)
        assessed[0]['residual_claims'] = [dict(
            excerpt='The author secretly intended to exploit workers.',
            judgment='UNSUPPORTED', kind='INFERENCE_BOUNDARY',
            rationale='The source has no such author intention.', source_quotes=[])]
        result = reconcile_reviews_v2(packet, key, manifest, assessed)
        self.assertFalse(result['scores_by_phase']['C']['eligible'])
        self.assertEqual(len(result['scores_by_phase']['C']['severe_unsupported_excerpts']), 1)

    def test_missing_coverage_identity_and_source_mutation_fail_closed(self):
        manifest, receipt = inputs()
        packet, key = build_packet_v2(manifest, receipt, ['C', 'P'], random.Random(5))
        rows = reviews_for(packet)
        for mutation in ('coverage', 'identity', 'missing', 'phase', 'source', 'packet'):
            p, k, m, r = deepcopy(packet), deepcopy(key), deepcopy(manifest), deepcopy(rows)
            if mutation == 'coverage': r[0]['coverage_attestation'] = False
            elif mutation == 'identity': r[0]['opaque_output_id'] = 'wrong-id'
            elif mutation == 'missing': r.pop()
            elif mutation == 'phase': r[0]['arm'] = 'C'
            elif mutation == 'source': m['sources'][0]['text'] += ' drift'
            else: p['outputs'][0]['answer']['answer'] += ' drift'
            with self.assertRaises(ValueError, msg=mutation):
                reconcile_reviews_v2(p, k, m, r)


if __name__ == '__main__':
    unittest.main()

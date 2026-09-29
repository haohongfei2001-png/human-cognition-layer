"""Versioned blind handoff requiring residual-claim review before reveal.

Historical v1 packets, allocations, reviews and scores remain immutable.
"""

import argparse
from copy import deepcopy
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.i02_blind_review_packet import (
    _write_new, build_packet, digest, load_json, reconcile_reviews)
from scripts.i02_residual_claim_audit import audit_residual_claims


REVIEW_FIELDS = frozenset(('schema', 'case_id', 'opaque_output_id', 'judgments',
    'coverage_attestation', 'residual_claims'))


def build_packet_v2(manifest, receipt, phases, rng=None):
    packet, allocation = build_packet(manifest, receipt, phases, rng)
    packet['schema'] = 'hcl-i02-blind-review-packet-v2'
    packet['required_review_schema'] = 'hcl-i02-blind-review-v2'
    packet['review_instruction'] = (
        'Review every frozen obligation and all material residual claims using '
        'the authorized source and exact output excerpts. Attest complete '
        'claim coverage before reveal. Do not consult the raw receipt, '
        'allocation key, phase names or model traces.')
    allocation['schema'] = 'hcl-i02-blind-allocation-key-v2'
    allocation['packet_sha256'] = digest(packet)
    return packet, allocation


def reconcile_reviews_v2(packet, allocation, manifest, reviews):
    """Return arm scores only after obligation and residual records are complete."""
    if (not isinstance(packet, dict) or
            packet.get('schema') != 'hcl-i02-blind-review-packet-v2' or
            packet.get('required_review_schema') != 'hcl-i02-blind-review-v2' or
            not isinstance(allocation, dict) or
            allocation.get('schema') != 'hcl-i02-blind-allocation-key-v2' or
            allocation.get('packet_sha256') != digest(packet) or
            not isinstance(reviews, list)):
        raise ValueError('v2 packet, allocation and exact commitment required')
    legacy_packet = deepcopy(packet)
    legacy_packet['schema'] = 'hcl-i02-blind-review-packet-v1'
    legacy_key = deepcopy(allocation)
    legacy_key['schema'] = 'hcl-i02-blind-allocation-key-v1'
    legacy_key['packet_sha256'] = digest(legacy_packet)
    obligation_reviews = []
    residual_reviews = {}
    for row in reviews:
        if not isinstance(row, dict) or set(row) != REVIEW_FIELDS or row['schema'] != 'hcl-i02-blind-review-v2':
            raise ValueError('complete exact v2 review required')
        opaque = row['opaque_output_id']
        if opaque in residual_reviews:
            raise ValueError('duplicate opaque review')
        obligation_reviews.append(dict(schema='hcl-i02-blind-review-v1',
            case_id=row['case_id'], opaque_output_id=opaque,
            judgments=row['judgments']))
        residual_reviews[opaque] = dict(schema='hcl-i02-residual-claim-audit-v1',
            case_id=row['case_id'], opaque_output_id=opaque,
            coverage_attestation=row['coverage_attestation'],
            claims=row['residual_claims'])
    baseline = reconcile_reviews(legacy_packet, legacy_key, manifest,
        obligation_reviews)
    by_id = {row['opaque_output_id']: row for row in obligation_reviews}
    results = {}
    for output in packet['outputs']:
        opaque = output['opaque_output_id']
        result = audit_residual_claims(manifest, output['answer'], by_id[opaque],
            residual_reviews[opaque])
        phase = allocation['opaque_to_phase'][opaque]
        if result['source_first_score'] != baseline['scores_by_phase'][phase]:
            raise ValueError('v1 reconciliation drift')
        results[phase] = result
    return {'schema': 'hcl-i02-blind-review-reconciliation-v2',
        'case_id': manifest['case_id'], 'packet_sha256': digest(packet),
        'scores_by_phase': results}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', required=True)
    parser.add_argument('--receipt', required=True)
    parser.add_argument('--phases', nargs='+', required=True)
    parser.add_argument('--packet-output', required=True)
    parser.add_argument('--allocation-output', required=True)
    args = parser.parse_args()
    if Path(args.packet_output).resolve() == Path(args.allocation_output).resolve():
        parser.error('packet and private allocation require separate paths')
    packet, allocation = build_packet_v2(load_json(args.manifest),
        load_json(args.receipt), args.phases)
    _write_new(args.allocation_output, allocation, 0o600)
    _write_new(args.packet_output, packet, 0o644)
    print('BLIND_V2_PACKET_WRITTEN_NO_SEMANTIC_REVIEW')


if __name__ == '__main__':
    main()

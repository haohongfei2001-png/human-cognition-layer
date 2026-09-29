"""Prepare and reconcile arm-blind, source-first I02 review packets.

The packet is a handoff boundary, not a semantic judge. A reviewer must see
only the packet; the allocation key is withheld until every review is frozen.
"""

import argparse
import hashlib
import json
import os
from pathlib import Path
import secrets
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.serious_eval_semantic_score import (
    load_rubric, score_review, validate_answer, validate_manifest)


FINAL_PHASES = ('C', 'P', 'G_final', 'H', 'H_new')


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False,
        sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def build_packet(manifest, receipt, phases, rng=None):
    """Return a reviewer packet and separately held arm key.

    The receipt's final messages are the only answer source. The map phase is
    never scored as an answer, and invalid citations fail before blinding.
    """
    sources = validate_manifest(manifest, load_rubric())
    if (not isinstance(receipt, dict) or not receipt.get('run_id') or
            receipt.get('status') !=
                'COMPLETED_REQUIRES_SOURCE_FIRST_SEMANTIC_AUDIT' or
            not isinstance(receipt.get('attempts'), list) or
            not isinstance(phases, (list, tuple)) or not phases or
            len(set(phases)) != len(phases) or
            any(phase not in FINAL_PHASES for phase in phases)):
        raise ValueError('completed frozen receipt and distinct final phases required')
    attempts = receipt['attempts']
    if len({row.get('phase') for row in attempts if isinstance(row, dict)}) != len(attempts):
        raise ValueError('duplicate provider phase')
    by_phase = {row['phase']: row for row in attempts}
    if any(phase not in by_phase for phase in phases):
        raise ValueError('requested final phase absent')
    gate = receipt.get('preflight', {}).get('source_gate', {})
    if len(sources) != 1 or gate.get('source_sha256') != hashlib.sha256(
            next(iter(sources.values())).encode()).hexdigest():
        raise ValueError('receipt source differs from frozen obligations')
    rng = rng or secrets.SystemRandom()
    rows, key = [], {}
    for phase in phases:
        attempt = by_phase[phase]
        raw = attempt.get('response_raw', {})
        choices = raw.get('choices') or []
        if (len(choices) != 1 or choices[0].get('finish_reason') != 'stop' or
                not isinstance(choices[0].get('message', {}).get('content'), str)):
            raise ValueError('final response missing or incomplete')
        try:
            answer = json.loads(choices[0]['message']['content'])
        except json.JSONDecodeError as exc:
            raise ValueError('final answer JSON invalid') from exc
        validate_answer(answer, sources)
        opaque = 'output-' + f'{rng.getrandbits(128):032x}'
        if opaque in key:
            raise ValueError('opaque ID collision')
        rows.append({'opaque_output_id': opaque, 'answer': answer})
        key[opaque] = phase
    rng.shuffle(rows)
    packet = {'schema': 'hcl-i02-blind-review-packet-v1',
        'case_id': manifest['case_id'], 'split': manifest['split'],
        'sources': manifest['sources'], 'obligations': manifest['obligations'],
        'rubric_sha256': manifest['rubric_sha256'],
        'source_first_manifest_sha256': digest(manifest),
        'raw_receipt_sha256': digest(receipt), 'outputs': rows,
        'review_instruction': ('Review every output independently using only this '
            'packet. Return the frozen hcl-i02-blind-review-v1 schema. Do not '
            'consult the raw receipt, allocation key, phase names or model traces.')}
    allocation = {'schema': 'hcl-i02-blind-allocation-key-v1',
        'case_id': manifest['case_id'], 'packet_sha256': digest(packet),
        'opaque_to_phase': key}
    return packet, allocation


def reconcile_reviews(packet, allocation, manifest, reviews):
    """Unblind only a complete, exact-ID set of already written reviews."""
    if (allocation.get('schema') != 'hcl-i02-blind-allocation-key-v1' or
            allocation.get('case_id') != manifest.get('case_id') or
            allocation.get('packet_sha256') != digest(packet) or
            packet.get('source_first_manifest_sha256') != digest(manifest) or
            packet.get('case_id') != manifest.get('case_id') or
            packet.get('split') != manifest.get('split') or
            packet.get('rubric_sha256') != manifest.get('rubric_sha256') or
            packet.get('sources') != manifest.get('sources') or
            packet.get('obligations') != manifest.get('obligations') or
            not isinstance(reviews, list)):
        raise ValueError('packet, allocation or frozen source audit drift')
    outputs = {row['opaque_output_id']: row['answer'] for row in packet['outputs']}
    if (len(outputs) != len(packet['outputs']) or
            set(outputs) != set(allocation.get('opaque_to_phase', {})) or
            len(set(allocation['opaque_to_phase'].values())) != len(outputs) or
            len(reviews) != len(outputs)):
        raise ValueError('complete blind allocation required')
    by_id = {review.get('opaque_output_id'): review for review in reviews
        if isinstance(review, dict)}
    if len(by_id) != len(reviews) or set(by_id) != set(outputs):
        raise ValueError('one exact review per opaque output required')
    scored = {}
    for opaque, answer in outputs.items():
        if set(by_id[opaque]) != {
                'schema', 'case_id', 'opaque_output_id', 'judgments'}:
            raise ValueError('review may not disclose an arm or add fields')
        result = score_review(manifest, answer, by_id[opaque])
        scored[allocation['opaque_to_phase'][opaque]] = result
    return {'schema': 'hcl-i02-blind-review-reconciliation-v1',
        'case_id': manifest['case_id'], 'packet_sha256': digest(packet),
        'scores_by_phase': scored}


def load_json(path):
    return json.loads(Path(path).read_text())


def _write_new(path, value, mode):
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, mode)
    with os.fdopen(descriptor, 'w') as stream:
        json.dump(value, stream, ensure_ascii=False, sort_keys=True, indent=2)
        stream.write('\n')


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
    packet, allocation = build_packet(load_json(args.manifest),
        load_json(args.receipt), args.phases)
    _write_new(args.allocation_output, allocation, 0o600)
    _write_new(args.packet_output, packet, 0o644)
    print('BLIND_PACKET_WRITTEN_NO_SEMANTIC_REVIEW')


if __name__ == '__main__':
    main()

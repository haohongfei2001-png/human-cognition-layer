"""Actual single-step and policy HCL answers expose source-bound decision reasons."""
import argparse
import json
from pathlib import Path

from scripts.witness_unified_weight_regions import witness as single_witness
from scripts.witness_unified_policy_weight_regions import witness as policy_witness


def witness():
    single, policy = single_witness(), policy_witness()
    assert single['checked_commit'] == policy['checked_commit']
    assert single['runtime_hashes'] == policy['runtime_hashes']
    rows = []
    for family, bundle in (('single', single), ('policy', policy)):
        for row in bundle['rows']:
            if 'actual' not in row:
                rows.append(dict(family=family, **row)); continue
            delivery = row['actual']['reasoned_delivery']
            assert delivery['text'] in row['answer']
            assert 'reasoned_delivery' in row['claim_fields']
            assert row['replay_new_attempts'] == 0
            if delivery['status'] == 'PARTIAL':
                assert not row['actual']['complete']
                assert 'resource-limited' in row['answer']
            elif row['actual']['analyses']:
                assert 'Coordinates in order:' in row['answer']
                assert 'provenance:' in row['answer']
                assert 'does not adopt' in row['answer']
            if family == 'single' and row['case'] == 'simplex':
                assert 'X minus Y' in row['answer'] and 'x (x)=4' in row['answer'] and 'y (y)=-6' in row['answer']
            if family == 'policy' and row['case'] == 'expected':
                assert "'r': 'ignore'" in row['answer'] and 'is PROHIBITED' in row['answer']
                assert 'care (care)=7' in row['answer'] and 'convenience (convenience)=-3' in row['answer']
            rows.append(dict(family=family, **row))
    return dict(schema='hcl-unified-weight-region-delivery-witness-1', checked_commit=single['checked_commit'],
        runtime_hashes=single['runtime_hashes'], rows=rows, provider_calls=0, provider_spend_usd=0, sealed_content_reads=0,
        evidence_scope='INTEGRATED_OFFLINE_PARTIAL_VERIFIED_WEIGHT_REGION_REASONS',
        not_established=['NEW_DECISION_RULES','PREFERENCE_INFERENCE','AUTOMATIC_NORM_ADOPTION','FULL_M14','FULL_T17','FULL_T18','FULL_S4','LIVE_EFFECT'])


if __name__ == '__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',required=True,type=Path);args=parser.parse_args()
    args.output.write_text(json.dumps(witness(),ensure_ascii=False,sort_keys=True,indent=2)+'\n')

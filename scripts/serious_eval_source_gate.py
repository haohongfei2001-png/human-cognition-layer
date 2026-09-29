"""I02 provider-free source-use gate; metadata never qualifies content by itself."""
import argparse
import json
from pathlib import Path


REGISTRY = Path('reports/HCL_I02_SOURCE_SCREEN.json')
SAFE_STATUS = 'QUALIFIED_FOR_MODEL_INPUT_AND_CONFIRMATION_SELECTION'


def validate_registry(registry):
    if registry.get('schema') != 'hcl-i02-source-screen-v1':
        raise ValueError('unknown source screen')
    if registry.get('provider_calls') != 0 or registry.get('longmemeval') != 'SEALED_NOT_ACCESSED':
        raise ValueError('source screen must remain provider-free and sealed')
    sources = registry.get('sources')
    if not isinstance(sources, list) or not sources:
        raise ValueError('source entries required')
    ids = [row.get('source_id') for row in sources if isinstance(row, dict)]
    if len(ids) != len(sources) or len(ids) != len(set(ids)):
        raise ValueError('distinct source IDs required')
    for row in sources:
        if not isinstance(row.get('status'), str) or not isinstance(row.get('primary_url'), str):
            raise ValueError('source status and primary URL required')
        if not row['primary_url'].startswith('https://'):
            raise ValueError('primary HTTPS evidence required')
    return True


def require_qualified(registry, source_id):
    """Fail closed before source text enters any provider or test selection."""
    validate_registry(registry)
    row = next((r for r in registry['sources'] if r['source_id'] == source_id), None)
    if row is None or row['status'] != SAFE_STATUS:
        raise ValueError('source not qualified for model input')
    if row.get('explicit_ai_use_prohibition') is not False:
        raise ValueError('AI use rights not clear')
    if row.get('license_verified_for_use') is not True:
        raise ValueError('license not verified for this use')
    if row.get('item_level_source_validity') != 'PASS_SOURCE_FIRST':
        raise ValueError('item-level source validity missing')
    if row.get('historical_exposure') != 'DISJOINT_CONFIRMED':
        raise ValueError('historical exposure not excluded')
    if row.get('source_sha256') is None or len(row['source_sha256']) != 64:
        raise ValueError('exact source content digest required')
    if not row.get('rights_evidence_url', '').startswith('https://'):
        raise ValueError('rights evidence required')
    return row


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--source-id')
    args = parser.parse_args()
    registry = json.loads(REGISTRY.read_text())
    validate_registry(registry)
    if args.source_id:
        require_qualified(registry, args.source_id)
    print('I02_SOURCE_SCREEN_VALID')

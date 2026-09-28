"""Owner-authorized, one-run CG-01 external development entry point."""
import argparse
import json
import os
from pathlib import Path
import sys

from scripts.cg01_external_package import (
    DeepSeekProvider, load_package, run_with_provider, verify_source,
)


def write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n')
    temporary.replace(path)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source-file', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--validate-only', action='store_true')
    args = parser.parse_args()

    package = load_package()
    verify_source(args.source_file.read_bytes(), package)
    if args.validate_only:
        print('CG-01 source and frozen package preflight passed; provider calls: 0')
        return 0

    if os.environ.get('HCL_CG01_AUTHORIZED_CAP_USD') != '0.75':
        raise SystemExit('exact CG-01 owner grant is absent')
    key = os.environ.get('DEEPSEEK_API_KEY')
    if not key:
        raise SystemExit('DeepSeek Actions secret is absent')
    provider = DeepSeekProvider(key, package)
    journal = args.out / 'journal.json'
    metadata = {
        'schema': 'hcl-cg01-external-run-v1',
        'git_sha': os.environ.get('GITHUB_SHA'),
        'run_id': os.environ.get('GITHUB_RUN_ID'),
        'run_attempt': os.environ.get('GITHUB_RUN_ATTEMPT'),
        'source_sha256': package['source']['sha256'],
        'model': package['model'],
        'usd_hard_cap': package['usd_hard_cap'],
        'cost_basis': 'PEAK_ALL_INPUT_CACHE_MISS_UPPER_BOUND',
    }
    def checkpoint(snapshot):
        write_json(journal, dict(metadata, state='IN_PROGRESS', **snapshot))

    try:
        result = run_with_provider(provider, package, on_update=checkpoint)
    except Exception as exc:
        current = json.loads(journal.read_text()) if journal.exists() else metadata
        write_json(journal, dict(current, state='FAILED', failure_type=type(exc).__name__))
        print(f'CG-01 run stopped: {type(exc).__name__}', file=sys.stderr)
        return 1
    if result['calls'] != 24 or len(result['rows']) != 20 or result['cost_usd'] > 0.75:
        write_json(journal, dict(metadata, state='INVALID_FINAL_RECEIPT', **result))
        return 1
    write_json(args.out / 'results.json', dict(metadata, state='COMPLETE', **result))
    write_json(journal, dict(metadata, state='COMPLETE', **result))
    print(json.dumps({'calls': result['calls'], 'rows': len(result['rows']),
                      'conservative_cost_upper_usd': result['cost_usd']}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

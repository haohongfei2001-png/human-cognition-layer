"""One-shot CG05 transport adapter; cognition and scoring use frozen code only."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess

from scripts.cg05_external_package import PACKAGE, build_package, score_answer
from scripts.run_cg03_external_once import BudgetLedger, CG03Provider, _write_json


def load_frozen_package():
    package = json.loads(PACKAGE.read_text())
    if package != build_package():
        raise ValueError('CG05 freeze or treatment drift')
    return package


def run_with_provider(provider, package, checkpoint=None):
    ledger = BudgetLedger(package, checkpoint)
    rows = []
    for case in package['cases']:
        for arm in package['arms']:
            messages = case['messages'][arm]
            result = ledger.call(provider, messages)
            rows.append(dict(case_id=case['case_id'], arm=arm, raw=result['raw'],
                score=score_answer(case, result['raw']), result=result,
                final_messages=messages, preflight=case['preflight'] if arm in ('H', 'H-new') else None))
            if checkpoint:
                checkpoint(ledger, rows)
    return dict(rows=rows, attempts=ledger.attempts, calls=ledger.calls, cost_usd=ledger.cost_usd)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--validate-only', action='store_true')
    args = parser.parse_args()
    package = load_frozen_package()
    if args.validate_only:
        print(json.dumps(dict(cases=4, arms=package['arms'], treatment_presence='PASS',
            provider_calls_executed=0, proposed_hard_cap_usd=package['proposed_new_hard_cap_usd'])))
        return 0
    if os.environ.get('HCL_CG05_AUTHORIZED_CAP_USD') != '0.30':
        raise SystemExit('exact new CG05 owner grant absent')
    baseline = os.environ.get('HCL_CG05_AUTHORIZED_BASE_SHA')
    sha = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
    if baseline != 'c7593bcf5ef8199eb8f1adb3b6f96fb2a0367b94' or sha != baseline:
        raise SystemExit('CG05 exact certified execution checkout required')
    if os.environ.get('GITHUB_RUN_ATTEMPT') != '1' or not os.environ.get('DEEPSEEK_API_KEY'):
        raise SystemExit('CG05 first attempt and existing secret required')
    metadata = dict(schema='hcl-cg05-external-run-v1', git_sha=sha, authorized_baseline_sha=baseline,
        run_id=os.environ.get('GITHUB_RUN_ID'), run_attempt=os.environ.get('GITHUB_RUN_ATTEMPT'),
        frozen_package_sha256=hashlib.sha256(PACKAGE.read_bytes()).hexdigest(),
        provider=package['provider'], model=package['model'], model_version=package['model_version'], runtime_sha256=package['runtime_sha256'],
        execution_adapter_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        usd_hard_cap=package['proposed_new_hard_cap_usd'], source_policy=package['evidence_class'],
        cost_basis='FROZEN_DEEPSEEK_PEAK_ALL_CACHE_MISS_NOT_VERIFIED_INVOICE')
    saved_rows = []
    journal = args.out / 'journal.json'
    def checkpoint(ledger, rows=None):
        nonlocal saved_rows
        if rows is not None:
            saved_rows = list(rows)
        _write_json(journal, dict(metadata, state='IN_PROGRESS', attempts=ledger.attempts,
            calls=ledger.calls, cost_usd=ledger.cost_usd, rows=saved_rows))
    provider_package = dict(package, maximum_output_tokens_per_call=512)
    provider = CG03Provider(os.environ['DEEPSEEK_API_KEY'], provider_package)
    try:
        result = run_with_provider(provider, package, checkpoint)
    except Exception as exc:
        receipt = json.loads(journal.read_text()) if journal.exists() else metadata
        _write_json(journal, dict(receipt, state='FAILED', failure_type=type(exc).__name__))
        return 1
    if result['calls'] != 20 or len(result['rows']) != 20 or result['cost_usd'] > .30:
        _write_json(journal, dict(metadata, state='INVALID_FINAL_RECEIPT', **result))
        return 1
    receipt = dict(metadata, state='COMPLETE', **result)
    _write_json(args.out / 'results.json', receipt)
    _write_json(journal, receipt)
    print(json.dumps(dict(calls=result['calls'], conservative_cost_upper_usd=result['cost_usd'])))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

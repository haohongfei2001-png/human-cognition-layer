"""Dormant one-shot CG03 runner; a new exact owner grant is required."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

from scripts.cg03_external_package import PACKAGE, build_package, score_answer
from scripts.run_cg02_external_once import DeepSeekProvider


def _write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n')
    temporary.replace(path)


def load_frozen_package():
    frozen = json.loads(PACKAGE.read_text())
    if frozen != build_package():
        raise ValueError('frozen CG03 package differs from provider-free preflight')
    if (frozen['provider'] != 'deepseek' or
        frozen['actions_secret_name'] != 'DEEPSEEK_API_KEY' or
        frozen['model'] != 'deepseek-v4-pro' or
        len(frozen['cases']) != 4 or len(frozen['arms']) != 5 or
        frozen['maximum_provider_calls_if_separately_authorized'] != 20 or
        frozen['retries_if_authorized'] != 0 or
        frozen['proposed_new_hard_cap_usd'] != 0.30 or
        frozen['execution_authorized'] or frozen['provider_calls_executed']):
        raise ValueError('CG03 provider, call or authorization contract drift')
    return frozen


class BudgetLedger:
    def __init__(self, package, checkpoint=None):
        self.package = package
        self.checkpoint = checkpoint
        self.calls = 0
        self.cost_usd = 0.0
        self.attempts = []

    def _reserve(self, messages):
        input_bytes = len(json.dumps(messages, ensure_ascii=False).encode())
        if input_bytes > self.package['maximum_serialized_input_bytes_per_call']:
            raise ValueError('serialized input byte bound exceeded')
        basis = self.package['price_basis']
        input_tokens = input_bytes + self.package['conservative_framing_token_reserve_per_call']
        cost = (input_tokens * basis['input_cache_miss_usd_per_million'] +
                self.package['maximum_output_tokens_per_call_if_authorized'] *
                basis['output_usd_per_million']) / 1_000_000
        return input_tokens, cost

    def call(self, provider, messages):
        if self.calls >= self.package['maximum_provider_calls_if_separately_authorized']:
            raise ValueError('call cap exceeded')
        input_bound, reserve = self._reserve(messages)
        if self.cost_usd + reserve > self.package['proposed_new_hard_cap_usd']:
            raise ValueError('USD hard cap would be exceeded')
        self.calls += 1
        attempt = {'call_index': self.calls, 'request_raw': {
            'endpoint': self.package['provider_endpoint'] + '/chat/completions',
            'model': self.package['model'], 'messages': messages,
            'max_tokens': self.package['maximum_output_tokens_per_call_if_authorized'],
            'response_format': self.package['provider_request']['response_format'],
            'thinking': self.package['provider_request']['thinking']},
            'pending_reservation_usd': reserve}
        self.attempts.append(attempt)
        if self.checkpoint:
            self.checkpoint(self)
        try:
            result = provider(messages)
            if (result['model'] not in (self.package['model'], self.package['model_version']) or
                result['input_tokens'] > input_bound or
                result['output_tokens'] > self.package['maximum_output_tokens_per_call_if_authorized'] or
                result['cost_usd'] < 0 or result['cost_usd'] > reserve or
                not isinstance(result['raw'], str)):
                raise ValueError('provider contract or cap violation')
        except Exception as exc:
            self.cost_usd += reserve
            attempt.pop('pending_reservation_usd', None)
            attempt['failure_reservation_usd'] = reserve
            attempt['failure_type'] = type(exc).__name__
            if self.checkpoint:
                self.checkpoint(self)
            raise
        attempt.pop('pending_reservation_usd', None)
        attempt['result'] = result
        self.cost_usd += result['cost_usd']
        if self.checkpoint:
            self.checkpoint(self)
        return result


def run_with_provider(provider, package, checkpoint=None):
    ledger = BudgetLedger(package, checkpoint)
    rows = []
    for case in package['cases']:
        for arm in package['arms']:
            messages = case['messages'][arm]
            result = ledger.call(provider, messages)
            rows.append({'case_id': case['case_id'], 'arm': arm,
                'raw': result['raw'], 'score': score_answer(case, result['raw']),
                'usage': {key: result[key] for key in ('model', 'input_tokens',
                    'output_tokens', 'cost_usd', 'provider_price_estimated_cost_usd',
                    'usage_raw')},
                'response_raw': result['response_raw'],
                'final_messages': messages,
                'preflight': case['preflight'] if arm in ('H', 'H-new') else None})
            if checkpoint:
                checkpoint(ledger, rows)
    return {'rows': rows, 'calls': ledger.calls,
        'cost_usd': ledger.cost_usd, 'attempts': ledger.attempts,
        'scope': 'HCL_AUTHORED_SYNTHETIC_DEVELOPMENT_NOT_FRESH_EXTERNAL_EVIDENCE'}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--validate-only', action='store_true')
    args = parser.parse_args()
    package = load_frozen_package()
    if args.validate_only:
        print(json.dumps({'cases': len(package['cases']), 'arms': package['arms'],
            'maximum_provider_calls': package['maximum_provider_calls_if_separately_authorized'],
            'proposed_hard_cap_usd': package['proposed_new_hard_cap_usd'],
            'treatment_presence': 'PASS', 'provider_calls_executed': 0}))
        return 0
    if os.environ.get('HCL_CG03_AUTHORIZED_CAP_USD') != '0.30':
        raise SystemExit('exact CG03 owner grant is absent')
    authorized_sha = os.environ.get('HCL_CG03_AUTHORIZED_BASE_SHA')
    git_sha = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
    if not authorized_sha or git_sha != authorized_sha:
        raise SystemExit('CG03 authorized SHA mismatch')
    key = os.environ.get('DEEPSEEK_API_KEY')
    if not key:
        raise SystemExit('existing DeepSeek Actions secret is absent')
    args.out.mkdir(parents=True, exist_ok=True)
    journal = args.out / 'journal.json'
    metadata = {'schema': 'hcl-cg03-external-run-v1', 'git_sha': git_sha,
        'run_id': os.environ.get('GITHUB_RUN_ID'),
        'run_attempt': os.environ.get('GITHUB_RUN_ATTEMPT'),
        'frozen_package_sha256': hashlib.sha256(PACKAGE.read_bytes()).hexdigest(),
        'provider': package['provider'], 'model': package['model'],
        'model_version': package['model_version'],
        'usd_hard_cap': package['proposed_new_hard_cap_usd'],
        'cost_basis': 'REPOSITORY_FROZEN_DEEPSEEK_PEAK_ALL_CACHE_MISS',
        'source_policy': package['evidence_class']}

    def checkpoint(ledger, rows=None):
        _write_json(journal, dict(metadata, state='IN_PROGRESS',
            calls=ledger.calls, cost_usd=ledger.cost_usd,
            attempts=ledger.attempts, rows=rows or []))

    # DeepSeekProvider is shared with the executed CG02 infrastructure. The
    # package remains unauthorized until the exact external owner gate above.
    provider_package = dict(package,
        maximum_output_tokens_per_call=package['maximum_output_tokens_per_call_if_authorized'])
    provider = DeepSeekProvider(key, provider_package)
    try:
        result = run_with_provider(provider, package, checkpoint=checkpoint)
    except Exception as exc:
        current = json.loads(journal.read_text()) if journal.exists() else metadata
        current.update(state='FAILED', failure_type=type(exc).__name__)
        _write_json(journal, current)
        print(f'CG03 run stopped: {type(exc).__name__}', file=sys.stderr)
        return 1
    if (result['calls'] != 20 or len(result['rows']) != 20 or
        result['cost_usd'] > package['proposed_new_hard_cap_usd']):
        _write_json(journal, dict(metadata, state='INVALID_FINAL_RECEIPT', **result))
        return 1
    final = dict(metadata, state='COMPLETE', **result)
    _write_json(args.out / 'results.json', final)
    _write_json(journal, final)
    print(json.dumps({'calls': result['calls'], 'rows': len(result['rows']),
        'conservative_cost_upper_usd': result['cost_usd']}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

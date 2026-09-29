"""Fresh G-ARCH operational smoke; never reuses the closed E03 grant."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.run_cg02_external_once import DeepSeekProvider
from scripts.run_cognition_functional_once import (
    ReplayExtraction, digest, execute, prepare, write_json)
from scripts.witness_identity_roles import SOURCE, QUERY

PACKAGE = Path('reports/HCL_G_ARCH_ENTRY_PACKAGE.json')
WORKFLOW = Path('.github/workflows/hcl-g-arch-entry-once.yml')
HISTORICAL = Path('reports/HCL_ORDINARY_ENTRY_FUNCTIONAL_36527863771/functional-run.json')
FIELDS = ('self_description', 'others_attribution', 'role_occupancy',
    'role_requirement', 'reported_behavior', 'personal_endorsement', 'unresolved')


def build_package():
    files = sorted([*Path('hcl').rglob('*.py'),
        Path('scripts/run_cognition_functional_once.py'),
        Path('scripts/run_cg02_external_once.py'),
        Path('scripts/witness_identity_roles.py'),
        Path('scripts/run_g_arch_entry_once.py'), WORKFLOW])
    hashes = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    return dict(schema='hcl-g-arch-entry-functional-v1',
        purpose='ONE_OPERATIONAL_SOURCE_ANCHOR_AND_FINAL_INPUT_SMOKE_NOT_EFFICACY',
        authorization='OWNER_DEFAULT_APPROVAL_EXISTING_PROVIDER_NORMAL_BOUNDED_COST',
        historical_budget_transfer=False, old_run_replayed_provider_free_only=True,
        provider='deepseek', provider_endpoint='https://api.deepseek.com',
        model='deepseek-flash', expected_model_family='DeepSeek-V4.1-Flash',
        provider_request=dict(thinking=dict(type='disabled'),
            response_format=dict(type='json_object'), temperature=0, max_retries=0),
        service_tier='provider_default_no_tier_parameter', maximum_provider_calls=2,
        maximum_output_tokens=dict(extraction=1024, final=512), budget_cap_usd=0.04,
        guard_rates_usd_per_million=dict(input=1.32, output=3.96),
        rated_peak_rates_usd_per_million=dict(input=0.30, cache_hit=0.006, output=1.20),
        price_source='https://api-docs.deepseek.com/quick_start/pricing/',
        price_verified_date='2026-09-29',
        price_note='Official Flash peak rates; guard reserves higher Pro rates. Invoice cost unavailable.',
        source=SOURCE, query=QUERY, source_id='authored-ordinary-entry-functional',
        final_fields=list(FIELDS), runtime_files=hashes, runtime_sha256=digest(hashes),
        source_class='HCL_AUTHORED_SYNTHETIC_OPERATIONAL',
        longmemeval='SEALED_NOT_ACCESSED')


def load_package():
    package = json.loads(PACKAGE.read_text())
    if package != build_package():
        raise ValueError('G-ARCH entry source/runtime/package drift')
    return package


class HistoricalResponse:
    def __init__(self):
        self.raw = json.loads(HISTORICAL.read_text())['attempts'][0]['response_raw']['choices'][0]['message']['content']

    def complete_json(self, messages, **kwargs):
        return self.raw


def preflight(package):
    local = prepare(package, ReplayExtraction())
    historical = prepare(package, HistoricalResponse())
    repairs = [d['source_derived_anchor'] for d in historical['semantic_diagnostics']
        if d['source_derived_anchor']]
    if len(repairs) < 1 or any(d['semantic_support'] != 'BOUNDED_LITERAL_FORM'
            for d in historical['semantic_diagnostics']):
        raise ValueError('historical actual response not safely anchored')
    if local['cognition_state']['role_status'] != historical['cognition_state']['role_status']:
        raise ValueError('historical response changes functional role check')
    return dict(status='PASS_PROVIDER_FREE', package_sha256=digest(package),
        runtime_sha256=package['runtime_sha256'], provider_calls=0,
        local_preparation=local, historical_actual_response_replay=historical,
        safe_unique_source_offset_repairs=repairs,
        historical_run='FAILED_CLOSED_NO_NEW_CALL',
        live_entry='NOT_YET_VERIFIED')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--freeze', action='store_true')
    parser.add_argument('--preflight', action='store_true')
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--output', default='g-arch-entry-preflight.json')
    args = parser.parse_args()
    if sum((args.freeze, args.preflight, args.execute)) != 1:
        parser.error('exactly one mode required')
    if args.freeze:
        write_json(PACKAGE, build_package())
        return
    package = load_package()
    passed = preflight(package)
    if args.preflight:
        write_json(args.output, passed)
        return
    if (os.environ.get('GITHUB_RUN_ATTEMPT') != '1' or
            os.environ.get('HCL_G_ARCH_ENTRY_AUTHORIZED') != 'ONE_BOUNDED_DEVELOPMENT_SMOKE'):
        raise ValueError('first workflow attempt and explicit one-shot environment required')
    provider = DeepSeekProvider(os.environ.get('DEEPSEEK_API_KEY'), package)
    def transport(request):
        response = provider.client.chat.completions.create(
            **{k: v for k, v in request.items() if k != 'thinking'},
            extra_body=dict(thinking=request['thinking']))
        return response.model_dump(mode='json')
    execute(package, transport, args.output)


if __name__ == '__main__':
    main()

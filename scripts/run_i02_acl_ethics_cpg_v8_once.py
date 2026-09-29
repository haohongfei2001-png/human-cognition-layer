"""One bounded strong C/P/G v8 development calibration on ACL abstract 3."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.i02_acl_ethics_development_preflight import audit as source_audit
from scripts.run_i02_comparator_calibration_once import (
    Ledger, PEAK, PHASES, digest, transport, write_json)
from scripts.serious_eval_arms_v8 import (
    call_spec_v8, prepare_generic_final_v8, prepare_primary_arms_v8)
from scripts.serious_eval_contract import runtime_digest
from scripts.serious_eval_generic_workspace_v6 import MAX_MAP_BYTES
from scripts.serious_eval_semantic_score import validate_answer


SOURCE = Path('reports/HCL_I02_ACL_ETHICS_DEVELOPMENT_SOURCE.json')
OBLIGATIONS = Path('reports/HCL_I02_ACL_ETHICS_SOURCE_FIRST_OBLIGATIONS.json')
OVERLAY = Path('reports/HCL_I02_ACL_ETHICS_EXPOSURE_OVERLAY.json')
PACKAGE = Path('reports/HCL_I02_ACL_ETHICS_CPG_V8_PACKAGE.json')
WORKFLOW = Path('.github/workflows/hcl-i02-acl-ethics-cpg-v8-once.yml')
CAP_USD = 0.24


def build_package():
    gate = source_audit()
    files = [SOURCE, OBLIGATIONS, OVERLAY,
        Path('reports/HCL_I01_EVALUATION_FREEZE.json'),
        Path('reports/HCL_I02_SEMANTIC_SCORER_FREEZE.json'),
        Path('reports/HCL_I02_EXPOSURE_LINEAGE.json'),
        Path('reports/HCL_I02_SOURCE_FINGERPRINTS_V4.json'),
        Path('reports/HCL_I02_SCREENED_SYSTEMS_V3.json'),
        Path('scripts/i02_acl_ethics_development_preflight.py'),
        Path('scripts/i02_acl_ethics_exposure_overlay.py'),
        Path('scripts/i02_source_lineage.py'),
        Path('scripts/i02_source_qualification_v3.py'),
        Path('scripts/i02_source_qualification_v4.py'),
        Path('scripts/serious_eval_arms.py'),
        Path('scripts/serious_eval_arms_v2.py'),
        Path('scripts/serious_eval_arms_v3.py'),
        Path('scripts/serious_eval_arms_v4.py'),
        Path('scripts/serious_eval_generic_workspace_v5.py'),
        Path('scripts/serious_eval_generic_workspace_v6.py'),
        Path('scripts/serious_eval_generic_workspace_v7.py'),
        Path('scripts/serious_eval_arms_v8.py'),
        Path('scripts/serious_eval_semantic_score.py'),
        Path('scripts/serious_eval_contract.py'),
        Path('scripts/run_i02_comparator_calibration_once.py'),
        Path('scripts/run_i02_acl_ethics_cpg_v8_once.py'), WORKFLOW]
    hashes = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    specs = {phase: call_spec_v8(phase) for phase in PHASES}
    return dict(schema='hcl-i02-acl-ethics-cpg-v8-calibration-v1',
        purpose='ONE_ACL_SYNTHETIC_DEVELOPMENT_SOURCE_STRONG_CPG_INTERFACE_CALIBRATION',
        authorization='OWNER_DEFAULT_EXISTING_PROVIDER_NORMAL_BOUNDED_COST',
        historical_budget_transfer=False, provider='deepseek',
        provider_endpoint='https://api.deepseek.com',
        model='deepseek-v4-pro', model_family='DeepSeek-V4-Pro-0813',
        service_tier='provider_default_no_tier_parameter',
        call_specs=specs, phases=list(PHASES), retries=0,
        maximum_provider_calls=4, maximum_map_bytes=MAX_MAP_BYTES,
        budget_cap_usd=CAP_USD, peak_rates_usd_per_million=PEAK,
        price_source='https://api-docs.deepseek.com/quick_start/pricing/',
        price_verified_date='2026-09-29',
        source_file_sha256=gate['source_file_sha256'],
        obligations_file_sha256=gate['obligations_file_sha256'],
        source_sha256=gate['source_sha256'],
        question_sha256=gate['question_sha256'],
        question_origin='ADAPTED_NATIVE_ACTIVITY_DEVELOPMENT_ONLY',
        source_distribution='ACL_EACL_2023_SYNTHETIC_ABSTRACTS_DEVELOPMENT_EXPOSED',
        confirmation_items_inspected=0, h_arm_calls=0, hnew_arm_calls=0,
        hcl_runtime_sha256=runtime_digest(),
        execution_files=hashes, execution_sha256=digest(hashes),
        longmemeval='SEALED_NOT_ACCESSED')


def load_package():
    package = json.loads(PACKAGE.read_text())
    if package != build_package():
        raise ValueError('ACL CPG v8 frozen package or execution surface drift')
    return package


def _input_bound(request):
    return len(json.dumps(request, ensure_ascii=False).encode()) * 2 + 2048


def _reservation(request):
    return (_input_bound(request) * PEAK['input'] +
        request['max_tokens'] * PEAK['output']) / 1_000_000


def _request(spec, messages):
    # `provider` is package metadata, not a Chat Completions request field.
    return dict((key, value) for key, value in spec.items()
                if key != 'provider') | {'messages': messages}


def preflight(package):
    gate = source_audit()
    if (gate['h_specialized_treatment_present'] or
            gate['independent_confirmation_qualified'] or
            gate['source_file_sha256'] != package['source_file_sha256'] or
            gate['obligations_file_sha256'] != package['obligations_file_sha256'] or
            gate['h_runtime_sha256'] != package['hcl_runtime_sha256'] or
            package['h_arm_calls'] or package['hnew_arm_calls'] or
            package['confirmation_items_inspected'] or
            package['longmemeval'] != 'SEALED_NOT_ACCESSED'):
        raise ValueError('source, H treatment or confirmation boundary failed')
    item = json.loads(SOURCE.read_text())
    arms = prepare_primary_arms_v8(item['ordinary_question'],
        item['source_id'], item['source_text'])
    if arms['call_specs'] != package['call_specs']:
        raise ValueError('native strong comparator call spec drift')
    mock = json.dumps(dict(source_index=[dict(id='e1',
        source_id=item['source_id'],
        quote='publicly-accessible EPub versions of all the books of the commercial Amazonia bookshop web storefront')],
        relations=[], answer_plan=[], open_questions=[]))
    final = prepare_generic_final_v8(arms, mock)
    if json.loads(final[-1]['content'])['sources'] != arms['ordinary_payload']['sources']:
        raise ValueError('G final original-source loss')
    messages = {phase: arms[phase] for phase in ('C', 'P', 'G_map')}
    messages['G_final'] = final
    bounds = {}
    for phase in PHASES:
        request = _request(package['call_specs'][phase], messages[phase])
        bounds[phase] = dict(input_token_bound=_input_bound(request),
            reserved_usd=_reservation(request))
    # The actual G map could occupy all 3,500 bytes. Reserve that entire
    # additional input in G-final, even if the provider returns a short map.
    bounds['G_final']['input_token_bound'] += 2 * MAX_MAP_BYTES
    bounds['G_final']['reserved_usd'] += (
        2 * MAX_MAP_BYTES * PEAK['input'] / 1_000_000)
    worst = sum(row['reserved_usd'] for row in bounds.values())
    if worst > package['budget_cap_usd']:
        raise ValueError('all-phase peak reservation exceeds hard cap')
    return dict(schema='hcl-i02-acl-ethics-cpg-v8-preflight-v1',
        status='PASS_SOURCE_FIRST_CPG_ONLY',
        package_sha256=digest(package), source_gate=gate,
        phase_bounds=bounds, all_phase_peak_reservation_usd=worst,
        provider_calls=0, provider_spend_usd=0,
        longmemeval='SEALED_NOT_ACCESSED'), arms


class LedgerV8(Ledger):
    def __init__(self, package, output):
        super().__init__(package, output)
        self.receipt['schema'] = 'hcl-i02-acl-ethics-cpg-v8-run-v1'
        self.receipt['source_attribution'] = (
            'Benotti, Fort, Kan and Tsvetkov; EACL 2023 Ethics Tutorial, CC BY 4.0')
        self.save()

    def call(self, phase, messages, provider):
        if (self.receipt['status'] != 'STARTED' or
                len(self.receipt['attempts']) >= len(PHASES) or
                phase != PHASES[len(self.receipt['attempts'])]):
            raise ValueError('one call per frozen phase; no retry')
        request = _request(self.package['call_specs'][phase], messages)
        bound, reserve = _input_bound(request), _reservation(request)
        if self.receipt['conservative_reserved_usd'] + reserve > self.package['budget_cap_usd']:
            raise ValueError('hard cap refuses next call before transport')
        attempt = dict(phase=phase, request_raw=request,
            input_token_bound=bound, reserved_usd=reserve)
        self.receipt['attempts'].append(attempt)
        self.receipt['provider_calls'] = len(self.receipt['attempts'])
        self.receipt['conservative_reserved_usd'] += reserve
        self.save()
        try:
            raw = provider(request)
            attempt['response_raw'] = raw
            self.save()
            choices = raw.get('choices') or []
            choice = choices[0] if choices else {}
            content = (choice.get('message') or {}).get('content')
            usage = raw.get('usage') or {}
            inp, out = usage.get('prompt_tokens'), usage.get('completion_tokens')
            attempt.update(actual_model_id=raw.get('model'), usage=usage)
            if type(inp) is int and type(out) is int and min(inp, out) >= 0:
                rated = (inp * PEAK['input'] + out * PEAK['output']) / 1_000_000
                self.receipt['rated_peak_cost_usd'] += rated
                attempt['rated_peak_cost_usd'] = rated
                hit, miss, created = (usage.get('prompt_cache_hit_tokens'),
                    usage.get('prompt_cache_miss_tokens'), raw.get('created'))
                estimated = None
                if (type(hit) is int and type(miss) is int and hit + miss == inp and
                        type(created) is int):
                    stamp = datetime.fromtimestamp(created, timezone.utc)
                    peak = stamp.weekday() < 5 and (
                        1 <= stamp.hour < 4 or 6 <= stamp.hour < 10)
                    factor = 1 if peak else 0.5
                    estimated = (hit * PEAK['cache_hit'] + miss * PEAK['input'] +
                                 out * PEAK['output']) / 1_000_000 * factor
                attempt['estimated_actual_cost_usd'] = estimated
                self.receipt['estimated_actual_cost_usd'] = (
                    self.receipt['estimated_actual_cost_usd'] + estimated
                    if estimated is not None and
                    self.receipt['estimated_actual_cost_usd'] is not None else None)
            else:
                self.receipt['estimated_actual_cost_usd'] = None
            self.save()
            if (raw.get('model') != self.package['model'] or
                    type(inp) is not int or not 0 <= inp <= bound or
                    type(out) is not int or not 0 <= out <= request['max_tokens'] or
                    choice.get('finish_reason') != 'stop' or
                    not isinstance(content, str)):
                raise ValueError('model, usage or completion contract failed')
            return content
        except Exception as exc:
            attempt['failure_type'] = type(exc).__name__
            self.receipt['status'] = 'FAILED_NO_RETRY'
            if 'response_raw' not in attempt:
                self.receipt['estimated_actual_cost_usd'] = None
            self.save()
            raise


def execute(package, provider, output):
    gate, arms = preflight(package)
    ledger = LedgerV8(package, output)
    ledger.receipt['preflight'] = gate
    ledger.save()
    source = json.loads(SOURCE.read_text())['source_text']
    source_id = json.loads(SOURCE.read_text())['source_id']
    try:
        results = {}
        for phase in PHASES:
            messages = (arms[phase] if phase != 'G_final' else
                prepare_generic_final_v8(arms, results['G_map']))
            content = ledger.call(phase, messages, provider)
            results[phase] = content
            try:
                parsed = json.loads(content)
                if phase == 'G_map':
                    if len(content.encode()) > MAX_MAP_BYTES:
                        raise ValueError('frozen map byte bound')
                    prepare_generic_final_v8(arms, content)
                else:
                    validate_answer(parsed, {source_id: source})
                disposition = 'SHAPE_AND_SOURCE_CITATIONS_VALID'
            except (ValueError, TypeError, KeyError) as exc:
                disposition = 'INVALID_' + type(exc).__name__.upper()
                ledger.receipt.setdefault('shape_results', {})[phase] = disposition
                ledger.save()
                if phase == 'G_map':
                    ledger.receipt['status'] = 'G_MAP_INVALID_G_FINAL_NOT_CALLED'
                    break
            ledger.receipt.setdefault('shape_results', {})[phase] = disposition
            ledger.save()
        if ledger.receipt['status'] == 'STARTED':
            ledger.receipt['status'] = 'COMPLETED_REQUIRES_SOURCE_FIRST_SEMANTIC_AUDIT'
    except Exception as exc:
        ledger.receipt['status'] = 'FAILED_NO_RETRY'
        ledger.receipt['failure_type'] = type(exc).__name__
        raise
    finally:
        ledger.receipt['authorization_remaining_usd'] = 0
        ledger.receipt['budget_state'] = 'CLOSED_NO_TRANSFER_NO_RERUN'
        ledger.save()
    return ledger.receipt


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--freeze', action='store_true')
    parser.add_argument('--preflight', action='store_true')
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--output', default='i02-acl-ethics-cpg-v8-receipt.json')
    args = parser.parse_args()
    if sum((args.freeze, args.preflight, args.execute)) != 1:
        parser.error('exactly one mode required')
    if args.freeze:
        write_json(PACKAGE, build_package())
        return
    package = load_package()
    gate, _ = preflight(package)
    if args.preflight:
        write_json(args.output, gate)
        return
    if (os.environ.get('GITHUB_RUN_ATTEMPT') != '1' or
            os.environ.get('HCL_I02_ACL_ETHICS_CPG_V8_AUTHORIZED') !=
                'ONE_CALIBRATION_ONLY'):
        raise ValueError('first unique one-shot workflow required')
    from openai import OpenAI
    key = os.environ.get('DEEPSEEK_API_KEY')
    if not key:
        raise ValueError('existing DeepSeek secret required')
    client = OpenAI(api_key=key, base_url=package['provider_endpoint'],
        max_retries=0, timeout=120)
    execute(package, lambda request: transport(request, client), args.output)


if __name__ == '__main__':
    main()

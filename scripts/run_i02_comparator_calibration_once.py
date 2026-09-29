"""One bounded C/P/G functional calibration on an exposed source group.

This cannot compare H or score independent efficacy. It preserves raw requests,
responses and usage, and closes its one-use budget even after a failed call.
"""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.i02_musr_calibration import (FIRST_GROUP_SHA256, SOURCE_SHA256,
    calibration_candidate, parse_pinned)
from scripts.serious_eval_arms import prepare_generic_final, prepare_primary_arms
from scripts.serious_eval_contract import (runtime_digest, validate_candidate,
    validate_runtime_amendment)

PACKAGE = Path('reports/HCL_I02_COMPARATOR_CALIBRATION_PACKAGE.json')
WORKFLOW = Path('.github/workflows/hcl-i02-comparator-calibration-once.yml')
SOURCE_PATH = Path('i02-musr-calibration.csv')
PHASES = ('C', 'P', 'G_map', 'G_final')
OUTPUT_LIMITS = dict(C=768, P=768, G_map=1024, G_final=768)
PEAK = dict(input=1.32, cache_hit=0.044, output=3.96)


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
        separators=(',', ':')).encode()).hexdigest()


def write_json(path, value):
    path = Path(path)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + '\n')
    temporary.replace(path)


def build_package():
    files = (Path('scripts/serious_eval_arms.py'),
        Path('scripts/i02_musr_calibration.py'),
        Path('scripts/run_i02_comparator_calibration_once.py'), WORKFLOW)
    hashes = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    amendment = json.loads(Path('reports/HCL_I02_RUNTIME_AMENDMENT.json').read_text())
    return dict(schema='hcl-i02-cpg-calibration-v1',
        purpose='ONE_EXPOSED_SOURCE_CPG_FUNCTIONAL_CALIBRATION_NO_H_EFFICACY',
        authorization='OWNER_DEFAULT_EXISTING_PROVIDER_NORMAL_BOUNDED_COST',
        historical_budget_transfer=False, provider='deepseek',
        provider_endpoint='https://api.deepseek.com', model='deepseek-v4-pro',
        model_family='DeepSeek-V4-Pro-0813', thinking='disabled',
        service_tier='provider_default_no_tier_parameter', temperature=0,
        response_format=dict(type='json_object'), retries=0,
        phases=list(PHASES), maximum_provider_calls=4,
        maximum_output_tokens=OUTPUT_LIMITS, maximum_map_bytes=5000,
        budget_cap_usd=0.12, peak_rates_usd_per_million=PEAK,
        price_source='https://api-docs.deepseek.com/quick_start/pricing/',
        price_verified_date='2026-09-29',
        source_distribution='TAUR-Lab/MuSR Hugging Face CC BY 4.0',
        source_file_sha256=SOURCE_SHA256,
        calibration_source_group_sha256=FIRST_GROUP_SHA256,
        calibration_row_index=0, native_gold_in_provider_input=False,
        confirmation_items_inspected=0, h_arm_calls=0,
        hcl_runtime_sha256=amendment['amended_hcl_runtime_sha256'],
        execution_files=hashes, execution_sha256=digest(hashes),
        longmemeval='SEALED_NOT_ACCESSED')


def load_package():
    package = json.loads(PACKAGE.read_text())
    if package != build_package():
        raise ValueError('I02 calibration package or execution surface drift')
    freeze = json.loads(Path('reports/HCL_I01_EVALUATION_FREEZE.json').read_text())
    amendment = json.loads(Path('reports/HCL_I02_RUNTIME_AMENDMENT.json').read_text())
    validate_runtime_amendment(freeze, amendment)
    if package['hcl_runtime_sha256'] != runtime_digest():
        raise ValueError('amended runtime drift')
    return package


def preflight(package, source_path):
    raw = Path(source_path).read_bytes()
    if hashlib.sha256(raw).hexdigest() != package['source_file_sha256']:
        raise ValueError('pinned calibration source hash mismatch')
    rows, groups = parse_pinned(raw)
    if groups[FIRST_GROUP_SHA256] != [0, 1, 2, 3]:
        raise ValueError('exposed source group drift')
    case = calibration_candidate(rows[0], source_group_id=FIRST_GROUP_SHA256)
    validate_candidate(json.loads(Path('reports/HCL_I01_EVALUATION_FREEZE.json').read_text()), case)
    arms = prepare_primary_arms(case['question'], FIRST_GROUP_SHA256, case['source_text'])
    ordinary = arms['ordinary_payload']
    if not all(json.loads(arms[arm][-1]['content']) == ordinary for arm in ('C', 'P', 'G_map')):
        raise ValueError('C/P/G ordinary input mismatch')
    if (package['native_gold_in_provider_input'] or package['h_arm_calls'] or
            package['confirmation_items_inspected'] or package['source_file_sha256'] != SOURCE_SHA256):
        raise ValueError('calibration input firewall failed')
    # A complete input bound plus output reservations fits the hard cap even
    # when the generic map occupies its maximum accepted character count.
    estimates = [len(json.dumps(arms[p], ensure_ascii=False).encode()) * 2 + 2048
                 for p in ('C', 'P', 'G_map')]
    estimates.append((len(json.dumps(arms['C'], ensure_ascii=False).encode()) +
                      package['maximum_map_bytes'] * 2) * 2 + 2048)
    worst = sum((bound * PEAK['input'] + OUTPUT_LIMITS[phase] * PEAK['output']) / 1_000_000
                for phase, bound in zip(PHASES, estimates))
    if worst > package['budget_cap_usd']:
        raise ValueError('all-phase conservative reservation exceeds hard cap')
    return dict(schema='hcl-i02-cpg-calibration-preflight-v1',
        status='PASS_PROVIDER_FREE_CPG_ONLY', package_sha256=digest(package),
        source_file_sha256=hashlib.sha256(raw).hexdigest(),
        source_group_sha256=FIRST_GROUP_SHA256, case_id=case['case_id'],
        question_sha256=hashlib.sha256(case['question'].encode()).hexdigest(),
        source_text_sha256=hashlib.sha256(case['source_text'].encode()).hexdigest(),
        input_equal=True, answer_fields=ordinary['answer_fields'],
        phase_max_input_token_bounds=estimates,
        all_phase_peak_reservation_usd=worst,
        h_native_treatment='FAIL_ABSENT_NOT_EVALUATED',
        source_semantics='FIRST_NATIVE_QUESTION_SOURCE_PLAUSIBLE_NOT_PRIVATE_TRUTH',
        provider_calls=0, provider_spend_usd=0,
        longmemeval='SEALED_NOT_ACCESSED'), arms


class Ledger:
    def __init__(self, package, output):
        self.package, self.output = package, Path(output)
        if self.output.exists():
            raise ValueError('existing receipt refuses rerun')
        self.receipt = dict(schema='hcl-i02-cpg-calibration-run-v1',
            status='STARTED', package_sha256=digest(package),
            run_id=os.environ.get('GITHUB_RUN_ID'),
            run_attempt=os.environ.get('GITHUB_RUN_ATTEMPT'),
            sha=os.environ.get('GITHUB_SHA'), attempts=[],
            conservative_reserved_usd=0.0, rated_peak_cost_usd=0.0,
            estimated_actual_cost_usd=0.0, actual_invoice_cost_usd=None,
            hard_cap_usd=package['budget_cap_usd'], provider_calls=0,
            retries=0, h_arm_calls=0, native_gold_used=False,
            longmemeval='SEALED_NOT_ACCESSED')
        self.save()

    def save(self):
        write_json(self.output, self.receipt)

    def call(self, phase, messages, provider):
        if (self.receipt['status'] != 'STARTED' or
                len(self.receipt['attempts']) >= len(PHASES) or
                phase != PHASES[len(self.receipt['attempts'])]):
            raise ValueError('one call per frozen phase; no retry')
        request = dict(model=self.package['model'], messages=messages,
            max_tokens=OUTPUT_LIMITS[phase], temperature=0,
            response_format=dict(type='json_object'),
            thinking=dict(type='disabled'))
        bound = len(json.dumps(request, ensure_ascii=False).encode()) * 2 + 2048
        reserve = (bound * PEAK['input'] + request['max_tokens'] * PEAK['output']) / 1_000_000
        if self.receipt['conservative_reserved_usd'] + reserve > self.package['budget_cap_usd']:
            raise ValueError('hard cap refuses next call before transport')
        attempt = dict(phase=phase, request_raw=request, input_token_bound=bound,
            reserved_usd=reserve)
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
                    peak = stamp.weekday() < 5 and (1 <= stamp.hour < 4 or 6 <= stamp.hour < 10)
                    factor = 1 if peak else 0.5
                    estimated = (hit * PEAK['cache_hit'] + miss * PEAK['input'] +
                                 out * PEAK['output']) / 1_000_000 * factor
                attempt['estimated_actual_cost_usd'] = estimated
                self.receipt['estimated_actual_cost_usd'] = (
                    self.receipt['estimated_actual_cost_usd'] + estimated
                    if estimated is not None and self.receipt['estimated_actual_cost_usd'] is not None
                    else None)
            else:
                self.receipt['estimated_actual_cost_usd'] = None
            self.save()
            if (raw.get('model') != self.package['model'] or
                    type(inp) is not int or not 0 <= inp <= bound or
                    type(out) is not int or not 0 <= out <= request['max_tokens'] or
                    choice.get('finish_reason') != 'stop' or not isinstance(content, str)):
                raise ValueError('model, usage or completion contract failed')
            return content
        except Exception as exc:
            attempt['failure_type'] = type(exc).__name__
            self.receipt['status'] = 'FAILED_NO_RETRY'
            if 'response_raw' not in attempt:
                self.receipt['estimated_actual_cost_usd'] = None
            self.save()
            raise


def execute(package, source_path, provider, output):
    gate, arms = preflight(package, source_path)
    ledger = Ledger(package, output)
    ledger.receipt['preflight'] = gate
    ledger.save()
    try:
        results = {}
        for phase in PHASES:
            messages = (arms[phase] if phase != 'G_final' else
                prepare_generic_final(arms, results['G_map']))
            raw = ledger.call(phase, messages, provider)
            parsed = json.loads(raw)
            if phase == 'G_map':
                if len(raw.encode()) > package['maximum_map_bytes']:
                    raise ValueError('generic map exceeds frozen bound')
                # The exact-source map is validated before any final G call.
                prepare_generic_final(arms, raw)
            elif not isinstance(parsed, dict) or set(parsed) != set(gate['answer_fields']):
                raise ValueError('answer field contract failed')
            results[phase] = raw
            ledger.receipt.setdefault('parsed_results', {})[phase] = parsed
            ledger.save()
        ledger.receipt['status'] = 'COMPLETED_REQUIRES_SOURCE_FIRST_CALIBRATION_AUDIT'
    except Exception as exc:
        ledger.receipt['status'] = 'FAILED_NO_RETRY'
        ledger.receipt['failure_type'] = type(exc).__name__
        raise
    finally:
        ledger.receipt['authorization_remaining_usd'] = 0
        ledger.receipt['budget_state'] = 'CLOSED_NO_TRANSFER_NO_RERUN'
        ledger.save()
    return ledger.receipt


def transport(request, client):
    response = client.chat.completions.create(
        **{k: v for k, v in request.items() if k != 'thinking'},
        extra_body={'thinking': request['thinking']})
    return response.model_dump(mode='json')


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--freeze', action='store_true')
    parser.add_argument('--preflight', action='store_true')
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--source', default=str(SOURCE_PATH))
    parser.add_argument('--output', default='i02-cpg-calibration-receipt.json')
    args = parser.parse_args()
    if sum((args.freeze, args.preflight, args.execute)) != 1:
        parser.error('exactly one mode required')
    if args.freeze:
        write_json(PACKAGE, build_package())
        return
    package = load_package()
    gate, _ = preflight(package, args.source)
    if args.preflight:
        write_json(args.output, gate)
        return
    if (os.environ.get('GITHUB_RUN_ATTEMPT') != '1' or
            os.environ.get('HCL_I02_CPG_AUTHORIZED') != 'ONE_CALIBRATION_ONLY'):
        raise ValueError('first unique one-shot workflow required')
    from openai import OpenAI
    key = os.environ.get('DEEPSEEK_API_KEY')
    if not key:
        raise ValueError('existing DeepSeek secret required')
    client = OpenAI(api_key=key, base_url=package['provider_endpoint'],
        max_retries=0, timeout=120)
    execute(package, args.source, lambda request: transport(request, client), args.output)


if __name__ == '__main__':
    main()

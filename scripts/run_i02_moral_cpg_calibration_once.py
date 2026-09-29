"""One bounded C/P/G v2 interface calibration on one exposed Moral Stories row."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.i02_moral_calibration import (FIRST_ID, FIRST_LINE_SHA256,
    SOURCE_SHA256, UPSTREAM, calibration_candidate)
from scripts.run_i02_comparator_calibration_once import (Ledger, OUTPUT_LIMITS,
    PEAK, PHASES, digest, transport, write_json)
from scripts.serious_eval_arms_v2 import (prepare_generic_final,
    prepare_primary_arms_v2)
from scripts.serious_eval_contract import (runtime_digest, validate_candidate,
    validate_runtime_amendment_v2)


PACKAGE = Path('reports/HCL_I02_MORAL_CPG_CALIBRATION_PACKAGE.json')
WORKFLOW = Path('.github/workflows/hcl-i02-moral-cpg-calibration-once.yml')
SOURCE_PATH = Path('i02-moral-stories-calibration.jsonl')
MAX_MAP_BYTES = 3000
CAP_USD = 0.06


def build_package():
    files = (Path('scripts/i02_moral_calibration.py'),
        Path('scripts/serious_eval_arms.py'),
        Path('scripts/serious_eval_arms_v2.py'),
        Path('scripts/run_i02_comparator_calibration_once.py'),
        Path('scripts/run_i02_moral_cpg_calibration_once.py'),
        Path('scripts/serious_eval_contract.py'), WORKFLOW)
    hashes = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    amendment = json.loads(Path('reports/HCL_I02_RUNTIME_AMENDMENT_V2.json').read_text())
    return dict(schema='hcl-i02-moral-cpg-calibration-v1',
        purpose='ONE_EXPOSED_SECOND_SOURCE_CPG_FUNCTIONAL_CALIBRATION_NO_H_EFFICACY',
        authorization='OWNER_DEFAULT_EXISTING_PROVIDER_NORMAL_BOUNDED_COST',
        historical_budget_transfer=False, provider='deepseek',
        provider_endpoint='https://api.deepseek.com', model='deepseek-v4-pro',
        model_family='DeepSeek-V4-Pro-0813', thinking='disabled',
        service_tier='provider_default_no_tier_parameter', temperature=0,
        response_format=dict(type='json_object'), retries=0,
        phases=list(PHASES), maximum_provider_calls=4,
        maximum_output_tokens=OUTPUT_LIMITS, maximum_map_bytes=MAX_MAP_BYTES,
        budget_cap_usd=CAP_USD, peak_rates_usd_per_million=PEAK,
        price_source='https://api-docs.deepseek.com/quick_start/pricing/',
        price_verified_date='2026-09-29',
        source_distribution='demelin/moral_stories author-team Hugging Face MIT',
        source_commit='b830cf56eb00bc4edd1860dd544a192216eb3587',
        source_url=UPSTREAM, source_file_sha256=SOURCE_SHA256,
        calibration_first_line_sha256=FIRST_LINE_SHA256,
        calibration_case_id=FIRST_ID, calibration_row_index=0,
        original_moral_immoral_field_names_in_model_input=False,
        native_gold_in_provider_input=False, confirmation_items_inspected=0,
        h_arm_calls=0, hcl_runtime_sha256=amendment['amended_hcl_runtime_sha256'],
        execution_files=hashes, execution_sha256=digest(hashes),
        longmemeval='SEALED_NOT_ACCESSED')


def load_package():
    package = json.loads(PACKAGE.read_text())
    if package != build_package():
        raise ValueError('Moral CPG package or execution surface drift')
    freeze = json.loads(Path('reports/HCL_I01_EVALUATION_FREEZE.json').read_text())
    v1 = json.loads(Path('reports/HCL_I02_RUNTIME_AMENDMENT.json').read_text())
    v2 = json.loads(Path('reports/HCL_I02_RUNTIME_AMENDMENT_V2.json').read_text())
    validate_runtime_amendment_v2(freeze, v1, v2)
    if package['hcl_runtime_sha256'] != runtime_digest():
        raise ValueError('amended HCL runtime drift')
    return package


def preflight(package, source_path):
    raw = Path(source_path).read_bytes()
    if hashlib.sha256(raw).hexdigest() != package['source_file_sha256']:
        raise ValueError('pinned source hash mismatch')
    case = calibration_candidate(raw)
    freeze = json.loads(Path('reports/HCL_I01_EVALUATION_FREEZE.json').read_text())
    validate_candidate(freeze, case)
    arms = prepare_primary_arms_v2(case['question'], case['source_id'],
        case['source_text'])
    c, p, g = [json.loads(arms[name][1]['content'])
        for name in ('C', 'P', 'G_map')]
    if (c != p or c['question'] != g['question'] or c['sources'] != g['sources'] or
            'answer_fields' in g or g.get('workspace_fields') !=
                ['source_index', 'open_questions'] or
            arms['ordinary_payload']['answer_fields'] != freeze['answer_fields']):
        raise ValueError('C/P/G ordinary input or map contract mismatch')
    if (package['native_gold_in_provider_input'] or package['h_arm_calls'] or
            package['confirmation_items_inspected'] or
            package['original_moral_immoral_field_names_in_model_input'] or
            any(label in case['source_text'] + case['question']
                for label in ('moral_action', 'immoral_action',
                              'moral_consequence', 'immoral_consequence'))):
        raise ValueError('source or label firewall failed')
    bounds = [len(json.dumps(arms[phase], ensure_ascii=False).encode()) * 2 + 2048
        for phase in ('C', 'P', 'G_map')]
    bounds.append((len(json.dumps(arms['C'], ensure_ascii=False).encode()) +
        package['maximum_map_bytes'] * 2) * 2 + 2048)
    worst = sum((bound * PEAK['input'] + OUTPUT_LIMITS[phase] * PEAK['output']) / 1_000_000
        for phase, bound in zip(PHASES, bounds))
    if worst > package['budget_cap_usd']:
        raise ValueError('all-phase peak reservation exceeds hard cap')
    return dict(schema='hcl-i02-moral-cpg-calibration-preflight-v1',
        status='PASS_PROVIDER_FREE_CPG_ONLY',
        package_sha256=digest(package), source_file_sha256=SOURCE_SHA256,
        first_line_sha256=FIRST_LINE_SHA256, case_id=case['case_id'],
        source_text_sha256=hashlib.sha256(case['source_text'].encode()).hexdigest(),
        question_sha256=hashlib.sha256(case['question'].encode()).hexdigest(),
        source_semantics='TWO_REPORTED_ALTERNATIVE_PATHS_NOT_ONE_ACTUAL_TIMELINE',
        author_norm_is_premise_not_moral_truth=True,
        first_row_only_exposed=True, confirmation_items_inspected=0,
        same_question_and_complete_source=True,
        answer_fields=list(c['answer_fields']),
        phase_max_input_token_bounds=bounds,
        all_phase_peak_reservation_usd=worst,
        h_arm_calls=0, provider_calls=0, provider_spend_usd=0,
        longmemeval='SEALED_NOT_ACCESSED'), arms


def execute(package, source_path, provider, output):
    gate, arms = preflight(package, source_path)
    ledger = Ledger(package, output)
    ledger.receipt['schema'] = 'hcl-i02-moral-cpg-calibration-run-v1'
    ledger.receipt['source_distribution'] = package['source_distribution']
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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--freeze', action='store_true')
    parser.add_argument('--preflight', action='store_true')
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--source', default=str(SOURCE_PATH))
    parser.add_argument('--output', default='i02-moral-cpg-calibration-receipt.json')
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
            os.environ.get('HCL_I02_MORAL_CPG_AUTHORIZED') != 'ONE_CALIBRATION_ONLY'):
        raise ValueError('first unique one-shot workflow required')
    from openai import OpenAI
    key = os.environ.get('DEEPSEEK_API_KEY')
    if not key:
        raise ValueError('existing DeepSeek secret required')
    client = OpenAI(api_key=key, base_url=package['provider_endpoint'],
        max_retries=0, timeout=120)
    execute(package, args.source, lambda request: transport(request, client),
        args.output)


if __name__ == '__main__':
    main()

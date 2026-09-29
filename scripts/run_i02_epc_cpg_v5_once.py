"""One source-first EPC development calibration of candidate C/P/G v5.

The native open question and publisher scenario were screened before any
provider output. This runner never tests H, confirmation, or a historical case.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import urllib.request

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.i02_input_coverage import audit_ordinary_input
from scripts.i02_source_lineage import require_development_calibration_input
from scripts.run_i02_comparator_calibration_once import (
    Ledger, OUTPUT_LIMITS, PEAK, PHASES, digest, transport, write_json)
from scripts.serious_eval_contract import (
    ARMS, FIELDS, runtime_digest, validate_candidate,
    validate_runtime_amendment_v2)
from scripts.serious_eval_generic_workspace_v5 import (
    prepare_generic_final_v5, prepare_primary_arms_v5)


PACKAGE = Path('reports/HCL_I02_EPC_CPG_V5_PACKAGE.json')
WORKFLOW = Path('.github/workflows/hcl-i02-epc-cpg-v5-once.yml')
URL = 'https://epc.ac.uk/toolkit/case-study-glass-safety-in-a-heritage-building-conversion/'
SOURCE_ID = 'epc-glass-safety-part-one-2022'
QUESTION = 'What ethical issues that can be identified in this scenario?'
SOURCE_SHA256 = '67d84d40b4a543e5eb1fda291360f701f66cb542b0f92838b1ab2cc19d51cda0'
QUESTION_SHA256 = '5a2a0cd2aadab9729a0050e31a9599ec0a629de1280617f0d56ab1a95c707fcb'
CAP_USD = 0.15
MAX_MAP_BYTES = 4000
OBLIGATIONS = (
    dict(id='changed_safety_standards_not_proved_violation', start=1631, length=93,
         sha256='ab20f89475589df5bd393fdb20dfbfa7a8293e5946fd25faf03808d2420431f0',
         required_behavior='STATE_AND_QUALIFY', weight=3),
    dict(id='developer_cost_pressure_not_malicious_motive', start=1467, length=75,
         sha256='235ff1662796b73b34816621f460fdaf190467fe09563ee0821529d94b20b7d7',
         required_behavior='STATE_AND_QUALIFY', weight=2),
    dict(id='contractor_risk_assessment_not_measured_probability', start=2471,
         length=87, sha256='b56ff9ec852704668e6cb053dff30abb82c557bc8c07ede0ee7ea932bc45501c',
         required_behavior='STATE_AND_QUALIFY', weight=2),
    dict(id='request_to_withhold_not_actual_concealment', start=2559, length=67,
         sha256='c6bd083507bde8bf4edbe3bc5f6bc61064f6648f300c84b143cd4a56986a7740',
         required_behavior='STATE_AND_QUALIFY', weight=3),
    dict(id='vague_records_preserve_uncertainty', start=1404, length=21,
         sha256='b3332edbf336fa4b126d762297a0223db865f3b8dec07a17afa5e3af301019de',
         required_behavior='STATE_AND_QUALIFY', weight=2),
)
GLOBAL_OBLIGATIONS = (
    dict(id='normative_premise_conditional',
         required_behavior='AVOID_UNCONDITIONAL_MORAL_OR_LEGAL_VERDICT', weight=3),
    dict(id='no_outside_code_as_source',
         required_behavior='AVOID_IMPORTING_EXTERNAL_PROFESSIONAL_CODE', weight=3),
)
AUTHORS = ('Sarah Jayne Hitt', 'Matthew Studley', 'Darian Meacham',
           'Nik Whitehead', 'Mike Bramhall', 'Isobel Grimley')


def _sha(value):
    return hashlib.sha256(value.encode()).hexdigest()


def _publisher_source(raw_html):
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(raw_html, 'html.parser')
    text = soup.get_text(' ', strip=True)
    if (not all(name in text for name in AUTHORS) or
            'creativecommons.org/licenses/by-sa/4.0' not in str(soup) or
            QUESTION not in text):
        raise ValueError('publisher attribution, license or native question missing')

    def section(label):
        marker = next((x for x in soup.find_all(string=True)
            if x.strip() == label), None)
        if marker is None:
            raise ValueError('publisher section missing')
        rows = []
        for tag in marker.parent.parent.next_siblings:
            if getattr(tag, 'name', None) == 'p':
                line = tag.get_text(' ', strip=True)
                if line.startswith('Optional STOP'):
                    break
                if line:
                    rows.append(line)
        return rows

    summary, part_one = section('Summary:'), section('Dilemma – Part one:')
    if len(summary) != 1 or len(part_one) != 3:
        raise ValueError('publisher scenario section drift')
    source = '\n\n'.join(summary + part_one)
    if _sha(source) != SOURCE_SHA256 or _sha(QUESTION) != QUESTION_SHA256:
        raise ValueError('publisher selected source or question drift')
    for obligation in OBLIGATIONS:
        quote = source[obligation['start']:obligation['start'] + obligation['length']]
        if _sha(quote) != obligation['sha256']:
            raise ValueError('source-first obligation anchor drift')
    return source


def fetch_source():
    request = urllib.request.Request(URL,
        headers={'User-Agent': 'Mozilla/5.0 (HCL I02 bounded source audit)'})
    with urllib.request.urlopen(request, timeout=30) as response:
        raw = response.read(500000)
    if not raw or len(raw) >= 500000:
        raise ValueError('bounded publisher page required')
    return _publisher_source(raw)


def build_package():
    files = [Path('scripts/serious_eval_arms.py'),
        Path('scripts/serious_eval_arms_v2.py'),
        Path('scripts/serious_eval_arms_v3.py'),
        Path('scripts/serious_eval_arms_v4.py'),
        Path('scripts/serious_eval_generic_workspace_v5.py'),
        Path('scripts/i02_input_coverage.py'),
        Path('scripts/i02_source_lineage.py'),
        Path('scripts/run_i02_comparator_calibration_once.py'),
        Path('scripts/run_i02_epc_cpg_v5_once.py'),
        Path('scripts/serious_eval_contract.py'), WORKFLOW]
    hashes = {str(path): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in files}
    return dict(schema='hcl-i02-epc-cpg-v5-calibration-v1',
        purpose='ONE_EPC_DEVELOPMENT_SOURCE_CPG_V5_COMPARATOR_CALIBRATION_NO_H_EFFICACY',
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
        source_url=URL, source_id=SOURCE_ID, source_sha256=SOURCE_SHA256,
        question_sha256=QUESTION_SHA256,
        source_selection='PUBLISHER_SUMMARY_AND_DILEMMA_PART_ONE_ONLY',
        native_question='FIRST_DISCUSSION_QUESTION_AFTER_PART_ONE',
        original_authors=list(AUTHORS), license='CC_BY_SA_4_0',
        license_url='https://creativecommons.org/licenses/by-sa/4.0/',
        source_first_obligation_anchors=list(OBLIGATIONS),
        global_source_first_obligations=list(GLOBAL_OBLIGATIONS),
        source_first_review_before_model_output=True,
        source_distribution='EPC_GLASS_SAFETY_PUBLISHER_CASE_DEVELOPMENT_EXPOSED',
        source_lineage_sha256=hashlib.sha256(Path(
            'reports/HCL_I02_EXPOSURE_LINEAGE.json').read_bytes()).hexdigest(),
        confirmation_items_inspected=0, h_arm_calls=0,
        hcl_runtime_sha256=runtime_digest(),
        execution_files=hashes, execution_sha256=digest(hashes),
        longmemeval='SEALED_NOT_ACCESSED')


def load_package():
    package = json.loads(PACKAGE.read_text())
    if package != build_package():
        raise ValueError('EPC CPG v5 frozen package or execution surface drift')
    freeze = json.loads(Path('reports/HCL_I01_EVALUATION_FREEZE.json').read_text())
    v1 = json.loads(Path('reports/HCL_I02_RUNTIME_AMENDMENT.json').read_text())
    v2 = json.loads(Path('reports/HCL_I02_RUNTIME_AMENDMENT_V2.json').read_text())
    validate_runtime_amendment_v2(freeze, v1, v2)
    if package['hcl_runtime_sha256'] != runtime_digest():
        raise ValueError('frozen HCL runtime drift')
    return package


def preflight(package, source):
    if _sha(source) != package['source_sha256']:
        raise ValueError('pinned publisher source drift')
    case = dict(case_id='epc-glass-safety-part-one-native-q1',
        task_family='RESPONSIBILITY_VALUE_INTEGRATION', split='CALIBRATION',
        source_origin='INDEPENDENT_NON_HCL_AUTHOR',
        source_license_status='VERIFIED_FOR_THIS_EVALUATION',
        source_access_status='AUTHORIZED_FOR_EVERY_ARM',
        longmemeval='NOT_USED', writing_system_id='epc-engineering-ethics-case-studies',
        author_id='epc-glass-safety-six-authors',
        template_id='epc-engineering-ethics-two-part-case-studies',
        source_group_id=SOURCE_SHA256, question=QUESTION, source_text=source,
        arm_inputs={arm: dict(question=QUESTION, source_text=source) for arm in ARMS},
        answer_fields=list(FIELDS))
    validate_candidate(json.loads(Path(
        'reports/HCL_I01_EVALUATION_FREEZE.json').read_text()), case)
    if hashlib.sha256(Path('reports/HCL_I02_EXPOSURE_LINEAGE.json').read_bytes()).hexdigest() != (
            package['source_lineage_sha256']):
        raise ValueError('source lineage changed after calibration freeze')
    require_development_calibration_input(case)
    arms = prepare_primary_arms_v5(QUESTION, SOURCE_ID, source)
    ordinary = arms['ordinary_payload']
    c, p, g = [json.loads(arms[name][-1]['content'])
        for name in ('C', 'P', 'G_map')]
    if (c != p or c != ordinary or
            g.get('question') != ordinary['question'] or
            g.get('sources') != ordinary['sources'] or
            ordinary['answer_fields'] != list(FIELDS) or
            g.get('workspace_fields') !=
                ['source_index', 'relations', 'answer_plan', 'open_questions']):
        raise ValueError('C/P/G v5 ordinary input or map contract mismatch')
    coverage = audit_ordinary_input(QUESTION, SOURCE_ID, source)
    if (coverage['h_entry'] != 'ACCEPTED_PROVIDER_FREE' or
            not coverage['h_complete_source_in_final_input'] or
            package['h_arm_calls'] != 0 or package['confirmation_items_inspected'] != 0):
        raise ValueError('source, H/no-H or confirmation boundary failed')
    bounds = [len(json.dumps(arms[phase], ensure_ascii=False).encode()) * 2 + 2048
        for phase in ('C', 'P', 'G_map')]
    bounds.append((len(json.dumps(arms['C'], ensure_ascii=False).encode()) +
        MAX_MAP_BYTES * 2) * 2 + 2048)
    worst = sum((bound * PEAK['input'] + OUTPUT_LIMITS[phase] * PEAK['output']) / 1_000_000
        for phase, bound in zip(PHASES, bounds))
    if worst > package['budget_cap_usd']:
        raise ValueError('all-phase peak reservation exceeds hard cap')
    return dict(schema='hcl-i02-epc-cpg-v5-preflight-v1',
        status='PASS_SOURCE_FIRST_CPG_ONLY', package_sha256=digest(package),
        source_sha256=_sha(source), question_sha256=_sha(QUESTION),
        source_first_obligation_anchors=list(OBLIGATIONS),
        global_source_first_obligations=list(GLOBAL_OBLIGATIONS),
        same_question_and_complete_source=True,
        h_ordinary_route='DIRECT_NO_COGNITION_TREATMENT_NOT_EXECUTED',
        source_selection=package['source_selection'],
        publisher_attribution=package['original_authors'],
        page_license=package['license'],
        phase_max_input_token_bounds=bounds,
        all_phase_peak_reservation_usd=worst,
        provider_calls=0, provider_spend_usd=0,
        longmemeval='SEALED_NOT_ACCESSED'), arms


def execute(package, source, provider, output):
    gate, arms = preflight(package, source)
    ledger = Ledger(package, output)
    ledger.receipt['schema'] = 'hcl-i02-epc-cpg-v5-run-v1'
    ledger.receipt['source_license_attribution'] = dict(
        authors=package['original_authors'], source_url=package['source_url'],
        license=package['license_url'],
        modification='Publisher summary and part-one paragraphs joined; no case wording changed.')
    ledger.receipt['preflight'] = gate
    ledger.save()
    try:
        results = {}
        for phase in PHASES:
            messages = (arms[phase] if phase != 'G_final' else
                prepare_generic_final_v5(arms, results['G_map']))
            raw = ledger.call(phase, messages, provider)
            parsed = json.loads(raw)
            if phase == 'G_map':
                if len(raw.encode()) > package['maximum_map_bytes']:
                    raise ValueError('generic map exceeds frozen bound')
                prepare_generic_final_v5(arms, raw)
            elif not isinstance(parsed, dict) or set(parsed) != set(FIELDS):
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
    parser.add_argument('--output', default='i02-epc-cpg-v5-receipt.json')
    args = parser.parse_args()
    if sum((args.freeze, args.preflight, args.execute)) != 1:
        parser.error('exactly one mode required')
    if args.freeze:
        write_json(PACKAGE, build_package())
        return
    package = load_package()
    source = fetch_source()
    gate, _ = preflight(package, source)
    if args.preflight:
        write_json(args.output, gate)
        return
    if (os.environ.get('GITHUB_RUN_ATTEMPT') != '1' or
            os.environ.get('HCL_I02_EPC_CPG_V5_AUTHORIZED') != 'ONE_CALIBRATION_ONLY'):
        raise ValueError('first unique one-shot workflow required')
    from openai import OpenAI
    key = os.environ.get('DEEPSEEK_API_KEY')
    if not key:
        raise ValueError('existing DeepSeek secret required')
    client = OpenAI(api_key=key, base_url=package['provider_endpoint'],
        max_retries=0, timeout=120)
    execute(package, source, lambda request: transport(request, client),
        args.output)


if __name__ == '__main__':
    main()

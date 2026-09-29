"""One source-first KPU C/P/G v6 development calibration; never H efficacy."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from hcl.v1 import CognitionRequest, HCLCognitionLayer
from scripts.i02_input_coverage import audit_ordinary_input
from scripts.i02_source_qualification_v3 import load_screens
from scripts.run_i02_comparator_calibration_once import (
    Ledger, OUTPUT_LIMITS, PEAK, PHASES, digest, transport, write_json)
from scripts.serious_eval_contract import (
    ARMS, FIELDS, runtime_digest, validate_candidate,
    validate_runtime_amendment_v2)
from scripts.serious_eval_generic_workspace_v6 import (
    MAX_MAP_BYTES, prepare_generic_final_v6, prepare_primary_arms_v6)


SOURCE = Path('reports/HCL_I02_KPU_CONFLICT_DEVELOPMENT_SOURCE.json')
PACKAGE = Path('reports/HCL_I02_KPU_CPG_V6_PACKAGE.json')
WORKFLOW = Path('.github/workflows/hcl-i02-kpu-cpg-v6-once.yml')
URL = 'https://kpu.pressbooks.pub/businesscomms/chapter/case-conflict-management/'
SOURCE_ID = 'kpu-conflict-management-case-2020'
WRITING_SYSTEM = 'kpu-business-communication-case-scenarios'
AUTHORS = ('Swati Bassi', 'Anthony Ciulla', 'Faris Khan', 'Stone Lacroix')
SOURCE_SHA256 = '9e029c7fa4abd6b48607bebb8147b48edf3e093f18b3cd78bd8be6cd8d25347b'
QUESTION_SHA256 = '1aad2264e49d331ddb7825e64551d1864a41c29d16dd99a65c93855b5e1b2693'
CAP_USD = 0.15
OBLIGATION_SPECS = (
    ('reported_overload_not_malicious_motive',
     'Mathew says he has other obligations to fulfill and other classes are too stressful for him', 3),
    ('unclear_task_not_refusal',
     'he is unclear about his given task and believes he will be of minimal help', 2),
    ('waiting_was_group_choice',
     'wait this out and hope Mathew makes time for this class', 2),
    ('peer_review_lacked_explanation',
     '0/5 on their peer review assessments. However, you do not give any qualitative feedback explaining why', 3),
    ('professor_removal_now_too_late',
     'there is nothing he can do as it is too late in the semester to remove them from the group', 3),
    ('suspected_plagiarism_cannot_be_used_as_safe_content',
     'clearly plagiarised using unreliable sources', 3),
)
GLOBAL_OBLIGATIONS = (
    dict(id='proposals_not_observed_outcomes',
         required_behavior='DISTINGUISH_PROPOSED_STEPS_FROM_SOURCE_FACTS', weight=3),
    dict(id='no_unobserved_private_motive',
         required_behavior='AVOID_PROMOTING_UNOBSERVED_MOTIVE_OR_EMOTION', weight=3),
    dict(id='no_guaranteed_grade',
         required_behavior='AVOID_GUARANTEED_OUTCOME_OR_AUTHORITY', weight=2),
)


def _sha(value):
    return hashlib.sha256(value.encode()).hexdigest()


def _source():
    raw = SOURCE.read_bytes()
    item = json.loads(raw)
    if (item.get('schema') != 'hcl-i02-kpu-conflict-development-source-v1' or
            item.get('source_url') != URL or
            item.get('source_license') != 'CC BY 4.0' or
            item.get('source_license_url') !=
                'https://creativecommons.org/licenses/by/4.0/' or
            tuple(item.get('case_authors', ())) != AUTHORS or
            item.get('development_exposed') is not True or
            item.get('provider_calls') != 0 or
            item.get('longmemeval') != 'SEALED_NOT_ACCESSED' or
            _sha(item.get('source_text', '')) != SOURCE_SHA256 or
            _sha(item.get('native_question', '')) != QUESTION_SHA256):
        raise ValueError('KPU publisher-source selection or rights drift')
    return item, hashlib.sha256(raw).hexdigest()


def _obligations(source_text):
    rows = []
    for name, quote, weight in OBLIGATION_SPECS:
        start = source_text.find(quote)
        if start < 0 or source_text.find(quote, start + 1) >= 0:
            raise ValueError('source-first anchor absent or ambiguous')
        rows.append(dict(id=name, start=start, length=len(quote),
            sha256=_sha(quote), required_behavior='STATE_AND_QUALIFY',
            weight=weight))
    return rows


def build_package():
    item, source_file_sha = _source()
    screened = load_screens()['screened']
    if not any(row['writing_system_id'] == WRITING_SYSTEM and
               row['publisher_url_prefix'] == URL and
               row['calibration_model_input_only'] is True and
               row['confirmation_qualified'] is False for row in screened):
        raise ValueError('KPU development-only lineage missing')
    files = [SOURCE, Path('reports/HCL_I02_SCREENED_SYSTEMS_V3.json'),
        Path('scripts/i02_source_qualification_v3.py'),
        Path('scripts/serious_eval_arms.py'),
        Path('scripts/serious_eval_arms_v2.py'),
        Path('scripts/serious_eval_arms_v3.py'),
        Path('scripts/serious_eval_arms_v4.py'),
        Path('scripts/serious_eval_generic_workspace_v5.py'),
        Path('scripts/serious_eval_generic_workspace_v6.py'),
        Path('scripts/i02_input_coverage.py'),
        Path('scripts/run_i02_comparator_calibration_once.py'),
        Path('scripts/run_i02_kpu_cpg_v6_once.py'),
        Path('scripts/serious_eval_contract.py'), WORKFLOW]
    hashes = {str(path): hashlib.sha256(path.read_bytes()).hexdigest()
              for path in files}
    return dict(schema='hcl-i02-kpu-cpg-v6-calibration-v1',
        purpose='ONE_KPU_DEVELOPMENT_SOURCE_CPG_V6_COMPARATOR_CALIBRATION_NO_H_EFFICACY',
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
        source_url=URL, source_id=SOURCE_ID,
        source_file_sha256=source_file_sha, source_sha256=SOURCE_SHA256,
        question_sha256=QUESTION_SHA256,
        source_selection=item['source_selection'],
        retrieval_limit=item['source_retrieval'],
        native_question='FIRST_QUESTIONS_TO_THINK_ABOUT_AFTER_CASE',
        original_authors=list(AUTHORS), license='CC_BY_4_0',
        license_url=item['source_license_url'],
        source_first_obligation_anchors=_obligations(item['source_text']),
        global_source_first_obligations=list(GLOBAL_OBLIGATIONS),
        source_first_review_before_model_output=True,
        source_distribution='KPU_BUSINESS_COMMUNICATION_CASE_DEVELOPMENT_EXPOSED',
        confirmation_items_inspected=0, h_arm_calls=0,
        hcl_runtime_sha256=runtime_digest(),
        execution_files=hashes, execution_sha256=digest(hashes),
        longmemeval='SEALED_NOT_ACCESSED')


def load_package():
    package = json.loads(PACKAGE.read_text())
    if package != build_package():
        raise ValueError('KPU CPG v6 frozen package or execution surface drift')
    freeze = json.loads(Path('reports/HCL_I01_EVALUATION_FREEZE.json').read_text())
    v1 = json.loads(Path('reports/HCL_I02_RUNTIME_AMENDMENT.json').read_text())
    v2 = json.loads(Path('reports/HCL_I02_RUNTIME_AMENDMENT_V2.json').read_text())
    validate_runtime_amendment_v2(freeze, v1, v2)
    if package['hcl_runtime_sha256'] != runtime_digest():
        raise ValueError('frozen HCL runtime drift')
    return package


def preflight(package):
    item, file_sha = _source()
    source, question = item['source_text'], item['native_question']
    if (file_sha != package['source_file_sha256'] or
            _obligations(source) != package['source_first_obligation_anchors'] or
            list(GLOBAL_OBLIGATIONS) != package['global_source_first_obligations']):
        raise ValueError('source or frozen obligations drift')
    case = dict(case_id='kpu-conflict-management-native-q1',
        task_family='MULTIPARTY_INFORMATION_STRATEGY', split='CALIBRATION',
        source_origin='INDEPENDENT_NON_HCL_AUTHOR',
        source_license_status='VERIFIED_FOR_THIS_EVALUATION',
        source_access_status='AUTHORIZED_FOR_EVERY_ARM', longmemeval='NOT_USED',
        writing_system_id=WRITING_SYSTEM, author_id='kpu-conflict-four-authors',
        template_id='kpu-business-communications-student-engagement-case',
        source_group_id=SOURCE_SHA256, question=question, source_text=source,
        arm_inputs={arm:dict(question=question, source_text=source)
            for arm in ARMS}, answer_fields=list(FIELDS))
    validate_candidate(json.loads(Path(
        'reports/HCL_I01_EVALUATION_FREEZE.json').read_text()), case)
    arms = prepare_primary_arms_v6(question, SOURCE_ID, source)
    ordinary = arms['ordinary_payload']
    c, p, g = [json.loads(arms[name][-1]['content'])
        for name in ('C', 'P', 'G_map')]
    if (c != p or c != ordinary or
            g.get('question') != ordinary['question'] or
            g.get('sources') != ordinary['sources'] or
            ordinary['answer_fields'] != list(FIELDS)):
        raise ValueError('C/P/G v6 ordinary input or contract mismatch')
    coverage = audit_ordinary_input(question, SOURCE_ID, source)
    h = HCLCognitionLayer(lambda _: '').prepare(CognitionRequest(question,
        narrative=source, max_context_chars=64000))
    if (coverage['h_entry'] != 'ACCEPTED_PROVIDER_FREE' or
            not coverage['h_complete_source_in_final_input'] or
            h.context is not None or h.plan.capabilities or len(h.messages) != 1 or
            package['h_arm_calls'] != 0 or package['confirmation_items_inspected'] != 0):
        raise ValueError('source, H/no-H treatment or confirmation boundary failed')
    # Prove a compact, checked map reaches G-final with the complete source.
    first = source[1372:1372 + 80]
    mock = json.dumps(dict(source_index=[dict(id='e1', source_id=SOURCE_ID,
        quote=first)], relations=[], answer_plan=[dict(operation='RETRIEVE',
        evidence_ids=['e1'])], open_questions=[]), ensure_ascii=False)
    final = prepare_generic_final_v6(arms, mock)
    if json.loads(final[-1]['content'])['sources'] != ordinary['sources']:
        raise ValueError('G-final loses complete source')
    bounds = [len(json.dumps(arms[phase], ensure_ascii=False).encode()) * 2 + 2048
        for phase in ('C', 'P', 'G_map')]
    bounds.append((len(json.dumps(arms['C'], ensure_ascii=False).encode()) +
        MAX_MAP_BYTES * 2) * 2 + 2048)
    worst = sum((bound * PEAK['input'] + OUTPUT_LIMITS[phase] * PEAK['output']) /
        1_000_000 for phase, bound in zip(PHASES, bounds))
    if worst > package['budget_cap_usd']:
        raise ValueError('all-phase peak reservation exceeds hard cap')
    return dict(schema='hcl-i02-kpu-cpg-v6-preflight-v1',
        status='PASS_SOURCE_FIRST_CPG_ONLY', package_sha256=digest(package),
        source_file_sha256=file_sha, source_sha256=_sha(source),
        question_sha256=_sha(question),
        source_first_obligation_anchors=package['source_first_obligation_anchors'],
        global_source_first_obligations=package['global_source_first_obligations'],
        same_question_and_complete_source=True,
        h_ordinary_route='DIRECT_NO_COGNITION_TREATMENT_NOT_EXECUTED',
        publisher_attribution=list(AUTHORS), page_license='CC_BY_4_0',
        retrieval_limit=item['source_retrieval'],
        phase_max_input_token_bounds=bounds,
        all_phase_peak_reservation_usd=worst,
        provider_calls=0, provider_spend_usd=0,
        longmemeval='SEALED_NOT_ACCESSED'), arms


def execute(package, provider, output):
    gate, arms = preflight(package)
    ledger = Ledger(package, output)
    ledger.receipt['schema'] = 'hcl-i02-kpu-cpg-v6-run-v1'
    ledger.receipt['source_license_attribution'] = dict(
        authors=package['original_authors'], source_url=package['source_url'],
        license=package['license_url'],
        modification='Publisher case sections joined; case wording preserved.')
    ledger.receipt['preflight'] = gate
    ledger.save()
    try:
        results = {}
        for phase in PHASES:
            messages = (arms[phase] if phase != 'G_final' else
                prepare_generic_final_v6(arms, results['G_map']))
            raw = ledger.call(phase, messages, provider)
            parsed = json.loads(raw)
            if phase == 'G_map':
                if len(raw.encode()) > package['maximum_map_bytes']:
                    raise ValueError('generic map exceeds frozen bound')
                prepare_generic_final_v6(arms, raw)
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
    parser.add_argument('--output', default='i02-kpu-cpg-v6-receipt.json')
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
            os.environ.get('HCL_I02_KPU_CPG_V6_AUTHORIZED') != 'ONE_CALIBRATION_ONLY'):
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

"""Provider-free CG05 authored development inputs; no provider client or grant."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from hcl.v1 import CognitionRequest, HCLCognitionLayer
from scripts.cg04_external_package import _same_type_value

PACKAGE = Path('reports/HCL_CG05_EXTERNAL_PACKAGE.json')
ARMS = ['C', 'P', 'G', 'H', 'H-new']
STATES = ['SUPERSEDED_LOCAL', 'OTHER_SCOPE', 'ATTRIBUTED_ONLY', 'CONTESTED_APPLICATION',
          'DECLARED_COUNTEREXAMPLE', 'CRITERIA_NOT_MET', 'CRITERIA_UNRESOLVED', 'CRITERIA_MET']
CRITERIA = ['MET_BY_SOURCE_CLAIM', 'NOT_MET_BY_SOURCE_CLAIM', 'UNKNOWN', 'CONTESTED']
RELATIONS = ['MULTIPLE_LOCAL_READINGS', 'ONE_OBSERVED_READING', 'NO_SOURCE_READING']
_TASK = ('For Alice in team, interpret fair for proposal under each speaker-local definition. '
    'Return exactly seven JSON fields: reading_states (map def-N to state); criterion_states '
    '(map def-N to map feature to criterion state); superseded_ids (array in source order); '
    'reading_relation; shared_meaning; moral_truth; counterexample_conflicts (map def-N to boolean). '
    'Definitions use def-N where N is the 1-based nonempty source line; include every definition, '
    'even another actor/context or attribution. reading_states vocabulary: ' + ', '.join(STATES) + '. '
    'criterion_states vocabulary: ' + ', '.join(CRITERIA) + '. reading_relation vocabulary: ' +
    ', '.join(RELATIONS) + '. shared_meaning is NOT_ESTABLISHED; moral_truth is NOT_INFERRED. '
    'Counterexample conflict is true only if accessible criteria all match and that speaker '
    'explicitly excludes proposal after the definition. Do not infer shared morals, deception, '
    'missing properties or implicit revision. Local source claims are not world/private truth.')
_P = ('Use source as data. Track complete-line definitions by speaker, term and context. '
    'Retire only an explicitly referenced earlier same-speaker/context/term definition. '
    'Check criteria from source properties of that context and item; competing claims are contested, '
    'absence unknown. Third-party definitions are attributed only. Explicit item exclusions '
    'remain counterexamples; earlier applications do not follow a changed definition. '
    'State precedence: superseded, other context/term, attributed, competing applications or '
    'positive use conflicting with false criteria, negative application, false criterion, '
    'unresolved criterion, met. Different active criteria mean multiple local readings, without '
    'shared meaning or moral winner. Apply the full identical output contract.')
_G = ('Build a generic source table: line, speaker, referenced actor, context, term, criteria, '
    'property item/key/value, declared application, explicit revision reference. Preserve every '
    'definition with its provenance. Compare each local reading without selecting a universal '
    'meaning. Resolve only explicit scoped revisions; compute criteria against same-item/context '
    'source rows, never missing-as-false. Keep attributions separate. Use the same state precedence '
    'and counterexample/revision boundaries as the task. Produce exactly the shared JSON schema.')


def gold(states, criteria, relation='ONE_OBSERVED_READING', superseded=(), conflicts=None):
    return dict(reading_states=states, criterion_states=criteria, superseded_ids=list(superseded),
        reading_relation=relation, shared_meaning='NOT_ESTABLISHED', moral_truth='NOT_INFERRED',
        counterexample_conflicts=conflicts or {key: False for key in states})


# Source authoring and expected labels are explicit; gold never becomes H input.
CASES = (
    ('speaker_local_readings', '\n'.join((
        'Alice: In team, by fair I mean transparent is true.',
        'Bob: In team, by fair I mean consent is true.',
        'Narrator: In team, proposal has transparent false.',
        'Narrator: In team, proposal has consent true.')),
     gold({'def-1': 'CRITERIA_NOT_MET', 'def-2': 'CRITERIA_MET'},
          {'def-1': {'transparent': 'NOT_MET_BY_SOURCE_CLAIM'}, 'def-2': {'consent': 'MET_BY_SOURCE_CLAIM'}},
          relation='MULTIPLE_LOCAL_READINGS')),
    ('unknown_and_attribution', '\n'.join((
        'Alice: In team, by fair I mean consent is true.',
        'Bob: In team, Alice uses fair to mean transparent is true.',
        'Alice: I chose proposal today.')),
     gold({'def-1': 'CRITERIA_UNRESOLVED', 'def-2': 'ATTRIBUTED_ONLY'},
          {'def-1': {'consent': 'UNKNOWN'}, 'def-2': {'transparent': 'UNKNOWN'}})),
    ('explicit_scope_revision', '\n'.join((
        'Alice: In team, by fair I mean consent is true.',
        'Alice: In family, by fair I mean consent is false.',
        'Alice: In team, I now use fair to mean transparent is true instead of consent is true.',
        'Narrator: In team, proposal has transparent true.')),
     gold({'def-1': 'SUPERSEDED_LOCAL', 'def-2': 'OTHER_SCOPE', 'def-3': 'CRITERIA_MET'},
          {'def-1': {'consent': 'UNKNOWN'}, 'def-2': {'consent': 'UNKNOWN'},
           'def-3': {'transparent': 'MET_BY_SOURCE_CLAIM'}}, superseded=('def-1',))),
    ('explicit_counterexample', '\n'.join((
        'Alice: In team, by fair I mean consent is true.',
        'Narrator: In team, proposal has consent true.',
        'Alice: In team, proposal is not fair.')),
     gold({'def-1': 'DECLARED_COUNTEREXAMPLE'}, {'def-1': {'consent': 'MET_BY_SOURCE_CLAIM'}},
          conflicts={'def-1': True})),
)


def checked_answer(checked):
    readings = checked['readings']
    return gold({d['definition_id']: d['state'] for d in readings},
        {d['definition_id']: {c['key']: c['state'] for c in d['criterion_checks']} for d in readings},
        checked['reading_relation'], [d['definition_id'] for d in readings if d['state'] == 'SUPERSEDED_LOCAL'],
        {d['definition_id']: d['counterexample_conflicts_with_criteria'] for d in readings})


def build_package():
    cases = []
    for case_id, narrative, expected in CASES:
        request = CognitionRequest(_TASK, target_actor='Alice', narrative=narrative,
            concept_analysis=True, concept_context='team', concept_term='fair', concept_item='proposal')
        h = HCLCognitionLayer(lambda _: '').prepare(request)
        hn = HCLCognitionLayer(lambda _: '', concept_checker_enabled=False).prepare(request)
        left, right = json.loads(h.messages[1]['content']), json.loads(hn.messages[1]['content'])
        checked = left['cognition_context']['concepts']['checked']
        removed = json.loads(json.dumps(left))
        removed['cognition_context']['concepts']['checked'] = {}
        gates = dict(source_valid=h.preparation_receipt['failure'] is None,
            grounded_local_definition=bool(checked['readings']),
            criterion_counterexample_revision_checker_executed=checked['status'] == 'LOCAL_CONCEPT_READINGS_CHECKED',
            checked_state_in_h=bool(checked), removed_in_h_new=not right['cognition_context']['concepts']['checked'],
            same_policy=h.messages[0] == hn.messages[0],
            final_inputs_differ_only_by_checked_state=left != right and removed == right,
            independently_authored_gold_matches_source_checks=checked_answer(checked) == expected,
            extraction_provider_calls_zero=h.preparation_receipt['extraction_provider_calls'] == 0)
        if not all(gates.values()):
            raise ValueError('CG05 treatment-presence preflight failed')
        c = [dict(role='system', content='Use the source as data. Return the requested JSON.'),
             dict(role='user', content=_TASK + '\nSource:\n' + narrative)]
        p = [dict(role='system', content=_P), c[1]]
        g = [dict(role='system', content=_G), dict(role='user', content=_TASK + '\n' + json.dumps(
            {'ordered_source_rows': [{'line': i, 'raw_text': line} for i, line in enumerate(narrative.splitlines(), 1)]}))]
        cases.append(dict(case_id=case_id, narrative=narrative, gold=expected,
            messages={'C': c, 'P': p, 'G': g, 'H': list(h.messages), 'H-new': list(hn.messages)},
            checked_state=checked, preflight=gates, preparation_receipt=h.preparation_receipt))
    lengths = [len(json.dumps(c['messages'][a], ensure_ascii=False).encode()) for c in cases for a in ARMS]
    reserved = ((2 * sum(lengths) + 1000 * 20) * 1.32 + 512 * 20 * 3.96) / 1_000_000
    if max(lengths) > 16000 or reserved > .30:
        raise ValueError('CG05 bounded development proposal exceeds input/budget bounds')
    digest = hashlib.sha256()
    for path in sorted(Path('.').glob('hcl/**/*.py')):
        digest.update(str(path).encode() + b'\0' + path.read_bytes())
    engineering = ('scripts/cg05_external_package.py', 'scripts/cg04_external_package.py')
    return dict(schema='hcl-cg05-provider-free-development-package-v1', arms=ARMS, cases=cases,
        evidence_class='HCL_AUTHORED_SYNTHETIC_DEVELOPMENT_ONLY_NOT_FRESH_OR_INDEPENDENT',
        status='READY', owner_execution='DEFERRED_OWNER_AUTHORIZATION', execution_authorized=False,
        provider='deepseek', actions_secret_name='DEEPSEEK_API_KEY', provider_endpoint='https://api.deepseek.com',
        model='deepseek-v4-pro', model_version='DeepSeek-V4-Pro-0813', service_tier='provider_default_no_tier_parameter',
        provider_request=dict(thinking={'type': 'disabled'}, response_format={'type': 'json_object'}, max_retries=0),
        maximum_provider_calls_if_separately_authorized=20, retries_if_authorized=0,
        maximum_output_tokens_per_call_if_authorized=512, maximum_serialized_input_bytes_per_call=16000,
        conservative_input_token_reserve_per_byte=2, conservative_framing_token_reserve_per_call=1000,
        total_serialized_input_bytes=sum(lengths),
        price_basis=dict(input_cache_miss_usd_per_million=1.32, output_usd_per_million=3.96,
            basis='repository-frozen conservative peak rates; revalidate before any future grant'),
        estimated_worst_case_usd_at_repository_frozen_rate=reserved, proposed_new_hard_cap_usd=.30,
        historical_budget_transfer_usd=0, provider_calls_executed=0, runtime_sha256=digest.hexdigest(),
        frozen_engineering_sha256={str(p): hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in engineering},
        longmemeval='SEALED_NOT_ACCESSED')


def score_answer(case, answer):
    try:
        row = json.loads(answer)
    except (TypeError, ValueError):
        row = None
    expected = case['gold']
    if not isinstance(row, dict) or row.keys() != expected.keys():
        return dict(valid=False, exact_fields=0, all_fields_correct=False)
    count = sum(_same_type_value(row[k], expected[k]) for k in expected)
    return dict(valid=True, exact_fields=count, all_fields_correct=count == len(expected))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--write', action='store_true')
    args = parser.parse_args()
    package = build_package()
    data = json.dumps(package, ensure_ascii=False, sort_keys=True, indent=2) + '\n'
    if args.write:
        PACKAGE.write_text(data)
    elif PACKAGE.read_text() != data:
        raise SystemExit('CG05 frozen package drift; no paid execution allowed')
    print(json.dumps(dict(treatment_presence='PASS', provider_calls=0,
        serialized_bytes=package['total_serialized_input_bytes'],
        reservation_usd=package['estimated_worst_case_usd_at_repository_frozen_rate'])))

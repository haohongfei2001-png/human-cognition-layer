"""Zero-provider native entrypoint audit of eight already source-exposed families.

No new source hunt, gold-driven selection, task rewriting or HCL-specific labels.
Native data stays outside the repository under its non-commercial research license.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
from hcl.v1 import HCLCognitionLayer
from hcl.v1.person_question import prepare_person_context

SOURCE_SHA256 = '9d5af2e580d809c73872a7dd43fe93d0b07c6f6086b04a9a9a1917603009d961'
SELECTION = (('21-43', 0), ('9-70', 0), ('14-83', 0), ('12-281', 0),
             ('5-149', 3), ('20-55', 3), ('16-158', 1), ('1-34', 3))


def audit(source_path):
    raw = Path(source_path).read_bytes()
    if hashlib.sha256(raw).hexdigest() != SOURCE_SHA256:
        raise ValueError('pinned independent source digest mismatch')
    corpus = json.loads(raw)
    rows, calls = [], []
    def forbidden_provider(messages):
        calls.append(messages)
        raise AssertionError('native readiness audit cannot call a provider')
    for dialogue_id, question_index in SELECTION:
        family = next(record for record in corpus if record[2] == dialogue_id)
        # Do not retrieve, print or use the native answer field. Selection predates this audit.
        question = family[1][question_index]['question']
        choices = family[1][question_index]['choice']
        narrative = '\n'.join(family[0])
        prepared = prepare_person_context(HCLCognitionLayer(forbidden_provider), question, narrative)
        receipt = prepared.preparation_receipt
        messages = list(prepared.messages)
        rows.append(dict(dialogue_id=dialogue_id, question_index=question_index,
            native_question_sha256=hashlib.sha256(question.encode()).hexdigest(), native_choices_sha256=hashlib.sha256(json.dumps(choices).encode()).hexdigest(),
            native_dialogue_sha256=hashlib.sha256(narrative.encode()).hexdigest(),
            final_messages_sha256=hashlib.sha256(json.dumps(messages, ensure_ascii=False, sort_keys=True).encode()).hexdigest(),
            source_rewritten=False, task_rewritten=False, manual_psychological_state_supplied=False,
            gold_accessed_or_scored=False, selected_capabilities=list(prepared.plan.capabilities),
            preparation_failure=receipt.get('failure'), preparation_method=receipt.get('method'),
            extraction_provider_calls=receipt['extraction_provider_calls'], actual_provider_calls=len(calls),
            specialized_treatment_present=receipt.get('failure') is None and not prepared.plan.direct,
            declared_answer_calls_in_receipt=receipt.get('answer_provider_calls'),
            declared_answer_calls_executed=False))
    if calls:
        raise AssertionError('unexpected provider attempt')
    digest = hashlib.sha256()
    for path in sorted(Path('.').glob('hcl/**/*.py')):
        digest.update(str(path).encode() + b'\0' + path.read_bytes())
    return dict(schema='hcl-post-cg05-native-readiness-v1',
        runtime_sha=subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
        runtime_sha256=digest.hexdigest(), source_repository='nlpdata/dream',
        source_pin='bb64644c209cb6497bb9e13244fbf220c900a740', source_sha256=SOURCE_SHA256,
        selection_policy='REUSE_EIGHT_PREVIOUS_SOURCE_AUDIT_EXPOSED_NOT_PROVIDER_CONSUMED_FAMILIES',
        source_exposure='PUBLIC_EXTERNALLY_AUTHORED_ALREADY_SOURCE_EXPOSED_NOT_FRESH',
        data_license='NON_COMMERCIAL_RESEARCH_ONLY_NO_RAW_CORPUS_REDISTRIBUTION',
        evidence_scope='ENTRYPOINT_TREATMENT_READINESS_ONLY_NOT_EXTERNAL_UTILITY_OR_NATIVE_SCORE',
        provider_calls=0, provider_spend_usd=0, gold_accessed_or_scored=False,
        treatment_present_cases=sum(r['specialized_treatment_present'] for r in rows),
        package_state='NOT_READY_NO_PAID_PACKAGE_OR_TRIGGER', rows=rows,
        longmemeval='SEALED_NOT_ACCESSED')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.source)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'rows'}))

"""Source-first development gate; no expert answer or specialized H treatment."""
import hashlib
import json
from pathlib import Path
from hcl.v1 import CognitionRequest, HCLCognitionLayer
from scripts.serious_eval_arms_v8 import prepare_primary_arms_v8, prepare_generic_final_v8
from scripts.serious_eval_contract import runtime_digest
from scripts.serious_eval_semantic_score import validate_manifest, load_rubric

SOURCE = Path('reports/HCL_I02_OBP_METAETHICS_DEVELOPMENT_SOURCE.json')
OBLIGATIONS = Path('reports/HCL_I02_OBP_METAETHICS_SOURCE_FIRST_OBLIGATIONS.json')
SOURCE_HASH = '268665309d08875af75ca4eceebdd9f367b474e0f86fdec27325af6476a4975e'
QUESTION_HASH = '11207a82743bc39bd399f6dae90f0003c751f8ec9ebd733fd4045bb2e8e15ab1'

SOURCE_FILE_HASH = '10d12d6cb623da330321b6dc897f8c38919fbd05570bf9f5f887085914504950'
OBLIGATIONS_FILE_HASH = '556553cc3065245283c7e3f5fc07adac60176d643e7deffebfff08d0e1b8ecc3'

def sha(text):
    return hashlib.sha256(text.encode()).hexdigest()

def audit():
    raw, rubric_raw = SOURCE.read_bytes(), OBLIGATIONS.read_bytes()
    if (hashlib.sha256(raw).hexdigest() != SOURCE_FILE_HASH or
            hashlib.sha256(rubric_raw).hexdigest() != OBLIGATIONS_FILE_HASH):
        raise ValueError('source-first package metadata or obligations drift')
    item, rubric = json.loads(raw), json.loads(rubric_raw)
    source, question, sid = item['source_text'], item['ordinary_question'], item['source_id']
    if (sha(source) != SOURCE_HASH or sha(question) != QUESTION_HASH or
            item['source_sha256'] != SOURCE_HASH or item['question_sha256'] != QUESTION_HASH or
            item['license'] != 'CC BY 4.0' or item['provider_input_allowed'] is not True or
            item['development_exposed'] is not True or
            item['independent_confirmation_qualified'] is not False or
            item['expert_gold_used'] or item['arm_outputs_seen'] or
            item['source_unit'] != 'COMPLETE_AUTHOR_ORIGINAL_SECTION_7_METAETHICS_AND_STEALING' or
            item['family'] != 'ABSTRACT_CONCEPT_PHILOSOPHY' or
            item['longmemeval'] != 'SEALED_NOT_ACCESSED'):
        raise ValueError('source, rights or exposure boundary drift')
    validate_manifest(rubric, load_rubric())
    if (rubric['case_id'] != sid or rubric['sources'] != [dict(source_id=sid, text=source)] or
            rubric['arm_output_seen'] is not False or len(rubric['obligations']) != 3):
        raise ValueError('source-first obligations drift')
    arms = prepare_primary_arms_v8(question, sid, source)
    expected = [dict(source_id=sid, text=source)]
    for phase in ('C', 'P', 'G_map'):
        payload = json.loads(arms[phase][-1]['content'])
        if payload['question'] != question or payload['sources'] != expected:
            raise ValueError('ordinary input inequality')
    mock = json.dumps(dict(source_index=[dict(id='e1',source_id=sid,
        quote=rubric['obligations'][0]['source_quotes'][0]['quote'])],
        relations=[],answer_plan=[],open_questions=[]))
    final = prepare_generic_final_v8(arms, mock)
    payload = json.loads(final[-1]['content'])
    if payload['question'] != question or payload['sources'] != expected:
        raise ValueError('G final original-source loss')
    h = HCLCognitionLayer(lambda _: '').prepare(CognitionRequest(question, narrative=source))
    hp = json.loads(h.messages[-1]['content'])
    if (hp['query'] != question or hp['narrative'] != source or
            not h.plan.direct or h.plan.capabilities or h.context is not None):
        raise ValueError('measured direct H boundary drift; never relabel as treatment')
    return dict(schema='hcl-i02-obp-metaethics-preflight-v1',
        source_file_sha256=hashlib.sha256(raw).hexdigest(),
        obligations_file_sha256=hashlib.sha256(rubric_raw).hexdigest(),
        source_sha256=SOURCE_HASH,question_sha256=QUESTION_HASH,
        source_valid=True,rights_verified_for_development=True,
        source_unit_not_whole_chapter=True, native_question_number=10,
        family_scope='ABSTRACT_CONCEPT_PHILOSOPHY_CALIBRATION_ONLY',
        difficulty_qualified=False, broader_comparator_semantics_qualified=False,
        source_first_obligation_count=3, full_ordinary_input_equal_for_cpg=True,
        g_final_original_source_present=True,h_runtime_sha256=runtime_digest(),
        h_direct=True,h_selected_capabilities=[],h_specialized_treatment_present=False,
        h_final_messages=h.messages,h_hnew_calls_allowed=False,
        cpg_model_semantics_qualified=False,independent_confirmation_qualified=False,
        provider_calls=0,provider_spend_usd=0,longmemeval='SEALED_NOT_ACCESSED')

if __name__ == '__main__':
    print(json.dumps(audit(),ensure_ascii=False,indent=2))

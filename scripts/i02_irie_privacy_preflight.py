"""Source-first development gate; no expert answer or specialized H treatment."""
import hashlib
import json
from pathlib import Path
from hcl.v1 import CognitionRequest, HCLCognitionLayer
from scripts.serious_eval_arms_v8 import prepare_primary_arms_v8, prepare_generic_final_v8
from scripts.serious_eval_contract import runtime_digest
from scripts.serious_eval_semantic_score import validate_manifest, load_rubric

SOURCE = Path('reports/HCL_I02_IRIE_PRIVACY_DEVELOPMENT_SOURCE.json')
OBLIGATIONS = Path('reports/HCL_I02_IRIE_PRIVACY_SOURCE_FIRST_OBLIGATIONS.json')
SOURCE_HASH = '84630476faa359a964021d4d4615a708627c1bbc052a92c3ac11e4c774330791'
QUESTION_HASH = '6930600c3c5dc2cdede17f2a8186620648482b82f90d1b548e303e3c8a1e4191'

def sha(text):
    return hashlib.sha256(text.encode()).hexdigest()

def audit():
    raw, rubric_raw = SOURCE.read_bytes(), OBLIGATIONS.read_bytes()
    item, rubric = json.loads(raw), json.loads(rubric_raw)
    source, question, sid = item['source_text'], item['ordinary_question'], item['source_id']
    if (sha(source) != SOURCE_HASH or sha(question) != QUESTION_HASH or
            item['source_sha256'] != SOURCE_HASH or item['question_sha256'] != QUESTION_HASH or
            item['license'] != 'CC BY 4.0' or item['provider_input_allowed'] is not True or
            item['development_exposed'] is not True or
            item['independent_confirmation_qualified'] is not False or
            item['expert_analysis_in_input'] or item['expert_analysis_displayed'] or
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
    return dict(schema='hcl-i02-irie-privacy-preflight-v1',
        source_file_sha256=hashlib.sha256(raw).hexdigest(),
        obligations_file_sha256=hashlib.sha256(rubric_raw).hexdigest(),
        source_sha256=SOURCE_HASH,question_sha256=QUESTION_HASH,
        source_valid=True,rights_verified_for_development=True,
        source_first_obligation_count=3, full_ordinary_input_equal_for_cpg=True,
        g_final_original_source_present=True,h_runtime_sha256=runtime_digest(),
        h_direct=True,h_selected_capabilities=[],h_specialized_treatment_present=False,
        h_final_messages=h.messages,h_hnew_calls_allowed=False,
        cpg_model_semantics_qualified=False,independent_confirmation_qualified=False,
        provider_calls=0,provider_spend_usd=0,longmemeval='SEALED_NOT_ACCESSED')

if __name__ == '__main__':
    print(json.dumps(audit(),ensure_ascii=False,indent=2))

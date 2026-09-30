"""Actual ordinary-source B01 report channel, ablation and revision correctness."""
import argparse,hashlib,json
from pathlib import Path
from hcl.v1 import HCLCognitionLayer,prepare_person_context
from hcl.v1.long_source_question import prepare_long_source_context
from hcl.v1.person_question import answer_person_context
from scripts.serious_eval_full_source_arms_v10 import prepare_primary_arms_v10
from scripts.serious_eval_contract import runtime_digest

def witness():
    source='Neutral authored development archive.\r\n'*650+'\r\n'+'\r\n\r\n'.join([
        'Mina does not believe that Jo believes the gate is safe.',
        'Mina said: "I believe the gate is safe."',
        'Jo heard the gate is safe.'])
    query='Which mental states are reported, by whom, and what remains unproved?'
    def prohibited(_):raise AssertionError('no provider in preparation witness')
    h=prepare_person_context(HCLCognitionLayer(prohibited),query,source)
    n=prepare_long_source_context(query,source,epistemic_checks=False)
    hp,np=(json.loads(p.messages[-1]['content']) for p in (h,n))
    checked=hp.pop('checked_epistemic');assert hp==np
    report=checked['epistemic_objects'][0]
    assert report['public_expression']['channel']=='SOURCE_NARRATOR_ATTRIBUTION'
    assert report['private_interpretation'] is None
    tree=report['public_expression']['expressed_content']
    assert tree['attitude']=='REPORTED_ATTRIBUTION' and tree['content']['polarity']=='DENY'
    assert tree['content']['content']['polarity']=='AFFIRM'
    assert hp['sources'][0]['text']==source
    arms=prepare_primary_arms_v10(query,'ordinary-source',source)
    for phase in ('C','P','G_map'):assert json.loads(arms[phase][-1]['content'])['sources'][0]['text']==source
    revised=prepare_person_context(HCLCognitionLayer(prohibited),query,source.replace('Mina does not believe','Mina believes'))
    revised_rows=json.loads(revised.messages[-1]['content'])['checked_epistemic']['epistemic_objects']
    assert revised_rows[0]['public_expression']['expressed_content']['content']['polarity']=='AFFIRM'
    assert revised_rows[2]['public_expression']['expressed_content']==checked['epistemic_objects'][2]['public_expression']['expressed_content']
    calls=[]
    smoke=answer_person_context(HCLCognitionLayer(lambda messages:calls.append(messages) or 'Authored correctness stub only.'),query,source,debug=True)
    assert len(calls)==1 and smoke.prepared.messages==h.messages
    sha=lambda v:hashlib.sha256(json.dumps(v,ensure_ascii=False,sort_keys=True).encode()).hexdigest()
    return dict(schema='hcl-i02-narrator-epistemic-v12-witness-v1',
        CAPABILITY_DELTA='Complete ordinary source now grounds standalone named narrator mental reports into existing B01 while keeping the source reporter separate from the subject own expression. Nested denial, knowledge/exposure/uncertainty, source-local identity and local correction remain scoped; no private/world truth or direct C03 belief premise is inferred.',
        origin='HCL_AUTHORED_SYNTHETIC_DEVELOPMENT_ONLY',runtime_sha256=runtime_digest(),
        source_sha256=hashlib.sha256(source.encode()).hexdigest(),source_characters=len(source),
        h_receipt=h.preparation_receipt,h_new_receipt=n.preparation_receipt,revision_receipt=revised.preparation_receipt,
        h_input_sha256=sha(h.messages),h_new_input_sha256=sha(n.messages),
        equal_complete_task_source_candidates=True,treatment_input_differs=h.messages!=n.messages,
        positive_witness='NARRATOR_ATTRIBUTION_VS_SUBJECT_EXPRESSION_WITH_OUTER_DENIAL',
        positive_revision='REPORTED_POLARITY_CHANGES_UNRELATED_EXPOSURE_PRESERVED',
        smoke_stub_calls=1,extraction_provider_calls=0,provider_calls=0,provider_spend_usd=0,
        answer_gain_established=False,independent_confirmation_qualified=False,
        longmemeval='SEALED_NOT_ACCESSED')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);a=p.parse_args()
    Path(a.output).write_text(json.dumps(witness(),ensure_ascii=False,indent=2)+'\n')
    print('B01_NARRATOR_REPORT_ACTUAL_H_ABLATION_REVISION_PROVIDER_FREE')

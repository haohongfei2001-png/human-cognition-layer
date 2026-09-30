"""Protected native-choice ordinary entry; options are tasks, never source facts.

No provider calls, source/question display, native-answer scoring or automatic
source qualification. A real candidate still needs independent task/rights review.
"""
import argparse
import hashlib
import json
from pathlib import Path
from hcl.v1 import CognitionRequest,HCLCognitionLayer
from scripts.serious_eval_arms_v8 import prepare_primary_arms_v8,prepare_generic_final_v8
from scripts.serious_eval_contract import runtime_digest
from scripts.i02_exposure_history import audit_history

PIN='aefef5b6beb7097370cf3bc0c6503ed8caa495530297a4b184c4c31002e23169'
PUBLISHER_COMMIT='4f491f0784ed31ef93a8837615fbc48f885cf78d'
SOURCE_ID='tombench-persuasion-first-native-en-protected'

def sha(value):
    return hashlib.sha256(value.encode()).hexdigest()

def ordinary_choice(source,question,alternatives):
    """Preserve native question and every option without asserting any option."""
    if (not isinstance(source,str) or not source.strip() or
            not isinstance(question,str) or not question.strip() or
            not isinstance(alternatives,dict) or tuple(alternatives)!=('A','B','C','D') or
            any(not isinstance(v,str) or not v.strip() for v in alternatives.values())):
        raise ValueError('complete ordinary native-choice input required')
    return dict(source_text=source,question=question+'\n\n'+
        '\n'.join(k+'. '+v for k,v in alternatives.items()))

def protected_native_row(raw):
    if not isinstance(raw,bytes) or hashlib.sha256(raw).hexdigest()!=PIN:
        raise ValueError('pinned publisher file mismatch')
    rows=[json.loads(line) for line in raw.splitlines() if line.strip()]
    if len(rows)!=100:
        raise ValueError('publisher inventory drift')
    row=rows[0]
    # Native label, Chinese duplicate and ability metadata never enter any arm.
    return ordinary_choice(row['STORY'],row['QUESTION'],
        {k:row['OPTION-'+k] for k in ('A','B','C','D')})

def inspect_ordinary(task,source_id):
    source,question=task['source_text'],task['question']
    arms=prepare_primary_arms_v8(question,source_id,source)
    expected=[dict(source_id=source_id,text=source)]
    for phase in ('C','P','G_map'):
        p=json.loads(arms[phase][-1]['content'])
        if p['sources']!=expected or p['question']!=question:
            raise ValueError('ordinary native input inequality')
    # Source quote is only a provider-free map-interface witness, never an answer.
    mock=json.dumps(dict(source_index=[dict(id='e1',source_id=source_id,quote=source)],
        relations=[],answer_plan=[],open_questions=[]))
    final=prepare_generic_final_v8(arms,mock)
    payload=json.loads(final[-1]['content'])
    if payload['sources']!=expected or payload['question']!=question:
        raise ValueError('G final source/options loss')
    h=HCLCognitionLayer(lambda _: '').prepare(CognitionRequest(question,narrative=source))
    hp=json.loads(h.messages[-1]['content'])
    def contains(value,target):
        if isinstance(value,str):
            return target in value
        if isinstance(value,dict):
            return any(contains(v,target) for v in value.values())
        if isinstance(value,list):
            return any(contains(v,target) for v in value)
        return False
    source_present=contains(hp,source)
    question_present=contains(hp,question)
    return dict(source_sha256=sha(source),question_with_options_sha256=sha(question),
        source_characters=len(source),question_with_options_characters=len(question),
        cpg_ordinary_input_equality=True,h_source_complete=source_present,
        h_question_complete=question_present,options_in_question_only=True,
        native_label_in_input=False,ability_metadata_in_input=False,
        h_direct=h.plan.direct,h_selected_capabilities=list(h.plan.capabilities),
        h_context_present=h.context is not None,
        h_final_messages_sha256=sha(json.dumps(h.messages,ensure_ascii=False,sort_keys=True)),
        h_runtime_sha256=runtime_digest())

def audit(raw,repository):
    task=protected_native_row(raw)
    entry=inspect_ordinary(task,SOURCE_ID)
    history=audit_history(repository,task['source_text'])
    return dict(schema='hcl-i02-protected-native-choice-candidate-v1',
        publisher_commit=PUBLISHER_COMMIT,publisher_file='data/Persuasion Story Task.jsonl',
        publisher_file_sha256=PIN,selection='FIRST_FILE_ROW_ENGLISH_NO_SEMANTIC_OR_LABEL_SELECTION',
        writing_system_id='tombench-original-bilingual-social-scenarios',
        author_id='zhuang-chen-tombench-author-team',template_id='tombench-native-four-option-v1',
        source_id=SOURCE_ID,inventory_rows=100,entry=entry,history=history,
        source_text_displayed=False,question_or_options_displayed=False,native_labels_displayed=False,
        source_text_processed_for_fingerprints_and_entry=True,
        candidate_status='DEVELOPMENT_ENTRY_PROBE_NOT_CONFIRMATION'
        ,development_use='USED_FOR_GENERIC_SOURCE_ENTRY_REPAIR_DESPITE_UNDISPLAYED_TEXT',
        rights_state='PUBLISHER_MIT_AND_EVALUATION_ONLY_NOTICE_ITEM_REVIEW_PENDING',
        task_fit='PENDING_SOURCE_FIRST_REVIEW_NOT_INFERRED_FROM_TASK_NAME',
        privacy_state='PENDING_ITEM_FICTIONALITY_REVIEW',
        model_input_allowed=False,confirmation_qualified=False,
        model_training_exposure='UNKNOWN_PUBLIC_2024_MATERIAL_NOT_FRESHNESS_PROOF',
        provider_calls=0,provider_spend_usd=0,longmemeval='SEALED_NOT_ACCESSED')

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--input',required=True)
    parser.add_argument('--repository',required=True)
    parser.add_argument('--output',required=True)
    args=parser.parse_args()
    Path(args.output).write_text(json.dumps(audit(Path(args.input).read_bytes(),args.repository),
        ensure_ascii=False,indent=2)+'\n')
    print('PROTECTED_METADATA_WRITTEN_NO_TEXT_LABEL_OR_SEMANTIC_QUALIFICATION')

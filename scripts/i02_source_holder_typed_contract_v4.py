"""Future typed auditor prompt contract; strict v3 receiver and consumed runs stay unchanged.

The actual v3 long fixture completed JSON and source references, but all five
expectation fields were prose rather than categorical enum values. This adds a
machine-readable output contract; it never normalizes old answers into passes.
No transport, grant, semantic judge or independent evidence is provided here.
"""
from copy import deepcopy
import json
from scripts.i02_source_holder_line_index_v3 import messages as messages_v3, resolve_review

STR=dict(type='string',minLength=1)
LINE=dict(type='integer',minimum=1)
HASH=dict(type='string',pattern='^[0-9a-f]{64}$')

def row(properties):
    return dict(type='object',properties=properties,required=list(properties),additionalProperties=False)

CONTRACT=row(dict(
    source_id=STR,source_sha256=HASH,question_sha256=HASH,
    family_judgment=dict(type='string',enum=['PASS','REJECT','UNRESOLVED']),
    answerability_judgment=dict(type='string',enum=['PASS','REJECT','UNRESOLVED']),
    episodes=dict(type='array',maxItems=8,items=row(dict(id=STR,start_line=LINE,end_line=LINE,
        evidence_kind=dict(type='string',enum=['NARRATOR_REPORT','REPORTED_SPEECH','INFERENCE_OR_UNCERTAIN','EXPLICIT_EVENT']),
        time_basis=dict(type='string',enum=['SOURCE_ORDER_ONLY','EXPLICIT_STORY_TIME','UNRESOLVED']),analysis=STR))),
    obligations=dict(type='array',minItems=3,maxItems=6,items=row(dict(id=STR,
        expectation=dict(type='string',enum=['STATE','QUALIFY','AVOID']),start_line=LINE,end_line=LINE,audit_question=STR))),
    serious_unsupported_upgrades=dict(type='array',minItems=1,items=STR),
    unresolved_limits=dict(type='array',items=STR),judge_limits=STR))

CLARIFICATION='''The supplied output_contract describes your response shape; do not echo the schema or add output_contract to the response. Every expectation field is a categorical enum, exactly one uppercase string: STATE, QUALIFY, or AVOID. Never put a sentence, explanation or paraphrase in expectation. Put the natural-language obligation in audit_question, and explanations in analysis/judge_limits. Across obligations include all three expectation categories. Copy source_id/source_sha256/question_sha256 exactly from the input; line references are existing integer line numbers, not strings or invented text. The local strict receiver still verifies ranges, hashes, coverage and uncertainty; the schema is prompt metadata, not server-enforced structured output or semantic truth. '''


def output_contract():return deepcopy(CONTRACT)

def messages(question,source_id,source):
    prepared=messages_v3(question,source_id,source)
    prepared[0]=dict(role='system',content=CLARIFICATION+prepared[0]['content'])
    payload=json.loads(prepared[-1]['content']);payload['output_contract']=output_contract()
    prepared[-1]=dict(role='user',content=json.dumps(payload,ensure_ascii=False))
    return prepared

def resolve_review_v4(review,question,source_id,source,index):
    # No repair/mapping of actual invalid enum strings. The consumed v3 receiver
    # remains the exact authority; only future request instructions are clearer.
    return resolve_review(review,question,source_id,source,index)

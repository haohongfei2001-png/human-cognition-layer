"""Provider-free source-holder reference interface; no paid transport or semantic judge.

Resolve model-selected line ranges locally instead of making it reproduce exact
source strings. All original bytes remain in the reviewer view. Line order is
source order only; the checker cannot establish story time, motive or truth.
Consumed v1/v2 requests, source questions, receipts and budgets never migrate.
"""
import hashlib
import json

MAX_SOURCE_BYTES = 500_000
KINDS = {'NARRATOR_REPORT', 'REPORTED_SPEECH', 'INFERENCE_OR_UNCERTAIN', 'EXPLICIT_EVENT'}
TIMES = {'SOURCE_ORDER_ONLY', 'EXPLICIT_STORY_TIME', 'UNRESOLVED'}

def sha(source):
    return hashlib.sha256(source.encode()).hexdigest()

def index_source(source_id, source):
    if (not isinstance(source_id, str) or not source_id.strip() or
            not isinstance(source, str) or not source.strip() or
            len(source.encode()) > MAX_SOURCE_BYTES):
        raise ValueError('complete identified bounded source required; never truncate')
    records=[]; offset=0
    for number,text in enumerate(source.splitlines(keepends=True),1):
        records.append(dict(line=number,text=text,start=offset,end=offset+len(text)))
        offset+=len(text)
    assert ''.join(row['text'] for row in records)==source
    return dict(schema='hcl-i02-complete-source-line-index-v3',source_id=source_id,
                source_sha256=sha(source),records=records)

def reviewer_payload(question,index):
    if not isinstance(question,str) or not question.strip():
        raise ValueError('ordinary question required')
    source=''.join(row['text'] for row in index['records'])
    if index!=index_source(index['source_id'],source):
        raise ValueError('source index drift')
    return dict(question=question,question_sha256=sha(question),sources=[dict(source_id=index['source_id'],source_sha256=index['source_sha256'],
        lines=[dict(line=row['line'],text=row['text']) for row in index['records']])])

def resolve_review(review,question,source_id,source,index):
    if index!=index_source(source_id,source):
        raise ValueError('current complete source identity/hash/index drift')
    fields={'source_id','source_sha256','question_sha256','family_judgment','answerability_judgment',
            'episodes','obligations','serious_unsupported_upgrades','unresolved_limits','judge_limits'}
    if (not isinstance(review,dict) or set(review)!=fields or
            review['source_id']!=source_id or review['source_sha256']!=sha(source) or
            not isinstance(question,str) or not question.strip() or review['question_sha256']!=sha(question) or
            any(review[k] not in {'PASS','REJECT','UNRESOLVED'} for k in ('family_judgment','answerability_judgment'))):
        raise ValueError('complete source-bound review required')
    if (not isinstance(review['episodes'],list) or len(review['episodes'])>8 or
            (review['family_judgment']=='PASS' and len(review['episodes'])<3) or
            not isinstance(review['obligations'],list) or not 3<=len(review['obligations'])<=6):
        raise ValueError('source-led episode/obligation coverage required')
    ids=set()
    def anchor(row,keys):
        if not isinstance(row,dict) or set(row)!=keys:
            raise ValueError('range-reference row shape mismatch')
        a,z=row['start_line'],row['end_line']
        if (type(a) is not int or type(z) is not int or not 1<=a<=z<=len(index['records']) or
                any(not isinstance(row[k],str) or not row[k].strip() for k in keys-{'start_line','end_line'}) or
                row['id'] in ids):
            raise ValueError('identified existing line range required')
        ids.add(row['id']);begin=index['records'][a-1]['start'];end=index['records'][z-1]['end']
        quote=source[begin:end].strip()
        if not 1<=len(quote)<=500:
            raise ValueError('bounded nonempty exact source anchor required')
        return dict(row,quote=quote,source_start=begin,source_end=end)
    episodes=[];positions=[]
    for row in review['episodes']:
        got=anchor(row,{'id','start_line','end_line','evidence_kind','time_basis','analysis'})
        if row['evidence_kind'] not in KINDS or row['time_basis'] not in TIMES:
            raise ValueError('source/time categories required; no automatic chronology')
        episodes.append(got);positions.append(got['source_start'])
    if positions!=sorted(set(positions)):
        raise ValueError('distinct episode source order required')
    obligations=[anchor(row,{'id','expectation','start_line','end_line','audit_question'}) for row in review['obligations']]
    if {row['expectation'] for row in obligations}!={'STATE','QUALIFY','AVOID'}:
        raise ValueError('supported content, uncertainty and unsupported inference boundaries required')
    for key in ('serious_unsupported_upgrades','unresolved_limits'):
        if not isinstance(review[key],list) or any(not isinstance(x,str) or not x.strip() for x in review[key]):
            raise ValueError('reasoned limits/errors required')
    if not review['serious_unsupported_upgrades'] or not isinstance(review['judge_limits'],str) or not review['judge_limits'].strip():
        raise ValueError('critical errors and judge limits required')
    return dict(schema='hcl-i02-source-holder-resolved-ranges-v3',episodes=episodes,obligations=obligations,
        source_sha256=sha(source),question_sha256=sha(question),source_order_verified=True,story_time_verified=False,
        semantic_truth_verified=False,actor_or_motive_semantics_verified=False,
        confirmation_qualified=False,provider_calls_authorized=0,provider_spend_authorized_usd=0,
        consumed_package_migration=False,live_capacity_verified=False)


INSTRUCTION = """Audit only the complete source and fixed ordinary question. No arm answer, architecture, reference answer, hidden mental state or gold is supplied. Return one JSON object with exactly source_id, source_sha256, question_sha256, family_judgment, answerability_judgment, episodes, obligations, serious_unsupported_upgrades, unresolved_limits, judge_limits. Copy the source identity/hash and fixed-question hash from the input. Judgments are PASS, REJECT or UNRESOLVED; they remain preliminary automated judgments.
For PASS family_judgment, give 3-8 distinct source-supported episodes in source order; each has exactly id, start_line, end_line, evidence_kind, time_basis, analysis. Select existing integer line ranges totaling at most 500 characters. Refer to provided line numbers instead of reproducing source quotes or counting character offsets. evidence_kind: NARRATOR_REPORT, REPORTED_SPEECH, INFERENCE_OR_UNCERTAIN or EXPLICIT_EVENT; time_basis: SOURCE_ORDER_ONLY, EXPLICIT_STORY_TIME or UNRESOLVED. Source order does not prove story chronology. Preserve report, event, interpretation, counterfactual and unsupported motive distinctions. Do not infer private intention, diagnosis or moral truth.
Give 3-6 pre-output source-led obligations, each with exactly id, expectation, start_line, end_line, audit_question; include STATE, QUALIFY and AVOID. All ids must be globally unique. serious_unsupported_upgrades and unresolved_limits are string arrays; judge_limits is a nonempty string explaining reviewer limits. Do not change the question, invent support, assess difficulty/baseline saturation or a system's benefit. A structural resolver reconstructs exact source passages; it cannot certify semantic truth, independence or complete claim coverage."""

def messages(question,source_id,source):
    return [dict(role='system',content=INSTRUCTION),dict(role='user',content=json.dumps(
        reviewer_payload(question,index_source(source_id,source)),ensure_ascii=False))]
